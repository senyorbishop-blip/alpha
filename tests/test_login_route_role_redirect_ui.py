from pathlib import Path


def test_login_route_role_is_redirect_authority_over_account_role():
    src = Path("client/templates/casual-dnd-login.html").read_text(encoding="utf-8")

    assert "const routeRole = String(ROUTE_ROLE || '').trim().toLowerCase();" in src
    assert "const effectiveRole = routeRole || userRole;" in src
    assert "if (effectiveRole === 'viewer') return storedInviteDestination('viewer') || '/viewer/watch';" in src
    assert "if (effectiveRole === 'player') return storedInviteDestination('player') || '/player/characters';" in src
