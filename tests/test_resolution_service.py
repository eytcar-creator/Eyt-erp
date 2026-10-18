from api.orders.resolution_service import _norm


def test_normalizes_persian_arabic_variants():
    assert _norm("بوش طبقِ جك S5") == _norm("بوش طبق جک s5")


def test_normalizes_spaces_and_punctuation():
    assert _norm("JAC-S5 / 3K000") == "jac-s53k000"
