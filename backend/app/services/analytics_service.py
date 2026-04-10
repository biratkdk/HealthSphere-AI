from __future__ import annotations

from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.db.enterprise_repository import get_analytics_overview
from backend.app.models import AnalyticsOverview, UserProfile


def build_analytics_overview(db: Session, current_user: UserProfile) -> AnalyticsOverview:
    return get_analytics_overview(db, current_user, get_settings())
