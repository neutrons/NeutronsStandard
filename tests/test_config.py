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
from ruamel.yaml import YAML as rYAML  # noqa: N811

import neutrons_standard.config as config_module
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
    # Test that a test environment's `module_root` is set to the `tests` directory.
    assert _find_root_dir().endswith("/tests")


def test_version_default():
    # Test that Config["version.default"] is implicitly set
    assert isinstance(Config["version.default"], int)


@mock.patch.dict(os.environ, values={"env": "dev"}, clear=True)
def test_find_root_dir_non_test_env():
    # Test that a non-test environment's `module_root` is set to the package_name module directory
    assert Path(_find_root_dir()) == Path(sys.modules[package_name].__file__).parent


@mock.patch.dict(os.environ, values={"env": "dev_test"}, clear=True)
def test_find_root_dir_special_test_env():
    # Test that a special test environment's (any "env" with "test" in the name)
    #   `module_root` is set to the `tests` directory.
    assert _find_root_dir().endswith("/tests")


@mock.patch.dict(os.environ, values={"env": "dev"}, clear=True)
@mock.patch.dict(sys.modules, clear=True)
def test_find_root_dir_failure():
    # Test that not being able to define the `module_root` raises an exception.
    with pytest.raises(Exception, match="Unable to determine neutrons_standard module-root directory"):
        _find_root_dir()


def test_resource_package_mode(caplog):
    # Test that "package mode" is recognized appropriately.

    # TODO: At present, 'Config' has a _redundant_ '@Singleton' =>  It is also initialized
    #   explicitly as a singleton.  This needs to be fixed!

    root_module = Path(sys.modules[package_name].__file__).parent
    yml_path = root_module / "resources" / "application.yml"

    # In the below, we need to trigger a fresh import for the 'Config' module.
    # AND, we need an absolute path for an "application.yml" which is _outside_ of "package_name/resources".
    with (
        mock.patch.dict(os.environ),
        mock.patch.dict(sys.modules),
        TemporaryDirectory() as tmpdir,
    ):
        # An absolute path for "application.yml" _outside_ of "package_name/resources".
        non_module_env_path = Path(tmpdir) / "application.yml"
        shutil.copy2(yml_path, non_module_env_path)
        os.environ["env"] = str(non_module_env_path)

        # Trigger a fresh import for the "Config" module.
        del sys.modules[f"{package_name}.config"]
        from neutrons_standard.config import _Resource

        # `@Singleton` is now active for tests:
        #    we need to reset it, so that we can recreate the class.
        # In this case, we need to fully remove the decorator, so that the original `__init__` will be called.
        # Otherwise, the applied mocks will have no effect during the initialization.
        _Resource._reset_singleton(fully_unwrap=True)

        with (
            mock.patch.object(_Resource, "_exists_in_package") as mock_exists_in_package,
            caplog.at_level(logging.DEBUG, logger=f"{package_name}.config.Resource"),
        ):
            # This mock bypasses the fact that "application.yml" actually does exist
            #   under "package_name/resources".  Probably there's a better way to do this!
            mock_exists_in_package.return_value = False
            rs = _Resource()
            assert rs._package_mode
        assert "In package mode" in caplog.text


def test_resource_not_package_mode(caplog):
    # Test that a test env is recognized as non-"package mode".

    with mock.patch.dict(sys.modules):
        # Trigger a fresh import for the "Config" module.
        del sys.modules[f"{package_name}.config"]
        with caplog.at_level(logging.DEBUG, logger=f"{package_name}.config.Resource"):
            from neutrons_standard.config import _Resource

            rs = _Resource()
            assert not rs._package_mode
    assert "Not in package mode" in caplog.text


