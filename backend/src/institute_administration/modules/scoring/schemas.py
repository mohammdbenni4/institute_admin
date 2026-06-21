"""Scoring settings presentation layer: Pydantic schemas."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from institute_administration.modules.scoring.repository import ScoringSettings

_Points = Field(ge=0, le=100)


class ScoringSettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    present_points: int
    rating_4_points: int
    rating_3_points: int
    rating_2_points: int
    rating_1_points: int
    attitude_3_points: int
    attitude_2_points: int
    attitude_1_points: int


class ScoringSettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    present_points: int = _Points
    rating_4_points: int = _Points
    rating_3_points: int = _Points
    rating_2_points: int = _Points
    rating_1_points: int = _Points
    attitude_3_points: int = _Points
    attitude_2_points: int = _Points
    attitude_1_points: int = _Points

    def to_settings(self) -> ScoringSettings:
        return ScoringSettings(**self.model_dump())
