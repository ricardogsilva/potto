from ..schemas.auth import PottoScope, PottoUser


def get_cli_system_user() -> PottoUser:
    """A synthetic, admin-scoped user representing a trusted CLI caller.

    The CLI is admin-only by convention (it runs with direct access to the
    deployment, not through any web-facing authentication). Passing this user
    to manager methods lets the CLI reuse the same authorization checks as any
    other admin-scoped caller, instead of a separate bypass mechanism.
    """
    return PottoUser(
        id="cli",
        username="cli",
        is_active=True,
        scopes=[PottoScope.ADMIN.value],
    )
