from __future__ import annotations

from typing import Any

import guessit
from pydantic import BaseModel, Field


class GuessitParsed(BaseModel):
    title: str | None = None
    type: str | None = None
    seasons: list[int] = Field(default_factory=list)
    episodes: list[int] = Field(default_factory=list)
    season: int | None = None
    episode: int | None = None
    year: int | None = None
    raw: dict[str, Any] = Field(default_factory=dict, repr=False)

    @property
    def has_season(self) -> bool:
        return bool(self.seasons)

    @property
    def has_episode(self) -> bool:
        return bool(self.episodes)


def _to_int_list(value: Any) -> list[int]:
    if value is None:
        return []
    if isinstance(value, list):
        out: list[int] = []
        for v in value:
            try:
                out.append(int(v))
            except (TypeError, ValueError):
                continue
        return out
    try:
        return [int(value)]
    except (TypeError, ValueError):
        return []


def _to_int_or_none(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, list):
        if not value:
            return None
        try:
            return int(value[0])
        except (TypeError, ValueError):
            return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def parse_guessit(value: str) -> GuessitParsed:
    try:
        raw: dict[str, Any] = guessit.guessit(value)
    except Exception:
        raw = {}
    seasons = _to_int_list(raw.get("season"))
    episodes = _to_int_list(raw.get("episode"))
    return GuessitParsed(
        title=raw.get("title") if isinstance(raw.get("title"), str) else None,
        type=raw.get("type") if isinstance(raw.get("type"), str) else None,
        seasons=seasons,
        episodes=episodes,
        season=_to_int_or_none(raw.get("season")),
        episode=_to_int_or_none(raw.get("episode")),
        year=_to_int_or_none(raw.get("year")),
        raw=dict(raw),
    )


def parse(value: str) -> GuessitParsed:
    return parse_guessit(value)
