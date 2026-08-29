from pydantic import BaseModel


class Metadata(BaseModel):
    titles: dict[str, str]