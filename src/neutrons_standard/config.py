"""Application configuration management."""

import copy
import importlib.resources as resources
import logging
import os
import re
import shutil
import subprocess
import sys
from enum import StrEnum
from importlib import metadata
from pathlib import Path
from typing import IO, Any, Dict, TypeVar

import yaml
from ruamel.yaml import YAML as rYAML  # noqa: N811

from neutrons_standard import Spec
from neutrons_standard.decorators.singleton import Singleton
from neutrons_standard.time import isoFromTimestamp, timestamp


class DeployEnvEnum(StrEnum):
    """Deployment environment enumeration."""

    NEXT = "next"
    QA = "qa"
    PROD = "prod"

    def envName(self) -> str:
        """Get the client's environment name for this deployment, e.g. `<package>_next`."""
        return f"{Spec.client_package_name}_{self.value}"


def isTestEnv() -> bool:
    """
    Check if the current environment is a test environment.

    This is determined by the presence of the "env" environment variable
    and whether it contains the string "test".
    """
    env = os.environ.get("env")
    return env and "test" in env and "conftest" in sys.modules


def _find_root_dir() -> str:
    """Find the root directory of the client module."""
    package_name = Spec.client_package_name
    try:
        MODULE_ROOT = Path(sys.modules[package_name].__file__).parent

        # Using `"test" in env` here allows different versions of "[category]_test.yml" to be used for different
        #  test categories: e.g. unit tests use "test.yml" but integration tests use "integration_test.yml".
        if isTestEnv():
            # WARNING: there are now multiple "conftest.py" at various levels in the test hierarchy.
            MODULE_ROOT = MODULE_ROOT.parent.parent / "tests"
    except Exception as e:
        raise RuntimeError(f"Unable to determine {package_name} module-root directory") from e

    return str(MODULE_ROOT)


# update config with self._config, deep_update does not work with ruamel.yaml
def merge_dicts(d1: Dict[str, Any], d2: Dict[str, Any]) -> Dict[str, Any]:
    """Merge two dictionaries with d2 overwriting values in d1."""
    for key, value in d2.items():
        if isinstance(value, dict) and key in d1:
            merge_dicts(d1[key], value)
        else:
            d1[key] = value
    return d1


# `~user` values whose user doesn't exist, so the warning is logged once rather than on every read
_unknownHomes: set[str] = set()


def _expandHome(value: Any) -> Any:
    """Expand a leading `~` or `~user` in a string value to that user's home directory."""
    if not isinstance(value, str) or not re.match(r"~[^/]*(/|$)", value):
        return value
    expanded = os.path.expanduser(value)
    # `expanduser` returns the value unchanged when the user's home directory can't be found
    if expanded == value and value not in _unknownHomes:
        _unknownHomes.add(value)
        user = value[1:].split("/", 1)[0]
        logging.getLogger(__name__ + ".Config").warning(
            f"Unable to expand '{value}': no home directory found for user '{user}'. The value is used as written"
        )
    return expanded


@Singleton
class _Resource:
    """Resource manager for loading application resources."""

    _package_mode: bool
    _resources_path: str
    _logger = logging.getLogger(__name__ + ".Resource")

    def __init__(self) -> None:
        """Initialize the resource manager."""
        # where the location of resources are depends on whether or not this is in package mode
        self._package_mode = not self._existsInPackage("application.yml")
        if self._package_mode:
            self._logger.debug("In package mode")
            self._resources_path = "/resources/"
        else:
            self._logger.debug("Not in package mode")
            self._resources_path = os.path.join(_find_root_dir(), "resources/")

    def _existsInPackage(self, sub_path: str) -> bool:
        """Check if a resource exists in the package."""
        with resources.path(f"{Spec.client_package_name}.resources", sub_path) as path:
            return os.path.exists(path)

    def exists(self, sub_path: str) -> bool:
        """Check if a resource exists."""
        if self._package_mode:
            return self._existsInPackage(sub_path)
        else:
            return os.path.exists(self.getPath(sub_path))

    def getPath(self, sub_path: str) -> str:
        """Get the path to a resource."""
        if sub_path.startswith("/"):
            return os.path.join(self._resources_path, sub_path[1:])
        else:
            return os.path.join(self._resources_path, sub_path)

    def read(self, sub_path: str) -> str:
        """Read a resource file."""
        with self.open(sub_path, "r") as file:
            return file.read()

    def open(self, sub_path: str, mode: str) -> IO[Any]:
        """Open a resource file."""
        if self._package_mode:
            with resources.path(f"{Spec.client_package_name}.resources", sub_path) as path:
                return open(path, mode)
        else:
            return open(self.getPath(sub_path), mode)


Resource = _Resource()

KeyType = TypeVar("KeyType")


