from inspect import signature
from unittest.mock import patch

from fastapi import HTTPException

from app.models.access import Permission, Role, User
from app.routers.meta import RESET_ATS_ALLOWED_EMAIL, reset_ats
from scripts.seed import RESET_PERMISSION, RESET_ROLE, RESET_USER_EMAIL, ROLES


def main() -> None:
    assert all(RESET_PERMISSION not in permissions for permissions in ROLES.values())
    assert RESET_ATS_ALLOWED_EMAIL == RESET_USER_EMAIL
    reset_role = Role(name=RESET_ROLE, permissions=[Permission(code=RESET_PERMISSION)])
    vamshi = User(id=1, email=RESET_USER_EMAIL, roles=[reset_role])
    rishith = User(id=2, email="rishith@allknownservices.com", roles=[Role(name="team_member")])

    permission_check = signature(reset_ats).parameters["user"].default.dependency
    assert permission_check(vamshi) is vamshi
    try:
        permission_check(rishith)
    except HTTPException as error:
        assert error.status_code == 403
    else:
        raise AssertionError("A team member without ats.reset was authorized")

    with patch("app.routers.meta.reset_ats_data", return_value={"ok": True}) as reset_data:
        assert reset_ats(db=None, user=vamshi) == {"ok": True}
        reset_data.assert_called_once_with(None, actor_id=vamshi.id)
        john_with_misassigned_role = User(
            id=3, email="john@allknownservices.com", roles=[reset_role]
        )
        try:
            reset_ats(db=None, user=john_with_misassigned_role)
        except HTTPException as error:
            assert error.status_code == 403
        else:
            raise AssertionError("A non-Vamshi account was authorized to reset ATS")
        reset_data.assert_called_once()

    print("Vamshi-only ATS reset authorization checks passed.")


if __name__ == "__main__":
    main()
