import httpx
import pytest
import respx
from httpx import Response

from saga.models.query import MovieQuery, SeriesQuery
from saga.providers.exceptions import ProviderStatusError, ProviderTimeoutError
from saga.providers.jackett import JackettProvider

# Inline samples — self-contained, no external files (like test_torrent_resolver.py)
THE_SUMMIT_OF_THE_GODS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:torznab="http://torznab.com/schemas/2015/feed"><channel>
<item><title>The Summit of the Gods</title><link>magnet:?xt=urn:btih:A9B5A8965470B5A29BFDA623330F9244FE3A2589</link>
<torznab:attr name="infohash" value="A9B5A8965470B5A29BFDA623330F9244FE3A2589" />
<torznab:attr name="magneturl" value="magnet:?xt=urn:btih:A9B5A8965470B5A29BFDA623330F9244FE3A2589" /></item>
<item><title>The Summit of the Gods</title><link>http://localhost:9117/dl/yts/?path=abc</link>
<torznab:attr name="infohash" value="07DC98E008C28B23859AAA915E6A3886428DD44F" />
<torznab:attr name="magneturl" value="magnet:?xt=urn:btih:07DC98E008C28B23859AAA915E6A3886428DD44F" /></item>
</channel></rss>"""

XML_TWO_VALID_ITEM = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:torznab="http://torznab.com/schemas/2015/feed"><channel>
<item><title>[PHTM] Cowboy Bebop - S01</title><link>magnet:?xt=urn:btih:ad07c84915b3e82834c1523fbc12ca03ea5548bc</link>
<torznab:attr name="infohash" value="ad07c84915b3e82834c1523fbc12ca03ea5548bc" />
<torznab:attr name="magneturl" value="magnet:?xt=urn:btih:ad07c84915b3e82834c1523fbc12ca03ea5548bc" /></item>
<item><title>[ReinForce] Class de 2 Banme</title><link>magnet:?xt=urn:btih:23df37b2380c80958fd9227a3616c3a74460a7c8</link>
<torznab:attr name="infohash" value="23df37b2380c80958fd9227a3616c3a74460a7c8" />
<torznab:attr name="magneturl" value="magnet:?xt=urn:btih:23df37b2380c80958fd9227a3616c3a74460a7c8" /></item>
</channel></rss>"""

XML_NO_VALID_ITEM = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:torznab="http://torznab.com/schemas/2015/feed"><channel>
<item><title>NoHash</title><link>http://example.com/file.torrent</link>
<torznab:attr name="magneturl" value="magnet:?xt=urn:btih:abc" /></item>
</channel></rss>"""


@pytest.fixture
async def provider():
    p = JackettProvider(base_url="http://jackett:9117", api_key="123")
    try:
        yield p
    finally:
        await p.client.aclose()


@respx.mock
async def test_jackett_movie(provider: JackettProvider):
    route = respx.get(
        "http://jackett:9117/api/v2.0/indexers/all/results/torznab/api"
    ).respond(status_code=200, text=THE_SUMMIT_OF_THE_GODS)
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
    route = respx.get(
        "http://jackett:9117/api/v2.0/indexers/all/results/torznab/api"
    ).mock(
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
    route = respx.get(
        "http://jackett:9117/api/v2.0/indexers/all/results/torznab/api"
    ).mock(
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
        status_code=200, text=XML_NO_VALID_ITEM
    )
    query = MovieQuery(title="No Result Movie")
    result = await provider.search(query)
    assert result == []


@respx.mock
async def test_jackett_http_error_movie(provider: JackettProvider):
    respx.get("http://jackett:9117/api/v2.0/indexers/all/results/torznab/api").respond(
        status_code=500, text="Internal Server Error"
    )
    query = MovieQuery(title="Error Movie")
    with pytest.raises(ProviderStatusError):
        await provider.search(query)


@respx.mock
async def test_jackett_http_error_series(provider: JackettProvider):
    respx.get("http://jackett:9117/api/v2.0/indexers/all/results/torznab/api").respond(
        status_code=403, text="Forbidden"
    )
    query = SeriesQuery(title="Error Series", season=1, episode=1)
    with pytest.raises(ProviderStatusError):
        await provider.search(query)


@respx.mock
async def test_search_timeout(provider: JackettProvider):
    respx.get(
        "http://jackett:9117/api/v2.0/indexers/all/results/torznab/api"
    ).side_effect = httpx.ReadTimeout("Jackett is taking too long to respond")
    query = SeriesQuery(title="Call of the Night", season=1, episode=1)
    with pytest.raises(ProviderTimeoutError):
        await provider.search(query)
