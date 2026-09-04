from core.size_rules import get_sizes, load_size_rules

RULES = load_size_rules()


def test_eight_size_waist_group():
    sizes = get_sizes("EIGHT_SIZE_WAIST", RULES)
    assert sizes == [
        "076cm(30인치)",
        "078cm(31인치)",
        "082cm(32인치)",
        "084cm(33인치)",
        "086cm(34인치)",
        "088cm(35인치)",
        "092cm(36인치)",
        "096cm(38인치)",
    ]


def test_default_group():
    assert get_sizes(None, RULES) == ["095", "100", "105", "110"]


def test_unknown_group_falls_back_to_default():
    assert get_sizes("SOME_UNKNOWN_GROUP", RULES) == ["095", "100", "105", "110"]