def test_resource_package_mode_exists():
    # Test that the "exists" method in package mode implements <exists in the package> functionality.

    root_module = Path(sys.modules[package_name].__file__).parent
    yml_path = root_module / "resources" / "application.yml"

    # In the below, we need to trigger a fresh import for the 'Config' module.
    # AND, we need an absolute path for an "application.yml" which is _outside_ of "package_name/resources".
    with (
        mock.patch.dict(os.environ),
        mock.patch.dict(sys.modules),
        TemporaryDirectory() as tmpdir,
    ):
        # An absolute path for "application.yml" _outside_ of "package_name/resources".
        non_module_env_path = Path(tmpdir) / "application.yml"
        shutil.copy2(yml_path, non_module_env_path)
        os.environ["env"] = str(non_module_env_path)

        # Trigger a fresh import for the "Config" module.
        del sys.modules[f"{package_name}.config"]
        from neutrons_standard.config import _Resource

        # `@Singleton` is now active for tests:
        #    we need to reset it, so that we can recreate the class.
        # In this case, we need to fully remove the decorator, so that the original `__init__` will be called.
        # Otherwise, the applied mocks will have no effect during the initialization.
        _Resource._reset_singleton(fully_unwrap=True)

        with (
            mock.patch.object(_Resource, "_exists_in_package") as mock_exists_in_package,
        ):
            # This mock bypasses the fact that "application.yml" actually does exist
            #   under "package_name/resources".  Probably there's a better way to do this!
            mock_exists_in_package.return_value = False
            rs = _Resource()
            assert rs._package_mode
            test_path = "any/path"
            rs.exists(test_path)
            mock_exists_in_package.assert_called_with(test_path)


def test_resource_exists():
    with mock.patch.object(Resource, "_exists_in_package") as mock_exists_in_package:
        assert Resource.exists("application.yml")
        mock_exists_in_package.assert_not_called()


def test_resource_exists_false():
    assert not Resource.exists("not_a_real_file.yml")


def test_resource_read():
    assert Resource.read("application.yml") is not None


def test_resource_open():
    with mock.patch.object(config_module.resources, "path") as mock_resources_path:
        assert not Resource._package_mode
        with Resource.open("application.yml", "r") as file:
            assert file is not None
            mock_resources_path.assert_not_called()


def test_resource_package_mode_open():
    actual_path = Resource.get_path("application.yml")
    with (
        mock.patch.object(config_module.resources, "path") as mock_resources_path,
        mock.patch.object(Resource, "_package_mode") as mock_package_mode,
    ):
        mock_resources_path.return_value = mock.Mock(
            __enter__=mock.Mock(return_value=actual_path),
            __exit__=mock.Mock(),
        )
        mock_package_mode.return_value = True
        test_path = "application.yml"
        with Resource.open(test_path, "r") as file:
            assert file is not None
            mock_resources_path.assert_called_once_with(f"{package_name}.resources", test_path)


def test_config_persist_backup():
    # mock Path.home() to temporary directory
    with TemporaryDirectory() as tmpdir:
        with mock.patch.object(config_module._Config, "_user_home", lambda _: Path(tmpdir) / f".{package_name}"):
            inst = config_module._Config()
            # remove the application.yml.bak file if it exists
            if (Path(tmpdir) / f".{package_name}" / "application.yml.bak").exists():
                os.remove(Path(tmpdir) / f".{package_name}" / "application.yml.bak")
                os.rmdir(Path(tmpdir) / f".{package_name}")

            assert not (Path(tmpdir) / f".{package_name}").exists()
            # call the persist_backup method
            inst.persist_backup()
            assert (Path(tmpdir) / f".{package_name}").exists()
            assert (Path(tmpdir) / f".{package_name}" / "application.yml.bak").exists()


def test_config_accessor():
    # these values are copied from tests/resources/application.yml
    assert Config["environment"] == "test"

    # these should throw KeyError
    with pytest.raises(KeyError):
        assert Config["garbage"]
    with pytest.raises(KeyError):
        assert Config["orchestration.garbage"]


def test_key_substitution():
    test_string = "This is a test string with a ${test.key} in it"
    Config._config["test"]["key"] = "value"
    Config._config["test"]["substitution"] = test_string
    assert Config["test.substitution"] == "This is a test string with a value in it"


def test_multi_level_substitution():
    assert Config["test.multi-substitution.home"] == f"{Config['user.application.home']}/test"


