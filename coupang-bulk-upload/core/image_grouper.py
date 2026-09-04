import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from core.models import ImageSet, Issue, Severity

FILENAME_PATTERN = re.compile(r"^(?P<productCode>.+)_(?P<imageIndex>\d+)\.(?P<ext>[A-Za-z0-9]+)$")
SUPPORTED_EXTENSIONS = {"jpg", "jpeg", "png"}

REPRESENTATIVE_INDEX = 1
ADDITIONAL_INDEX_RANGE = range(2, 8)  # 2~7
MATERIAL_LABEL_INDEX = 8
COUNTRY_LABEL_INDEX = 9
KNOWN_INDEXES = {1, 2, 3, 4, 5, 6, 7, 8, 9}


@dataclass
class GroupedProduct:
    product_code: str
    images: ImageSet = field(default_factory=ImageSet)
    issues: list[Issue] = field(default_factory=list)


def group_images(folder: str | Path) -> dict[str, GroupedProduct]:
    folder = Path(folder)
    groups: dict[str, GroupedProduct] = {}
    seen_indexes: dict[str, set[int]] = defaultdict(set)
    batch_issues: list[Issue] = []

    files = sorted(p for p in folder.iterdir() if p.is_file())

    for path in files:
        match = FILENAME_PATTERN.match(path.name)
        if not match:
            batch_issues.append(
                Issue(Severity.ERROR, "filename", f"파일명 규칙에 맞지 않아 품번을 추출할 수 없음: {path.name}")
            )
            continue

        product_code = match.group("productCode")
        try:
            image_index = int(match.group("imageIndex"))
        except ValueError:
            batch_issues.append(
                Issue(Severity.ERROR, "filename", f"imageIndex가 숫자가 아님: {path.name}")
            )
            continue

        ext = match.group("ext").lower()

        group = groups.setdefault(product_code, GroupedProduct(product_code=product_code))

        if ext not in SUPPORTED_EXTENSIONS:
            group.issues.append(
                Issue(Severity.ERROR, "images", f"지원하지 않는 확장자: {path.name}")
            )
            continue

        if image_index in seen_indexes[product_code]:
            group.issues.append(
                Issue(Severity.ERROR, "images", f"동일 품번+동일 imageIndex 중복: {path.name}")
            )
            continue
        seen_indexes[product_code].add(image_index)

        if image_index not in KNOWN_INDEXES:
            group.issues.append(
                Issue(Severity.WARNING, "images", f"예상하지 않은 imageIndex({image_index}): {path.name}")
            )
            continue

        if not path.exists() or path.stat().st_size == 0:
            group.issues.append(
                Issue(Severity.ERROR, "images", f"이미지 파일 손상/접근 불가능: {path.name}")
            )
            continue

        if image_index == REPRESENTATIVE_INDEX:
            group.images.representative = str(path)
        elif image_index in ADDITIONAL_INDEX_RANGE:
            group.images.additional.append(str(path))
        elif image_index == MATERIAL_LABEL_INDEX:
            group.images.material_label = str(path)
        elif image_index == COUNTRY_LABEL_INDEX:
            group.images.country_label = str(path)

    for group in groups.values():
        if not group.images.representative:
            group.issues.append(
                Issue(Severity.ERROR, "images", f"대표 이미지(_1)가 없음: {group.product_code}")
            )

    if batch_issues:
        unmatched_group = groups.setdefault("__UNMATCHED__", GroupedProduct(product_code="__UNMATCHED__"))
        unmatched_group.issues.extend(batch_issues)

    return groups
