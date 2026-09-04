from dataclasses import dataclass, field
from enum import Enum


class Severity(str, Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


@dataclass
class Issue:
    severity: Severity
    field: str
    message: str


@dataclass
class ImageSet:
    representative: str | None = None
    additional: list[str] = field(default_factory=list)
    material_label: str | None = None  # _8
    country_label: str | None = None  # _9


@dataclass
class OptionRow:
    color: str
    size: str
    stock: int


@dataclass
class Product:
    product_code: str

    internal_category_code: str | None = None
    internal_category_name: str | None = None

    season_code: str | None = None
    season_label: str | None = None
    carryover: bool | None = None

    color: str | None = None

    sale_price: int | None = None
    reference_price: int | None = None

    sizes: list[str] = field(default_factory=list)
    options: list[OptionRow] = field(default_factory=list)

    material: str | None = None
    outer_material: str | None = None
    lining_material: str | None = None
    country_of_origin: str | None = None
    manufacture_date: str | None = None

    product_name: str | None = None
    keywords: list[str] = field(default_factory=list)

    images: ImageSet = field(default_factory=ImageSet)

    missing_fields: list[str] = field(default_factory=list)
    issues: list[Issue] = field(default_factory=list)

    def add_issue(self, severity: Severity, field_name: str, message: str) -> None:
        self.issues.append(Issue(severity=severity, field=field_name, message=message))

    def has_errors(self) -> bool:
        return any(i.severity == Severity.ERROR for i in self.issues)
