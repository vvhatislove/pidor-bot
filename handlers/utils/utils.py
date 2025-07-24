from database.models import User

def get_display_name(user: User) -> str:
    if user.username:
        return f"@{user.username}"
    return user.first_name or "НоуНейм"
