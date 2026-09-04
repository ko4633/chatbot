from core.models import OptionRow


def expand_options(color: str, sizes: list[str], stock_per_option: int) -> list[OptionRow]:
    """색상 1개 x 사이즈 N개 -> 옵션 row N개. 동일 조합 중복 생성 방지를 위해 sizes를 순서 유지한 채 중복 제거."""
    seen = set()
    deduped_sizes = []
    for size in sizes:
        if size not in seen:
            seen.add(size)
            deduped_sizes.append(size)

    return [OptionRow(color=color, size=size, stock=stock_per_option) for size in deduped_sizes]