def test_home_expansion(caplog):
    home = os.path.expanduser("~")
    assert Config["user.application.home"] == f"{home}/.neutrons_standard"
    assert Config["test.multi-substitution.home"] == f"{home}/.neutrons_standard/test"
    # the stored value is left as written
    assert Config._config["user"]["application"]["home"] == "~/.neutrons_standard"

    Config._config["test"]["tilde"] = "~"
    assert Config["test.tilde"] == home
    for unexpanded in ("/data/~/tmp", "a ~/b"):
        Config._config["test"]["tilde"] = unexpanded
        assert Config["test.tilde"] == unexpanded

    # `~user` expands to that user's home directory
    user = Path(home).name
    Config._config["test"]["tilde"] = f"~{user}/data"
    assert Config["test.tilde"] == os.path.expanduser(f"~{user}/data")

    # an unknown user's `~user` is used as written, with a warning logged once
    Config._config["test"]["tilde"] = "~nonexistent-user-xyz/data"
    with caplog.at_level(logging.WARNING, logger=f"{package_name}.config.Config"):
        assert Config["test.tilde"] == "~nonexistent-user-xyz/data"
        assert Config["test.tilde"] == "~nonexistent-user-xyz/data"
    warnings = [r for r in caplog.records if "nonexistent-user-xyz" in r.getMessage()]
    assert len(warnings) == 1
    assert "no home directory found for user 'nonexistent-user-xyz'" in warnings[0].getMessage()


def test_package_version():
    with mock.patch.object(config_module.metadata, "version", return_value="1.2.3") as mock_version:
        assert Config.package_version() == "1.2.3"
        mock_version.assert_called_once_with(package_name)


def test_package_version_not_installed():
    with mock.patch.object(
        config_module.metadata, "version", side_effect=config_module.metadata.PackageNotFoundError(package_name)
    ):
        assert len(Config.package_version()) == len("b2e9c58bd94d0c95cdfa81cb845deb7c636047db")


def test_package_version_empty():
    with (
        mock.patch.object(config_module.metadata, "version", return_value=""),
        mock.patch.object(config_module.subprocess, "check_output", return_value=b""),
    ):
        with pytest.raises(ValueError, match="The neutrons_standard Version is not set correctly."):
            Config.package_version()


def test_package_version_not_a_repo():
    with (
        mock.patch.object(
            config_module.metadata, "version", side_effect=config_module.metadata.PackageNotFoundError(package_name)
        ),
        mock.patch.object(
            config_module.subprocess,
            "check_output",
            side_effect=config_module.subprocess.CalledProcessError(128, ["git", "rev-parse", "HEAD"]),
        ),
    ):
        with pytest.raises(ValueError, match="The neutrons_standard Version is not set correctly."):
            Config.package_version()


def test_get_current_env():
    # Test that the current environment is returned correctly
    assert Config.get_current_env() == "test"


def test_swap_to_user_yml():
    # setup temp dir
    with TemporaryDirectory(prefix=Resource.get_path("outputs/")) as tmp_path:
        # mock out path's home method
        with mock.patch(f"{package_name}.config.Path.home") as mock_home:
            Config.package_version = lambda: "1.0.0"
            mock_home.return_value = Path(tmp_path)
            Config.swap_to_user_yml()
            # check that the file exists
            assert Path(tmp_path).exists()
            assert (Path(tmp_path) / ".config" / package_name).exists()
            assert (Path(tmp_path) / ".config" / package_name / f"{package_name}-user.yml").exists()

            assert f"{package_name}-user" in Config["environment"]

            with open(Path(tmp_path) / ".config" / package_name / f"{package_name}-user.yml", "r") as file:
                yml = rYAML(typ="safe").load(file)
                assert yml["application"]["version"] == "1.0.0"


def test_should_swap_to_user_yml():
    # Test that the method returns True when the user configuration file exists and is not in a test environment
    with mock.patch.object(Config, "_user_home") as mock_home, mock.patch.dict(os.environ, values={}, clear=True):
        with TemporaryDirectory() as tmp_dir:
            mock_home.return_value = Path(f"{tmp_dir}/{package_name}")
            mock_home.return_value.mkdir(exist_ok=True)
            (mock_home.return_value / f"{package_name}-user.yml").touch()
            assert "env" not in os.environ
            assert Config.should_swap_to_user_yml()

    # Test that the method returns False when the user configuration file does not exist
    with mock.patch.object(Config, "_user_home") as mock_home:
        mock_home.return_value = Path(f"/tmp/{package_name}")
        assert not Config.should_swap_to_user_yml()

    # Test that the method returns False when the environment variable 'env' is set
    with mock.patch.object(Config, "_user_home") as mock_home, mock.patch.dict(os.environ, {"env": "test"}):
        with TemporaryDirectory() as tmp_dir:
            mock_home.return_value = Path(f"{tmp_dir}/{package_name}")
            mock_home.return_value.mkdir(exist_ok=True)
            (mock_home.return_value / f"{package_name}-user.yml").touch()

            assert not Config.should_swap_to_user_yml()


