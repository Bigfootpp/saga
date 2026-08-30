import httpx
import pytest
import respx

from saga.models.query import MovieQuery, SeriesQuery
from saga.providers.exceptions import ProviderTimeoutError
from saga.providers.jackett import JackettProvider
from tests.samples.jackett_mock_sample import THE_SUMMIT_OF_THE_GODS


@pytest.fixture
async def provider():
    yield JackettProvider(
        base_url="http://jackett:9117",
        api_key="123"
    )

@respx.mock
async def test_jackett_series(provider: JackettProvider):
    route = respx.get("http://jackett:9117/api/v2.0/indexers/all/results/torznab/api").respond(
        status_code=200,
        text=THE_SUMMIT_OF_THE_GODS
    )

    query = MovieQuery(title="The Summit of the Gods")

    result = await provider.search(query)
    assert len(result) == 2
    assert result[0].title == "The Summit of the Gods"
    assert result[0].info_hash == "a9b5a8965470b5a29bfda623330f9244fe3a2589"

    assert route.called
    sent_params = route.calls.last.request.url.params
    assert sent_params["apikey"] == "123"
    assert sent_params["t"] == "movie"
    assert sent_params["q"] == "The Summit of the Gods"

@respx.mock
async def test_search_timeout(provider: JackettProvider):
    respx.get("http://jackett:9117/api/v2.0/indexers/all/results/torznab/api").side_effect = (
        httpx.ReadTimeout("Jackett is taking too long to respond")
    )

    query = SeriesQuery(title="Call of the Night", season=1, episode=1)

    with pytest.raises(ProviderTimeoutError):
        await provider.search(query)