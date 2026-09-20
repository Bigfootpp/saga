from __future__ import annotations

import re
from typing import Any

import guessit
from pydantic import BaseModel, Field

EDITION_MODIFIERS = [
    "director's cut",
    "directors cut",
    "special edition",
    "the animation",
    "open matte",
    "web series",
    "tv series",
    "the series",
    "remastered",
    "intégrale",
    "integrale",
    "theatrical",
    "re-encoded",
    "remaster",
    "restored",
    "criterion",
    "extended",
    "integral",
    "complete",
    "henshuu",
    "henshū",
    "unrated",
    "custom",
    "henshu",
    "repack",
    "proper",
    "hybrid",
    "uncut",
    "batch",
    "recap",
    "remux",
    "imax",
]

_sorted_modifiers = sorted(EDITION_MODIFIERS, key=len, reverse=True)
_pattern = re.compile(
    r"\b(" + "|".join(re.escape(m) for m in _sorted_modifiers) + r")\b",
    flags=re.IGNORECASE,
)


def clean_title(title: str) -> str:
    cleaned = _pattern.sub("", title)

    cleaned = re.sub(r"[\s:\-_]+$", "", cleaned)
    cleaned = re.sub(r"^[\s:\-_]+", "", cleaned)

    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    return cleaned


class GuessitResult(BaseModel):
    title: str | None = None
    type: str | None = None
    seasons: list[int] = Field(default_factory=list)
    episodes: list[int] = Field(default_factory=list)
    year: int | None = None
    audio_languages: list[str] = Field(default_factory=list)
    subtitle_languages: list[str] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict, repr=False)
    raw_text: str

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
    seasons = [season for season in seasons if season < 61]
    episodes = _to_int_list(raw.get("episode"))
    title = raw.get("title")
    return GuessitResult(
        title=clean_title(title) if isinstance(title, str) else None,
        type=raw.get("type") if isinstance(raw.get("type"), str) else None,
        seasons=seasons,
        episodes=episodes,
        year=_to_int_or_none(raw.get("year")),
        audio_languages=_to_lang_list(raw.get("language")),
        subtitle_languages=_to_lang_list(raw.get("subtitle_language")),
        raw=dict(raw),
        raw_text=value,
    )


def parse(value: str) -> GuessitResult:
    return parse_guessit(value)
