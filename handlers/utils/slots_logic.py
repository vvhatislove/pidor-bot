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


def get_slots_and_multiplier(dice_value: int) -> tuple[list[str], float]:
    """
    Возвращает кортеж из:
    - списка символов слотов (слева направо как у Telegram)
    - множителя выигрыша (валовой, к ставке)

    :param dice_value: значение дайса от Telegram (1–64)
    :return: (symbols, multiplier)
    """
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
