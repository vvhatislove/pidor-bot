from dataclasses import dataclass


@dataclass(frozen=True)
class TransactionCategory:
    debit: bool
    display_name: str


class TransactionReason:
    PIDOR_REWARD = "pidor_reward"
    ADMIN_ADD_BALANCE = "admin_add_balance"
    SLOTS_BET = "slots_bet"
    SLOTS_WIN = "slots_win"
    DUEL_INITIATOR_BET = "duel_initiator_bet"
    DUEL_OPPONENT_BET = "duel_opponent_bet"
    DUEL_WINNER_PAYOUT = "duel_winner_payout"
    DUEL_INITIATOR_REFUND = "duel_initiator_refund"
    DUEL_OPPONENT_REFUND = "duel_opponent_refund"
    ACHIEVEMENT_REWARD = "achievement_reward"


_LEGACY_REASON_MAP = {
    "pidor of the day": TransactionReason.PIDOR_REWARD,
    "admin addbalance": TransactionReason.ADMIN_ADD_BALANCE,
    "slots bet": TransactionReason.SLOTS_BET,
    "slots win": TransactionReason.SLOTS_WIN,
    "duel initiator bet": TransactionReason.DUEL_INITIATOR_BET,
    "duel opponent bet": TransactionReason.DUEL_OPPONENT_BET,
    "duel winner payout": TransactionReason.DUEL_WINNER_PAYOUT,
    "refund initiator bet(duel was cancelled)": TransactionReason.DUEL_INITIATOR_REFUND,
    "refund opponent bet(duel was cancelled)": TransactionReason.DUEL_OPPONENT_REFUND,
}

_CATEGORIES = {
    TransactionReason.PIDOR_REWARD: TransactionCategory(False, "награда за пидора дня"),
    TransactionReason.ADMIN_ADD_BALANCE: TransactionCategory(False, "начисление админом"),
    TransactionReason.SLOTS_BET: TransactionCategory(True, "ставка в слотах"),
    TransactionReason.SLOTS_WIN: TransactionCategory(False, "выигрыш в слотах"),
    TransactionReason.DUEL_INITIATOR_BET: TransactionCategory(True, "ставка инициатора дуэли"),
    TransactionReason.DUEL_OPPONENT_BET: TransactionCategory(True, "ставка оппонента дуэли"),
    TransactionReason.DUEL_WINNER_PAYOUT: TransactionCategory(False, "выплата победителю дуэли"),
    TransactionReason.DUEL_INITIATOR_REFUND: TransactionCategory(False, "возврат ставки инициатору дуэли"),
    TransactionReason.DUEL_OPPONENT_REFUND: TransactionCategory(False, "возврат ставки оппоненту дуэли"),
    TransactionReason.ACHIEVEMENT_REWARD: TransactionCategory(False, "награда за достижение"),
}


def normalize_transaction_reason(reason: str) -> str:
    normalized = reason.strip().lower()
    base = normalized.split(maxsplit=1)[0]
    return _LEGACY_REASON_MAP.get(normalized, _LEGACY_REASON_MAP.get(base, base))


def transaction_category(reason: str) -> TransactionCategory:
    normalized = normalize_transaction_reason(reason)
    return _CATEGORIES.get(normalized, TransactionCategory(False, reason))


def transaction_display_name(reason: str) -> str:
    return transaction_category(reason).display_name


def is_transaction_debit(reason: str) -> bool:
    return transaction_category(reason).debit


def admin_add_balance_reason(admin_telegram_id: int) -> str:
    return f"{TransactionReason.ADMIN_ADD_BALANCE} by={admin_telegram_id}"


def achievement_reward_reason(code: str) -> str:
    return f"{TransactionReason.ACHIEVEMENT_REWARD} code={code}"
