"""Contains the entry point for the application"""

try:
    from neutrons_standard._version import __version__
except ImportError:
    __version__ = "unknown"


class _Spec:
    """Package-level settings registered by the client via `init`."""

    def __init__(self) -> None:
        self._client_package_name: str | None = None

    @property
    def client_package_name(self) -> str:
        if self._client_package_name is None:
            raise RuntimeError("`neutrons_standard.init(<client_package_name>)` must be called first")
        return self._client_package_name

    @client_package_name.setter
    def client_package_name(self, name: str) -> None:
        if self._client_package_name not in (None, name):
            raise RuntimeError(f"`neutrons_standard` is already initialized for '{self._client_package_name}'")
        self._client_package_name = name


Spec: _Spec = _Spec()


def init(client_package_name: str) -> None:
    Spec.client_package_name = client_package_name


def __getattr__(name: str):  # noqa: ANN202
    # `Config` is loaded lazily: importing it here eagerly would run `config` before `Spec` is defined,
    #   and before the client has called `init(...)`.
    if name == "Config":
        from neutrons_standard.config import Config

        return Config
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["Config", "Spec", "__version__", "init"]
