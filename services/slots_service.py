from dataclasses import dataclass

from database.money_format import money_2

"""
Однорукий бандит Telegram (🎰): dice.value 1–64, 4 символа × 3 барабана.

Исходы равновероятны: 4 тройки, 24 «две подряд», 12 «бутерброд» (края совпали),
24 проигрыша.

Подбор множителей под RTP (после комиссии 2% на выигрыш в handlers/user/slots.py):
  E[gross] = (MULT_TRIPLE_* сумма по 4 тройкам + 24*MULT_PAIR_ADJACENT + 12*MULT_SANDWICH) / 64
  RTP_net  ≈ 0.98 * E[gross]  →  с текущими константами ~94.4%.
"""

MULT_TRIPLE_SEVEN = 12.0
MULT_TRIPLE_BAR = 6.0
MULT_TRIPLE_GRAPE = 3.0
MULT_TRIPLE_LEMON = 2.0

MULT_PAIR_ADJACENT = 1.45
MULT_SANDWICH = 0.32
SLOTS_COMMISSION_PERCENT = 2.0
MIN_SLOTS_BET = 1.0
MAX_SLOTS_BET = 5000.0


@dataclass(frozen=True)
class SlotsPayout:
    gross_win: float
    commission: float
    net_win: float


def parse_slots_bet(raw_bet: str, balance: float) -> tuple[float, bool]:
    normalized = raw_bet.strip().lower().replace(",", ".")
    is_all_in = normalized == "allin"
    if is_all_in:
        return money_2(balance), True

    bet = money_2(float(normalized))
    return bet, False


def validate_slots_bet(bet: float, balance: float, is_all_in: bool) -> str | None:
    normalized_balance = money_2(balance)
    if is_all_in:
        if normalized_balance <= 0:
            return "❌ У вас недостаточно 🪙PidorCoins для all in"
        if bet > normalized_balance:
            return "❌ У вас недостаточно 🪙PidorCoins."
        return None
    if not (MIN_SLOTS_BET <= bet <= MAX_SLOTS_BET):
        return f"💰 Сумма должна быть от {MIN_SLOTS_BET:.0f} до {MAX_SLOTS_BET:.0f} 🪙PidorCoins. Или вместо числа allin"
    if bet > normalized_balance:
        return "❌ У вас недостаточно 🪙PidorCoins."
    return None


def calculate_slots_payout(
        bet: float,
        multiplier: float,
        commission_percent: float = SLOTS_COMMISSION_PERCENT,
) -> SlotsPayout:
    gross_win = money_2(bet * multiplier)
    commission = money_2(gross_win * commission_percent / 100)
    net_win = money_2(gross_win - commission)
    return SlotsPayout(
        gross_win=gross_win,
        commission=commission,
        net_win=net_win,
    )


def get_slots_and_multiplier(dice_value: int) -> tuple[list[str], float]:
    """
    Возвращает кортеж из:
    - списка символов слотов (слева направо как у Telegram)
    - множителя выигрыша (валовой, к ставке)

    :param dice_value: значение дайса от Telegram (1–64)
    :return: (symbols, multiplier)
    """
    if not 1 <= dice_value <= 64:
        raise ValueError(f"Telegram slot dice value must be in 1..64, got {dice_value}")

    values = ["bar", "grape", "lemon", "seven"]

    dice_value -= 1
    slots: list[str] = []
    for _ in range(3):
        slots.append(values[dice_value % 4])
        dice_value //= 4

    s1, s2, s3 = slots

    if s1 == s2 == s3:
        match s1:
            case "seven":
                return slots, MULT_TRIPLE_SEVEN
            case "bar":
                return slots, MULT_TRIPLE_BAR
            case "grape":
                return slots, MULT_TRIPLE_GRAPE
            case "lemon":
                return slots, MULT_TRIPLE_LEMON

    if s1 == s2 or s2 == s3:
        return slots, MULT_PAIR_ADJACENT

    if s1 == s3:
        return slots, MULT_SANDWICH

    return slots, 0.0
