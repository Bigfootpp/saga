from __future__ import annotations

from typing import Any

import guessit
from pydantic import BaseModel, Field


class GuessitResult(BaseModel):
    title: str | None = None
    type: str | None = None
    seasons: list[int] = Field(default_factory=list)
    episodes: list[int] = Field(default_factory=list)
    year: int | None = None
    audio_languages: list[str] = Field(default_factory=list)
    subtitle_languages: list[str] = Field(default_factory=list)
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


def _lang_to_code(lang: Any) -> str | None:
    if lang is None:
        return None
    if isinstance(lang, str):
        return None if lang == "und" else lang
    try:
        s = str(lang)
        return None if s == "und" else s
    except Exception:
        return None


def _to_lang_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        out: list[str] = []
        for v in value:
            code = _lang_to_code(v)
            if code is not None:
                out.append(code)
        return out
    code = _lang_to_code(value)
    return [code] if code is not None else []


def parse_guessit(value: str) -> GuessitResult:
    try:
        raw: dict[str, Any] = guessit.guessit(value)
    except Exception:
        raw = {}
    seasons = _to_int_list(raw.get("season"))
    episodes = _to_int_list(raw.get("episode"))
    return GuessitResult(
        title=raw.get("title") if isinstance(raw.get("title"), str) else None,
        type=raw.get("type") if isinstance(raw.get("type"), str) else None,
        seasons=seasons,
        episodes=episodes,
        year=_to_int_or_none(raw.get("year")),
        audio_languages=_to_lang_list(raw.get("language")),
        subtitle_languages=_to_lang_list(raw.get("subtitle_language")),
        raw=dict(raw),
    )


def parse(value: str) -> GuessitResult:
    return parse_guessit(value)
