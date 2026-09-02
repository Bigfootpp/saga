import pathlib
from unittest.mock import patch

import httpx
import pytest
import respx

from saga.models.torrent import RawTorrent, TorrentFileEntry
from saga.torrent.exceptions import TorrentResolveError
from saga.torrent.resolver import TorrentResolver

TORRENT_PATH = (
    pathlib.Path(__file__).parent / "samples" / "torrents" / "call_of_the_night.torrent"
)
TORRENT_BYTES = TORRENT_PATH.read_bytes()

EXPECTED_FILES = [
    TorrentFileEntry(
        file_idx=0,
        file_name="[Shroud] Call of the Night Season 2 - S02E01 - That Time`s Not for Us. (1080p BD REMUX AVC FLAC) [8403377E].mkv",
        path="[Shroud] Call of the Night Season 2 (1080p BD REMUX AVC FLAC)/[Shroud] Call of the Night Season 2 - S02E01 - That Time`s Not for Us. (1080p BD REMUX AVC FLAC) [8403377E].mkv",
        size=6031513350,
    ),
    TorrentFileEntry(
        file_idx=11,
        file_name="[Shroud] Call of the Night Season 2 - S02E12 - Call of the Night (1080p BD REMUX AVC FLAC) [CA1C957C].mkv",
        path="[Shroud] Call of the Night Season 2 (1080p BD REMUX AVC FLAC)/[Shroud] Call of the Night Season 2 - S02E12 - Call of the Night (1080p BD REMUX AVC FLAC) [CA1C957C].mkv",
        size=6252012944,
    ),
]


@pytest.fixture
async def client():
    c = httpx.AsyncClient()
    try:
        yield c
    finally:
        await c.aclose()


@pytest.fixture
def resolver(client: httpx.AsyncClient):
    return TorrentResolver(client=client, timeout=2.0)


def test_parse_torf_bytes_valid():
    entries = TorrentResolver._parse_torf_bytes(TORRENT_BYTES)
    assert len(entries) == 12
    assert entries[0] == EXPECTED_FILES[0]
    assert entries[-1] == EXPECTED_FILES[1]
    for e in entries:
        assert e.file_name == pathlib.Path(e.path).name
        assert e.size > 0


def test_parse_torf_bytes_invalid_raises():
    with pytest.raises(Exception):
        TorrentResolver._parse_torf_bytes(b"not a torrent")


@respx.mock
async def test_resolve_via_torrent_link_success(resolver: TorrentResolver):
    raw = RawTorrent(
        title="Call of the Night",
        info_hash="F3584460E77F6F7D5EA3327E0CC1B4C4F51DB1D2",
        magnet="magnet:?xt=urn:btih:f3584460e77f6f7d5ea3327e0cc1b4c4f51db1d2",
        torrent_link="http://example.com/call_of_the_night.torrent",
    )
    route = respx.get("http://example.com/call_of_the_night.torrent").respond(
        content=TORRENT_BYTES
    )

    with patch.object(TorrentResolver, "_fetch_via_libtorrent_sync") as mock_lt:
        resolved = await resolver.resolve(raw)
        mock_lt.assert_not_called()

    assert route.called
    assert resolved.title == "Call of the Night"
    assert resolved.info_hash == "f3584460e77f6f7d5ea3327e0cc1b4c4f51db1d2"
    assert resolved.magnet == raw.magnet
    assert len(resolved.files) == 12
    assert resolved.files[0].file_idx == 0
    assert resolved.files[0].path.endswith(
        "S02E01 - That Time`s Not for Us. (1080p BD REMUX AVC FLAC) [8403377E].mkv"
    )
    assert resolved.files[0].size == 6031513350
    assert resolved.files[11].size == 6252012944


@respx.mock
async def test_resolve_via_torrent_link_http_error_fallback(resolver: TorrentResolver):
    raw = RawTorrent(
        title="Call of the Night",
        info_hash="f3584460e77f6f7d5ea3327e0cc1b4c4f51db1d2",
        magnet="magnet:?xt=urn:btih:f3584460e77f6f7d5ea3327e0cc1b4c4f51db1d2",
        torrent_link="http://example.com/bad.torrent",
    )
    respx.get("http://example.com/bad.torrent").respond(status_code=404)

    fallback_entries = [
        TorrentFileEntry(file_idx=0, file_name="a.mkv", path="Folder/a.mkv", size=100),
        TorrentFileEntry(file_idx=1, file_name="b.mkv", path="Folder/b.mkv", size=200),
    ]

    with patch.object(
        TorrentResolver, "_fetch_via_libtorrent_sync", return_value=fallback_entries
    ) as mock_lt:
        resolved = await resolver.resolve(raw)
        mock_lt.assert_called_once_with(raw.magnet, resolver.timeout)

    assert len(resolved.files) == 2
    assert resolved.files[0].path == "Folder/a.mkv"


