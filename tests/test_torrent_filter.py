from saga.filter.torrent_filter import (
    _filter_raw_torrents_movie,
    _filter_raw_torrents_series,
    filter_raw_torrents,
)
from saga.models.query import MovieQuery, SeriesQuery
from saga.models.torrent import RawTorrent


def make(title: str) -> RawTorrent:
    return RawTorrent(
        title=title, info_hash="abc123", magnet="magnet:?xt=urn:btih:abc123"
    )


def test_series_no_season_no_episode_kept():
    q = SeriesQuery(title="Call of the Night", season=2, episode=5)
    raw = [make("Call of the Night 1080p Remux")]
    assert len(_filter_raw_torrents_series(raw, q)) == 1


def test_series_season_pack_kept():
    q = SeriesQuery(title="Call of the Night", season=2, episode=5)
    raw = [make("Call of the Night S02 1080p")]
    assert len(_filter_raw_torrents_series(raw, q)) == 1


def test_series_exact_episode_kept():
    q = SeriesQuery(title="Call of the Night", season=2, episode=5)
    raw = [make("Call of the Night S02E05 1080p")]
    assert len(_filter_raw_torrents_series(raw, q)) == 1


def test_series_wrong_episode_filtered():
    q = SeriesQuery(title="Call of the Night", season=2, episode=5)
    raw = [make("Call of the Night S02E06 1080p")]
    assert len(_filter_raw_torrents_series(raw, q)) == 0


def test_series_wrong_season_filtered():
    q = SeriesQuery(title="Call of the Night", season=2, episode=5)
    raw = [make("Call of the Night S01E05 1080p")]
    assert len(_filter_raw_torrents_series(raw, q)) == 0


def test_series_wrong_season_no_episode_filtered():
    q = SeriesQuery(title="Call of the Night", season=2, episode=5)
    raw = [make("Call of the Night S01 1080p")]
    assert len(_filter_raw_torrents_series(raw, q)) == 0


def test_series_multiple_episodes_kept_if_contains_target():
    q = SeriesQuery(title="Show", season=2, episode=5)
    raw = [make("Show S02E05E06 1080p")]
    assert len(_filter_raw_torrents_series(raw, q)) == 1


def test_series_multiple_episodes_filtered_if_not_contains_target():
    q = SeriesQuery(title="Show", season=2, episode=5)
    raw = [make("Show S02E06E07 1080p")]
    assert len(_filter_raw_torrents_series(raw, q)) == 0


def test_series_mixed_list_filters_correctly():
    q = SeriesQuery(title="Call of the Night", season=2, episode=5)
    raw = [
        make("Call of the Night S02E05 1080p"),  # keep
        make("Call of the Night S02E06 1080p"),  # filter
        make("Call of the Night S02 1080p"),  # keep (season pack)
        make("Call of the Night 1080p"),  # keep (no info)
        make("Call of the Night S01E05 1080p"),  # filter
    ]
    result = _filter_raw_torrents_series(raw, q)
    assert len(result) == 3
    titles = [r.title for r in result]
    assert "Call of the Night S02E05 1080p" in titles
    assert "Call of the Night S02 1080p" in titles
    assert "Call of the Night 1080p" in titles


def test_series_empty_list():
    q = SeriesQuery(title="Show", season=1, episode=1)
    assert _filter_raw_torrents_series([], q) == []


def test_movie_no_season_no_episode_kept():
    q = MovieQuery(title="The Summit of the Gods")
    raw = [make("The Summit of the Gods 2021 1080p")]
    assert len(_filter_raw_torrents_movie(raw, q)) == 1


def test_movie_with_season_filtered():
    q = MovieQuery(title="The Summit of the Gods")
    raw = [make("The Summit of the Gods S01E01 1080p")]
    assert len(_filter_raw_torrents_movie(raw, q)) == 0


def test_movie_with_episode_filtered():
    q = MovieQuery(title="Movie")
    raw = [make("Movie S02E05 1080p")]
    assert len(_filter_raw_torrents_movie(raw, q)) == 0


def test_movie_with_season_only_filtered():
    q = MovieQuery(title="Movie")
    raw = [make("Movie S02 1080p")]
    assert len(_filter_raw_torrents_movie(raw, q)) == 0


def test_movie_no_info_kept_even_with_year():
    q = MovieQuery(title="Movie", year=2021)
    raw = [make("Movie 2021 2160p Remux")]
    assert len(_filter_raw_torrents_movie(raw, q)) == 1


def test_movie_mixed_list():
    q = MovieQuery(title="Movie")
    raw = [
        make("Movie 2021 1080p"),  # keep
        make("Movie S01E01 1080p"),  # filter
        make("Movie S02 1080p"),  # filter
    ]
    result = _filter_raw_torrents_movie(raw, q)
    assert len(result) == 1
    assert result[0].title == "Movie 2021 1080p"


def test_movie_empty_list():
    q = MovieQuery(title="Movie")
    assert _filter_raw_torrents_movie([], q) == []


# --- Dispatcher ---


def test_filter_raw_torrents_dispatch_series():
    q = SeriesQuery(title="Show", season=1, episode=1)
    raw = [make("Show S01E01 1080p")]
    assert len(filter_raw_torrents(raw, q)) == 1


def test_filter_raw_torrents_dispatch_movie():
    q = MovieQuery(title="Movie")
    raw = [make("Movie 2021 1080p")]
    assert len(filter_raw_torrents(raw, q)) == 1


def test_filter_preserves_objects():
    q = SeriesQuery(title="Show", season=1, episode=1)
    r1 = make("Show S01E01 1080p")
    r2 = make("Show S01E02 1080p")
    result = filter_raw_torrents([r1, r2], q)
    assert result[0] is r1
