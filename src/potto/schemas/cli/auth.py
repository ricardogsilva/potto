import pydantic

from ..auth import PottoUser


class UserListItem(pydantic.BaseModel):
    id: str
    username: str
    scopes: list[str]

    @classmethod
    def from_potto(cls, user: PottoUser) -> "UserListItem":
        return cls(id=user.id, username=user.username, scopes=user.scopes)


class UserDetail(UserListItem):
    @classmethod
    def from_potto(cls, user: PottoUser) -> "UserDetail":
        return cls(id=user.id, username=user.username, scopes=user.scopes)
