"""All enum types used in the schema. See docs/DATA_MODEL.md for meaning.

Kept in one module so every place that needs to know the allowed values
(models, scoring, API schemas, frontend type generation) imports from here
rather than redefining the same strings.
"""

from __future__ import annotations

import enum


class SourceType(enum.StrEnum):
    MARKETPLACE_HTML = "MARKETPLACE_HTML"
    MARKETPLACE_API = "MARKETPLACE_API"
    GOVERNMENT_API = "GOVERNMENT_API"
    COMMUNITY_FORUM = "COMMUNITY_FORUM"
    NEWS = "NEWS"
    SOCIAL = "SOCIAL"
    FIXTURE = "FIXTURE"
    MANUAL = "MANUAL"


class TrustTier(enum.StrEnum):
    OFFICIAL = "OFFICIAL"
    PRIMARY = "PRIMARY"
    REPUTABLE_SECONDARY = "REPUTABLE_SECONDARY"
    MARKETPLACE = "MARKETPLACE"
    COMMUNITY = "COMMUNITY"
    SOCIAL = "SOCIAL"
    UNKNOWN = "UNKNOWN"


class ReliabilityLevel(enum.StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ExtractionMethod(enum.StrEnum):
    HTML_SELECTOR = "HTML_SELECTOR"
    JSON_FIELD = "JSON_FIELD"
    API_RESPONSE = "API_RESPONSE"
    MANUAL = "MANUAL"
    FIXTURE = "FIXTURE"
    DERIVED = "DERIVED"


class SnapshotStatus(enum.StrEnum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"


class IdentifierType(enum.StrEnum):
    JAN = "JAN"
    EAN = "EAN"
    UPC = "UPC"
    GTIN = "GTIN"
    ISBN = "ISBN"
    MPN = "MPN"
    MODEL_NUMBER = "MODEL_NUMBER"
    NONE = "NONE"


class ProductStatus(enum.StrEnum):
    ACTIVE = "ACTIVE"
    MERGED = "MERGED"
    SPLIT = "SPLIT"


class MarketplaceType(enum.StrEnum):
    ECOMMERCE_GENERAL = "ECOMMERCE_GENERAL"
    ECOMMERCE_MARKETPLACE = "ECOMMERCE_MARKETPLACE"
    C2C = "C2C"
    BRAND_DIRECT = "BRAND_DIRECT"


class OfferStatus(enum.StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    UNKNOWN = "UNKNOWN"


class MatchType(enum.StrEnum):
    EXACT = "EXACT"
    LIKELY = "LIKELY"
    POSSIBLE = "POSSIBLE"
    REJECTED = "REJECTED"
    UNKNOWN = "UNKNOWN"


class MatchStage(enum.StrEnum):
    IDENTIFIER = "IDENTIFIER"
    ATTRIBUTES = "ATTRIBUTES"
    STRING = "STRING"
    FUZZY = "FUZZY"
    EMBEDDING = "EMBEDDING"
    VISION = "VISION"
    LLM_JUDGE = "LLM_JUDGE"


class EventEntityType(enum.StrEnum):
    PRODUCT = "PRODUCT"
    PRODUCT_VARIANT = "PRODUCT_VARIANT"
    OFFER = "OFFER"
    SELLER = "SELLER"


class EventType(enum.StrEnum):
    PRICE_DROP = "PRICE_DROP"
    PRICE_RISE = "PRICE_RISE"
    NEW_SELLER = "NEW_SELLER"
    SELLER_EXIT = "SELLER_EXIT"
    STOCK_OUT = "STOCK_OUT"
    RESTOCK = "RESTOCK"
    NEW_PRODUCT = "NEW_PRODUCT"
    REVIEW_ACCELERATION = "REVIEW_ACCELERATION"
    OPPORTUNITY_SCORE_CHANGE = "OPPORTUNITY_SCORE_CHANGE"


class OpportunityType(enum.StrEnum):
    IMPORT_RESALE = "IMPORT_RESALE"


class RegulationStatus(enum.StrEnum):
    UNKNOWN = "UNKNOWN"
    LIKELY_LOW = "LIKELY_LOW"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    KNOWN_RESTRICTED = "KNOWN_RESTRICTED"


class OpportunityStatus(enum.StrEnum):
    NEW = "NEW"
    ACTIVE = "ACTIVE"
    STALE = "STALE"
    REJECTED = "REJECTED"


class DecisionType(enum.StrEnum):
    BUY_TEST = "BUY_TEST"
    WATCH = "WATCH"
    REJECT = "REJECT"
    ARCHIVE = "ARCHIVE"


class WatchlistEntityType(enum.StrEnum):
    PRODUCT = "PRODUCT"
    BRAND = "BRAND"
    CATEGORY = "CATEGORY"
    KEYWORD = "KEYWORD"


class AnalysisRunType(enum.StrEnum):
    INGEST = "INGEST"
    MATCH = "MATCH"
    SCORE = "SCORE"
    FULL = "FULL"


class AnalysisRunStatus(enum.StrEnum):
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"


class AIRunPurpose(enum.StrEnum):
    ENTITY_MATCH_JUDGE = "ENTITY_MATCH_JUDGE"
    NAME_NORMALIZATION = "NAME_NORMALIZATION"
    CATEGORY_CLASSIFICATION = "CATEGORY_CLASSIFICATION"
    OPPORTUNITY_NARRATIVE = "OPPORTUNITY_NARRATIVE"
    COUNTER_ARGUMENT = "COUNTER_ARGUMENT"
    EMBEDDING = "EMBEDDING"


class AIRunStatus(enum.StrEnum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    DISABLED = "DISABLED"


class DemandMetricType(enum.StrEnum):
    SEARCH_INTEREST = "SEARCH_INTEREST"
    REVIEW_VELOCITY = "REVIEW_VELOCITY"
    MANUAL_ESTIMATE = "MANUAL_ESTIMATE"
