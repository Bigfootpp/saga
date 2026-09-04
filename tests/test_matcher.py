import pytest

from saga.models.query import MovieQuery, SeriesQuery
from saga.models.torrent import ResolvedTorrent, TorrentFileEntry
from saga.services.matching import NoMatchError, _valid_file, find_file_idx


def make_entry(idx: int, file_name: str, path: str | None = None) -> TorrentFileEntry:
    return TorrentFileEntry(
        file_idx=idx, file_name=file_name, path=path or file_name, size=1000 + idx
    )


def make_torrent(files: list[TorrentFileEntry]) -> ResolvedTorrent:
    return ResolvedTorrent(
        title="Test",
        info_hash="abc123",
        magnet="magnet:?xt=urn:btih:abc123",
        files=files,
    )


# --- _valid_file ---


def test_valid_file_no_season():
    assert _valid_file(make_entry(0, "Movie.mkv"), season=2) is True
    assert _valid_file(make_entry(0, "E05.mkv"), season=2) is True


def test_valid_file_matching_single_season():
    assert _valid_file(make_entry(0, "S02E05.mkv"), season=2) is True
    assert _valid_file(make_entry(0, "S02.mkv"), season=2) is True


def test_valid_file_non_matching_season():
    assert _valid_file(make_entry(0, "S01E05.mkv"), season=2) is False


def test_valid_file_multiple_seasons():
    assert _valid_file(make_entry(0, "S01 S02.mkv"), season=2) is False


# --- find_file_idx ---


def test_find_file_idx_exact_match():
    torrent = make_torrent(
        [
            make_entry(0, "[Shroud] Call of the Night S02E01.mkv"),
            make_entry(1, "[Shroud] Call of the Night S02E05.mkv"),
            make_entry(2, "[Shroud] Call of the Night S02E06.mkv"),
        ]
    )
    q = SeriesQuery(title="Call of the Night", season=2, episode=5)
    media = find_file_idx(torrent, q)
    assert media.file_idx == 1
    assert media.file_name == "[Shroud] Call of the Night S02E05.mkv"
    assert media.info_hash == "abc123"
    assert media.magnet == "magnet:?xt=urn:btih:abc123"


def test_find_file_idx_returns_first_match():
    torrent = make_torrent(
        [
            make_entry(5, "S02E05.mkv"),
            make_entry(7, "S02E05.mkv"),  # duplicate episode, first wins
        ]
    )
    q = SeriesQuery(title="Show", season=2, episode=5)
    media = find_file_idx(torrent, q)
    assert media.file_idx == 5


def test_find_file_idx_no_match_raises():
    torrent = make_torrent([make_entry(0, "S02E06.mkv"), make_entry(1, "S02E07.mkv")])
    q = SeriesQuery(title="Show", season=2, episode=5)
    with pytest.raises(NoMatchError, match="No matched file found"):
        find_file_idx(torrent, q)


def test_find_file_idx_season_filtered_before_episode():
    # File has correct episode but wrong season -> filtered out by _filter_files
    torrent = make_torrent([make_entry(0, "S01E05.mkv")])
    q = SeriesQuery(title="Show", season=2, episode=5)
    with pytest.raises(NoMatchError):
        find_file_idx(torrent, q)


def test_find_file_idx_file_with_no_season_but_episode_matches():
    # E05 has no season, _filter keeps it, then episode matches -> found
    torrent = make_torrent([make_entry(0, "E05.mkv")])
    q = SeriesQuery(title="Show", season=2, episode=5)
    media = find_file_idx(torrent, q)
    assert media.file_idx == 0


def test_find_file_idx_ignores_multi_episode():
    # S02E05E06 has episodes [5,6] len 2 -> not matched (requires len==1)
    torrent = make_torrent([make_entry(0, "S02E05E06.mkv")])
    q = SeriesQuery(title="Show", season=2, episode=5)
    with pytest.raises(NoMatchError):
        find_file_idx(torrent, q)


def test_find_file_idx_season_pack_no_episode_no_match():
    # S02 has no episode -> _filter keeps, but find requires episode -> no match
    torrent = make_torrent([make_entry(0, "S02.mkv")])
    q = SeriesQuery(title="Show", season=2, episode=5)
    with pytest.raises(NoMatchError):
        find_file_idx(torrent, q)


def test_find_file_idx_real_torrent_sample():
    # Use real file names from call_of_the_night.torrent
    torrent = make_torrent(
        [
            make_entry(
                0,
                "[Shroud] Call of the Night Season 2 - S02E01 - That Time`s Not for Us. (1080p BD REMUX AVC FLAC) [8403377E].mkv",
            ),
            make_entry(
                4,
                "[Shroud] Call of the Night Season 2 - S02E05 - The Few Years I Spent with You... (1080p BD REMUX AVC FLAC) [02946E1D].mkv",
            ),
            make_entry(
                5,
                "[Shroud] Call of the Night Season 2 - S02E06 - I`m Not Asking About the Quality! (1080p BD REMUX AVC FLAC) [554BD3F2].mkv",
            ),
        ]
    )
    q = SeriesQuery(title="Call of the Night", season=2, episode=5)
    media = find_file_idx(torrent, q)
    assert media.file_idx == 4


def test_find_file_idx_empty_torrent_raises():
    torrent = make_torrent([])
    q = SeriesQuery(title="Show", season=1, episode=1)
    with pytest.raises(NoMatchError):
        find_file_idx(torrent, q)


def test_find_file_idx_with_no_season_files():
    # No season in file name, but has episode -> should still match because _filter keeps no-season
    torrent = make_torrent([make_entry(0, "Movie.mkv")])
    q = SeriesQuery(title="Movie", season=1, episode=1)
    with pytest.raises(NoMatchError):
        find_file_idx(torrent, q)


def test_find_file_idx_movie_largest():
    torrent = make_torrent(
        [
            TorrentFileEntry(file_idx=0, file_name="a.mkv", path="a.mkv", size=100),
            TorrentFileEntry(file_idx=1, file_name="b.mkv", path="b.mkv", size=999),
            TorrentFileEntry(file_idx=2, file_name="c.mkv", path="c.mkv", size=500),
        ]
    )
    q = MovieQuery(title="Movie")
    media = find_file_idx(torrent, q)
    assert media.file_idx == 1
    assert media.file_name == "b.mkv"


def test_find_file_idx_movie_single_file():
    torrent = make_torrent([TorrentFileEntry(file_idx=0, file_name="movie.mkv", path="movie.mkv", size=1234)])
    q = MovieQuery(title="Movie", year=2021)
    media = find_file_idx(torrent, q)
    assert media.file_idx == 0


def test_resolved_torrent_inherits_raw():
    # ResolvedTorrent now inherits from RawTorrent
    torrent = ResolvedTorrent(
        title="Test",
        info_hash="ABC123",
        magnet="magnet:?xt=urn:btih:ABC123",
        torrent_link="http://example.com/file.torrent",
        files=[make_entry(0, "S01E01.mkv")],
    )
    assert torrent.title == "Test"
    assert torrent.torrent_link == "http://example.com/file.torrent"
    assert torrent.files[0].file_idx == 0
