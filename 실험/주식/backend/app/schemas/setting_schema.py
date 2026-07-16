from pydantic import BaseModel, ConfigDict, Field


class SettingUpsert(BaseModel):
    key: str = Field(min_length=1, max_length=100)
    value: str


class SettingRead(BaseModel):
    id: int
    key: str
    value: str

    model_config = ConfigDict(from_attributes=True)

