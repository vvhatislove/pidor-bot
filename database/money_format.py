from decimal import ROUND_DOWN, Decimal


def money_2(value: float) -> float:
    """
    Два знака после запятой: лишняя дробная часть отбрасывается вниз (ROUND_DOWN).
    Сначала убираем бинарный мусор float, чтобы не терять копейки при вычитании.
    """
    cleaned = round(float(value), 10)
    return float(Decimal(str(cleaned)).quantize(Decimal("0.01"), rounding=ROUND_DOWN))
