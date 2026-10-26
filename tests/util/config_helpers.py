from collections import namedtuple
from contextlib import ExitStack, contextmanager
from typing import Any, Dict, Tuple

import pytest

from neutrons_standard.config import Config

Node = namedtuple("Node", "dict key")

# Implementation notes:
# * In order to allow convenient usage within CIS-test scripts,
# `config_override` is deliberately _not_ implemented as a test fixture.
# * Multi-level substitution is not implemented: in general this can _effectively_ result in a
# period-delimited key corresponding to values from _multiple_ `Config` nodes.
# It's assumed that this does not pose much limitation, and that it should be possible
# to accomplish any required "override" usage with (possibly multiple) single-node substitutions.


@contextmanager
def config_override(key: str, value: Any):
    # Context manager to safely override a `Config` entry:
    # * `__enter__` returns the `Config` instance.

    # Find the _primary_ node associated with a period-delimited key.
    def lookup_node(dict_: Dict[str, Any], key: str) -> Tuple[Dict[str, Any], str]:
        # key_1.key_2. ... key_(n-1) lookup
        ks = key.split(".")
        val = dict_
        for k in ks[0:-1]:
            val = val.get(k)
            if not isinstance(val, dict):
                # Anything else may not correspond to a _single_ `Config` node
                raise RuntimeError(
                    f"not implemented: probable multilevel substitution with key: '{key}' for value: {value}"
                )

        return Node(val, ks[-1])

    # __enter__
    # test failing with exepction will pollute other tests with this config change if not caught up the stack
    try:
        _saved_node: Tuple[Dict[str, Any], str] = lookup_node(Config._config, key)
        _saved_value: Any = _saved_node.dict[_saved_node.key]
        _saved_node.dict[_saved_node.key] = value
        yield Config
    finally:
        # __exit__
        del _saved_node.dict[_saved_node.key]
        if _saved_value is not None:
            _saved_node.dict[_saved_node.key] = _saved_value


@pytest.fixture
def config_override_fixture():
    _stack = ExitStack()

    def _config_override_fixture(key: str, value: Any):
        return _stack.enter_context(config_override(key, value))

    yield _config_override_fixture

    # teardown => __exit__
    _stack.close()