@respx.mock
async def test_resolve_via_torrent_link_invalid_bytes_fallback(
    resolver: TorrentResolver,
):
    raw = RawTorrent(
        title="Test",
        info_hash="abc",
        magnet="magnet:?xt=urn:btih:abc",
        torrent_link="http://example.com/invalid.torrent",
    )
    respx.get("http://example.com/invalid.torrent").respond(content=b"invalid bencode")

    fallback_entries = [TorrentFileEntry(file_idx=0, file_name="x.mkv", path="x.mkv", size=123)]

    with patch.object(
        TorrentResolver, "_fetch_via_libtorrent_sync", return_value=fallback_entries
    ):
        resolved = await resolver.resolve(raw)

    assert resolved.files[0].file_name == "x.mkv"


@respx.mock
async def test_resolve_without_torrent_link_uses_libtorrent(resolver: TorrentResolver):
    raw = RawTorrent(
        title="No Link",
        info_hash="ABCDEF",
        magnet="magnet:?xt=urn:btih:ABCDEF",
        torrent_link=None,
    )

    expected = [TorrentFileEntry(file_idx=0, file_name="f.mkv", path="f.mkv", size=456)]
    with patch.object(
        TorrentResolver, "_fetch_via_libtorrent_sync", return_value=expected
    ) as mock:
        resolved = await resolver.resolve(raw)
        mock.assert_called_once()

    assert resolved.info_hash == "abcdef"
    assert resolved.files == expected


@respx.mock
async def test_resolve_via_torrent_link_empty_content_fallback(
    resolver: TorrentResolver,
):
    raw = RawTorrent(
        title="Empty",
        info_hash="abc",
        magnet="magnet:?xt=urn:btih:abc",
        torrent_link="http://example.com/empty.torrent",
    )
    respx.get("http://example.com/empty.torrent").respond(content=b"")

    fallback = [TorrentFileEntry(file_idx=0, file_name="y.mkv", path="y.mkv", size=789)]
    with patch.object(
        TorrentResolver, "_fetch_via_libtorrent_sync", return_value=fallback
    ):
        resolved = await resolver.resolve(raw)

    assert resolved.files == fallback


@respx.mock
async def test_resolve_timeout_via_httpx_fallback(resolver: TorrentResolver):
    raw = RawTorrent(
        title="Timeout",
        info_hash="abc",
        magnet="magnet:?xt=urn:btih:abc",
        torrent_link="http://example.com/timeout.torrent",
    )
    respx.get("http://example.com/timeout.torrent").side_effect = httpx.ReadTimeout(
        "timeout"
    )

    fallback = [TorrentFileEntry(file_idx=0, file_name="z.mkv", path="z.mkv", size=999)]
    with patch.object(
        TorrentResolver, "_fetch_via_libtorrent_sync", return_value=fallback
    ):
        resolved = await resolver.resolve(raw)

    assert resolved.files == fallback


async def test_resolve_libtorrent_timeout_raises(resolver: TorrentResolver):
    raw = RawTorrent(
        title="Timeout LT",
        info_hash="abc",
        magnet="magnet:?xt=urn:btih:abc",
        torrent_link=None,
    )

    with (
        patch.object(
            TorrentResolver,
            "_fetch_via_libtorrent_sync",
            side_effect=TimeoutError("timeout"),
        ),
        pytest.raises(TorrentResolveError, match="Timeout"),
    ):
        await resolver.resolve(raw)


async def test_resolve_libtorrent_invalid_magnet_raises(resolver: TorrentResolver):
    raw = RawTorrent(
        title="Invalid",
        info_hash="abc",
        magnet="not a magnet",
        torrent_link=None,
    )

    def raise_invalid(*_args, **_kwargs):
        raise TorrentResolveError("Invalid magnet URI")

    with (
        patch.object(
            TorrentResolver, "_fetch_via_libtorrent_sync", side_effect=raise_invalid
        ),
        pytest.raises(TorrentResolveError, match="Invalid magnet"),
    ):
        await resolver.resolve(raw)


async def test_resolve_libtorrent_generic_error_wrapped(resolver: TorrentResolver):
    raw = RawTorrent(
        title="Error",
        info_hash="abc",
        magnet="magnet:?xt=urn:btih:abc",
        torrent_link=None,
    )

    with (
        patch.object(
            TorrentResolver,
            "_fetch_via_libtorrent_sync",
            side_effect=RuntimeError("boom"),
        ),
        pytest.raises(TorrentResolveError, match="Failed to resolve"),
    ):
        await resolver.resolve(raw)
