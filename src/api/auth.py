from __future__ import annotations

import json
import logging
import secrets
import string
import threading
import urllib.parse
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import httpx
from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from src.config import settings
from src.db.database import get_session
from src.db.models import DeviceToken, User
from src.garmin.client import GarminClient
from src.security import encrypt
from src.services.data_sync import DataSyncService
from src.services.sync_helper import garmin_login, sync_with_client
from src.services.sync_tasks import run_backfill
from src.rate_limit import limiter


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))

router = APIRouter(prefix="/auth", tags=["auth"])
security = HTTPBearer()
logger = logging.getLogger(__name__)

ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

# ── Pairing code store (in-memory) ──────────────────────────────────────────
_pairing_codes: dict[str, dict] = {}
_pair_lock = threading.Lock()

BACKEND_BASE = (settings.backend_url or "http://localhost:8000").rstrip("/")

def _generate_pairing_code() -> str:
    return "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))

def _cleanup_expired_pairs() -> None:
    now = datetime.now(timezone.utc)
    expired = [k for k, v in list(_pairing_codes.items()) if v.get("expires_at") and v["expires_at"] < now]
    for k in expired:
        del _pairing_codes[k]

# ── Pairing endpoints ───────────────────────────────────────────────────────

class PairClaimRequest(BaseModel):
    code: str
    access_token: str


@router.post("/pair")
def create_pairing_code() -> dict:
    """Create a new pairing code for watch pairing."""
    _cleanup_expired_pairs()
    code = _generate_pairing_code()
    with _pair_lock:
        _pairing_codes[code] = {
            "code": code,
            "status": "waiting",
            "created_at": datetime.now(timezone.utc),
            "expires_at": datetime.now(timezone.utc) + timedelta(minutes=5),
            "access_token": None,
            "token_type": "bearer",
            "expires_in": None,
            "user": None,
        }
    return {"code": code, "expires_at": _pairing_codes[code]["expires_at"].isoformat()}


@router.get("/pair")
def check_pairing(code: str) -> dict:
    """Polling endpoint — returns pairing status."""
    _cleanup_expired_pairs()
    pair = _pairing_codes.get(code)
    if not pair:
        raise HTTPException(status_code=404, detail="Invalid or expired code")
    if pair["status"] == "paired":
        return {
            "status": "paired",
            "access_token": pair["access_token"],
            "token_type": pair["token_type"],
            "expires_in": pair["expires_in"],
            "user": pair["user"],
        }
    return {"status": "waiting"}


