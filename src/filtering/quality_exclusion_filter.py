from typing import Any, ClassVar

from filtering.base_filter import BaseFilter


class QualityExclusionFilter(BaseFilter):
    RIPS: ClassVar[list[str]] = [
        "HDRIP",
        "BRRIP",
        "BDRIP",
        "WEBRIP",
        "TVRIP",
        "VODRIP",
    ]
    CAMS: ClassVar[list[str]] = [
        "CAM",
        "TS",
        "TC",
        "R5",
        "DVDSCR",
        "HDTV",
        "PDTV",
        "DSR",
        "WORKPRINT",
        "VHSRIP",
        "HDCAM",
    ]

    def filter(self, data: list[Any]) -> list[Any]:
        filtered_items = []
        excluded_qualities = [quality.upper() for quality in self.config.exclusion]
        rips = "RIPS" in excluded_qualities
        cams = "CAM" in excluded_qualities

        for stream in data:
            quality = stream.parsed_data.quality if stream.parsed_data else None
            if quality:
                quality_upper = quality.upper()
                if quality_upper in excluded_qualities:
                    continue
                if rips and quality_upper in self.RIPS:
                    continue
                if cams and quality_upper in self.CAMS:
                    continue
                filtered_items.append(stream)
            else:
                if "Unknown" not in excluded_qualities:
                    filtered_items.append(stream)

        return filtered_items

    def can_filter(self) -> bool:
        return len(self.config.exclusion) > 0
