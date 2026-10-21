import logging
import os
import shutil
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

##
## In order to preserve the normal import order as much as possible,
##   place test-specific imports last.
##
from unittest import mock

import pytest
from ruamel.yaml import YAML as rYaml

import neutrons_standard.config as Config_module
from neutrons_standard import Spec
from neutrons_standard.config import (
    Config,
    DeployEnvEnum,
    Resource,
    _find_root_dir,
)

package_name = Spec.client_package_name


def test_environment():
    assert Config["environment"] == "test"


def test_find_root_dir_test_env():
    # Test that a test environment's `MODULE_ROOT` is set to the `tests` directory.
    assert _find_root_dir().endswith("/tests")


def test_version_default():
    # Test that Config["version.default"] is implicitly set
    assert isinstance(Config["version.default"], int)


@mock.patch.dict(os.environ, values={"env": "dev"}, clear=True)
def test_find_root_dir_non_test_env():
    # Test that a non-test environment's `MODULE_ROOT` is set to the package_name module directory
    assert Path(_find_root_dir()) == Path(sys.modules[package_name].__file__).parent


@mock.patch.dict(os.environ, values={"env": "dev_test"}, clear=True)
def test_find_root_dir_special_test_env():
    # Test that a special test environment's (any "env" with "test" in the name)
    #   `MODULE_ROOT` is set to the `tests` directory.
    assert _find_root_dir().endswith("/tests")


@mock.patch.dict(os.environ, values={"env": "dev"}, clear=True)
@mock.patch.dict(sys.modules, clear=True)
def test_find_root_dir_failure():
    # Test that not being able to define the `MODULE_ROOT` raises an exception.
    with pytest.raises(Exception, match="Unable to determine neutrons_standard module-root directory"):
        _find_root_dir()


def test_resource_packageMode(caplog):
    # Test that "package mode" is recognized appropriately.

    # TODO: At present, 'Config' has a _redundant_ '@Singleton' =>  It is also initialized
    #   explicitly as a singleton.  This needs to be fixed!

    ROOT_MODULE = Path(sys.modules[package_name].__file__).parent
    ymlPath = ROOT_MODULE / "resources" / "application.yml"

    # In the below, we need to trigger a fresh import for the 'Config' module.
    # AND, we need an absolute path for an "application.yml" which is _outside_ of "package_name/resources".
    with (
        mock.patch.dict(os.environ),
        mock.patch.dict(sys.modules),
        TemporaryDirectory() as tmpdir,
    ):
        # An absolute path for "application.yml" _outside_ of "package_name/resources".
        nonModuleEnvPath = Path(tmpdir) / "application.yml"
        shutil.copy2(ymlPath, nonModuleEnvPath)
        os.environ["env"] = str(nonModuleEnvPath)

        # Trigger a fresh import for the "Config" module.
        del sys.modules[f"{package_name}.config"]
        from neutrons_standard.config import _Resource

        # `@Singleton` is now active for tests:
        #    we need to reset it, so that we can recreate the class.
        # In this case, we need to fully remove the decorator, so that the original `__init__` will be called.
        # Otherwise, the applied mocks will have no effect during the initialization.
        _Resource._reset_Singleton(fully_unwrap=True)

        with (
            mock.patch.object(_Resource, "_existsInPackage") as mockExistsInPackage,
            caplog.at_level(logging.DEBUG, logger=f"{package_name}.config.Resource"),
        ):
            # This mock bypasses the fact that "application.yml" actually does exist
            #   under "package_name/resources".  Probably there's a better way to do this!
            mockExistsInPackage.return_value = False
            rs = _Resource()
            assert rs._package_mode
        assert "In package mode" in caplog.text


def test_resource_not_packageMode(caplog):
    # Test that a test env is recognized as non-"package mode".

    with mock.patch.dict(sys.modules):
        # Trigger a fresh import for the "Config" module.
        del sys.modules[f"{package_name}.config"]
        with caplog.at_level(logging.DEBUG, logger=f"{package_name}.config.Resource"):
            from neutrons_standard.config import _Resource

            rs = _Resource()
            assert not rs._package_mode
    assert "Not in package mode" in caplog.text


