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
    """추가입력필요.xlsx 왕복 전까지, 사용자가 이미 알고 있는 값(색상/가격 등)을 임시로 주입하는 자리.
    실제로는 나중에 추가입력 Excel round-trip 모듈이 이 자리를 대체한다."""

    color: str | None = None
    sale_price: int | None = None
    reference_price: int | None = None
    product_name: str | None = None
    keywords: list[str] | None = None


def run_pipeline(
    image_folder: str | Path,
    user_inputs: dict[str, UserInput],
    fixed_values: dict,
) -> tuple[list[Product], list[Product]]:
    """이미지 폴더 + 사용자 입력값 -> (생성 가능한 상품 목록, 오류로 막힌 상품 목록)."""
    rules = load_rules()
    size_rules = load_size_rules()

    grouped = group_images(image_folder)

    ready: list[Product] = []
    blocked: list[Product] = []

    for product_code, group in grouped.items():
        if product_code == "__UNMATCHED__":
            continue

        parsed = parse_product_code(product_code, rules)
        user_input = user_inputs.get(product_code, UserInput())

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
            images=group.images,
        )
        product.issues.extend(group.issues)

        product.sizes = get_sizes(parsed.size_rule_group, size_rules)
        if product.color:
            product.options = expand_options(product.color, product.sizes, fixed_values["stockPerOption"])

        validate_product(product)

        if product.has_errors():
            blocked.append(product)
        else:
            ready.append(product)

    return ready, blocked
