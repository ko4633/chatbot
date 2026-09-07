import zipfile
from pathlib import Path

from core.excel_writer import write_products
from core.models import ImageSet, OptionRow, Product

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
TEMPLATE = FIXTURES / "coupang_template_v4.6.xlsm"

FIXED_VALUES = {
    "brand": "트레몰로",
    "manufacturer": "세정",
    "productStatus": "새 상품",
    "stockPerOption": 10,
    "outboundShippingTimeDay": 2,
    "adultOnly": "N",
    "taxType": "Y",
    "parallelImported": "N",
    "overseasPurchased": "N",
}


def make_product():
    p = Product(product_code="TEST1", color="블랙", sale_price=10000)
    p.images = ImageSet(representative="/tmp/x_1.jpg")
    p.options = [OptionRow(color="블랙", size="095", stock=10)]
    return p


def test_no_broken_vba_relationship_when_source_has_no_real_macro(tmp_path):
    """실제 버그 재현: fixtures 템플릿은 .xlsm이지만 vbaProject.bin이 없는 참고용 파일이다.
    이런 파일을 keep_vba=True로 무조건 저장하면 존재하지 않는 vbaProject.bin을 가리키는
    깨진 relationship이 생겨서 엑셀이 '복구' 오류를 띄운다."""
    output_path = tmp_path / "output.xlsm"
    write_products(
        template_path=TEMPLATE,
        output_path=output_path,
        sheet_name="1. 패션잡화",
        category_text="test",
        products=[make_product()],
        fixed_values=FIXED_VALUES,
    )

    with zipfile.ZipFile(output_path) as zf:
        names = zf.namelist()
        rels = zf.read("xl/_rels/workbook.xml.rels").decode("utf-8")

    assert "xl/vbaProject.bin" not in names
    assert "vbaProject" not in rels, "원본에 없는 vbaProject를 가리키는 깨진 relationship이 생기면 안 됨"
