from pydantic import BaseModel


class UserPreferences(BaseModel):
    preferred_dubs: list[str]
    dubs_max_result: int = 5
    other_max_results: int = 10
