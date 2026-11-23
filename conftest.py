import pytest


@pytest.fixture(autouse=True)
def _disable_mock_bls_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MOCK_BLS_DATA", "false")
