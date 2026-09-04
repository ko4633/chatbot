from core.models import Product, Severity


def validate_product(product: Product) -> list[str]:
    """ERROR만 추가로 리턴하지 않고, product.issues에 직접 쌓는다. 반환값은 missing_fields 요약."""
    if not product.product_code:
        product.add_issue(Severity.ERROR, "product_code", "품번 없음")

    if not product.images.representative:
        product.add_issue(Severity.ERROR, "images.representative", "대표 이미지(_1) 없음")

    if product.internal_category_code in (None, "UNKNOWN"):
        product.add_issue(
            Severity.WARNING, "internal_category_code", "품번에서 상품종류 코드를 인식하지 못함 (UNKNOWN)"
        )

    if not product.color:
        product.add_issue(Severity.ERROR, "color", "색상 미입력 (사용자 입력 필요)")
        product.missing_fields.append("color")

    if not product.sizes:
        product.add_issue(Severity.ERROR, "sizes", "사이즈 목록이 비어있음")

    if not product.options:
        product.add_issue(Severity.ERROR, "options", "옵션 row가 생성되지 않음")
    else:
        for opt in product.options:
            if opt.stock is None or opt.stock < 0:
                product.add_issue(Severity.ERROR, "options.stock", f"재고 값 이상: {opt.color}/{opt.size}")

    if product.sale_price is None:
        product.add_issue(Severity.ERROR, "sale_price", "판매가격 미입력 (사용자 입력 필요)")
        product.missing_fields.append("sale_price")

    if not product.material:
        product.add_issue(Severity.WARNING, "material", "소재 정보 없음 (Vision 미분석 또는 인식 실패)")
        product.missing_fields.append("material")

    if not product.country_of_origin:
        product.add_issue(Severity.WARNING, "country_of_origin", "제조국 정보 없음")
        product.missing_fields.append("country_of_origin")

    return product.missing_fields


def is_generation_blocked(products: list[Product]) -> bool:
    return any(p.has_errors() for p in products)
