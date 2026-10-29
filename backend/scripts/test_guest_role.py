from scripts.seed import ADMIN_ONLY, PERMISSIONS, RESET_PERMISSION, ROLES


guest = set(ROLES["guest"])
assert "candidate.view" in guest
assert "candidate.edit" in guest
assert "candidate.archive" in guest
assert "document.upload" in guest
assert "note.add" in guest
assert "job.manage" in guest
assert "submission.manage" in guest
assert "search.use" in guest
assert "candidate.delete" not in guest
assert "job.delete" not in guest
assert "user.manage" not in guest
assert "audit.view" not in guest
assert RESET_PERMISSION not in guest
assert guest == set(PERMISSIONS) - ADMIN_ONLY - {"job.delete"}
assert "job.delete" in ROLES["admin"] and "job.delete" in ROLES["team_member"]
assert "job.delete" in ROLES["recruiter"]
assert all(RESET_PERMISSION not in role_permissions for role_permissions in ROLES.values())
print("Guest role permission checks passed.")