def test_resource_packageMode_exists():
    # Test that the "exists" method in package mode implements <exists in the package> functionality.

    ROOT_MODULE = Path(sys.modules[package_name].__file__).parent
    ymlPath = ROOT_MODULE / "resources" / "application.yml"

    # In the below, we need to trigger a fresh import for the 'Config' module.
    # AND, we need an absolute path for an "application.yml" which is _outside_ of "package_name/resources".
    with (
        mock.patch.dict(os.environ),
        mock.patch.dict(sys.modules),
        TemporaryDirectory() as tmpdir,
    ):
        # An absolute path for "application.yml" _outside_ of "package_name/resources".
        nonModuleEnvPath = Path(tmpdir) / "application.yml"
        shutil.copy2(ymlPath, nonModuleEnvPath)
        os.environ["env"] = str(nonModuleEnvPath)

        # Trigger a fresh import for the "Config" module.
        del sys.modules[f"{package_name}.config"]
        from neutrons_standard.config import _Resource

        # `@Singleton` is now active for tests:
        #    we need to reset it, so that we can recreate the class.
        # In this case, we need to fully remove the decorator, so that the original `__init__` will be called.
        # Otherwise, the applied mocks will have no effect during the initialization.
        _Resource._reset_Singleton(fully_unwrap=True)

        with (
            mock.patch.object(_Resource, "_existsInPackage") as mockExistsInPackage,
        ):
            # This mock bypasses the fact that "application.yml" actually does exist
            #   under "package_name/resources".  Probably there's a better way to do this!
            mockExistsInPackage.return_value = False
            rs = _Resource()
            assert rs._package_mode
            test_path = "any/path"
            rs.exists(test_path)
            mockExistsInPackage.assert_called_with(test_path)


def test_resource_exists():
    with mock.patch.object(Resource, "_existsInPackage") as mockExistsInPackage:
        assert Resource.exists("application.yml")
        mockExistsInPackage.assert_not_called()


def test_resource_exists_false():
    assert not Resource.exists("not_a_real_file.yml")


def test_resource_read():
    assert Resource.read("application.yml") is not None


def test_resource_open():
    with mock.patch.object(Config_module.resources, "path") as mockResourcesPath:
        assert not Resource._package_mode
        with Resource.open("application.yml", "r") as file:
            assert file is not None
            mockResourcesPath.assert_not_called()


def test_resource_packageMode_open():
    actual_path = Resource.getPath("application.yml")
    with (
        mock.patch.object(Config_module.resources, "path") as mockResourcesPath,
        mock.patch.object(Resource, "_package_mode") as mockPackageMode,
    ):
        mockResourcesPath.return_value = mock.Mock(
            __enter__=mock.Mock(return_value=actual_path),
            __exit__=mock.Mock(),
        )
        mockPackageMode.return_value = True
        test_path = "application.yml"
        with Resource.open(test_path, "r") as file:
            assert file is not None
            mockResourcesPath.assert_called_once_with(f"{package_name}.resources", test_path)


def test_Config_persistBackup():
    # mock Path.home() to temporary directory
    with TemporaryDirectory() as tmpdir:
        with mock.patch.object(Config_module._Config, "_userHome", lambda _: Path(tmpdir) / f".{package_name}"):
            inst = Config_module._Config()
            # remove the application.yml.bak file if it exists
            if (Path(tmpdir) / f".{package_name}" / "application.yml.bak").exists():
                os.remove(Path(tmpdir) / f".{package_name}" / "application.yml.bak")
                os.rmdir(Path(tmpdir) / f".{package_name}")

            assert not (Path(tmpdir) / f".{package_name}").exists()
            # call the persistBackup method
            inst.persistBackup()
            assert (Path(tmpdir) / f".{package_name}").exists()
            assert (Path(tmpdir) / f".{package_name}" / "application.yml.bak").exists()


def test_Config_accessor():
    # these values are copied from tests/resources/application.yml
    assert Config["environment"] == "test"

    # these should throw KeyError
    with pytest.raises(KeyError):
        assert Config["garbage"]
    with pytest.raises(KeyError):
        assert Config["orchestration.garbage"]


def test_key_substitution():
    testString = "This is a test string with a ${test.key} in it"
    Config._config["test"]["key"] = "value"
    Config._config["test"]["substitution"] = testString
    assert Config["test.substitution"] == "This is a test string with a value in it"


def test_multi_level_substitution():
    assert Config["test.multi-substitution.home"] == f"{Config['user.application.home']}/test"


def test_home_expansion():
    home = os.path.expanduser("~")
    assert Config["user.application.home"] == f"{home}/.neutrons_standard"
    assert Config["test.multi-substitution.home"] == f"{home}/.neutrons_standard/test"
    # the stored value is left as written
    assert Config._config["user"]["application"]["home"] == "~/.neutrons_standard"

    Config._config["test"]["tilde"] = "~"
    assert Config["test.tilde"] == home
    for unexpanded in ("~user/data", "/data/~/tmp", "a ~/b"):
        Config._config["test"]["tilde"] = unexpanded
        assert Config["test.tilde"] == unexpanded


