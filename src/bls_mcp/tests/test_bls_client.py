import pytest

from bls_mcp.clients.bls import BLSClient


@pytest.mark.asyncio
async def test_get_series_observations_mock_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MOCK_BLS_DATA", "true")

    client = BLSClient()
    results = await client.get_series_observations(
        series_ids=["TEST_PPI_001"],
        start_year=2024,
        end_year=2025,
    )

    assert len(results) == 1
    assert results[0].series_id == "TEST_PPI_001"
    assert str(results[0].value) == "123.45"
