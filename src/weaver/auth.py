from fastapi import APIRouter, FastAPI, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from fastapi.security import OAuth2PasswordBearer
from typing import Optional
import time
import secrets
from jose import jwt, JWTError

from argon2 import PasswordHasher, exceptions as argon2_exceptions

from src.weaver.config import settings
from src.weaver.models.user import User
from src.weaver import rate_limiter

router = APIRouter(prefix="/auth", tags=["auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


class UserCreate(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


_ph = PasswordHasher()


def _hash_password(password: str) -> str:
    return _ph.hash(password)


def _verify_password(password: str, hashed: str) -> bool:
    try:
        return _ph.verify(hashed, password)
    except argon2_exceptions.VerifyMismatchError:
        return False
    except Exception:
        return False


# Simple in-memory rate limiter (sufficient for dev/demo; use Redis for prod)



def send_email(to: str, subject: str, body: str):
    # If SMTP is configured, send via SMTP; otherwise log at debug level.
    import logging
    logger = logging.getLogger("weaver.auth.email")
    from src.weaver.config import settings

    if settings.SMTP_HOST:
        try:
            import smtplib
            from email.message import EmailMessage

            msg = EmailMessage()
            msg["From"] = settings.SMTP_FROM or "no-reply@weaver.local"
            msg["To"] = to
            msg["Subject"] = subject
            msg.set_content(body)

            # Basic SMTP with optional TLS
            if settings.SMTP_USE_TLS:
                server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10)
                server.starttls()
            else:
                server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10)

            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)

            server.send_message(msg)
            server.quit()
            logger.info("Sent email to %s subject=%s", to, subject)
        except Exception:
            logger.exception("Failed to send email to %s", to)
    else:
        # No SMTP configured: do not print sensitive data to stdout in production.
        import logging

        logger = logging.getLogger("weaver.auth.email")
        logger.debug("Email (not sent) To=%s Subject=%s", to, subject)


@router.post("/register", response_model=dict)
async def register(payload: UserCreate):
    # rate-limit by email/IP
    from fastapi import Request
    # Request is not passed automatically; this function will rely on email key
    key = f"email:{payload.email.lower()}"
    if not await rate_limiter.allow(key, limit=10, per_seconds=60):
        raise HTTPException(status_code=429, detail="Too many requests")

    existing = await User.find_one(User.email == payload.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed = _hash_password(payload.password)
    user = User(email=payload.email, hashed_password=hashed)
    await user.insert()

    # send verification token
    exp = int(time.time()) + 3600 * 24
    token = jwt.encode({"sub": str(user.id), "action": "verify", "exp": exp}, settings.SECRET_KEY, algorithm="HS256")
    verify_url = f"/auth/verify?token={token}"
    send_email(user.email, "Verify your Weaver account", f"Verify here: {verify_url}")

    return {"id": str(user.id), "email": user.email}


@router.post("/login", response_model=Token)
async def login(form_data: UserCreate):
    # rate-limit by email/IP
    key = f"email:{form_data.email.lower()}"
    if not await rate_limiter.allow(key, limit=20, per_seconds=60):
        raise HTTPException(status_code=429, detail="Too many requests")

    user = await User.find_one(User.email == form_data.email)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid credentials")
    if not _verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    exp = int(time.time()) + settings.JWT_LIFETIME_SECONDS
    to_encode = {"sub": str(user.id), "exp": exp}
    token = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    return {"access_token": token, "token_type": "bearer"}


async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = await User.get(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


@router.get("/me")
async def whoami(current_user: User = Depends(get_current_user)):
    return {"id": str(current_user.id), "email": current_user.email}


def init_auth(app: FastAPI):
    app.include_router(router)


@router.get("/verify")
async def verify_account(token: str):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        if payload.get("action") != "verify":
            raise HTTPException(status_code=400, detail="Invalid token action")
        user_id = payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid token")

    user = await User.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_verified = True
    await user.save()
    return {"status": "verified", "id": str(user.id)}


class ResetRequest(BaseModel):
    email: EmailStr


@router.post("/request-reset")
async def request_reset(payload: ResetRequest):
    key = f"email:{payload.email.lower()}"
    if not await rate_limiter.allow(key, limit=3, per_seconds=300):
        raise HTTPException(status_code=429, detail="Too many requests")
    user = await User.find_one(User.email == payload.email)
    if not user:
        # Do not reveal whether the email exists
        return {"status": "ok"}
    exp = int(time.time()) + 3600
    token = jwt.encode({"sub": str(user.id), "action": "reset", "exp": exp}, settings.SECRET_KEY, algorithm="HS256")
    reset_url = f"/auth/reset?token={token}"
    send_email(user.email, "Weaver password reset", f"Reset here: {reset_url}")
    return {"status": "ok"}


class ResetPayload(BaseModel):
    token: str
    new_password: str


@router.post("/reset")
async def reset_password(payload: ResetPayload):
    try:
        decoded = jwt.decode(payload.token, settings.SECRET_KEY, algorithms=["HS256"])
        if decoded.get("action") != "reset":
            raise HTTPException(status_code=400, detail="Invalid token action")
        user_id = decoded.get("sub")
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid token")

    user = await User.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.hashed_password = _hash_password(payload.new_password)
    await user.save()
    return {"status": "ok"}
