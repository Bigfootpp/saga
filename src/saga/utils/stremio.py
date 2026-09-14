from itertools import chain

from saga.models.stream import StreamResult, StremioStream, StremioStreamResult
from saga.services.formatter import Formatter


def parse_series_id(full_id: str) -> tuple[str, int, int] | None:
    if full_id.startswith("tt") and full_id.find(":") and full_id.rfind(":"):
        splitted_id = full_id.split(":")
        series_id = splitted_id[0]
        season = int(splitted_id[1])
        episode = int(splitted_id[2])
        return series_id, season, episode


def convert_to_stremio_stream_result(
    stream_result: StreamResult, name: str, formatter: Formatter
) -> StremioStreamResult:
    results: list[StremioStream] = []
    for stream in chain(stream_result.dubs_stream, stream_result.others):
        results.append(
            StremioStream(
                name=name,
                description=formatter.format(stream.raw_name),
                fileIdx=stream.file_idx,
                infoHash=stream.info_hash,
                sources=[f"tracker:{source}" for source in stream.sources],
            )
        )

    return StremioStreamResult(streams=results)
