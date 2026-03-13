import re

from .db.models import Collection
from .schemas.auth import PottoScope, PottoUser

_COLLECTION_SCOPE_RE = re.compile(r"^collection-(.+):(editor|viewer)$")


def can_view_collection(user: PottoUser, collection: Collection) -> bool:
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


def can_edit_collection(user: PottoUser, collection: Collection) -> bool:
    if PottoScope.ADMIN.value in user.scopes:
        return True
    if user.id == collection.owner_id:
        return True
    if PottoScope.collection_editor(collection.resource_identifier) in user.scopes:
        return True
    return False


def get_accessible_collection_identifiers(user: PottoUser) -> list[str]:
    """Extract collection resource identifiers from the user's editor/viewer scopes."""
    return [
        m.group(1)
        for scope in user.scopes
        if (m := _COLLECTION_SCOPE_RE.match(scope))
    ]
