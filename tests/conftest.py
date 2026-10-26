import os

import pytest

import neutrons_standard
from neutrons_standard.decorators.singleton import reset_singletons

neutrons_standard.init("neutrons_standard")

if not os.environ.get("env"):
    os.environ["env"] = "test"


@pytest.fixture(autouse=True)
def _reset_singletons(request):
    if "integration" not in request.keywords:
        reset_singletons()
    yield


@pytest.fixture(scope="class", autouse=True)
def _reset_class_scope_singletons(request):
    if "integration" not in request.keywords:
        reset_singletons()
    yield


@pytest.fixture(scope="module", autouse=True)
def _reset_module_scope_singletons(request):
    if "integration" not in request.keywords:
        reset_singletons()
    yield
