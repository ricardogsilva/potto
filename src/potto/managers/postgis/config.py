import pydantic
from pydantic.networks import PostgresDsn
from sqlalchemy.ext.asyncio.engine import (
    AsyncEngine,
    create_async_engine,
)
from sqlalchemy.ext.asyncio.session import async_sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession


class PostgisManagerConfiguration(pydantic.BaseModel):
    _db_engine: AsyncEngine | None = None
    _db_session_maker: async_sessionmaker | None = None

    # None means "inherit PottoSettings.database_dsn" - resolved by the factory
    # function in manager.py. This keeps POTTO__DATABASE_DSN working as the
    # single source of truth for the default deployment, while still letting a
    # deployment point a specific manager at a different database explicitly.
    database_dsn: PostgresDsn | None = None

    def get_db_engine(self) -> AsyncEngine:
        # database_dsn is expected to already be resolved (non-None) by the time
        # any manager built from this config is actually used - see
        # _get_or_create_manager() in manager.py.
        assert self.database_dsn is not None
        if self._db_engine is None:
            self._db_engine = create_async_engine(self.database_dsn.unicode_string())
        return self._db_engine

    def get_db_session_maker(self) -> async_sessionmaker:
        if self._db_session_maker is None:
            self._db_session_maker = async_sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.get_db_engine(),
                expire_on_commit=False,
                class_=AsyncSession,
            )
        return self._db_session_maker
