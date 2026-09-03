
from beanie import Document
from pydantic import EmailStr


class User(Document):
    email: EmailStr
    hashed_password: str
    is_active: bool = True
    is_superuser: bool = False
    is_verified: bool = False
    # Roles allows flexible permission checks, e.g. ['dm', 'admin']
    roles: list[str] = []

    class Settings:
        name = "users"


# Note:
# This is a minimal Beanie `Document` for user records. Integration with
# `fastapi-users` will require a `UserCreate`, `UserRead`, and `UserUpdate`
# pydantic models and a compatible adapter (BeanieUserDatabase) from
# `fastapi-users-db-beanie` or similar package.
