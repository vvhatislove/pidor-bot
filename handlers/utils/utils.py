from database.models import User

def get_display_name(user: User) -> str:
    if user.username:
        return f"@{user.username}"
    else:
        return f'<a href="tg://user?id={user.telegram_id}">{user.first_name}</a>'
