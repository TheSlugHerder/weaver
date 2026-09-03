from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from src.weaver import decorators, rate_limiter


@pytest.mark.asyncio
async def test_rate_limit_dep_allows(monkeypatch):
    recorded = {}

    async def fake_allow(key, limit, per_seconds):
        recorded['args'] = (key, limit, per_seconds)
        return True

    monkeypatch.setattr(rate_limiter, 'allow', fake_allow)
    user = SimpleNamespace(id='user123', is_superuser=False)
    dep = decorators.rate_limit_dep(5, 10)
    # call dependency directly
    await dep(None, user)
    assert recorded['args'][1] == 5 and recorded['args'][2] == 10
    assert recorded['args'][0].startswith('user:')


@pytest.mark.asyncio
async def test_rate_limit_dep_blocks(monkeypatch):
    async def fake_allow(key, limit, per_seconds):
        return False

    monkeypatch.setattr(rate_limiter, 'allow', fake_allow)
    user = SimpleNamespace(id='u', is_superuser=False)
    dep = decorators.rate_limit_dep(1, 1)
    with pytest.raises(HTTPException) as exc:
        await dep(None, user)
    assert exc.value.status_code == 429


@pytest.mark.asyncio
async def test_require_role_dep_allows_and_blocks():
    user_dm = SimpleNamespace(id='1', is_superuser=False, roles=['dm'])
    user_player = SimpleNamespace(id='2', is_superuser=False, roles=[])
    dep = decorators.require_role_dep('dm')
    # should not raise for DM
    await dep(user_dm)
    # non-DM should be forbidden
    import pytest as _pytest
    with _pytest.raises(HTTPException) as exc:
        await dep(user_player)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_require_role_dep_missing_user():
    dep = decorators.require_role_dep('dm')
    import pytest as _pytest
    with _pytest.raises(HTTPException) as exc:
        await dep(None)
    assert exc.value.status_code == 401
