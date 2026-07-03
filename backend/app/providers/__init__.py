"""
CareerPilot AI — Provider Package
==================================
"""
from app.providers.factory import ProviderFactory

# ------------------------------------------------------------------
#  Built-in import to trigger auto‑registration
# ------------------------------------------------------------------
from app.providers.scraper import native as _native_scraper
from app.providers.scraper import api as _api_scraper
from app.providers.resume import native as _native_resume
from app.providers.resume import api as _api_resume
from app.providers.matcher import native as _native_matcher
from app.providers.matcher import api as _api_matcher

# Register native providers
from app.providers.scraper.native import NativeScraperProvider
ProviderFactory.register_scraper("native", NativeScraperProvider)

from app.providers.scraper.api import ApiScraperProvider
ProviderFactory.register_scraper("api", ApiScraperProvider)

from app.providers.resume.native import NativeResumeProvider
ProviderFactory.register_resume("native", NativeResumeProvider)

from app.providers.resume.api import ApiResumeProvider
ProviderFactory.register_resume("api", ApiResumeProvider)

from app.providers.matcher.native import NativeMatcherProvider
ProviderFactory.register_matcher("native", NativeMatcherProvider)

from app.providers.matcher.api import ApiMatcherProvider
ProviderFactory.register_matcher("api", ApiMatcherProvider)

__all__ = [
    "ProviderFactory",
    "NativeScraperProvider",
    "ApiScraperProvider",
    "NativeResumeProvider",
    "ApiResumeProvider",
    "NativeMatcherProvider",
    "ApiMatcherProvider",
]
