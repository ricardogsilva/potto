from typing import Protocol

from ..db.models import Collection
from ..schemas.auth import PottoUser


class AuthorizationBackendProtocol(Protocol):
    async def can_view_collection(self, user: PottoUser | None, collection: Collection) -> bool:
        """Return True if the user is allowed to view the collection.

        A None user represents an unauthenticated (anonymous) visitor.
        """
        ...

    async def can_edit_collection(self, user: PottoUser | None, collection: Collection) -> bool:
        """Return True if the user is allowed to edit the collection.

        A None user represents an unauthenticated (anonymous) visitor.
        """
        ...

    async def get_accessible_collection_identifiers(
            self, user: PottoUser | None
    ) -> list[str] | None:
        """Return identifiers of collections accessible to the user.

        A None user represents an unauthenticated (anonymous) visitor.
        Returns None if the user has unrestricted access (e.g. admin), or a list of
        collection resource identifiers the user can explicitly access.
        """
        ...

    async def can_set_user_scopes(
            self,
            requesting_user: PottoUser | None,
            new_scopes: list[str],
            editable_collection_identifiers: list[str],
    ) -> bool:
        """Return True if requesting_user is allowed to assign new_scopes to a target user.

        editable_collection_identifiers: identifiers of collections the requesting user
        can edit (owner or editor role), pre-fetched by the caller.
        """
        ...

    async def can_assign_admin_scope(self, requesting_user: PottoUser | None) -> bool:
        """Return True if requesting_user is allowed to grant the admin scope to another user."""
        ...
