from pathlib import Path

from core.image_grouper import group_images
from core.models import Severity


def touch(path, size=10):
    path.write_bytes(b"x" * size)


def test_groups_by_product_code_and_assigns_roles(tmp_path):
    for i in range(1, 10):
        touch(tmp_path / f"TCNKA26F841104_{i}.jpg")

    groups = group_images(tmp_path)
    assert set(groups.keys()) == {"TCNKA26F841104"}

    g = groups["TCNKA26F841104"]
    assert g.images.representative.endswith("_1.jpg")
    assert len(g.images.additional) == 6  # _2~_7
    assert g.images.material_label.endswith("_8.jpg")
    assert g.images.country_label.endswith("_9.jpg")
    assert g.issues == []


def test_numeric_index_sorting_not_lexical(tmp_path):
    # 문자열 정렬이면 "_10"이 "_2"보다 앞에 오는 버그가 날 수 있음 -> 숫자 파싱 검증
    touch(tmp_path / "ABC_1.jpg")
    touch(tmp_path / "ABC_2.jpg")
    groups = group_images(tmp_path)
    g = groups["ABC"]
    assert g.images.additional == [str(tmp_path / "ABC_2.jpg")]


def test_missing_representative_is_error(tmp_path):
    touch(tmp_path / "XYZ_2.jpg")
    groups = group_images(tmp_path)
    g = groups["XYZ"]
    assert any(i.severity == Severity.ERROR and "대표 이미지" in i.message for i in g.issues)


def test_duplicate_index_is_error(tmp_path):
    touch(tmp_path / "DUP_1.jpg")
    touch(tmp_path / "DUP_1.png")
    groups = group_images(tmp_path)
    g = groups["DUP"]
    assert any("중복" in i.message for i in g.issues)


def test_unparseable_filename_reported_without_crashing_batch(tmp_path):
    touch(tmp_path / "no_underscore_index.jpg")
    touch(tmp_path / "GOOD_1.jpg")

    groups = group_images(tmp_path)
    assert "GOOD" in groups
    assert groups["GOOD"].images.representative is not None

    assert "__UNMATCHED__" in groups
    assert any("파일명 규칙" in i.message for i in groups["__UNMATCHED__"].issues)


def test_labels_are_last_two_regardless_of_photo_count(tmp_path):
    # 실사용 확인: TRHKA5F841156은 사진이 9장이 아니라 7장이고, 라벨이 _8/_9가 아니라 _6/_7(마지막 2장)이었음
    for i in range(1, 8):
        touch(tmp_path / f"TRHKA5F841156_{i}.jpg")

    groups = group_images(tmp_path)
    g = groups["TRHKA5F841156"]

    assert g.images.representative.endswith("_1.jpg")
    assert [Path(p).name for p in g.images.additional] == [
        "TRHKA5F841156_2.jpg",
        "TRHKA5F841156_3.jpg",
        "TRHKA5F841156_4.jpg",
        "TRHKA5F841156_5.jpg",
    ]
    assert g.images.material_label.endswith("_6.jpg")
    assert g.images.country_label.endswith("_7.jpg")


def test_too_few_images_to_detect_labels_is_warning(tmp_path):
    touch(tmp_path / "ONLYTWO_1.jpg")
    touch(tmp_path / "ONLYTWO_2.jpg")

    groups = group_images(tmp_path)
    g = groups["ONLYTWO"]

    assert g.images.material_label is None
    assert g.images.country_label is None
    assert any(i.severity == Severity.WARNING and "라벨 사진을 판별할 수 없음" in i.message for i in g.issues)


def test_unsupported_extension_is_error(tmp_path):
    touch(tmp_path / "BAD_1.gif")
    groups = group_images(tmp_path)
    g = groups["BAD"]
    assert any("지원하지 않는 확장자" in i.message for i in g.issues)