def test_swap_to_user_yml_error():
    # setup temp dir
    with mock.patch.object(Config, "_user_home") as mock_home:
        mock_home().exists.side_effect = RuntimeError("the file system messed up!!!")
        with pytest.raises(RuntimeError, match="Unable to swap to user configuration"):
            Config.swap_to_user_yml()


def test_swap_to_user_yml_archive():
    # setup temp dir
    with TemporaryDirectory(prefix=Resource.get_path("outputs/")) as tmp_path:
        # mock out path's home method
        with (
            mock.patch(f"{package_name}.config.Path.home") as mock_home,
            mock.patch.object(Config, "_timestamp") as mock_time_stamp,
        ):
            date_time = "2023-10-01 12:00:00"
            mock_time_stamp.return_value = date_time
            Config.package_version = lambda: "1.0.0"
            mock_home.return_value = Path(tmp_path)
            Config.swap_to_user_yml()
            # check that the file exists
            assert Path(tmp_path).exists()
            assert (Path(tmp_path) / ".config" / package_name).exists()
            assert (Path(tmp_path) / ".config" / package_name / f"{package_name}-user.yml").exists()

            assert f"{package_name}-user" in Config["environment"]
            Config.package_version = lambda: "1.0.8"
            Config.swap_to_user_yml()
            with open(Path(tmp_path) / ".config" / package_name / f"{package_name}-user.yml", "r") as file:
                yml = rYAML(typ="safe").load(file)
                assert yml["application"]["version"] == "1.0.8"
            assert (Path(tmp_path) / ".config" / package_name / f"{package_name}-user.yml").exists()
            assert (
                Path(tmp_path) / ".config" / package_name / f"{package_name}-user-1.0.0-{date_time}.yml.bak"
            ).exists(), os.listdir(Path(tmp_path) / ".config" / package_name)


def test_swap_to_user_yml_same_version_no_archive():
    with TemporaryDirectory(prefix=Resource.get_path("outputs/")) as tmp_path:
        with mock.patch(f"{package_name}.config.Path.home") as mock_home:
            Config.package_version = lambda: "1.0.0"
            mock_home.return_value = Path(tmp_path)
            Config.swap_to_user_yml()
            Config.swap_to_user_yml()
            assert not list((Path(tmp_path) / ".config" / package_name).glob(f"{package_name}-user-*.yml.bak"))


def test_archive_user_yml_limit():
    with TemporaryDirectory() as tmp_path:
        user_home = Path(tmp_path)
        with (
            mock.patch.object(Config, "_user_home", return_value=user_home),
            mock.patch.object(Config, "_default_user_yml_archive_limit", 2),
            mock.patch.object(Config, "_timestamp", return_value="new"),
        ):
            (user_home / f"{package_name}-user.yml").write_text("application:\n  version: 1.0.0\n")
            # pre-existing archives, oldest first
            for n in range(3):
                archive = user_home / f"{package_name}-user-0.0.{n}-old.yml.bak"
                archive.touch()
                os.utime(archive, (1000 + n, 1000 + n))
            # an unrelated file must not be touched
            (user_home / "application.yml.bak").touch()

            Config.archive_user_yml()

            remaining = sorted(p.name for p in user_home.glob(f"{package_name}-user-*.yml.bak"))
            assert remaining == [f"{package_name}-user-0.0.2-old.yml.bak", f"{package_name}-user-1.0.0-new.yml.bak"]
            assert (user_home / "application.yml.bak").exists()


