import pydantic

from ...db.models import User


class UserListItem(pydantic.BaseModel):
    id: str
    username: str
    scopes: list[str]

    @classmethod
    def from_db_item(cls, user: User) -> "UserListItem":
        return cls(**user.model_dump())


class UserDetail(UserListItem):
    @classmethod
    def from_db_item(cls, user: User) -> "UserDetail":
        return cls(**user.model_dump())
