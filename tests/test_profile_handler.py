from handlers.user.profile import _amount, _profit


def test_profile_amount_formatting_keeps_sign_only_for_profit():
    assert _amount(-100) == "100.00"
    assert _amount(100) == "100.00"
    assert _profit(-12.5) == "-12.50"
    assert _profit(12.5) == "+12.50"
    assert _profit(-0.0) == "0.00"
