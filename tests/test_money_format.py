from database.money_format import money_2


def test_money_2_truncates_to_two_decimals():
    assert money_2(10.239) == 10.23
    assert money_2(0.999) == 0.99


def test_money_2_avoids_common_float_noise():
    assert money_2(0.1 + 0.2) == 0.3
