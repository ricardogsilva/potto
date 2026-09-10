import pydantic
import sqlmodel
from pydantic.networks import PostgresDsn
from sqlalchemy import Engine
from sqlalchemy.ext.asyncio.engine import (
    AsyncEngine,
    create_async_engine,
)
from sqlalchemy.ext.asyncio.session import async_sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession


class PostgisManagerConfiguration(pydantic.BaseModel):
    _db_engine: AsyncEngine | None = None
    _sync_db_engine: Engine | None = None
    _db_session_maker: async_sessionmaker | None = None

    # Configured independently per manager instance (collections/server-metadata/
    # user-accounts each have their own settings_model) - this manager owns its DB
    # connection outright, it does not inherit from PottoSettings.
    database_dsn: PostgresDsn = PostgresDsn(
        "postgresql+psycopg://potto:pottopass@localhost/potto"
    )

    # Only ever read directly by the test suite (tests/conftest.py, tests/live_server.py)
    # to override this manager's own database_dsn when running tests - not used by any
    # production code path.
    test_database_dsn: PostgresDsn = PostgresDsn(
        "postgresql+psycopg://potto:pottopass@localhost/potto_test"
    )

    def get_db_engine(self) -> AsyncEngine:
        if self._db_engine is None:
            self._db_engine = create_async_engine(self.database_dsn.unicode_string())
        return self._db_engine

    def get_sync_db_engine(self) -> Engine:
        if self._sync_db_engine is None:
            self._sync_db_engine = sqlmodel.create_engine(
                self.database_dsn.unicode_string()
            )
        return self._sync_db_engine

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
