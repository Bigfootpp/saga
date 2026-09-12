from pydantic import BaseModel


class RankOptions(BaseModel):
    preferred_subs: list[str]
    preferred_dubs: list[str]
