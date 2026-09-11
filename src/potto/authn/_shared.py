from ..schemas.auth import PottoUser


def get_authn_system_user() -> PottoUser:
    """A synthetic, non-privileged user representing the identity-resolution step itself.

    Resolving who a request is coming from (from a validated session, JWT, or OIDC
    token) requires looking that user's own record up by id/username before a
    ``PottoUser`` for them even exists to act as the "requesting user" - there is no
    separate requester at that point, only an already-verified credential. Passing
    this sentinel instead of ``requesting_user=None`` avoids overloading ``None``
    (which already means "anonymous, deny" throughout ``LocalAuthorizationBackend``)
    as a trusted-caller signal.
    """
    return PottoUser(
        id="authn-system",
        username="authn-system",
        is_active=True,
        scopes=[],
    )
