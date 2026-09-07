import logging

from starlette_admin.contrib.sqlmodel import ModelView
from starlette_admin.exceptions import FormValidationError

from ...exceptions import (
    PottoCannotChangeCollectionOwnerException,
    PottoCannotCreateCollectionException,
    PottoCannotCreateUserException,
    PottoCannotEditCollectionException,
    PottoCannotEditServerMetadataException,
    PottoCannotSetAdminScopeException,
    PottoCannotSetScopesException,
)

logger = logging.getLogger(__name__)


class _PottoAdminModelView(ModelView):
    def handle_exception(self, exc: Exception) -> None:
        if isinstance(
            exc, (PottoCannotSetAdminScopeException, PottoCannotSetScopesException)
        ):
            raise FormValidationError({"scopes": str(exc)})
        if isinstance(exc, PottoCannotChangeCollectionOwnerException):
            raise FormValidationError({"owner": str(exc)})
        if isinstance(exc, PottoCannotEditCollectionException):
            raise FormValidationError({"resource_identifier": str(exc)})
        if isinstance(exc, PottoCannotCreateCollectionException):
            raise FormValidationError({"resource_identifier": str(exc)})
        if isinstance(exc, PottoCannotEditServerMetadataException):
            raise FormValidationError({"title": str(exc)})
        if isinstance(exc, PottoCannotCreateUserException):
            raise FormValidationError({"username": str(exc)})
        logger.exception("An error occurred", exc)
        return super().handle_exception(exc)
