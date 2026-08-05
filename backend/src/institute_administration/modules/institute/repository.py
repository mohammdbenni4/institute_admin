"""Institute settings infrastructure: SQLAlchemy repository."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from institute_administration.modules.institute.models import InstituteSettingsModel


@dataclass(frozen=True)
class InstituteSettings:
    name: str
    subtitle: str
    phone: str
    logo_url: str | None
    report_footer: str
    report_note: str

    @classmethod
    def from_default(cls) -> InstituteSettings:
        """Seed values matching the institute's existing paper report."""
        return cls(
            name="معهد الحسن بن علي",
            subtitle="لتحفيظ القرآن الكريم وعلومه",
            phone="0936277686",
            logo_url=None,
            report_footer="تعاد الورقة إلى المعهد",
            report_note="وفقنا الله وإياكم لخدمة القرآن الكريم.",
        )


def _to_settings(m: InstituteSettingsModel) -> InstituteSettings:
    return InstituteSettings(
        name=m.name,
        subtitle=m.subtitle,
        phone=m.phone,
        logo_url=m.logo_url,
        report_footer=m.report_footer,
        report_note=m.report_note,
    )


class SqlAlchemyInstituteSettingsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _model(self) -> InstituteSettingsModel | None:
        result = await self._session.execute(select(InstituteSettingsModel).limit(1))
        return result.scalar_one_or_none()

    async def get(self) -> InstituteSettings:
        model = await self._model()
        return _to_settings(model) if model else InstituteSettings.from_default()

    async def upsert(self, settings: InstituteSettings) -> InstituteSettings:
        model = await self._model()
        if model is None:
            model = InstituteSettingsModel(name=settings.name)
            self._session.add(model)
        model.name = settings.name
        model.subtitle = settings.subtitle
        model.phone = settings.phone
        model.logo_url = settings.logo_url
        model.report_footer = settings.report_footer
        model.report_note = settings.report_note
        await self._session.flush()
        return _to_settings(model)