def test_packageVersion():
    with mock.patch.object(Config_module.metadata, "version", return_value="1.2.3") as mockVersion:
        assert Config.packageVersion() == "1.2.3"
        mockVersion.assert_called_once_with(package_name)


def test_packageVersion_not_installed():
    with mock.patch.object(
        Config_module.metadata, "version", side_effect=Config_module.metadata.PackageNotFoundError(package_name)
    ):
        assert len(Config.packageVersion()) == len("b2e9c58bd94d0c95cdfa81cb845deb7c636047db")


def test_packageVersion_empty():
    with (
        mock.patch.object(Config_module.metadata, "version", return_value=""),
        mock.patch.object(Config_module.subprocess, "check_output", return_value=b""),
    ):
        with pytest.raises(ValueError, match="The neutrons_standard Version is not set correctly."):
            Config.packageVersion()


def test_packageVersion_not_a_repo():
    with (
        mock.patch.object(
            Config_module.metadata, "version", side_effect=Config_module.metadata.PackageNotFoundError(package_name)
        ),
        mock.patch.object(
            Config_module.subprocess,
            "check_output",
            side_effect=Config_module.subprocess.CalledProcessError(128, ["git", "rev-parse", "HEAD"]),
        ),
    ):
        with pytest.raises(ValueError, match="The neutrons_standard Version is not set correctly."):
            Config.packageVersion()


def test_getCurrentEnv():
    # Test that the current environment is returned correctly
    assert Config.getCurrentEnv() == "test"


def test_swapToUserYml():
    # setup temp dir
    with TemporaryDirectory(prefix=Resource.getPath("outputs/")) as tmpPath:
        # mock out path's home method
        with mock.patch(f"{package_name}.config.Path.home") as mockHome:
            Config.packageVersion = lambda: "1.0.0"
            mockHome.return_value = Path(tmpPath)
            Config.swapToUserYml()
            # check that the file exists
            assert Path(tmpPath).exists()
            assert (Path(tmpPath) / f".{package_name}").exists()
            assert (Path(tmpPath) / f".{package_name}" / f"{package_name}-user.yml").exists()

            assert f"{package_name}-user" in Config["environment"]

            with open(Path(tmpPath) / f".{package_name}" / f"{package_name}-user.yml", "r") as file:
                yml = rYaml(typ="safe").load(file)
                assert yml["application"]["version"] == "1.0.0"


def test_shouldSwapToUserYml():
    # Test that the method returns True when the user configuration file exists and is not in a test environment
    with mock.patch.object(Config, "_userHome") as mockHome, mock.patch.dict(os.environ, values={}, clear=True):
        with TemporaryDirectory() as tmpDir:
            mockHome.return_value = Path(f"{tmpDir}/{package_name}")
            mockHome.return_value.mkdir(exist_ok=True)
            (mockHome.return_value / f"{package_name}-user.yml").touch()
            assert "env" not in os.environ
            assert Config.shouldSwapToUserYml()

    # Test that the method returns False when the user configuration file does not exist
    with mock.patch.object(Config, "_userHome") as mockHome:
        mockHome.return_value = Path(f"/tmp/{package_name}")
        assert not Config.shouldSwapToUserYml()

    # Test that the method returns False when the environment variable 'env' is set
    with mock.patch.object(Config, "_userHome") as mockHome, mock.patch.dict(os.environ, {"env": "test"}):
        with TemporaryDirectory() as tmpDir:
            mockHome.return_value = Path(f"{tmpDir}/{package_name}")
            mockHome.return_value.mkdir(exist_ok=True)
            (mockHome.return_value / f"{package_name}-user.yml").touch()

            assert not Config.shouldSwapToUserYml()


def test_swapToUserYml_error():
    # setup temp dir
    with mock.patch.object(Config, "_userHome") as mockHome:
        mockHome().exists.side_effect = RuntimeError("the file system messed up!!!")
        with pytest.raises(RuntimeError, match="Unable to swap to user configuration"):
            Config.swapToUserYml()


