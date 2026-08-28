from datetime import datetime

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class AppliedJobIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str | None = None
    firm: str = ""
    location: str = ""
    title: str = ""
    link: str = ""
    applied_at: datetime | None = Field(
        default=None,
        validation_alias=AliasChoices("appliedAt", "applied_at"),
    )


class AppliedJobPatch(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    firm: str | None = None
    location: str | None = None
    title: str | None = None
    link: str | None = None
    applied_at: datetime | None = Field(
        default=None,
        validation_alias=AliasChoices("appliedAt", "applied_at"),
    )


class AppliedJobRead(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    firm: str
    location: str
    title: str
    link: str
    applied_at: datetime = Field(serialization_alias="appliedAt")
