import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from core.models import ImageSet, Issue, Severity

FILENAME_PATTERN = re.compile(r"^(?P<productCode>.+)_(?P<imageIndex>\d+)\.(?P<ext>[A-Za-z0-9]+)$")
SUPPORTED_EXTENSIONS = {"jpg", "jpeg", "png"}

REPRESENTATIVE_INDEX = 1
# 라벨(소재/제조국) 사진은 고정 인덱스가 아니라 "그 상품의 사진 중 항상 마지막 2장"이다.
# 실사용 확인: 9장짜리 상품은 _8,_9가 라벨이고, 7장짜리 상품은 _6,_7이 라벨이었음(둘 다 마지막 2장).
MIN_IMAGES_FOR_LABEL_DETECTION = 3  # 대표 1장 + 라벨 2장이 최소로 구분되려면 3장은 있어야 함


@dataclass
class GroupedProduct:
    product_code: str
    images: ImageSet = field(default_factory=ImageSet)
    issues: list[Issue] = field(default_factory=list)


def group_images(folder: str | Path) -> dict[str, GroupedProduct]:
    folder = Path(folder)
    groups: dict[str, GroupedProduct] = {}
    valid_files: dict[str, dict[int, Path]] = defaultdict(dict)
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
            batch_issues.append(Issue(Severity.ERROR, "filename", f"imageIndex가 숫자가 아님: {path.name}"))
            continue

        ext = match.group("ext").lower()
        group = groups.setdefault(product_code, GroupedProduct(product_code=product_code))

        if ext not in SUPPORTED_EXTENSIONS:
            group.issues.append(Issue(Severity.ERROR, "images", f"지원하지 않는 확장자: {path.name}"))
            continue

        if image_index in seen_indexes[product_code]:
            group.issues.append(Issue(Severity.ERROR, "images", f"동일 품번+동일 imageIndex 중복: {path.name}"))
            continue
        seen_indexes[product_code].add(image_index)

        if image_index < 1:
            group.issues.append(
                Issue(Severity.WARNING, "images", f"예상하지 않은 imageIndex({image_index}): {path.name}")
            )
            continue

        if not path.exists() or path.stat().st_size == 0:
            group.issues.append(Issue(Severity.ERROR, "images", f"이미지 파일 손상/접근 불가능: {path.name}"))
            continue

        valid_files[product_code][image_index] = path

    # 역할 분류: 대표=1번, 라벨=마지막 2장(소재→제조국 순), 나머지=추가이미지
    for product_code, index_map in valid_files.items():
        group = groups[product_code]
        indexes = sorted(index_map.keys())

        if REPRESENTATIVE_INDEX in index_map:
            group.images.representative = str(index_map[REPRESENTATIVE_INDEX])

        label_indexes: set[int] = set()
        if len(indexes) >= MIN_IMAGES_FOR_LABEL_DETECTION:
            material_idx, country_idx = indexes[-2], indexes[-1]
            label_indexes = {material_idx, country_idx}
            group.images.material_label = str(index_map[material_idx])
            group.images.country_label = str(index_map[country_idx])
        elif indexes:
            group.issues.append(
                Issue(Severity.WARNING, "images", f"이미지가 {len(indexes)}장뿐이라 라벨 사진을 판별할 수 없음")
            )

        for idx in indexes:
            if idx == REPRESENTATIVE_INDEX or idx in label_indexes:
                continue
            group.images.additional.append(str(index_map[idx]))

    for group in groups.values():
        if not group.images.representative:
            group.issues.append(Issue(Severity.ERROR, "images", f"대표 이미지(_1)가 없음: {group.product_code}"))

    if batch_issues:
        unmatched_group = groups.setdefault("__UNMATCHED__", GroupedProduct(product_code="__UNMATCHED__"))
        unmatched_group.issues.extend(batch_issues)

    return groups