def test_swapToUserYml_archive():
    # setup temp dir
    with TemporaryDirectory(prefix=Resource.getPath("outputs/")) as tmpPath:
        # mock out path's home method
        with (
            mock.patch(f"{package_name}.config.Path.home") as mockHome,
            mock.patch.object(Config, "_timestamp") as mockTimeStamp,
        ):
            dateTime = "2023-10-01 12:00:00"
            mockTimeStamp.return_value = dateTime
            Config.packageVersion = lambda: "1.0.0"
            mockHome.return_value = Path(tmpPath)
            Config.swapToUserYml()
            # check that the file exists
            assert Path(tmpPath).exists()
            assert (Path(tmpPath) / f".{package_name}").exists()
            assert (Path(tmpPath) / f".{package_name}" / f"{package_name}-user.yml").exists()

            assert f"{package_name}-user" in Config["environment"]
            Config.packageVersion = lambda: "1.0.8"
            Config.swapToUserYml()
            with open(Path(tmpPath) / f".{package_name}" / f"{package_name}-user.yml", "r") as file:
                yml = rYaml(typ="safe").load(file)
                assert yml["application"]["version"] == "1.0.8"
            assert (Path(tmpPath) / f".{package_name}" / f"{package_name}-user.yml").exists()
            assert (Path(tmpPath) / f".{package_name}" / f"{package_name}-user-1.0.0-{dateTime}.yml.bak").exists(), (
                os.listdir(Path(tmpPath) / f".{package_name}")
            )


def test_swapToUserYml_same_version_no_archive():
    with TemporaryDirectory(prefix=Resource.getPath("outputs/")) as tmpPath:
        with mock.patch(f"{package_name}.config.Path.home") as mockHome:
            Config.packageVersion = lambda: "1.0.0"
            mockHome.return_value = Path(tmpPath)
            Config.swapToUserYml()
            Config.swapToUserYml()
            assert not list((Path(tmpPath) / f".{package_name}").glob(f"{package_name}-user-*.yml.bak"))


def test_archiveUserYml_limit():
    with TemporaryDirectory() as tmpPath:
        userHome = Path(tmpPath)
        with (
            mock.patch.object(Config, "_userHome", return_value=userHome),
            mock.patch.object(Config, "_user_yml_archive_limit", 2),
            mock.patch.object(Config, "_timestamp", return_value="new"),
        ):
            (userHome / f"{package_name}-user.yml").write_text("application:\n  version: 1.0.0\n")
            # pre-existing archives, oldest first
            for n in range(3):
                archive = userHome / f"{package_name}-user-0.0.{n}-old.yml.bak"
                archive.touch()
                os.utime(archive, (1000 + n, 1000 + n))
            # an unrelated file must not be touched
            (userHome / "application.yml.bak").touch()

            Config.archiveUserYml()

            remaining = sorted(p.name for p in userHome.glob(f"{package_name}-user-*.yml.bak"))
            assert remaining == [f"{package_name}-user-0.0.2-old.yml.bak", f"{package_name}-user-1.0.0-new.yml.bak"]
            assert (userHome / "application.yml.bak").exists()


def test_configureForDeploy():
    # copy application.yml to a temporary directory
    with TemporaryDirectory() as tmpPath:
        applicationYmlPath: Path = Path(Resource.getPath("application.yml"))
        nextApplicationYmlPath = applicationYmlPath.parent / f"{package_name}_next.yml"
        (Path(tmpPath) / "application.yml").write_bytes(applicationYmlPath.read_bytes())
        (Path(tmpPath) / f"{package_name}_next.yml").write_bytes(nextApplicationYmlPath.read_bytes())
        with (
            mock.patch.object(Resource, "_resources_path", Path(tmpPath)),
            mock.patch.object(Config, "packageVersion", mock.Mock(return_value="dev")),
            #   Dont want to overwrite the config for the rest of the tests
            mock.patch.object(Config, "_config", {}),
        ):
            Config.configureForDeploy()
            # check that the file exists
            assert (Path(tmpPath) / "application.yml").exists()
            # check that the file is not empty
            assert (Path(tmpPath) / "application.yml").stat().st_size > 0
            # check that the file is a valid yaml file
            with open(Path(tmpPath) / "application.yml", "r") as file:
                yml = rYaml(typ="safe").load(file)
                assert "next" in yml["deploy"]


def test_configureForDeploy_qa_or_prod():
    with (
        mock.patch.object(Config, "packageVersion", mock.Mock(return_value="1.0.0")) as mockVersion,
        mock.patch.object(Config, "mergeAndExport", mock.Mock()) as mockMergeExport,
    ):
        Config.configureForDeploy()
        mockVersion.assert_called_once()
        mockMergeExport.assert_called_once_with(DeployEnvEnum.PROD.envName())
        mockVersion.reset_mock()
        mockMergeExport.reset_mock()
        mockVersion.return_value = "1.0.1rc2"
        Config.configureForDeploy()
        mockVersion.assert_called_once()
        mockMergeExport.assert_called_once_with(DeployEnvEnum.QA.envName())
