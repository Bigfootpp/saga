import json

import httpx
import pytest
import respx

from saga.metadata.exceptions import MetadataTimeoutError
from saga.metadata.tmdb import TMDBMetadataProvider
from saga.models.metadata import MediaType, MetadataQuery
from tests.samples.tmdb_mock_sample import TSOTG_FIND_MOCK, TSOTG_TRANSLATIONS_MOCK


@pytest.fixture
async def provider():
    yield TMDBMetadataProvider(
        api_key="123"
    )

@respx.mock
async def test_jackett_series(provider: TMDBMetadataProvider):
    imdb_id = "tt7014378"

    tsotg_find_json: dict = json.loads(TSOTG_FIND_MOCK)

    route1 = respx.get(f"{provider.base_url}/find/{imdb_id}").respond(
        status_code=200,
        text=TSOTG_FIND_MOCK
    )
    route2 = respx.get(f"{provider.base_url}/movie/{tsotg_find_json["movie_results"][0]["id"]}").respond(
        status_code=200,
        text=TSOTG_TRANSLATIONS_MOCK
    )

    query = MetadataQuery(
        type = MediaType.MOVIE,
        id=imdb_id
    )

    result = await provider.get_metadata(query)
    assert result
    assert result.titles["en"] == "The Summit of the Gods"
    assert result.titles["fr"] == "Le Sommet des dieux"

    assert route1.called and route2.called
    sent_params_route1 = route1.calls.last.request.url.params
    sent_params_route2 = route2.calls.last.request.url.params
    assert sent_params_route1["api_key"] == "123" and sent_params_route2["api_key"] == "123"

@respx.mock
async def test_search_timeout(provider: TMDBMetadataProvider):
    imdb_id = "tt2560140"

    respx.get(f"{provider.base_url}/find/{imdb_id}").side_effect = (
        httpx.ReadTimeout("Jackett is taking too long to respond")
    )

    query = MetadataQuery(
        type = MediaType.SERIES,
        id="tt2560140"
    )

    with pytest.raises(MetadataTimeoutError):
        await provider.get_metadata(query)