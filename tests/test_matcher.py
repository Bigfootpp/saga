import pytest

from saga.filter.matcher import NoMatchError, _filter_files, find_file_idx
from saga.models.query import SeriesQuery
from saga.models.torrent import ResolvedTorrent, TorrentFileEntry


def make_entry(idx: int, file_name: str, path: str | None = None) -> TorrentFileEntry:
    return TorrentFileEntry(file_idx=idx, file_name=file_name, path=path or file_name, size=1000 + idx)


def make_torrent(files: list[TorrentFileEntry]) -> ResolvedTorrent:
    return ResolvedTorrent(title="Test", info_hash="abc123", magnet="magnet:?xt=urn:btih:abc123", files=files)


# --- _filter_files ---


def test_filter_files_no_season_kept():
    files = [make_entry(0, "Movie 2021.mkv"), make_entry(1, "E05.mkv")]
    # Both have no seasons -> kept
    assert len(_filter_files(files, season=2)) == 2


def test_filter_files_matching_single_season_kept():
    files = [make_entry(0, "[Shroud] Call of the Night S02E05.mkv")]
    assert len(_filter_files(files, season=2)) == 1


def test_filter_files_non_matching_single_season_filtered():
    files = [make_entry(0, "Show S01E05.mkv")]
    assert len(_filter_files(files, season=2)) == 0


def test_filter_files_season_pack_single_season_kept():
    files = [make_entry(0, "Show S02.mkv")]
    assert len(_filter_files(files, season=2)) == 1


def test_filter_files_season_pack_wrong_season_filtered():
    files = [make_entry(0, "Show S01.mkv")]
    assert len(_filter_files(files, season=2)) == 0


def test_filter_files_multiple_seasons_filtered():
    files = [make_entry(0, "Show S01 S02.mkv")]
    # RTN parses [1, 2] -> len !=1 -> filtered even if contains target season
    assert len(_filter_files(files, season=2)) == 0


def test_filter_files_mixed():
    files = [
        make_entry(0, "S02E05.mkv"),  # keep (match)
        make_entry(1, "S01E05.mkv"),  # filter (wrong season)
        make_entry(2, "Movie.mkv"),  # keep (no season)
        make_entry(3, "S02.mkv"),  # keep (season pack)
    ]
    result = _filter_files(files, season=2)
    assert [f.file_idx for f in result] == [0, 2, 3]


def test_filter_files_empty():
    assert _filter_files([], season=1) == []


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
            make_entry(0, "[Shroud] Call of the Night Season 2 - S02E01 - That Time`s Not for Us. (1080p BD REMUX AVC FLAC) [8403377E].mkv"),
            make_entry(4, "[Shroud] Call of the Night Season 2 - S02E05 - The Few Years I Spent with You... (1080p BD REMUX AVC FLAC) [02946E1D].mkv"),
            make_entry(5, "[Shroud] Call of the Night Season 2 - S02E06 - I`m Not Asking About the Quality! (1080p BD REMUX AVC FLAC) [554BD3F2].mkv"),
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
