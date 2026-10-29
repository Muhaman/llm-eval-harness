import pytest

from helpers import FakeJudge


@pytest.fixture
def fake_judge() -> FakeJudge:
    return FakeJudge(0.8)