@pytest.mark.parametrize(
    ("limit", "kept"),
    [(None, 5), (2, 2), (0, 0), (-1, 7), (-2, 5), ("five", 5), (True, 5)],
)
def test_archive_user_yml_configured_limit(caplog, limit, kept):
    # `application.user_yml_archive_limit` sets the number of archives kept: -1 keeps all of them, 0 keeps none
    with TemporaryDirectory() as tmp_path:
        user_home = Path(tmp_path)
        application = {"version": "1.0.0"} if limit is None else {"version": "1.0.0", "user_yml_archive_limit": limit}
        with (
            mock.patch.object(Config, "_user_home", return_value=user_home),
            mock.patch.object(Config, "_timestamp", return_value="new"),
            mock.patch.dict(Config._config, {"application": application}),
        ):
            (user_home / f"{package_name}-user.yml").write_text("application:\n  version: 1.0.0\n")
            for n in range(6):
                archive = user_home / f"{package_name}-user-0.0.{n}-old.yml.bak"
                archive.touch()
                os.utime(archive, (1000 + n, 1000 + n))

            Config.archive_user_yml()

            remaining = list(user_home.glob(f"{package_name}-user-*.yml.bak"))
            assert len(remaining) == kept
            if kept:
                # the newest are kept
                assert (user_home / f"{package_name}-user-1.0.0-new.yml.bak") in remaining
            invalid = limit in (-2, "five", True)
            assert ("Invalid `application.user_yml_archive_limit" in caplog.text) == invalid


def test_user_home_moves_legacy_home():
    # files in the old `~/.<package>` are moved to `~/.config/<package>` once, and then used
    with TemporaryDirectory() as tmpdir, mock.patch(f"{package_name}.config.Path.home", return_value=Path(tmpdir)):
        legacy_home = Path(tmpdir) / f".{package_name}"
        legacy_home.mkdir()
        (legacy_home / f"{package_name}-user.yml").write_text("application:\n  version: 1.0.0\n")
        user_home = Config._user_home()
        assert user_home == Path(tmpdir) / ".config" / package_name
        assert (user_home / f"{package_name}-user.yml").exists()
        assert not legacy_home.exists()
        # an old directory created later is left alone: the new one is used
        legacy_home.mkdir()
        assert Config._user_home() == user_home
        assert legacy_home.exists()


def test_user_home_move_fails(caplog):
    # if the old directory can't be moved, it is still used
    with (
        TemporaryDirectory() as tmpdir,
        mock.patch(f"{package_name}.config.Path.home", return_value=Path(tmpdir)),
        mock.patch(f"{package_name}.config.shutil.move", side_effect=OSError("read-only")),
    ):
        legacy_home = Path(tmpdir) / f".{package_name}"
        legacy_home.mkdir()
        assert Config._user_home() == legacy_home
        assert "Unable to move the user configuration" in caplog.text


def test_configure_for_deploy():
    # copy application.yml to a temporary directory
    with TemporaryDirectory() as tmp_path:
        application_yml_path: Path = Path(Resource.get_path("application.yml"))
        next_application_yml_path = application_yml_path.parent / f"{package_name}_next.yml"
        (Path(tmp_path) / "application.yml").write_bytes(application_yml_path.read_bytes())
        (Path(tmp_path) / f"{package_name}_next.yml").write_bytes(next_application_yml_path.read_bytes())
        with (
            mock.patch.object(Resource, "_resources_path", Path(tmp_path)),
            mock.patch.object(Config, "package_version", mock.Mock(return_value="dev")),
            #   Dont want to overwrite the config for the rest of the tests
            mock.patch.object(Config, "_config", {}),
        ):
            Config.configure_for_deploy()
            # check that the file exists
            assert (Path(tmp_path) / "application.yml").exists()
            # check that the file is not empty
            assert (Path(tmp_path) / "application.yml").stat().st_size > 0
            # check that the file is a valid yaml file
            with open(Path(tmp_path) / "application.yml", "r") as file:
                yml = rYAML(typ="safe").load(file)
                assert "next" in yml["deploy"]


def test_configure_for_deploy_qa_or_prod():
    with (
        mock.patch.object(Config, "package_version", mock.Mock(return_value="1.0.0")) as mock_version,
        mock.patch.object(Config, "merge_and_export", mock.Mock()) as mock_merge_export,
    ):
        Config.configure_for_deploy()
        mock_version.assert_called_once()
        mock_merge_export.assert_called_once_with(DeployEnvEnum.PROD.env_name())
        mock_version.reset_mock()
        mock_merge_export.reset_mock()
        mock_version.return_value = "1.0.1rc2"
        Config.configure_for_deploy()
        mock_version.assert_called_once()
        mock_merge_export.assert_called_once_with(DeployEnvEnum.QA.env_name())
