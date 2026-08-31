import httpx
import pytest
import respx
from httpx import Response

from saga.models.query import MovieQuery, SeriesQuery
from saga.providers.exceptions import ProviderStatusError, ProviderTimeoutError
from saga.providers.jackett import JackettProvider
from tests.samples.jackett_mock_sample import THE_SUMMIT_OF_THE_GODS
from tests.samples.xml_sample import XML_NO_VALID_ITEM, XML_TWO_VALID_ITEM


@pytest.fixture
async def provider():
    p = JackettProvider(
        base_url="http://jackett:9117",
        api_key="123",
    )
    try:
        yield p
    finally:
        await p.client.aclose()


@respx.mock
async def test_jackett_movie(provider: JackettProvider):
    route = respx.get("http://jackett:9117/api/v2.0/indexers/all/results/torznab/api").respond(
        status_code=200,
        text=THE_SUMMIT_OF_THE_GODS,
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
async def test_jackett_series_three_calls(provider: JackettProvider):
    route = respx.get("http://jackett:9117/api/v2.0/indexers/all/results/torznab/api").mock(
        side_effect=[
            Response(200, text=XML_TWO_VALID_ITEM),
            Response(200, text=XML_NO_VALID_ITEM),
            Response(200, text=THE_SUMMIT_OF_THE_GODS),
        ]
    )

    query = SeriesQuery(title="Cowboy Bebop", season=1, episode=1)
    result = await provider.search(query)

    assert route.call_count == 3
    assert len(result) == 4

    first_params = route.calls[0].request.url.params
    assert first_params["t"] == "tvsearch"
    assert first_params["q"] == "Cowboy Bebop"
    assert first_params["season"] == "1"
    assert first_params["ep"] == "1"

    second_params = route.calls[1].request.url.params
    assert second_params["t"] == "tvsearch"
    assert second_params["season"] == "1"
    assert "ep" not in second_params

    third_params = route.calls[2].request.url.params
    assert third_params["t"] == "tvsearch"
    assert "season" not in third_params
    assert "ep" not in third_params


@respx.mock
async def test_jackett_series_dedup_case_insensitive(provider: JackettProvider):
    xml_upper = XML_TWO_VALID_ITEM.replace(
        "ad07c84915b3e82834c1523fbc12ca03ea5548bc",
        "AD07C84915B3E82834C1523FBC12CA03EA5548BC",
    )
    route = respx.get("http://jackett:9117/api/v2.0/indexers/all/results/torznab/api").mock(
        side_effect=[
            Response(200, text=XML_TWO_VALID_ITEM),
            Response(200, text=xml_upper),
            Response(200, text=XML_NO_VALID_ITEM),
        ]
    )
    query = SeriesQuery(title="Cowboy Bebop", season=1, episode=1)
    result = await provider.search(query)

    assert route.call_count == 3
    assert len(result) == 2
    hashes = [t.info_hash for t in result]
    assert hashes == [h.lower() for h in hashes]


@respx.mock
async def test_jackett_empty_result(provider: JackettProvider):
    respx.get("http://jackett:9117/api/v2.0/indexers/all/results/torznab/api").respond(
        status_code=200,
        text=XML_NO_VALID_ITEM,
    )
    query = MovieQuery(title="No Result Movie")
    result = await provider.search(query)
    assert result == []


@respx.mock
async def test_jackett_http_error_movie(provider: JackettProvider):
    respx.get("http://jackett:9117/api/v2.0/indexers/all/results/torznab/api").respond(
        status_code=500,
        text="Internal Server Error",
    )
    query = MovieQuery(title="Error Movie")
    with pytest.raises(ProviderStatusError):
        await provider.search(query)


@respx.mock
async def test_jackett_http_error_series(provider: JackettProvider):
    respx.get("http://jackett:9117/api/v2.0/indexers/all/results/torznab/api").respond(
        status_code=403,
        text="Forbidden",
    )
    query = SeriesQuery(title="Error Series", season=1, episode=1)
    with pytest.raises(ProviderStatusError):
        await provider.search(query)


@respx.mock
async def test_search_timeout(provider: JackettProvider):
    respx.get("http://jackett:9117/api/v2.0/indexers/all/results/torznab/api").side_effect = (
        httpx.ReadTimeout("Jackett is taking too long to respond")
    )

    query = SeriesQuery(title="Call of the Night", season=1, episode=1)

    with pytest.raises(ProviderTimeoutError):
        await provider.search(query)
