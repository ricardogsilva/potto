---
icon: lucide/plug
---

# Resource managers

potto resources are handled by _resource managers_. These are pluggable entities which respect a
known protocol.

A resource manager

## Server metadata manager

## User account manager

## Collection manager

The collection manager deals with collections. It implements the
``potto.collectionmanager.CollectionManagerProtocol``, which defines a set of capabilities:

- Read access to collections. This comprises listing, searching and filtering and getting details about existing
  collections
- Mutating the set of collections known to potto. This comprises creating new collections, deleting and modifying
  existing collections.
- Managing users' access controls over private collections. This comprises granting and revoking access


# Builtin resource managers

## Postgis manager

## Configuration file manager


# Implementing custom managers


potto keeps all storage for collections, server metadata, and user accounts behind
three `Protocol` interfaces, so the storage backend can be swapped without touching
core code (routers, CLI, admin UI, auth). A single class may implement all three
protocols at once, or a deployment could mix managers per concern.


## The three protocols

| Protocol | Module | Responsibility |
| --- | --- | --- |
| `CollectionManagerProtocol` | `potto.collectionmanager` | Get/list/create/update/delete collections; grant/revoke access |
| `ServerMetadataProtocol` | `potto.servermetadatamanager` | Get/update the server's own metadata |
| `UserAccountProtocol` | `potto.useraccountmanager` | User CRUD, local/OIDC authentication, resource editor/viewer lookup |

Every protocol shares the same base shape:

- `check_health() -> "ok" | "not-ready" | "error"`
- `potto_cli_group` (str property) + `get_cli_group() -> cyclopts.App | None` -
  mounted as `potto <group> ...`
- `get_<x>_admin_view() -> ModelView | None` - for potto's admin UI
- `get_<x>_capabilities() -> <X>ManagerCapabilities` - a frozen dataclass of
  booleans, all `False` by default

Mutating methods (`create_*`, `update_*`, `delete_*`,
`grant_*`/`revoke_collection_access`) must raise
`potto.exceptions.CapabilityNotSupported` when the corresponding capability flag is
`False`. Callers should check capabilities rather than assume support.


## Selecting a manager

`PottoSettings` (`potto.config`) holds three independent settings blocks -
`collection_manager`, `server_metadata_manager`, `user_account_manager` - each with:

- `manager_factory`: an importable `(raw_config: dict, settings: PottoSettings) ->
  <Protocol>` callable
- `settings_model`: an opaque `dict`, validated only by whichever factory consumes it

```shell
POTTO__COLLECTION_MANAGER__MANAGER_FACTORY="potto.managers.configurationfile.manager:get_configuration_file_manager"
POTTO__COLLECTION_MANAGER__SETTINGS_MODEL__CONFIG_FILE="/etc/potto/potto.toml"
```

Managers are built lazily and cached per `PottoSettings`; factories may cache
further by config identity (e.g. keyed by DSN or file path), so pointing all three
slots at the same backend/config yields a single shared instance.


## `PostgisManager`

`potto.managers.postgis` - the default for all three slots. DB-backed
(PostgreSQL/PostGIS), read-write, reports every capability `True`.

- Config: `PostgisManagerConfiguration(database_dsn=...)`
- `check_health()` compares the DB's alembic revision against the migrations' head
- Own CLI group `potto postgis-manager`: `upgrade`, `downgrade`, `list-history`,
  `check-for-changes`, `generate-migration`, `import-from-pygeoapi`
- Admin UI views backed by SQLModel


## `ConfigurationFileManager`

`potto.managers.configurationfile` - read-only, loads a static TOML file once at
startup and serves everything from memory. No DB dependency.

- Config: `ConfigurationFileManagerConfiguration(config_file=...)`
- Reports every capability `False`; every mutating method raises
  `CapabilityNotSupported` (except `authenticate`, which checks an optional bcrypt
  `hashed_password` field)
- No CLI group, no admin views - nothing to edit at runtime
- `check_health()` just checks the file still exists

TOML shape:

```toml
[[user_account]]
id = "u1"
username = "alice"
is_active = true
scopes = ["admin"]
hashed_password = "$2b$12$..."   # optional - omit for OIDC-only users

[[collection]]
identifier = "buildings"
type_ = "feature"           # a potto.constants.CollectionType value
owner_id = "u1"              # resolved against [[user_account]] entries
is_public = true
title = "Buildings"
crs = ["http://www.opengis.net/def/crs/OGC/1.3/CRS84"]
created_at = 2024-01-01T00:00:00Z
updated_at = 2024-01-01T00:00:00Z

[server_metadata]
title = "My potto server"
```

Good fit for small, read-only, or demo deployments that don't need a database.


## Writing a new manager

1. Implement whichever protocol(s) it should back - one class may implement all
   three.
2. Write a `get_<name>_manager(raw_config: dict, settings: PottoSettings) ->
   YourManager` factory.
3. Point the relevant `manager_factory` setting at it.
4. Validate it against `tests/test_manager_contract.py`'s parametrized contract
   suite - add your manager as a new backend fixture there to confirm it conforms to
   the same protocol-level behavior as the existing managers.
