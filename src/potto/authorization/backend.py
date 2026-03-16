import re
from typing import Protocol

from ..db.models import Collection
from ..schemas.auth import PottoScope, PottoUser

_COLLECTION_SCOPE_RE = re.compile(r"^collection-(.+):(editor|viewer)$")


class AuthorizationBackendProtocol(Protocol):
    async def can_view_collection(self, user: PottoUser, collection: Collection) -> bool:
        """Return True if the user is allowed to view the collection."""
        ...

    async def can_edit_collection(self, user: PottoUser, collection: Collection) -> bool:
        """Return True if the user is allowed to edit the collection."""
        ...

    async def get_accessible_collection_identifiers(
            self, user: PottoUser
    ) -> list[str] | None:
        """Return identifiers of collections accessible to the user.

        Returns None if the user has unrestricted access (e.g. admin), or a list of
        collection resource identifiers the user can explicitly access.
        """
        ...


class LocalAuthorizationBackend:
    """Authorization backend that evaluates permissions from locally-stored user scopes."""

    async def can_view_collection(self, user: PottoUser, collection: Collection) -> bool:
        if collection.is_public:
            return True
        if PottoScope.ADMIN.value in user.scopes:
            return True
        if user.id == collection.owner_id:
            return True
        if PottoScope.collection_editor(collection.resource_identifier) in user.scopes:
            return True
        if PottoScope.collection_viewer(collection.resource_identifier) in user.scopes:
            return True
        return False

    async def can_edit_collection(self, user: PottoUser, collection: Collection) -> bool:
        if PottoScope.ADMIN.value in user.scopes:
            return True
        if user.id == collection.owner_id:
            return True
        if PottoScope.collection_editor(collection.resource_identifier) in user.scopes:
            return True
        return False

    async def get_accessible_collection_identifiers(
            self, user: PottoUser
    ) -> list[str] | None:
        if PottoScope.ADMIN.value in user.scopes:
            return None
        return [
            m.group(1)
            for scope in user.scopes
            if (m := _COLLECTION_SCOPE_RE.match(scope))
        ]
