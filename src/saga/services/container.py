from saga.models.stream import Stream
from saga.models.torrent import RawTorrent, ResolvedTorrent
from saga.services.matching import (
    check_torrent_coverage,
    contain_dubs,
    extract_audio_languages,
    find_file_idx,
    matches_titles,
    parse_trackers,
)


class RawTorrentContainer:
    def __init__(
        self,
        titles: list[str],
        dubs: list[str],
        original_language: str,
        episode: int | None,
        season: int | None,
    ) -> None:
        self._dub_torrents: list[RawTorrent] = []
        self._other_torrents: list[RawTorrent] = []
        self._titles = titles
        self._dubs = dubs
        self.original_language = original_language
        self._season = season
        self._episode = episode

    def add_torrents(self, raw_torrents: list[RawTorrent]):
        for torrent in raw_torrents:
            if (
                (torrent.seeders > 0)
                and (
                    self._episode is not None
                    and self._season is not None
                    and check_torrent_coverage(
                        torrent.title, episode=self._episode, season=self._season
                    )
                )
                and matches_titles(torrent.title, titles=self._titles)
            ):
                if contain_dubs(torrent.title, self._dubs, self.original_language):
                    self._dub_torrents.append(torrent)
                else:
                    self._other_torrents.append(torrent)

    @property
    def dubs(self) -> list[RawTorrent]:
        return self._dub_torrents

    @property
    def others(self) -> list[RawTorrent]:
        return self._other_torrents

    @property
    def torrents(self) -> list[RawTorrent]:
        return self._dub_torrents + self._other_torrents


class StreamContainer:
    def __init__(
        self,
        season: int,
        episode: int,
        original_language: str,
        abs_episode: int | None = None,
    ) -> None:
        self._season = season
        self._episode = episode
        self._abs_episode = abs_episode
        self._original_language = original_language
        self._streams: list[Stream] = []

    def add_torrents(self, torrent: ResolvedTorrent) -> bool:
        file_idx = find_file_idx(
            torrent, self._season, self._episode, self._abs_episode
        )
        if file_idx is not None:
            stream = Stream(
                torrent_name=torrent.title,
                raw_name=torrent.files[file_idx].file_name,
                dubs_language=extract_audio_languages(
                    torrent.title, original_language=self._original_language
                ),
                info_hash=torrent.info_hash,
                file_idx=file_idx,
                sources=parse_trackers(torrent.magnet),
            )
            self._streams.append(stream)
            return True
        return False

    @property
    def streams(self) -> list[Stream]:
        return self._streams
