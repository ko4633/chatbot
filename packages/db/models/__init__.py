"""Import every model module so Base.metadata is complete for Alembic
autogenerate and for create_all() in tests."""

from packages.db.models.catalog import Brand, Manufacturer, Market, Marketplace, Seller
from packages.db.models.decision import UserDecision, WatchlistItem
from packages.db.models.entity_match import EntityMatch
from packages.db.models.event import Event
from packages.db.models.forecast import Forecast
from packages.db.models.fx import FXObservation
from packages.db.models.insight import Insight
from packages.db.models.observations import (
    DemandObservation,
    InventoryObservation,
    PriceObservation,
    ReviewObservation,
)
from packages.db.models.offer import Offer
from packages.db.models.opportunity import Opportunity
from packages.db.models.product import Product, ProductVariant
from packages.db.models.raw_object import RawObject
from packages.db.models.run import AIRun, AnalysisRun
from packages.db.models.source import Source, SourceSnapshot

__all__ = [
    "Brand",
    "Manufacturer",
    "Market",
    "Marketplace",
    "Seller",
    "UserDecision",
    "WatchlistItem",
    "EntityMatch",
    "Event",
    "Forecast",
    "FXObservation",
    "Insight",
    "DemandObservation",
    "InventoryObservation",
    "PriceObservation",
    "ReviewObservation",
    "Offer",
    "Opportunity",
    "Product",
    "ProductVariant",
    "RawObject",
    "AIRun",
    "AnalysisRun",
    "Source",
    "SourceSnapshot",
]
