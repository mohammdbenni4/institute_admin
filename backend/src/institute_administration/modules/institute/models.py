"""Institute settings infrastructure: the single-row ``institute_settings`` table."""

from __future__ import annotations

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from institute_administration.infrastructure.database.base import Base
from institute_administration.infrastructure.database.mixins import (
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class InstituteSettingsModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """The institute's own identity. Only one row is ever used."""

    __tablename__ = "institute_settings"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    subtitle: Mapped[str] = mapped_column(
        String(200), nullable=False, default="", server_default=""
    )
    phone: Mapped[str] = mapped_column(String(50), nullable=False, default="", server_default="")
    # A data: URI or an absolute URL. Kept as text so the report stays self-contained
    # and printable without a second request.
    logo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Standing text printed on every monthly report.
    report_footer: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    report_note: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
