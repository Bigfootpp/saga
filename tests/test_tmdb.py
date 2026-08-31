import json

import httpx
import pytest
import respx

from saga.metadata.exceptions import MetadataStatusError, MetadataTimeoutError
from saga.metadata.tmdb import (
    IMDbIDNotFoundError,
    InvalidIMDbIDError,
    TMDBMetadataProvider,
)
from saga.models.metadata import MediaType, MetadataQuery

# Inline mocks — self-contained like test_torrent_resolver.py
TSOTG_FIND_MOCK = json.dumps(
    {
        "movie_results": [
            {
                "id": 712454,
                "title": "The Summit of the Gods",
                "original_title": "Le Sommet des dieux",
            }
        ],
        "tv_results": [],
    }
)
TSOTG_TRANSLATIONS_MOCK = json.dumps(
    {
        "id": 712454,
        "original_language": "fr",
        "original_title": "Le Sommet des dieux",
        "translations": {
            "translations": [
                {
                    "iso_3166_1": "US",
                    "iso_639_1": "en",
                    "name": "English",
                    "english_name": "English",
                    "data": {"title": "The Summit of the Gods"},
                },
                {
                    "iso_3166_1": "FR",
                    "iso_639_1": "fr",
                    "name": "Français",
                    "english_name": "French",
                    "data": {"title": ""},
                },
                {
                    "iso_3166_1": "ES",
                    "iso_639_1": "es",
                    "name": "Español",
                    "english_name": "Spanish",
                    "data": {"title": "La cumbre de los dioses"},
                },
            ]
        },
    }
)
AOT_FIND_MOCK = json.dumps(
    {
        "movie_results": [],
        "tv_results": [
            {"id": 1429, "name": "Attack on Titan", "original_name": "進撃の巨人"}
        ],
    }
)
AOT_TRANSLATIONS_MOCK = json.dumps(
    {
        "id": 1429,
        "original_language": "ja",
        "original_name": "進撃の巨人",
        "status": "Ended",
        "translations": {
            "translations": [
                {
                    "iso_3166_1": "US",
                    "iso_639_1": "en",
                    "name": "English",
                    "english_name": "English",
                    "data": {"name": "Attack on Titan"},
                },
                {
                    "iso_3166_1": "FR",
                    "iso_639_1": "fr",
                    "name": "Français",
                    "english_name": "French",
                    "data": {"name": "L'Attaque des Titans"},
                },
                {
                    "iso_3166_1": "JP",
                    "iso_639_1": "ja",
                    "name": "日本語",
                    "english_name": "Japanese",
                    "data": {"name": ""},
                },
            ]
        },
    }
)


@pytest.fixture
async def provider():
    p = TMDBMetadataProvider(api_key="123")
    try:
        yield p
    finally:
        await p.client.aclose()


@respx.mock
async def test_tmdb_movie_success(provider: TMDBMetadataProvider):
    imdb_id = "tt7014378"
    tsotg_find_json: dict = json.loads(TSOTG_FIND_MOCK)
    route1 = respx.get(f"{provider.base_url}/find/{imdb_id}").respond(
        status_code=200, text=TSOTG_FIND_MOCK
    )
    route2 = respx.get(
        f"{provider.base_url}/movie/{tsotg_find_json['movie_results'][0]['id']}"
    ).respond(status_code=200, text=TSOTG_TRANSLATIONS_MOCK)
    query = MetadataQuery(type=MediaType.MOVIE, id=imdb_id)
    result = await provider.get_metadata(query)

    assert result.titles["en"] == "The Summit of the Gods"
    assert result.titles["fr"] == "Le Sommet des dieux"
    assert route1.called and route2.called
    assert route1.calls.last.request.url.params["api_key"] == "123"
    assert route1.calls.last.request.url.params["external_source"] == "imdb_id"
    assert route2.calls.last.request.url.params["api_key"] == "123"
    assert route2.calls.last.request.url.params["append_to_response"] == "translations"


@respx.mock
async def test_tmdb_series_success(provider: TMDBMetadataProvider):
    imdb_id = "tt2560140"
    aot_find_json: dict = json.loads(AOT_FIND_MOCK)
    route1 = respx.get(f"{provider.base_url}/find/{imdb_id}").respond(
        status_code=200, text=AOT_FIND_MOCK
    )
    route2 = respx.get(
        f"{provider.base_url}/tv/{aot_find_json['tv_results'][0]['id']}"
    ).respond(status_code=200, text=AOT_TRANSLATIONS_MOCK)
    query = MetadataQuery(type=MediaType.SERIES, id=imdb_id)
    result = await provider.get_metadata(query)

    assert result.titles["en"] == "Attack on Titan"
    assert result.titles["fr"] == "L'Attaque des Titans"
    assert result.titles["ja"] == "進撃の巨人"
    assert route1.called and route2.called


