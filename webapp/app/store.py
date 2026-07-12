"""Access helpers for the platform Settings singleton."""

from __future__ import annotations

from sqlalchemy.orm import Session

from . import config
from .models import Settings
from .statutory import RateConfig

# Fields shared between the Settings row and the engine's RateConfig.
_RATE_FIELDS = [
    "epf_emp_rate", "epf_er_rate_low", "epf_er_rate_high", "epf_er_threshold",
    "socso_eis_ceiling", "socso_c1_emp", "socso_c1_er", "socso_c2_er", "eis_rate",
    "personal_relief", "epf_relief_cap", "tax_rebate", "rebate_ceiling",
]

# Cheap process-local cache for display-only bits (company name) so templates and
# the PDF layer don't each need a DB round-trip.
_company_cache = config.COMPANY_NAME


def get_settings(db: Session) -> Settings:
    """Return the singleton Settings row, creating it with defaults if absent."""
    settings = db.get(Settings, 1)
    if settings is None:
        settings = Settings(id=1, company_name=config.COMPANY_NAME)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    refresh_cache(settings)
    return settings


def rate_config(db: Session) -> RateConfig:
    """Build the engine RateConfig from the current settings."""
    s = get_settings(db)
    return RateConfig(**{f: getattr(s, f) for f in _RATE_FIELDS})


def refresh_cache(settings: Settings) -> None:
    global _company_cache
    _company_cache = settings.company_name or config.COMPANY_NAME


def company() -> str:
    return _company_cache
