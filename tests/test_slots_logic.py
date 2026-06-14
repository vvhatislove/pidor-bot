from services.slots_service import (
    MAX_SLOTS_BET,
    MIN_SLOTS_BET,
    MULT_PAIR_ADJACENT,
    MULT_SANDWICH,
    MULT_TRIPLE_BAR,
    MULT_TRIPLE_GRAPE,
    MULT_TRIPLE_LEMON,
    MULT_TRIPLE_SEVEN,
    calculate_slots_payout,
    get_slots_and_multiplier,
    parse_slots_bet,
    validate_slots_bet,
)


def test_all_telegram_slot_values_are_supported():
    outcomes = [get_slots_and_multiplier(value) for value in range(1, 65)]

    assert len(outcomes) == 64
    assert all(len(slots) == 3 for slots, _ in outcomes)
    assert all(multiplier >= 0 for _, multiplier in outcomes)


def test_slot_multiplier_distribution_matches_documented_rules():
    multipliers = [get_slots_and_multiplier(value)[1] for value in range(1, 65)]

    assert multipliers.count(0.0) == 24
    assert multipliers.count(MULT_PAIR_ADJACENT) == 24
    assert multipliers.count(MULT_SANDWICH) == 12
    assert multipliers.count(MULT_TRIPLE_BAR) == 1
    assert multipliers.count(MULT_TRIPLE_GRAPE) == 1
    assert multipliers.count(MULT_TRIPLE_LEMON) == 1
    assert multipliers.count(MULT_TRIPLE_SEVEN) == 1


def test_slots_payout_applies_commission_to_gross_win():
    payout = calculate_slots_payout(100, 1.45)

    assert payout.gross_win == 145.0
    assert payout.commission == 2.9
    assert payout.net_win == 142.1


def test_slots_bet_parser_supports_allin_and_comma_decimal():
    assert parse_slots_bet("ALLIN", 12.349) == (12.34, True)
    assert parse_slots_bet("10,25", 100) == (10.25, False)


def test_slots_bet_validation_rejects_invalid_edges():
    assert validate_slots_bet(0, 0, True) == "❌ У вас недостаточно 🪙PidorCoins для all in"
    assert validate_slots_bet(0.5, 0.5, True) is None
    assert validate_slots_bet(10_000, 10_000, True) is None
    assert "Сумма должна" in validate_slots_bet(MIN_SLOTS_BET - 0.01, 100, False)
    assert "Сумма должна" in validate_slots_bet(MAX_SLOTS_BET + 0.01, 10_000, False)
    assert validate_slots_bet(100, 99, False) == "❌ У вас недостаточно 🪙PidorCoins."
    assert validate_slots_bet(100, 100, False) is None


def test_slot_dice_value_must_be_telegram_range():
    for invalid_value in (0, 65):
        try:
            get_slots_and_multiplier(invalid_value)
        except ValueError as exc:
            assert "1..64" in str(exc)
        else:
            raise AssertionError("invalid dice value should fail")