def deep_update(mapping: Dict[KeyType, Any], *updating_mappings: Dict[KeyType, Any]) -> Dict[KeyType, Any]:
    """Crawl through initial dictionary while appending and updating entries in nested dicts."""
    updated_mapping = mapping.copy()
    for updating_mapping in updating_mappings:
        for k, v in updating_mapping.items():
            if k in updated_mapping and isinstance(updated_mapping[k], dict) and isinstance(v, dict):
                updated_mapping[k] = deep_update(updated_mapping[k], v)
            else:
                updated_mapping[k] = v
    return updated_mapping


@Singleton
class _Config:
    _config: Dict[str, Any] = {}
    _logger = logging.getLogger(__name__ + ".Config")
    _property_change_warnings: Dict[str, str] = {}
    _default_env: str = "application.yml"
    # the default number of archived `-user.yml` files to keep, if `application.userYmlArchiveLimit` isn't set
    _user_yml_archive_limit: int = 5

    def __init__(self) -> None:
        self._property_change_warnings = {
            "version.start": (
                "It is NOT ADVISED to change the `version.start` property"
                " WITHOUT CAREFUL CONSIDERATION of the file indexes on disk."
            ),
        }

        self.reload()
        # if -user.yml exists, then load it by default
        if self.shouldSwapToUserYml():
            self._logger.info("Found user configuration file, swapping to it")
            self.swapToUserYml()

    def shouldSwapToUserYml(self) -> bool:
        """Check if the app should use a user config."""
        isExplicitEnv = "env" in os.environ
        isUserYmlExists = (self._userHome() / f"{Spec.client_package_name}-user.yml").exists()
        return isUserYmlExists and not isExplicitEnv and not isTestEnv()

    def configureForDeploy(self) -> None:
        version = self.packageVersion()
        if "dev" in version:
            self.mergeAndExport(DeployEnvEnum.NEXT.envName())
        elif "rc" in version:
            self.mergeAndExport(DeployEnvEnum.QA.envName())
        else:
            self.mergeAndExport(DeployEnvEnum.PROD.envName())

    def mergeAndExport(self, envName: str) -> None:
        """Merge/export the current configuration with the specified environment configuration."""
        self._logger.debug(f"Merging/exporting configuration with environment: {envName}")
        self.refresh(envName, False)

        ryaml = rYAML()
        ryaml.default_flow_style = False
        ryaml.indent(mapping=2, sequence=4, offset=2)

        with Resource.open(self._default_env, "r") as file:
            config = ryaml.load(file)

        # overwrite default env application.yml with exported config
        merge_dicts(config, self._config)

        # Export the merged configuration to application.yml
        with Resource.open(self._default_env, "w") as file:
            ryaml.dump(config, file)

    def reload(self, env_name: str = None) -> None:
        # use refresh to do initial load, clearing shouldn't matter
        self.refresh(self._default_env, True)

        # ---------- internal values: --------------------------
        # allow "resources" relative paths to be entered into the "yml"
        #   using "${module.root}"
        self._config["module"] = {}
        self._config["module"]["root"] = _find_root_dir()

        self._config["version"] = self._config.get("version", {})
        self._config["version"]["default"] = -1

        # ---------- end: internal values: -----------------------------

        watchedProperties = {}
        for key in self._property_change_warnings:
            if self.exists(key):
                watchedProperties[key] = self[key]

        # see if user used environment injection to modify what is needed
        # this will get from the os environment or from the currently loaded one
        # first case wins
        self.env = env_name
        if self.env is None:
            self.env = os.environ.get("env", self._config.get("environment", None))
        if self.env is not None:
            self._logger.info(f"Loading environment config: {self.env}")
            self.refresh(self.env)
        else:
            self._logger.info("No environment config specified, using default")
        self.warnSensitiveProperties(watchedProperties)
        self.persistBackup()

    def persistBackup(self) -> None:
        self._userHome().mkdir(parents=True, exist_ok=True)
        backupFile = self._userHome() / "application.yml.bak"
        with open(backupFile, "w") as file:
            yaml.dump(self._config, file, default_flow_style=False)
        self._logger.info(f"Backup of application.yml created at {backupFile.absolute()}")

    def loadEnv(self, env_name: str) -> None:
        # load the new environment
        self.reload(env_name)

    @staticmethod
    def _timestamp() -> str:
        return isoFromTimestamp(timestamp())

    def archiveUserYml(self) -> None:
        """Archive the user config for safe keeping."""
        # check if -user.yml exists
        userHome = self._userHome()
        if (userHome / f"{Spec.client_package_name}-user.yml").exists():
            version = self.getUserYmlVersionDisk()

            # generate human readable timestamp
            timestamp = self._timestamp()

            # archive the old -user.yml
            archivePath = userHome / f"{Spec.client_package_name}-user-{version}-{timestamp}.yml.bak"
            shutil.copy(str(userHome / f"{Spec.client_package_name}-user.yml"), str(archivePath))
            self._pruneUserYmlArchives()

    def _userYmlArchiveLimit(self) -> int | None:
        """The number of archived user configs to keep: None keeps all of them."""
        application = self._config.get("application")
        limit = application.get("userYmlArchiveLimit") if isinstance(application, dict) else None
        if limit is None:
            return self._user_yml_archive_limit
        if limit == -1:
            return None
        # a YAML boolean is a Python `int`: it is not a number of archives
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 0:
            self._logger.warning(
                f"Invalid `application.userYmlArchiveLimit: {limit!r}`: it must be a number of archives, or -1 for "
                f"no limit. Keeping {self._user_yml_archive_limit} archives"
            )
            return self._user_yml_archive_limit
        return limit

    def _pruneUserYmlArchives(self) -> None:
        """Delete all but the newest `application.userYmlArchiveLimit` archived user configs."""
        limit = self._userYmlArchiveLimit()
        if limit is None:
            return
        archives = sorted(
            self._userHome().glob(f"{Spec.client_package_name}-user-*.yml.bak"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        for archive in archives[limit:]:
            self._logger.debug(f"Removing old user configuration archive: {archive}")
            archive.unlink()

    @classmethod
    def _userHome(cls) -> Path:
        """The directory of the user's config, archives and backup: `~/.config/<package>`."""
        userHome = Path.home() / ".config" / Spec.client_package_name
        # older releases used `~/.<package>`: its files are moved once, so the user's config keeps being used
        legacyHome = Path.home() / f".{Spec.client_package_name}"
        if not userHome.exists() and legacyHome.is_dir():
            try:
                userHome.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(legacyHome), str(userHome))
            except OSError as e:
                cls._logger.warning(f"Unable to move the user configuration from {legacyHome} to {userHome}: {e}")
                return legacyHome
            cls._logger.warning(f"Moved the user configuration from {legacyHome} to {userHome}")
        return userHome

    ###################################################################################
    ### Versioning methods

    def _getVersionFromMetadata(self) -> str:
        version = None
        try:
            version = metadata.version(Spec.client_package_name)
        except metadata.PackageNotFoundError:
            version = None
        if version:
            return version

    def _getVersionFromGit(self) -> str:
        version = None
        try:
            version = (
                subprocess.check_output(
                    ["git", "rev-parse", "HEAD"],
                    cwd=Path(sys.modules[Spec.client_package_name].__file__).parent,
                    stderr=subprocess.DEVNULL,
                )
                .strip()
                .decode("utf-8")
            )
        except (OSError, subprocess.CalledProcessError):
            pass
        return version

    def _raiseNoVersionError(self):
        raise ValueError(
            f"The {Spec.client_package_name} Version is not set correctly. "
            f"Please ensure that the {Spec.client_package_name} package is installed correctly."
        )

    def packageVersion(self) -> str:
        """Get the version of the client package."""
        versionSources = [self._getVersionFromMetadata, self._getVersionFromGit, self._raiseNoVersionError]
        version = None

        for versionSource in versionSources:
            version = versionSource()
            if version:
                break

        return version

    ###################################################################################

    def getUserYmlVersionDisk(self) -> str | None:
        """Get the associated app version the user config was generated with."""
        # check if -user.yml exists
        userHome = self._userHome()
        if (userHome / f"{Spec.client_package_name}-user.yml").exists():
            with open(str(userHome / f"{Spec.client_package_name}-user.yml"), "r") as f:
                applicationYml = rYAML(typ="safe").load(f)
            version = applicationYml.get("application", {"version": None})["version"]
            return version
        else:
            return None

    def swapToUserYml(self) -> None:
        """Swap to user generated config."""
        # generate root directory for user configurations
        userHome = self._userHome()

        try:
            if not userHome.exists():
                userHome.mkdir(parents=True, exist_ok=True)

            # check if -user.yml exists
            if self.getUserYmlVersionDisk() != self.packageVersion():
                # if the version is not the same, then we need to archive the old one
                if self.getUserYmlVersionDisk() is not None:
                    self._logger.warning(
                        "The user configuration file is out of date. A new configuration file will be generated."
                    )
                # archive the old -user.yml
                self.archiveUserYml()
                # generate a new valid -user.yml
                self._generateUserYml()

        except Exception as e:  # noqa: BLE001
            raise RuntimeError(
                (
                    "Unable to swap to user configuration: "
                    f"{userHome / f'{Spec.client_package_name}-user.yml'}"
                    "\nOriginal configuration maintained."
                )
            ) from e
        else:
            # load the user yml file if the filesystem is ready
            self.loadEnv(str(userHome / f"{Spec.client_package_name}-user.yml"))

    def _generateUserYml(self) -> None:
        """Generate a default application config in the user's home dir."""
        userHome = self._userHome()
        # copy commented out application.yml as -user.yml
        # read the application.yml as a dict from resources
        applicationYml = None
        with Resource.open("application.yml", "r") as f:
            applicationYml = rYAML(typ="safe").load(f)

        if applicationYml.get("application") is None:
            applicationYml["application"] = {}
        applicationYml["application"]["version"] = self.packageVersion()
        applicationYml["environment"] = f"{Spec.client_package_name}-user"

        # convert the dict back to a yaml string
        applicationYmlStr = yaml.dump(applicationYml, default_flow_style=False)

        # write the application.yml to the user home as -user.yml
        with open(userHome / f"{Spec.client_package_name}-user.yml", "w") as f:
            f.write(applicationYmlStr)

    def getCurrentEnv(self) -> str:
        if self.env is not None:
            return self.env
        else:
            # this is the default environment
            return "default"

    def refresh(self, env_name: str, clearPrevious: bool = False) -> None:
        """Load and refresh configuration from environment files."""
        # save a copy of previous config if it fails to load
        prevConfig = copy.deepcopy(self._config)

        try:
            if clearPrevious:
                self._config.clear()

            if env_name.endswith(".yml"):
                # name to be put into config
                new_env_name = env_name

                # this is a filename that should be loaded
                filepath = Path(env_name)
                if filepath.exists():
                    self._logger.debug(f"Loading config from {filepath.absolute()}")
                    with open(filepath, "r") as file:
                        envConfig = rYAML(typ="safe").load(file)
                else:
                    # load from the resource
                    with Resource.open(env_name, "r") as file:
                        envConfig = rYAML(typ="safe").load(file)
                    new_env_name = env_name.replace(".yml", "")
                # update the configuration with the  new environment
                self._config = merge_dicts(self._config, envConfig)

                # add the name to the config object if it wasn't specified
                if "environment" not in envConfig:
                    self._config["environment"] = new_env_name
            else:
                # recurse this function with a fuller name
                self.refresh(f"{env_name}.yml", clearPrevious)
        except Exception:
            # if it fails, restore the previous config
            self._logger.warning(f"Failed to load {env_name}.yml, restoring previous config")
            self._config = prevConfig
            raise

    def warnSensitiveProperties(self, watchedProperties: dict[str, Any]) -> None:
        for key in watchedProperties:
            msg = self._property_change_warnings[key]
            if watchedProperties[key] != self[key]:
                warningBar = ("/" * 20) + " WARNING " + ("/" * 20)
                self._logger.warning(warningBar)
                self._logger.warning(f"Property '{key}' was changed in {self.env}.yml")
                self._logger.warning(msg)
                self._logger.warning(warningBar)

    # method to regex for string pattern of ${key} and replace with value
    def _replace(self, value: str, remainingKeys: list[str]) -> str:
        # if the value is not a string, then just return it
        if not isinstance(value, str):
            return value

        # Regex all keys of the form ${key.subkey} and store in a list
        regex = r"\$\{([a-zA-Z0-9_\.]+)\}"
        matches = [match for match in re.finditer(regex, value, re.MULTILINE)]
        # replace all keys with their values
        if len(remainingKeys) == 0:
            for match in matches:
                key = match.group()[2:-1]
                if isinstance(self[key], dict):
                    return value
                value = value.replace(f"${{{key}}}", self[key])
        else:
            match = matches[0]
            rootKey = match.group()[2:-1]
            key = rootKey
            val = self[key]

            # while val is a dict, keep appending keys
            while isinstance(val, dict):
                key = key + f".{remainingKeys.pop(0)}"
                val = self[key]

            value = value.replace(f"${{{rootKey}}}", val)
            # if(len(remainingKeys) > 0):
            value = self._replace(value, remainingKeys)

        return value

    def exists(self, key: str) -> bool:
        val = self._find(key)
        return val is not None

    def _find(self, key: str) -> Any:
        keys = key.split(".")
        val = self._config.get(keys[0])
        totalProcessed = 0
        for k in keys[1:]:
            if val is None:
                break
            if isinstance(val, str):
                break
            totalProcessed += 1
            val = val.get(k)

        if val is not None:
            val = self._replace(val, keys[1 + totalProcessed :])
        return val

    # period delimited key lookup
    def __getitem__(self, key: str) -> Any:
        """Lookup config value via . delimited key."""
        val = self._find(key)
        if val is None:
            raise KeyError(f"Key '{key}' not found in configuration")
        if isinstance(val, dict):
            # we need to solve the keys present in dict members
            # we can accomplish this by recursively calling __getitem__
            return {k: self[f"{key}.{k}"] for k in val}
        return _expandHome(val)

    def validate(self) -> None:
        """Validate for conflicting property values."""
        pass


Config = _Config()
