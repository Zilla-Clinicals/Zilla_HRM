"""Optional TOTP two-factor: setup, enable, login challenge, verify, recovery, disable."""
import pyotp

from tests.conftest import ADMIN_EMAIL, ADMIN_PASSWORD, auth


async def _code_for(secret: str) -> str:
    return pyotp.TOTP(secret).now()


async def test_setup_returns_secret_and_uri(client, admin_token):
    r = await client.post("/api/users/me/2fa/setup", headers=auth(admin_token))
    assert r.status_code == 200
    d = r.json()
    assert d["secret"] and len(d["secret"]) >= 16
    assert d["otpauth_uri"].startswith("otpauth://totp/")
    assert "Zilla" in d["otpauth_uri"]
    # not yet enabled — /me still reports off
    me = (await client.get("/api/users/me", headers=auth(admin_token))).json()
    assert me["user"]["mfa_enabled"] is False


async def test_enable_requires_valid_code(client, admin_token):
    await client.post("/api/users/me/2fa/setup", headers=auth(admin_token))
    r = await client.post(
        "/api/users/me/2fa/enable", headers=auth(admin_token), json={"code": "000000"}
    )
    assert r.status_code == 400


async def test_enable_flow_and_me_flag(client, admin_token):
    setup = (await client.post("/api/users/me/2fa/setup", headers=auth(admin_token))).json()
    secret = setup["secret"]
    r = await client.post(
        "/api/users/me/2fa/enable",
        headers=auth(admin_token),
        json={"code": await _code_for(secret)},
    )
    assert r.status_code == 200
    codes = r.json()["recovery_codes"]
    assert len(codes) == 10 and all("-" in c for c in codes)

    me = (await client.get("/api/users/me", headers=auth(admin_token))).json()
    assert me["user"]["mfa_enabled"] is True


async def test_login_challenge_and_totp_verify(client, admin_token):
    setup = (await client.post("/api/users/me/2fa/setup", headers=auth(admin_token))).json()
    secret = setup["secret"]
    await client.post(
        "/api/users/me/2fa/enable",
        headers=auth(admin_token),
        json={"code": await _code_for(secret)},
    )

    # password login now returns a challenge, not tokens
    r = await client.post(
        "/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    assert r.status_code == 200
    d = r.json()
    assert d["mfa_required"] is True and d["access_token"] is None and d["mfa_token"]

    # a wrong code is rejected
    bad = await client.post(
        "/api/auth/login/verify", json={"mfa_token": d["mfa_token"], "code": "000000"}
    )
    assert bad.status_code == 401

    # correct TOTP completes login
    good = await client.post(
        "/api/auth/login/verify",
        json={"mfa_token": d["mfa_token"], "code": await _code_for(secret)},
    )
    assert good.status_code == 200 and good.json()["access_token"]


async def test_login_verify_with_recovery_code_single_use(client, admin_token):
    setup = (await client.post("/api/users/me/2fa/setup", headers=auth(admin_token))).json()
    secret = setup["secret"]
    codes = (
        await client.post(
            "/api/users/me/2fa/enable",
            headers=auth(admin_token),
            json={"code": await _code_for(secret)},
        )
    ).json()["recovery_codes"]
    recovery = codes[0]

    challenge = (
        await client.post(
            "/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
    ).json()
    r = await client.post(
        "/api/auth/login/verify",
        json={"mfa_token": challenge["mfa_token"], "code": recovery},
    )
    assert r.status_code == 200 and r.json()["access_token"]

    # the same recovery code cannot be reused
    challenge2 = (
        await client.post(
            "/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
    ).json()
    reuse = await client.post(
        "/api/auth/login/verify",
        json={"mfa_token": challenge2["mfa_token"], "code": recovery},
    )
    assert reuse.status_code == 401


async def test_disable_requires_password_then_restores_plain_login(client, admin_token):
    setup = (await client.post("/api/users/me/2fa/setup", headers=auth(admin_token))).json()
    secret = setup["secret"]
    await client.post(
        "/api/users/me/2fa/enable",
        headers=auth(admin_token),
        json={"code": await _code_for(secret)},
    )

    # wrong password rejected
    bad = await client.post(
        "/api/users/me/2fa/disable", headers=auth(admin_token), json={"password": "nope"}
    )
    assert bad.status_code == 400

    ok = await client.post(
        "/api/users/me/2fa/disable",
        headers=auth(admin_token),
        json={"password": ADMIN_PASSWORD},
    )
    assert ok.status_code == 204

    me = (await client.get("/api/users/me", headers=auth(admin_token))).json()
    assert me["user"]["mfa_enabled"] is False

    # login goes straight to tokens again
    r = await client.post(
        "/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    assert r.json()["mfa_required"] is False and r.json()["access_token"]


async def test_mfa_challenge_token_is_not_an_access_token(client, admin_token):
    """Regression (F1): the pre-2FA challenge token must NOT authorize protected routes."""
    setup = (await client.post("/api/users/me/2fa/setup", headers=auth(admin_token))).json()
    await client.post(
        "/api/users/me/2fa/enable",
        headers=auth(admin_token),
        json={"code": await _code_for(setup["secret"])},
    )
    challenge = (
        await client.post(
            "/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
    ).json()
    assert challenge["mfa_required"] is True
    # Using the mfa_token as a Bearer must be rejected — otherwise 2FA is bypassable.
    r = await client.get("/api/users/me", headers=auth(challenge["mfa_token"]))
    assert r.status_code == 401


async def test_totp_code_cannot_be_replayed(client, admin_token):
    """Regression (F4): a TOTP code is single-use within its validity window."""
    setup = (await client.post("/api/users/me/2fa/setup", headers=auth(admin_token))).json()
    secret = setup["secret"]
    await client.post(
        "/api/users/me/2fa/enable", headers=auth(admin_token), json={"code": await _code_for(secret)}
    )
    code = pyotp.TOTP(secret).now()

    ch1 = (
        await client.post(
            "/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
    ).json()
    first = await client.post(
        "/api/auth/login/verify", json={"mfa_token": ch1["mfa_token"], "code": code}
    )
    assert first.status_code == 200

    ch2 = (
        await client.post(
            "/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
    ).json()
    replay = await client.post(
        "/api/auth/login/verify", json={"mfa_token": ch2["mfa_token"], "code": code}
    )
    assert replay.status_code == 401


async def test_double_setup_conflicts_after_enable(client, admin_token):
    setup = (await client.post("/api/users/me/2fa/setup", headers=auth(admin_token))).json()
    await client.post(
        "/api/users/me/2fa/enable",
        headers=auth(admin_token),
        json={"code": await _code_for(setup["secret"])},
    )
    again = await client.post("/api/users/me/2fa/setup", headers=auth(admin_token))
    assert again.status_code == 409
