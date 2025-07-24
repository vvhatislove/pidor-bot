def get_slots_and_multiplier(dice_value: int) -> tuple[list[str], float]:
    """
    Возвращает кортеж из:
    - списка символов слотов (['bar', 'grape', 'lemon'])
    - множителя выигрыша (float)

    :param dice_value: значение дайса от Telegram (1–64)
    :return: (symbols, multiplier)
    """
    values = ["bar", "grape", "lemon", "seven"]

    # Декодируем dice_value → список символов
    dice_value -= 1
    slots = []
    for _ in range(3):
        slots.append(values[dice_value % 4])
        dice_value //= 4

    # Вычисляем множитель
    s1, s2, s3 = slots
    if s1 == s2 == s3:
        match s1:
            case "seven":
                return slots, 50
            case "bar":
                return slots, 20
            case "grape":
                return slots, 10
            case "lemon":
                return slots, 5

    if slots.count("seven") == 2:
        return slots, 5

    if len(set(slots)) == 2:
        return slots, 2

    return slots, 0
