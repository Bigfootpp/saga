from itertools import chain

from saga.models.stream import StreamResult, StremioStream, StremioStreamResult
from saga.services.formatter import Formatter


def parse_series_id(full_id: str) -> tuple[str, int, int] | None:
    parts = full_id.split(":")
    if len(parts) == 3 and parts[0].startswith("tt"):
        series_id, season, episode = parts
    elif len(parts) == 4 and parts[0] == "kitsu":
        series_id = f"{parts[0]}:{parts[1]}"
        season, episode = parts[2], parts[3]
    else:
        return None
    try:
        return series_id, int(season), int(episode)
    except ValueError:
        return None


def convert_to_stremio_stream_result(
    stream_result: StreamResult, name: str, formatter: Formatter
) -> StremioStreamResult:
    results: list[StremioStream] = []
    for stream in chain(stream_result.dubs_stream, stream_result.others):
        results.append(
            StremioStream(
                name=name,
                description=formatter.format(stream.torrent_name),
                fileIdx=stream.file_idx,
                infoHash=stream.info_hash,
                sources=[f"tracker:{source}" for source in stream.sources],
            )
        )

    return StremioStreamResult(streams=results)
