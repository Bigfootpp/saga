from pydantic import BaseModel, ConfigDict, Field


class UserPreferences(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    preferred_dubs: list[str] = Field(..., alias="preferredDubs")
    dub_max_results: int = Field(5, alias="dubMaxResult")
    other_max_results: int = Field(10, alias="otherMaxResult")
