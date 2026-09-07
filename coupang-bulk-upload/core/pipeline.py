from dataclasses import dataclass
from pathlib import Path

from core.image_grouper import group_images
from core.models import Product
from core.option_expander import expand_options
from core.product_code_parser import load_rules, parse_product_code
from core.size_rules import get_sizes, load_size_rules
from core.validator import validate_product


@dataclass
class UserInput:
    """추가입력필요.xlsx 왕복 전, 이미 알고 있는 값(색상/가격 등)을 최초 1회 주입하는 자리.
    (예: 발주서/기존 시스템에 이미 있는 값을 미리 넣어두고 싶을 때)"""

    color: str | None = None
    sale_price: int | None = None
    reference_price: int | None = None
    product_name: str | None = None
    keywords: list[str] | None = None
    material: str | None = None
    country_of_origin: str | None = None
    manufacture_date: str | None = None


def build_product(product_code: str, group, user_input: UserInput, rules: dict, size_rules: dict) -> Product:
    parsed = parse_product_code(product_code, rules)

    product = Product(
        product_code=product_code,
        internal_category_code=parsed.internal_category_code,
        internal_category_name=parsed.internal_category_name,
        season_code=parsed.season_code,
        season_label=parsed.season_label,
        carryover=parsed.carryover,
        color=user_input.color,
        sale_price=user_input.sale_price,
        reference_price=user_input.reference_price,
        product_name=user_input.product_name,
        keywords=user_input.keywords or [],
        material=user_input.material,
        country_of_origin=user_input.country_of_origin,
        manufacture_date=user_input.manufacture_date,
        images=group.images,
    )
    product.issues.extend(group.issues)
    product.sizes = get_sizes(parsed.size_rule_group, size_rules)
    return product


def finalize(product: Product, fixed_values: dict) -> Product:
    """색상이 채워졌으면 옵션 재생성, 검증 재실행. merge 이후 재검증에도 그대로 재사용."""
    product.issues = [i for i in product.issues if i.field not in _RECOMPUTED_FIELDS]
    product.missing_fields = []

    if product.color:
        product.options = expand_options(product.color, product.sizes, fixed_values["stockPerOption"])
    else:
        product.options = []

    validate_product(product)
    return product


_RECOMPUTED_FIELDS = {
    "color",
    "sizes",
    "options",
    "options.stock",
    "sale_price",
    "reference_price",
    "material",
    "country_of_origin",
    "internal_category_code",
    "product_code",
    "images.representative",
}


def run_pipeline(
    image_folder: str | Path,
    user_inputs: dict[str, UserInput],
    fixed_values: dict,
) -> tuple[list[Product], list[Product]]:
    """이미지 폴더 + 사용자 입력값 -> (생성 가능한 상품 목록, 오류로 막힌 상품 목록)."""
    rules = load_rules()
    size_rules = load_size_rules()

    grouped = group_images(image_folder)

    all_products: list[Product] = []
    for product_code, group in grouped.items():
        if product_code == "__UNMATCHED__":
            continue
        user_input = user_inputs.get(product_code, UserInput())
        product = build_product(product_code, group, user_input, rules, size_rules)
        finalize(product, fixed_values)
        all_products.append(product)

    ready = [p for p in all_products if not p.has_errors()]
    blocked = [p for p in all_products if p.has_errors()]
    return ready, blocked


def apply_overrides_and_revalidate(
    products: list[Product],
    overrides: dict[str, dict],
    fixed_values: dict,
) -> tuple[list[Product], list[Product]]:
    """추가입력필요.xlsx 재import 결과(overrides)를 기존 product 목록에 병합하고 재검증.
    이미 정상 확보된 값은 건드리지 않고, overrides에 실제 값이 있는 필드만 덮어쓴다."""
    for product in products:
        override = overrides.get(product.product_code)
        if not override:
            continue
        for field_name, value in override.items():
            if value in (None, ""):
                continue
            setattr(product, field_name, value)
        finalize(product, fixed_values)

    ready = [p for p in products if not p.has_errors()]
    blocked = [p for p in products if p.has_errors()]
    return ready, blocked
