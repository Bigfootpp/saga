from pydantic import BaseModel, ConfigDict, Field


class BehaviorHints(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    configurable: bool = True
    configuration_required: bool = Field(default=False, alias="configurationRequired")


class ManifestResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    id: str
    name: str
    version: str
    description: str
    icon: str
    resources: list[str]
    types: list[str]
    catalogs: list[dict]
    behavior_hints: BehaviorHints = Field(
        default_factory=lambda: BehaviorHints(), alias="behaviorHints"
    )
