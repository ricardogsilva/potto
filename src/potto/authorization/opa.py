import logging

import httpx

from ..db.models import Collection
from ..schemas.auth import PottoUser

logger = logging.getLogger(__name__)


class OPAAuthorizationBackend:
    """Authorization backend that delegates policy decisions to Open Policy Agent."""

    def __init__(self, opa_url: str, policy_path: str = "potto/authz") -> None:
        self._base_url = opa_url.rstrip("/")
        self._policy_path = policy_path.strip("/")

    async def _query(self, rule: str, input_data: dict) -> object:
        url = f"{self._base_url}/v1/data/{self._policy_path}/{rule}"
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json={"input": input_data})
            response.raise_for_status()
            return response.json().get("result")

    def _user_input(self, user: PottoUser) -> dict | None:
        return {
            "id": user.id,
            "username": user.username,
            "scopes": user.scopes,
        } if user.is_authenticated else None

    def _collection_input(self, collection: Collection) -> dict:
        return {
            "id": collection.id,
            "resource_identifier": collection.resource_identifier,
            "is_public": collection.is_public,
            "owner_id": collection.owner_id,
        }

    async def can_view_collection(self, user: PottoUser, collection: Collection) -> bool:
        result = await self._query(
            "can_view_collection",
            {
                "user": self._user_input(user),
                "collection": self._collection_input(collection),
            },
        )
        return bool(result)

    async def can_edit_collection(self, user: PottoUser, collection: Collection) -> bool:
        result = await self._query(
            "can_edit_collection",
            {
                "user": self._user_input(user),
                "collection": self._collection_input(collection),
            },
        )
        return bool(result)

    async def get_accessible_collection_identifiers(
            self, user: PottoUser
    ) -> list[str] | None:
        result = await self._query(
            "accessible_collection_identifiers",
            {"user": self._user_input(user)},
        )
        if result is None:
            return None
        return list(result)
