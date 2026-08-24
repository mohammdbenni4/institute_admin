"""Scoring settings presentation layer: Pydantic schemas."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from institute_administration.modules.scoring.repository import ScoringPreset, ScoringSettings

# Point weights may be negative (e.g. a penalty for absence) up to ±100.
_Points = Field(ge=-100, le=100)


class ScoringSettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    present_points: int
    rating_4_points: int
    rating_3_points: int
    rating_2_points: int
    rating_1_points: int
    revision_4_points: int
    revision_3_points: int
    revision_2_points: int
    revision_1_points: int
    attitude_3_points: int
    attitude_2_points: int
    attitude_1_points: int
    absent_points: int
    excused_points: int
    late_points: int


class ScoringSettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    present_points: int = _Points
    rating_4_points: int = _Points
    rating_3_points: int = _Points
    rating_2_points: int = _Points
    rating_1_points: int = _Points
    revision_4_points: int = _Points
    revision_3_points: int = _Points
    revision_2_points: int = _Points
    revision_1_points: int = _Points
    attitude_3_points: int = _Points
    attitude_2_points: int = _Points
    attitude_1_points: int = _Points
    absent_points: int = _Points
    excused_points: int = _Points
    late_points: int = _Points

    def to_settings(self) -> ScoringSettings:
        return ScoringSettings(**self.model_dump())


# --- Named presets ----------------------------------------------------------------


class ScoringPresetResponse(ScoringSettingsResponse):
    """A preset is the same fifteen weights plus an identity, so the teacher app can
    reuse every scoring field it already knows how to read."""

    id: UUID
    name: str

    @classmethod
    def from_entity(cls, preset: ScoringPreset) -> ScoringPresetResponse:
        return cls(id=preset.id, name=preset.name, **vars(preset.settings))


class ScoringPresetListResponse(BaseModel):
    items: list[ScoringPresetResponse]
    total: int


class ScoringPresetWriteRequest(ScoringSettingsUpdate):
    """Create or replace a preset. Inherits the ±100 bounds on every weight."""

    name: str = Field(min_length=1, max_length=120)

    def to_settings(self) -> ScoringSettings:
        return ScoringSettings(**self.model_dump(exclude={"name"}))
