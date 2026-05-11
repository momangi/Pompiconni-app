"""Site-level models — moved verbatim from ``server.py`` (Fase 4A)."""
from typing import Optional

from pydantic import BaseModel


class SiteSettings(BaseModel):
    show_reviews: bool = True
    stripe_enabled: bool = False
    # Legal contact information with visibility flags
    legal_company_name: Optional[str] = None
    show_legal_company_name: bool = True
    legal_address: Optional[str] = None
    show_legal_address: bool = True
    legal_vat_number: Optional[str] = None
    show_legal_vat_number: bool = True
    legal_email: Optional[str] = None
    show_legal_email: bool = True
    legal_pec_email: Optional[str] = None
    show_legal_pec_email: bool = True


class SiteSettingsUpdate(BaseModel):
    show_reviews: Optional[bool] = None
    legal_company_name: Optional[str] = None
    show_legal_company_name: Optional[bool] = None
    legal_address: Optional[str] = None
    show_legal_address: Optional[bool] = None
    legal_vat_number: Optional[str] = None
    show_legal_vat_number: Optional[bool] = None
    legal_email: Optional[str] = None
    show_legal_email: Optional[bool] = None
    legal_pec_email: Optional[str] = None
    show_legal_pec_email: Optional[bool] = None


class HeroImageResponse(BaseModel):
    hasHeroImage: bool
    heroImageUrl: Optional[str] = None
    updatedAt: Optional[str] = None
