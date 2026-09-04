from pathlib import Path

import openpyxl

from core.models import Product

HEADER_ROW = 2
GROUP_ROW = 1
DATA_START_ROW = 5

# 실제 템플릿 1행 그룹셀 텍스트 그대로 (줄바꿈/안내문구 포함). 헤더 매핑 키로 사용하려면 정확히 일치해야 함.
GROUP_IMAGES = "이미지\n*파일 업로드 방식이 변경되었으니 아래 안내를 참조하세요."


def build_header_map(ws) -> dict[tuple[str, str], int]:
    """(그룹명, 필드명) -> 컬럼번호. 그룹은 1행 병합셀 기준으로 컬럼 범위에 forward-fill."""
    group_by_col: dict[int, str] = {}
    for rng in ws.merged_cells.ranges:
        if rng.min_row == GROUP_ROW and rng.max_row == GROUP_ROW:
            value = ws.cell(row=GROUP_ROW, column=rng.min_col).value
            if value:
                for col in range(rng.min_col, rng.max_col + 1):
                    group_by_col[col] = value

    header_map: dict[tuple[str, str], int] = {}
    for col in range(1, ws.max_column + 1):
        field = ws.cell(row=HEADER_ROW, column=col).value
        if not field:
            continue
        group = group_by_col.get(col, "")
        header_map[(group, field)] = col

    return header_map


def _col(header_map: dict[tuple[str, str], int], group: str, field: str) -> int:
    key = (group, field)
    if key not in header_map:
        raise KeyError(f"엑셀 템플릿에서 컬럼을 찾을 수 없음: group={group!r}, field={field!r}")
    return header_map[key]


def clear_data_rows(ws, start_row: int = DATA_START_ROW, end_row: int | None = None) -> None:
    end_row = end_row or ws.max_row
    for row in range(start_row, end_row + 1):
        for col in range(1, ws.max_column + 1):
            ws.cell(row=row, column=col).value = None


def write_products(
    template_path: str | Path,
    output_path: str | Path,
    sheet_name: str,
    category_text: str,
    products: list[Product],
    fixed_values: dict,
) -> None:
    is_macro_enabled = str(template_path).lower().endswith(".xlsm")
    wb = openpyxl.load_workbook(template_path, keep_vba=is_macro_enabled)
    ws = wb[sheet_name]

    header_map = build_header_map(ws)
    clear_data_rows(ws)

    row = DATA_START_ROW
    for product in products:
        for option in product.options:
            ws.cell(row=row, column=_col(header_map, "기본정보", "카테고리")).value = category_text
            ws.cell(row=row, column=_col(header_map, "기본정보", "등록상품명")).value = (
                product.product_name or product.product_code
            )
            ws.cell(row=row, column=_col(header_map, "기본정보", "상품상태")).value = fixed_values["productStatus"]
            ws.cell(row=row, column=_col(header_map, "기본정보", "브랜드")).value = fixed_values["brand"]
            ws.cell(row=row, column=_col(header_map, "기본정보", "제조사")).value = fixed_values["manufacturer"]
            if product.keywords:
                ws.cell(row=row, column=_col(header_map, "기본정보", "검색어")).value = "/".join(product.keywords)

            ws.cell(row=row, column=_col(header_map, "구매옵션", "옵션유형1")).value = "색상"
            ws.cell(row=row, column=_col(header_map, "구매옵션", "옵션값1")).value = option.color
            ws.cell(row=row, column=_col(header_map, "구매옵션", "옵션유형2")).value = "사이즈"
            ws.cell(row=row, column=_col(header_map, "구매옵션", "옵션값2")).value = option.size

            if product.sale_price is not None:
                ws.cell(row=row, column=_col(header_map, "구성 정보", "판매가격")).value = product.sale_price
            if product.reference_price is not None:
                ws.cell(row=row, column=_col(header_map, "구성 정보", "할인율기준가")).value = product.reference_price
            ws.cell(row=row, column=_col(header_map, "구성 정보", "재고수량")).value = option.stock
            ws.cell(row=row, column=_col(header_map, "구성 정보", "출고리드타임")).value = fixed_values[
                "outboundShippingTimeDay"
            ]
            ws.cell(row=row, column=_col(header_map, "구성 정보", "성인상품(19)")).value = fixed_values["adultOnly"]
            ws.cell(row=row, column=_col(header_map, "구성 정보", "과세여부")).value = fixed_values["taxType"]
            ws.cell(row=row, column=_col(header_map, "구성 정보", "병행수입여부")).value = fixed_values[
                "parallelImported"
            ]
            ws.cell(row=row, column=_col(header_map, "구성 정보", "해외구매대행")).value = fixed_values[
                "overseasPurchased"
            ]
            ws.cell(row=row, column=_col(header_map, "구성 정보", "업체상품코드")).value = product.product_code

            if product.images.representative:
                ws.cell(row=row, column=_col(header_map, GROUP_IMAGES, "대표(옵션)이미지")).value = Path(
                    product.images.representative
                ).name
            if product.images.additional:
                ws.cell(row=row, column=_col(header_map, GROUP_IMAGES, "추가이미지")).value = ",".join(
                    Path(p).name for p in product.images.additional
                )

            row += 1

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    wb.save(output_path)
