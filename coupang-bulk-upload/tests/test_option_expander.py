from core.option_expander import expand_options


def test_expand_four_sizes():
    options = expand_options("네이비", ["095", "100", "105", "110"], stock_per_option=10)
    assert len(options) == 4
    assert [o.size for o in options] == ["095", "100", "105", "110"]
    assert all(o.color == "네이비" and o.stock == 10 for o in options)


def test_expand_dedupes_sizes():
    options = expand_options("블랙", ["095", "095", "100"], stock_per_option=10)
    assert [o.size for o in options] == ["095", "100"]
