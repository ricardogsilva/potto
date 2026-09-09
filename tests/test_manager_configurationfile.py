"""ConfigurationFileManager-specific tests.

Protocol-level behavior shared with other manager implementations (collection
visibility, pagination, capability-driven `CapabilityNotSupported` raising, user
lookups, authentication, resource-editor/viewer listing) lives in
`tests/test_manager_contract.py` instead, parametrized across all manager backends.
This file only covers what's genuinely specific to this manager: TOML parsing/
type-coercion, and its file-existence-based health check.
"""

from pathlib import Path

import pytest
import shapely

from potto import config
from potto.constants import CollectionType, ProvidedDataType
from potto.exceptions import CapabilityNotSupported
from potto.managers.configurationfile import manager as configurationfile_manager
from potto.managers.configurationfile import parsing
from potto.schemas.auth import PottoUser, UserCreateFromOidc

SAMPLE_CONFIG_FILE = (
    Path(__file__).parent / "data" / "configurationfile" / "sample_config.toml"
)


@pytest.fixture
def settings() -> config.PottoSettings:
    return config.PottoSettings()


@pytest.fixture
def manager(settings) -> configurationfile_manager.ConfigurationFileManager:
    return configurationfile_manager.get_configuration_file_manager(
        {"config_file": SAMPLE_CONFIG_FILE}, settings
    )


@pytest.fixture
def admin_user(manager) -> PottoUser:
    return manager.user_accounts["admin-1"]


class TestParsing:
    def test_collections_have_correctly_typed_fields(self, manager):
        geo_collection = manager.collections["geo-collection"]
        assert geo_collection.type_ is CollectionType.FEATURE_COLLECTION
        assert isinstance(geo_collection.owner, PottoUser)
        assert geo_collection.owner.id == "admin-1"
        assert isinstance(geo_collection.spatial_extent, shapely.Geometry)
        assert ProvidedDataType.FEATURE in geo_collection.providers
        assert geo_collection.providers[ProvidedDataType.FEATURE].provider_name == (
            "collection-config"
        )

    def test_server_metadata_has_correctly_typed_nested_fields(self, manager):
        server_metadata = manager.server_metadata
        assert server_metadata.license is not None
        assert server_metadata.license.name == "CC-BY-4.0"
        assert server_metadata.data_provider is not None
        assert server_metadata.data_provider.name == "Geobeyond"
        assert server_metadata.point_of_contact is not None
        assert server_metadata.point_of_contact.name == "Jane Doe"

    def test_unknown_owner_id_raises(self, manager):
        with pytest.raises(ValueError, match="unknown owner_id"):
            parsing.parse_collections(
                [{"identifier": "broken", "owner_id": "does-not-exist"}],
                manager.user_accounts,
            )


class TestCollections:
    @pytest.mark.asyncio
    async def test_get_collection_admin_view_is_none(self, manager):
        assert await manager.get_collection_admin_view() is None


class TestUserAccounts:
    @pytest.mark.asyncio
    async def test_authenticate_no_local_password(self, manager):
        # bob (user-2) has no `hashed_password` set in the sample config - a manager
        # backing an OIDC-only deployment. PostgisManager can't produce this
        # scenario through its protocol (UserCreate.password is required), so it
        # stays configurationfile-specific.
        assert await manager.authenticate("bob", "whatever") is None

    @pytest.mark.asyncio
    async def test_provision_oidc_user_raises(self, manager):
        # Not capability-gated (UserAccountManagerCapabilities has no corresponding
        # flag), so it can't be part of the shared, capability-branched contract test.
        with pytest.raises(CapabilityNotSupported):
            await manager.provision_oidc_user(
                UserCreateFromOidc(id="oidc-1", username="oidcuser")
            )


class TestCommon:
    @pytest.mark.asyncio
    async def test_check_health_missing_file(self, settings, tmp_path):
        config_file = tmp_path / "will-be-deleted.toml"
        config_file.write_text('[server_metadata]\ntitle = "Minimal"\n')
        instance_manager = configurationfile_manager.ConfigurationFileManager(
            configurationfile_manager.ConfigurationFileManagerConfiguration(
                config_file=config_file
            ),
            settings.get_authorization_backend(),
        )
        config_file.unlink()
        assert await instance_manager.check_health() == "error"

    def test_potto_cli_group(self, manager):
        assert manager.potto_cli_group == "configuration-file-manager"
