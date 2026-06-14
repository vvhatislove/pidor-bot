from types import SimpleNamespace

from config.config import config
from database.repositories.chat_repository import ChatRepository
from database.repositories.currency_transaction_repository import CurrencyTransactionRepository
from database.repositories.user_repository import UserRepository
from database.transaction_reasons import TransactionReason
from handlers.admin.add_balance import cmd_add_balance


class FakeMessage:
    def __init__(self, text: str):
        self.text = text
        self.chat = SimpleNamespace(id=-100, type="group")
        self.from_user = SimpleNamespace(id=config.ADMIN_ID)
        self.answers = []
        self.replies = []

    async def answer(self, text: str, **kwargs):
        self.answers.append(text)

    async def reply(self, text: str, **kwargs):
        self.replies.append(text)


async def test_admin_addbalance_records_source_in_transaction_reason(session):
    await ChatRepository.create_chat(session, -100, "chat")
    user = await UserRepository.create_user(session, 1, -100, "User", "user")

    await cmd_add_balance(FakeMessage("/addbalance @user 125.50"), session)

    assert user.balance == 125.50

    transactions = await CurrencyTransactionRepository.get_user_transactions(session, user.id)
    assert len(transactions) == 1
    assert transactions[0].amount == 125.50
    assert transactions[0].reason == f"{TransactionReason.ADMIN_ADD_BALANCE} by={config.ADMIN_ID}"
