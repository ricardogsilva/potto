# Potto authorization policy.
#
# This policy mirrors the logic of the LocalAuthorizationBackend and serves as a
# starting point for customisation. Potto queries three rules:
#
#   potto/authz/can_view_collection        input: {user, collection}  -> boolean
#   potto/authz/can_edit_collection        input: {user, collection}  -> boolean
#   potto/authz/accessible_collection_identifiers  input: {user}      -> [string] | null
#
# The user object has: id, username, scopes (list of strings).
# The collection object has: id, resource_identifier, is_public, owner_id.
#
# accessible_collection_identifiers must return null when the user should see all
# collections (e.g. admin), or a list of resource_identifier strings otherwise.

package potto.authz

import rego.v1

default can_view_collection := false
default can_edit_collection := false

# --- can_view_collection ---

can_view_collection if {
    input.collection.is_public
}

can_view_collection if {
    "admin" in input.user.scopes
}

can_view_collection if {
    input.user.id == input.collection.owner_id
}

can_view_collection if {
    concat("", ["collection-", input.collection.resource_identifier, ":editor"]) in input.user.scopes
}

can_view_collection if {
    concat("", ["collection-", input.collection.resource_identifier, ":viewer"]) in input.user.scopes
}

# --- can_edit_collection ---

can_edit_collection if {
    "admin" in input.user.scopes
}

can_edit_collection if {
    input.user.id == input.collection.owner_id
}

can_edit_collection if {
    concat("", ["collection-", input.collection.resource_identifier, ":editor"]) in input.user.scopes
}

# --- accessible_collection_identifiers ---
#
# Returns null for admins (unrestricted access), or the list of collection
# resource identifiers the user has explicit editor/viewer scope for.

accessible_collection_identifiers := null if {
    "admin" in input.user.scopes
}

accessible_collection_identifiers := identifiers if {
    not "admin" in input.user.scopes
    identifiers := [id |
        some scope in input.user.scopes
        matches := regex.find_all_string_submatch_n(`^collection-(.+):(editor|viewer)$`, scope, 1)
        count(matches) > 0
        id := matches[0][1]
    ]
}
