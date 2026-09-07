import dataclasses
from typing import (
    Any,
    Callable,
    Literal,
    Protocol,
    TypeAlias,
    TYPE_CHECKING,
)

if TYPE_CHECKING:
    from starlette_admin.contrib.sqlmodel import ModelView

    from .config import PottoSettings
    from .schemas.auth import PottoUser
    from .schemas.metadata import ServerMetadata, ServerMetadataUpdate


class PottoServerMetadataManagerError(Exception): ...


class ServerMetadataManagerCapabilityNotSupported(PottoServerMetadataManagerError): ...


@dataclasses.dataclass(frozen=True)
class ServerMetadataManagerCapabilities:
    supports_modification: bool = False


class ServerMetadataProtocol(Protocol):
    """A protocol for potto server metadata managers."""

    async def check_health(self) -> Literal["ok", "not-ready", "error"]:
        """Check whether the manager is healthy."""

    async def set_up(self) -> bool:
        """Ensure the manager is ready to be used by potto."""

    async def get_server_metadata_admin_view(self) -> "ModelView | None":
        """Return a starlette_admin view suitable for use in potto's admin ui."""

    async def get_server_metadata_capabilities(
        self,
    ) -> ServerMetadataManagerCapabilities:
        """Return the manager's capabilities."""

    async def get_server_metadata(self) -> "ServerMetadata":
        """Return pre-existing server metadata, creating a default record if none exists."""

    async def update_server_metadata(
        self,
        to_update: "ServerMetadataUpdate",
        user: "PottoUser | None",
    ) -> "ServerMetadata":
        """Update the server's metadata.

        When the manager does not support updating metadata this should raise
        ``potto.servermetadatamanager.ServerMetadataManagerCapabilityNotSupported``.
        """


ServerMetadataManagerFactoryProtocol: TypeAlias = Callable[
    [dict[str, Any], "PottoSettings"],
    ServerMetadataProtocol,
]