@respx.mock
async def test_tmdb_empty_title_filtered(provider: TMDBMetadataProvider):
    imdb_id = "tt7014378"
    tsotg_find_json: dict = json.loads(TSOTG_FIND_MOCK)
    respx.get(f"{provider.base_url}/find/{imdb_id}").respond(
        status_code=200, text=TSOTG_FIND_MOCK
    )
    respx.get(
        f"{provider.base_url}/movie/{tsotg_find_json['movie_results'][0]['id']}"
    ).respond(status_code=200, text=TSOTG_TRANSLATIONS_MOCK)
    query = MetadataQuery(type=MediaType.MOVIE, id=imdb_id)
    result = await provider.get_metadata(query)

    assert result.titles["fr"] == "Le Sommet des dieux"
    assert result.titles["es"] == "La cumbre de los dioses"
    assert "en" in result.titles


async def test_tmdb_invalid_imdb_id(provider: TMDBMetadataProvider):
    query = MetadataQuery(type=MediaType.MOVIE, id="7014378")
    with pytest.raises(InvalidIMDbIDError):
        await provider.get_metadata(query)
    query2 = MetadataQuery(type=MediaType.MOVIE, id="invalid")
    with pytest.raises(InvalidIMDbIDError):
        await provider.get_metadata(query2)


@respx.mock
async def test_tmdb_not_found(provider: TMDBMetadataProvider):
    imdb_id = "tt0000000"
    respx.get(f"{provider.base_url}/find/{imdb_id}").respond(
        status_code=200, text=json.dumps({"movie_results": [], "tv_results": []})
    )
    query = MetadataQuery(type=MediaType.MOVIE, id=imdb_id)
    with pytest.raises(IMDbIDNotFoundError):
        await provider.get_metadata(query)


@respx.mock
async def test_tmdb_status_error_on_find(provider: TMDBMetadataProvider):
    imdb_id = "tt7014378"
    respx.get(f"{provider.base_url}/find/{imdb_id}").respond(
        status_code=401, text="Unauthorized"
    )
    query = MetadataQuery(type=MediaType.MOVIE, id=imdb_id)
    with pytest.raises(MetadataStatusError, match="401"):
        await provider.get_metadata(query)


@respx.mock
async def test_tmdb_status_error_on_details(provider: TMDBMetadataProvider):
    imdb_id = "tt7014378"
    tsotg_find_json: dict = json.loads(TSOTG_FIND_MOCK)
    respx.get(f"{provider.base_url}/find/{imdb_id}").respond(
        status_code=200, text=TSOTG_FIND_MOCK
    )
    respx.get(
        f"{provider.base_url}/movie/{tsotg_find_json['movie_results'][0]['id']}"
    ).respond(status_code=404, text="Not Found")
    query = MetadataQuery(type=MediaType.MOVIE, id=imdb_id)
    with pytest.raises(MetadataStatusError, match="404"):
        await provider.get_metadata(query)


@respx.mock
async def test_tmdb_timeout_on_find(provider: TMDBMetadataProvider):
    imdb_id = "tt2560140"
    respx.get(f"{provider.base_url}/find/{imdb_id}").side_effect = httpx.ReadTimeout(
        "TMDB is taking too long to respond"
    )
    query = MetadataQuery(type=MediaType.SERIES, id="tt2560140")
    with pytest.raises(MetadataTimeoutError):
        await provider.get_metadata(query)


@respx.mock
async def test_tmdb_timeout_on_details(provider: TMDBMetadataProvider):
    imdb_id = "tt7014378"
    tsotg_find_json: dict = json.loads(TSOTG_FIND_MOCK)
    respx.get(f"{provider.base_url}/find/{imdb_id}").respond(
        status_code=200, text=TSOTG_FIND_MOCK
    )
    respx.get(
        f"{provider.base_url}/movie/{tsotg_find_json['movie_results'][0]['id']}"
    ).side_effect = httpx.ReadTimeout("TMDB is taking too long to respond")
    query = MetadataQuery(type=MediaType.MOVIE, id=imdb_id)
    with pytest.raises(MetadataTimeoutError):
        await provider.get_metadata(query)


@respx.mock
async def test_search_timeout(provider: TMDBMetadataProvider):
    imdb_id = "tt2560140"
    respx.get(f"{provider.base_url}/find/{imdb_id}").side_effect = httpx.ReadTimeout(
        "Jackett is taking too long to respond"
    )
    query = MetadataQuery(type=MediaType.SERIES, id="tt2560140")
    with pytest.raises(MetadataTimeoutError):
        await provider.get_metadata(query)