@router.get("/pair-login")
def pair_login_page(code: str) -> HTMLResponse:
    """Phone login page — user opens this to pair their watch."""
    supabase_url = settings.supabase_url or ""
    callback_url = f"{BACKEND_BASE}/api/v1/auth/pair-callback/{code}"
    escaped_callback = urllib.parse.quote(callback_url, safe="")
    supabase_auth_url = f"{supabase_url}/auth/v1/authorize?provider=google&redirect_to={escaped_callback}"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Vitality AI Coach — Pair Watch</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: #779bc1; color: #fff;
    display: flex; justify-content: center; align-items: center;
    min-height: 100vh; padding: 20px;
}}
.card {{
    background: #fff; color: #1a1a1a; border-radius: 24px;
    padding: 40px 32px; width: 100%; max-width: 380px;
    text-align: center; box-shadow: 0 8px 32px rgba(0,0,0,0.15);
}}
.logo {{ margin-bottom: 24px; }}
.logo-circle {{
    width: 48px; height: 48px; background: #1a1a1a;
    border-radius: 50%; display: inline-flex; align-items: center;
    justify-content: center; color: #fff;
    font-size: 22px; font-weight: 700;
}}
h1 {{ font-size: 20px; margin: 12px 0 8px; }}
.code-display {{
    background: #f5f5f5; border-radius: 12px;
    padding: 16px; margin: 20px 0;
    font-size: 32px; font-weight: 700; letter-spacing: 6px;
    font-family: 'SFMono', 'Monaco', monospace;
}}
p {{ font-size: 14px; color: #666; margin-bottom: 16px; }}
.google-btn {{
    width: 100%; height: 52px;
    background: #1a1a1a; color: #fff; border: none;
    border-radius: 9999px; font-size: 15px; font-weight: 600;
    cursor: pointer; display: flex; align-items: center;
    justify-content: center; gap: 10px;
    transition: opacity 0.2s;
}}
.google-btn:hover {{ opacity: 0.9; }}
.google-btn svg {{ width: 20px; height: 20px; }}
.hint {{ font-size: 12px; color: #999; margin-top: 20px; }}
</style>
</head>
<body>
<div class="card">
    <div class="logo"><div class="logo-circle">V</div></div>
    <h1>Vitality AI Coach</h1>
    <p>Pair your watch by signing in with Google</p>
    <div class="code-display">{code}</div>
    <button class="google-btn" onclick="window.location.href='{supabase_auth_url}'">
        <svg viewBox="0 0 24 24"><path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"/><path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/><path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/></svg>
        Sign in with Google
    </button>
    <p class="hint">This code will expire in 5 minutes</p>
</div>
</body>
</html>"""
    return HTMLResponse(content=html)


@router.get("/pair-callback/{code}")
def pair_callback(code: str) -> HTMLResponse:
    """Supabase OAuth callback — JS reads fragment token and claims pairing."""
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Vitality AI Coach — Connecting...</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: #fff; display: flex; justify-content: center;
    align-items: center; min-height: 100vh; padding: 20px;
}}
.card {{ text-align: center; padding: 32px; }}
.spinner {{
    width: 40px; height: 40px;
    border: 3px solid #ddd; border-top-color: #1a1a1a;
    border-radius: 50%; animation: spin 0.8s linear infinite;
    margin: 0 auto 16px;
}}
@keyframes spin {{ to {{ transform: rotate(360deg); }} }}
h1 {{ font-size: 20px; color: #333; margin-bottom: 8px; }}
p {{ font-size: 14px; color: #666; }}
.error {{ color: #e53e3e; }}
</style>
</head>
<body>
<div class="card">
    <div class="spinner"></div>
    <h1>Connecting...</h1>
    <p id="status">Linking to your watch...</p>
</div>
<script>
(function() {{
    var statusEl = document.getElementById('status');
    var code = {json.dumps(code)};
    var hash = window.location.hash;

    if (!hash || hash.length < 2) {{
        statusEl.innerHTML = '<span class="error">No session data received.</span>';
        return;
    }}

    var params = new URLSearchParams(hash.substring(1));
    var accessToken = params.get('access_token');

    if (!accessToken) {{
        statusEl.innerHTML = '<span class="error">Access token not found.</span>';
        return;
    }}

    statusEl.textContent = 'Signing in...';

    fetch('/api/v1/auth/token', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify({{ token: accessToken }})
    }})
    .then(function(r) {{ return r.json(); }})
    .then(function(data) {{
        if (data.access_token) {{
            statusEl.textContent = 'Pairing with watch...';
            return fetch('/api/v1/auth/pair/claim', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ code: code, access_token: data.access_token }})
            }});
        }} else {{
            throw new Error(data.detail || 'Login failed');
        }}
    }})
    .then(function(r) {{ return r.json(); }})
    .then(function(data) {{
        if (data.status === 'paired') {{
            statusEl.innerHTML = '<p style="color:#22c55e; font-size:48px; margin-bottom:12px;">✓</p><h1>Connected!</h1><p>Your watch is now paired. You can close this page.</p>';
        }} else {{
            throw new Error('Pairing failed');
        }}
    }})
    .catch(function(err) {{
        statusEl.innerHTML = '<span class="error">Error: ' + err.message + '</span>';
    }});
}})();
</script>
</body>
</html>"""
    return HTMLResponse(content=html)


@router.post("/pair/claim")
def claim_pairing(req: PairClaimRequest) -> dict:
    """Claim a pairing code — stores the JWT for the watch to poll."""
    code = req.code
    access_token = req.access_token

    try:
        payload = jwt.decode(access_token, settings.app_secret_key, algorithms=["HS256"])
        user_id = int(payload.get("sub", 0))
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")

    session = get_session()
    try:
        user = session.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        with _pair_lock:
            pair = _pairing_codes.get(code)
            if not pair:
                raise HTTPException(status_code=404, detail="Invalid pairing code")
            pair["status"] = "paired"
            pair["access_token"] = access_token
            pair["token_type"] = "bearer"
            pair["expires_in"] = ACCESS_TOKEN_EXPIRE_MINUTES * 60
            pair["user"] = _user_to_dict(user)

        return {"status": "paired"}
    finally:
        session.close()


# ── Existing endpoints below ─────────────────────────────────────────────────


class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str
    garmin_email: str | None = None
    garmin_password: str | None = None


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict[str, Any]


class SocialLoginRequest(BaseModel):
    email: str
    full_name: str | None = None
    provider: str
    token: str = ""


class ConnectGarminRequest(BaseModel):
    garmin_email: str
    garmin_password: str


class UpdateProfileRequest(BaseModel):
    goal: str | None = None
    activities: str | None = None
    fitness_level: str | None = None
    equipment: str | None = None
    onboarding_completed: bool | None = None


def create_access_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.app_secret_key, algorithm="HS256")


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.app_secret_key, algorithms=["HS256"])
        user_id = int(payload.get("sub", 0))
    except (JWTError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    session = get_session()
    try:
        user = session.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        return user
    finally:
        session.close()


def _user_to_dict(user: User) -> dict[str, Any]:
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "garmin_connected": user.garmin_connected,
        "language": user.language,
        "created_at": user.created_at.isoformat(),
        "last_sync": user.last_sync.isoformat() + "Z" if user.last_sync else None,
        "goal": user.goal,
        "activities": user.activities,
        "fitness_level": user.fitness_level,
        "equipment": user.equipment,
        "onboarding_completed": user.onboarding_completed,
    }


@router.post("/register", response_model=TokenResponse)
@limiter.limit("15/minute")
def register(req: RegisterRequest, request: Request) -> dict[str, Any]:
    session = get_session()
    try:
        existing = session.query(User).filter(User.email == req.email).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")

        encrypted_garmin_email = encrypt(req.garmin_email) if req.garmin_email else None
        encrypted_garmin_password = encrypt(req.garmin_password) if req.garmin_password else None

        user = User(
            email=req.email,
            hashed_password=_hash_password(req.password),
            full_name=req.full_name,
            garmin_email=encrypted_garmin_email,
            garmin_password=encrypted_garmin_password,
        )

        garmin_client = None
        if req.garmin_email and req.garmin_password:
            try:
                garmin_client = GarminClient(req.garmin_email, req.garmin_password)
                garmin_client.login()
                user.garmin_connected = True
            except Exception:
                user.garmin_connected = False

        session.add(user)
        session.commit()
        session.refresh(user)

        if user.garmin_connected and garmin_client:
            try:
                sync_service = DataSyncService(garmin_client)
                sync_service.sync_user(user.id, sync_days=14, max_activities=50)
                user.last_sync = datetime.now(timezone.utc)
                session.commit()
                run_backfill(user.id)
            except Exception:
                pass

        token = create_access_token(user.id)
        return {"access_token": token, "token_type": "bearer", "user": _user_to_dict(user)}
    finally:
        session.close()


@router.post("/login", response_model=TokenResponse)
@limiter.limit("30/minute")
def login(req: LoginRequest, request: Request) -> dict[str, Any]:
    session = get_session()
    try:
        user = session.query(User).filter(User.email == req.email).first()
        if not user or not _verify_password(req.password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Invalid email or password")

        token = create_access_token(user.id)
        return {"access_token": token, "token_type": "bearer", "user": _user_to_dict(user)}
    finally:
        session.close()



def _verify_supabase_token(access_token: str) -> dict:
    """Verify a Supabase access token via GoTrue API."""
    if not settings.supabase_url or not settings.supabase_anon_key:
        raise HTTPException(status_code=500, detail="Supabase not configured")

    try:
        resp = httpx.get(
            f"{settings.supabase_url}/auth/v1/user",
            headers={
                "Authorization": f"Bearer {access_token}",
                "apikey": settings.supabase_anon_key,
            },
            timeout=10,
        )
        if resp.status_code != 200:
            logger.warning("GoTrue /auth/v1/user returned %s: %s", resp.status_code, resp.text[:200])
            raise HTTPException(status_code=401, detail="Invalid token")
        return resp.json()
    except httpx.RequestError as exc:
        logger.error("GoTrue request failed: %s", exc)
        raise HTTPException(status_code=502, detail="Cannot verify token")


@router.post("/social-login", response_model=TokenResponse)
@limiter.limit("30/minute")
def social_login(req: SocialLoginRequest, request: Request) -> dict[str, Any]:
    if req.token:
        verified = _verify_supabase_token(req.token)
        verified_email = verified.get("email", "")
        if not verified_email:
            raise HTTPException(status_code=401, detail="Token missing email claim")
        req.email = verified_email

    session = get_session()
    try:
        user = session.query(User).filter(User.email == req.email).first()
        if not user:
            user = User(
                email=req.email,
                full_name=req.full_name or req.email.split("@")[0],
                hashed_password="",
            )
            session.add(user)
            session.commit()
            session.refresh(user)
        elif req.full_name and (not user.full_name or user.full_name == user.email.split("@")[0]):
            user.full_name = req.full_name
            session.commit()
            session.refresh(user)

        token = create_access_token(user.id)
        return {"access_token": token, "token_type": "bearer", "user": _user_to_dict(user)}
    finally:
        session.close()


@router.get("/me")
def get_me(user: User = Depends(get_current_user)) -> dict[str, Any]:
    return _user_to_dict(user)


@router.post("/connect-garmin")
@limiter.limit("5/minute")
def connect_garmin(
    req: ConnectGarminRequest,
    user: User = Depends(get_current_user),
    request: Request = None,
) -> dict[str, Any]:
    try:
        client = GarminClient(req.garmin_email, req.garmin_password)
        client.login()
    except Exception as e:
        logger.warning("Garmin login failed for user %s: %s", user.id, e)
        raise HTTPException(status_code=400, detail="Garmin login failed. Check your credentials.")

    session = get_session()
    try:
        db_user = session.query(User).filter(User.id == user.id).first()
        db_user.garmin_email = encrypt(req.garmin_email)
        db_user.garmin_password = encrypt(req.garmin_password)
        db_user.garmin_connected = True
        session.commit()

        sync_service = DataSyncService(client)
        try:
            sync_service.sync_user(db_user.id, sync_days=14, max_activities=50)
            db_user.last_sync = datetime.now(timezone.utc)
            session.commit()
        except Exception as e:
            logger.error("Initial sync failed for user %s: %s", db_user.id, e)
            session.rollback()

        run_backfill(db_user.id)

        session.refresh(db_user)
        return _user_to_dict(db_user)
    finally:
        session.close()


class RegisterDeviceRequest(BaseModel):
    token: str
    platform: str = "android"


class UnregisterDeviceRequest(BaseModel):
    token: str


@router.post("/register-device")
def register_device(
    req: RegisterDeviceRequest,
    user: User = Depends(get_current_user),
) -> dict[str, str]:
    session = get_session()
    try:
        existing = session.query(DeviceToken).filter(
            DeviceToken.token == req.token,
        ).first()
        if existing:
            existing.platform = req.platform
        else:
            dt = DeviceToken(user_id=user.id, token=req.token, platform=req.platform)
            session.add(dt)
        session.commit()
        return {"status": "registered"}
    finally:
        session.close()


@router.post("/unregister-device")
def unregister_device(
    req: UnregisterDeviceRequest,
    user: User = Depends(get_current_user),
) -> dict[str, str]:
    session = get_session()
    try:
        session.query(DeviceToken).filter(
            DeviceToken.token == req.token,
            DeviceToken.user_id == user.id,
        ).delete()
        session.commit()
        return {"status": "unregistered"}
    finally:
        session.close()


@router.patch("/profile")
def update_profile(
    req: UpdateProfileRequest,
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    session = get_session()
    try:
        db_user = session.query(User).filter(User.id == user.id).first()
        if req.goal is not None:
            db_user.goal = req.goal
        if req.activities is not None:
            db_user.activities = req.activities
        if req.fitness_level is not None:
            db_user.fitness_level = req.fitness_level
        if req.equipment is not None:
            db_user.equipment = req.equipment
        if req.onboarding_completed is not None:
            db_user.onboarding_completed = req.onboarding_completed
        session.commit()
        session.refresh(db_user)
        return _user_to_dict(db_user)
    finally:
        session.close()


# ──────────────────────────────────────────────────────────────────────────────
# Garmin Connect IQ Watch Auth Endpoints
# ──────────────────────────────────────────────────────────────────────────────

CONNECTIQ_REDIRECT_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Vitality AI Coach - Completing sign in...</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f5f5;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            padding: 20px;
        }}
        .card {{
            background: white;
            border-radius: 16px;
            padding: 32px;
            width: 100%;
            max-width: 360px;
            box-shadow: 0 4px 24px rgba(0,0,0,0.08);
            text-align: center;
        }}
        .logo-icon {{
            width: 48px;
            height: 48px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 12px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 24px;
            margin-bottom: 12px;
        }}
        h1 {{ font-size: 20px; color: #333; margin-bottom: 8px; }}
        .spinner {{
            width: 40px;
            height: 40px;
            border: 3px solid #ddd;
            border-top-color: #667eea;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
            margin: 24px auto;
        }}
        @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
        .error {{ color: #e53e3e; font-size: 14px; margin-top: 16px; }}
    </style>
</head>
<body>
    <div class="card">
        <div class="logo-icon">V</div>
        <h1>Vitality AI Coach</h1>
        {body}
    </div>
    {script}
</body>
</html>
"""

WATCH_LOGIN_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Vitality AI Coach - Log In</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: #ffffff;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            min-height: 100dvh;
            padding: 20px;
            -webkit-font-smoothing: antialiased;
        }
        .card {
            background: #ffffff;
            border-radius: 24px;
            padding: 32px;
            width: 100%;
            max-width: 448px;
            box-shadow: 0 4px 24px rgba(16,55,132,0.03), 0 1px 3px rgba(16,55,132,0.02);
            border: 1px solid rgba(200,197,203,0.2);
        }
        .logo {
            text-align: center;
            margin-bottom: 32px;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }
        .logo-icon {
            width: 36px;
            height: 36px;
            background: #070709;
            border-radius: 50%;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 14px;
            font-weight: 700;
        }
        .logo-text {
            font-size: 15px;
            font-weight: 600;
            color: #070709;
        }
        .form-group {
            margin-bottom: 20px;
        }
        .form-group label {
            display: block;
            font-size: 12px;
            color: #60606c;
            margin-bottom: 6px;
            font-weight: 500;
            margin-left: 4px;
        }
        input {
            width: 100%;
            height: 56px;
            padding: 0 16px;
            background: #ffffff;
            border: 1px solid rgba(200,197,203,0.5);
            border-radius: 12px;
            font-family: 'Inter', sans-serif;
            font-size: 16px;
            color: #070709;
            transition: border-color 0.2s, box-shadow 0.2s;
        }
        input::placeholder { color: #8b8b8b; }
        input:focus {
            outline: none;
            border-color: #2597d0;
            box-shadow: 0 0 0 1px #2597d0;
        }
        .btn-primary {
            width: 100%;
            height: 56px;
            background: #070709;
            color: #ffffff;
            border: none;
            border-radius: 9999px;
            font-family: 'Inter', sans-serif;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            margin-top: 8px;
            transition: opacity 0.2s, transform 0.2s;
            box-shadow: 0 4px 24px rgba(16,55,132,0.03), 0 1px 3px rgba(16,55,132,0.02);
        }
        .btn-primary:hover { opacity: 0.9; }
        .btn-primary:active { transform: scale(0.98); }
        .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
        .error {
            color: #ba1a1a;
            font-size: 13px;
            margin-top: 8px;
            text-align: center;
            display: none;
        }
        .error.show { display: block; }
        .divider {
            display: flex;
            align-items: center;
            gap: 16px;
            margin: 24px 0;
        }
        .divider::before, .divider::after {
            content: '';
            flex: 1;
            height: 1px;
            background: rgba(200,197,203,0.4);
        }
        .divider span {
            font-size: 11px;
            color: #8b8b8b;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .google-btn {
            width: 100%;
            height: 56px;
            background: #ffffff;
            color: #070709;
            border: 1px solid rgba(200,197,203,0.4);
            border-radius: 9999px;
            font-family: 'Inter', sans-serif;
            font-size: 15px;
            font-weight: 500;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            transition: background 0.2s, transform 0.2s;
        }
        .google-btn:hover { background: #f2f2f2; }
        .google-btn:active { transform: scale(0.98); }
        .google-btn svg { width: 20px; height: 20px; }
        .footer {
            text-align: center;
            margin-top: 24px;
            font-size: 11px;
            color: #8b8b8b;
            line-height: 1.5;
        }
        @media (max-width: 480px) {
            .card { padding: 24px; border-radius: 20px; }
        }
    </style>
</head>
<body>
    <div class="card">
        <div class="logo">
            <div class="logo-icon">V</div>
            <span class="logo-text">Vitality AI Coach</span>
        </div>
        <form id="loginForm" method="POST" action="/api/v1/auth/watch-login-redirect">
            <div class="form-group">
                <label for="email">Email Address</label>
                <input type="email" id="email" name="email" required placeholder="name@example.com" autocomplete="email">
            </div>
            <div class="form-group">
                <label for="password">Password</label>
                <input type="password" id="password" name="password" required placeholder="\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022" autocomplete="current-password">
            </div>
            <div id="error" class="error"></div>
            <button type="submit" class="btn-primary" id="submitBtn">Sign In</button>
        </form>
        <div class="divider"><span>or</span></div>
        <button type="button" class="google-btn" onclick="handleGoogleLogin()">
            <svg viewBox="0 0 24 24" width="20" height="20">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"/>
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
            </svg>
            Continue with Google
        </button>
        <p class="footer">Your Garmin watch will be connected automatically</p>
    </div>
    <script>
        function handleGoogleLogin() {
            var supabaseUrl = '__SUPABASE_URL__';
            var callbackUrl = window.location.origin + '/api/v1/auth/watch-google-callback';
            window.location.href = supabaseUrl + '/auth/v1/authorize?provider=google&redirect_to=' + encodeURIComponent(callbackUrl);
        }
    </script>
</body>
</html>
"""


class WatchTokenRequest(BaseModel):
    email: str = ""
    password: str = ""
    token: str = ""


@router.post("/watch-login-redirect")
@limiter.limit("30/minute")
def watch_login_redirect(email: str = Form(...), password: str = Form(...), request: Request = None) -> Response:
    """Email/password login with server-side 302 redirect to connectiq://.
    Uses form POST so the redirect is a proper HTTP 302, not a JavaScript redirect.
    Garmin companion app intercepts HTTP 302 redirects to connectiq://.
    """
    session = get_session()
    try:
        user = session.query(User).filter(User.email == email).first()
        if not user or not _verify_password(password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Invalid email or password")

        token = create_access_token(user.id)
        user_name = user.full_name or user.email

        from urllib.parse import quote
        redirect_url = f"connectiq://oauth?access_token={quote(token)}&token_type=bearer&user_name={quote(user_name)}"
        return RedirectResponse(url=redirect_url, status_code=302)
    finally:
        session.close()


@router.get("/authorize")
def watch_authorize() -> HTMLResponse:
    """Serve login page for Garmin Connect IQ watch."""
    supabase_url = settings.supabase_url or ""
    html = WATCH_LOGIN_HTML.replace("__SUPABASE_URL__", supabase_url)
    return HTMLResponse(content=html)


@router.post("/token")
@limiter.limit("30/minute")
def watch_token(req: WatchTokenRequest, request: Request) -> dict[str, Any]:
    """Exchange email/password or Supabase token for JWT token (for watch app)."""
    session = get_session()
    try:
        if req.token:
            verified = _verify_supabase_token(req.token)
            email = verified.get("email", "")
            if not email:
                raise HTTPException(status_code=401, detail="Token missing email claim")
            user = session.query(User).filter(User.email == email).first()
            if not user:
                user = User(
                    email=email,
                    full_name=verified.get("full_name") or email.split("@")[0],
                    hashed_password="",
                )
                session.add(user)
                session.commit()
                session.refresh(user)
        else:
            if not req.email or not req.password:
                raise HTTPException(status_code=400, detail="Email and password are required")
            user = session.query(User).filter(User.email == req.email).first()
            if not user or not _verify_password(req.password, user.hashed_password):
                raise HTTPException(status_code=401, detail="Invalid email or password")

        token = create_access_token(user.id)
        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user": _user_to_dict(user),
        }
    finally:
        session.close()


@router.get("/token-redirect")
@limiter.limit("30/minute")
def token_redirect(supabase_token: str, request: Request) -> RedirectResponse:
    """Exchange a Supabase access token for a JWT and redirect to connectiq://.

    This is a GET endpoint that performs server-side token exchange and returns
    a 302 redirect. Garmin Connect companion app intercepts HTTP 302 redirects
    (not JavaScript-based redirects), so this is the reliable way to pass the
    token back to the watch app.
    """
    try:
        verified = _verify_supabase_token(supabase_token)
        email = verified.get("email", "")
        if not email:
            raise HTTPException(status_code=401, detail="Token missing email claim")

        session = get_session()
        try:
            user = session.query(User).filter(User.email == email).first()
            if not user:
                user = User(
                    email=email,
                    full_name=verified.get("full_name") or email.split("@")[0],
                    hashed_password="",
                )
                session.add(user)
                session.commit()
                session.refresh(user)
        finally:
            session.close()

        token = create_access_token(user.id)
        user_name = user.full_name or user.email
        expires_in = ACCESS_TOKEN_EXPIRE_MINUTES * 60
        redirect_url = f"connectiq://oauth?access_token={urllib.parse.quote(token)}&token_type=bearer&expires_in={expires_in}&user_name={urllib.parse.quote(user_name)}"
        return RedirectResponse(url=redirect_url, status_code=302)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("token-redirect failed: %s", e)
        raise HTTPException(status_code=500, detail="Token exchange failed")


@router.get("/watch-google-callback")
def watch_google_callback(code: str | None = None) -> HTMLResponse:
    """Client-side page that extracts Supabase session from URL fragment,
    exchanges it for a JWT, and redirects to connectiq:// via meta refresh.

    The fragment is client-side only, so JS reads it and calls /token to get
    a JWT. Then it renders a meta refresh tag to redirect to connectiq://.
    Meta refresh is a declarative page redirect (not JavaScript navigation),
    which the Garmin companion app intercepts.
    """
    html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Connecting...</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #ffffff;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            margin: 0;
        }
        .card {
            text-align: center;
            padding: 32px;
        }
        .spinner {
            width: 40px; height: 40px;
            border: 3px solid #ddd;
            border-top-color: #667eea;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
            margin: 0 auto 16px;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        p { color: #666; font-size: 14px; }
        .error { color: #e53e3e; }
    </style>
</head>
<body>
    <div class="card">
        <div class="spinner"></div>
        <p id="status">Connecting to your watch...</p>
    </div>
    <script>
        (function() {
            var statusEl = document.getElementById('status');
            var hash = window.location.hash;

            if (!hash || hash.length < 2) {
                statusEl.innerHTML = '<span class="error">No session data received. Please try again.</span>';
                return;
            }

            var params = new URLSearchParams(hash.substring(1));
            var accessToken = params.get('access_token');

            if (!accessToken) {
                statusEl.innerHTML = '<span class="error">Access token not found. Please try again.</span>';
                return;
            }

            statusEl.textContent = 'Signing you in...';

            // Server-side token exchange + 302 redirect to connectiq://oauth
            // The Garmin Companion App intercepts HTTP 302 redirects to resultUrl.
            var redirectUrl = '/api/v1/auth/token-redirect?supabase_token=' + encodeURIComponent(accessToken);
            window.location.replace(redirectUrl);
        })();
    </script>
</body>
</html>"""
    return HTMLResponse(content=html)


@router.get("/user")
def watch_user(user: User = Depends(get_current_user)) -> dict[str, Any]:
    """Get user info (for watch app)."""
    return _user_to_dict(user)
