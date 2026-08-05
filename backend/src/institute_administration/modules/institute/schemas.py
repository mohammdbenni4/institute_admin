"""Institute settings presentation layer: Pydantic schemas."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from institute_administration.modules.institute.repository import InstituteSettings


class InstituteSettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    subtitle: str
    phone: str
    logo_url: str | None
    report_footer: str
    report_note: str


class InstituteSettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200)
    subtitle: str = Field(default="", max_length=200)
    phone: str = Field(default="", max_length=50)
    # Data URI or URL; generous limit so a small inlined logo fits.
    logo_url: str | None = Field(default=None, max_length=2_000_000)
    report_footer: str = Field(default="", max_length=500)
    report_note: str = Field(default="", max_length=500)

    def to_settings(self) -> InstituteSettings:
        return InstituteSettings(**self.model_dump())
