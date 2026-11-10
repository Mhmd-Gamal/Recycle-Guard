import pytest
from adviser.core import Core

@pytest.fixture
def core():
    with Core() as c:
        yield c
