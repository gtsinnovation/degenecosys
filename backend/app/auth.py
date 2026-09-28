import base64
import datetime as dt
import hashlib
import hmac
import json
import os
import secrets
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from nacl.exceptions import BadSignatureError
from nacl.signing import VerifyKey
from prisma import Prisma
from app.database import db
from pydantic import BaseModel, Field
from solders.pubkey import Pubkey

router = APIRouter(prefix="/api/auth", tags=["Wallet authentication"])
bearer = HTTPBearer(auto_error=False)
TOKEN_TTL_SECONDS = 60 * 60
CHALLENGE_TTL_SECONDS = 5 * 60


async def get_db() -> Prisma:
    if not db.is_connected():
        await db.connect()
    return db


class ChallengeRequest(BaseModel):
    wallet_address: str = Field(min_length=32, max_length=44)


class VerifyRequest(BaseModel):
    wallet_address: str = Field(min_length=32, max_length=44)
    nonce: str = Field(min_length=32, max_length=128)
    signature: str = Field(min_length=80, max_length=128)


def _jwt_secret() -> bytes:
    secret = os.getenv("AUTH_JWT_SECRET", "")
    if len(secret.encode("utf-8")) < 32:
        raise HTTPException(status_code=503, detail="Wallet authentication is not configured.")
    return secret.encode("utf-8")


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _issue_token(wallet_address: str) -> str:
    now = int(dt.datetime.now(dt.timezone.utc).timestamp())
    header = _b64url(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    payload = _b64url(json.dumps({
        "sub": wallet_address,
        "iat": now,
        "exp": now + TOKEN_TTL_SECONDS,
        "iss": "degenecosys",
    }, separators=(",", ":")).encode())
    message = f"{header}.{payload}".encode("ascii")
    signature = hmac.new(_jwt_secret(), message, hashlib.sha256).digest()
    return f"{header}.{payload}.{_b64url(signature)}"


def _decode_token(token: str) -> dict[str, Any]:
    try:
        header, payload, signature = token.split(".")
        expected = hmac.new(
            _jwt_secret(), f"{header}.{payload}".encode("ascii"), hashlib.sha256
        ).digest()
        supplied = base64.urlsafe_b64decode(signature + "=" * (-len(signature) % 4))
        if not hmac.compare_digest(expected, supplied):
            raise ValueError("invalid signature")
        claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        if claims.get("iss") != "degenecosys" or not isinstance(claims.get("sub"), str):
            raise ValueError("invalid claims")
        if int(claims.get("exp", 0)) <= int(dt.datetime.now(dt.timezone.utc).timestamp()):
            raise ValueError("expired")
        return claims
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired bearer token.") from exc


async def get_current_wallet(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> str:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Wallet authentication required.")
    return _decode_token(credentials.credentials)["sub"]


async def require_admin_wallet(wallet_address: str = Depends(get_current_wallet)) -> str:
    admins = {item.strip() for item in os.getenv("ADMIN_WALLETS", "").split(",") if item.strip()}
    if not admins or wallet_address not in admins:
        raise HTTPException(status_code=403, detail="Administrator wallet required.")
    return wallet_address


@router.post("/challenge")
async def create_wallet_challenge(
    payload: ChallengeRequest, client: Prisma = Depends(get_db)
):
    try:
        Pubkey.from_string(payload.wallet_address)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid Solana wallet address.") from exc

    now = dt.datetime.now(dt.timezone.utc)
    nonce = secrets.token_urlsafe(32)
    expires_at = now + dt.timedelta(seconds=CHALLENGE_TTL_SECONDS)
    message = (
        "Degen Ecosystem wallet sign-in\n"
        f"Wallet: {payload.wallet_address}\n"
        f"Nonce: {nonce}\n"
        f"Issued At: {now.isoformat()}\n"
        f"Expiration Time: {expires_at.isoformat()}"
    )
    await client.walletchallenge.create(data={
        "walletAddress": payload.wallet_address,
        "nonce": nonce,
        "message": message,
        "expiresAt": expires_at,
    })
    return {"nonce": nonce, "message": message, "expires_at": expires_at}


@router.post("/verify")
async def verify_wallet_challenge(
    payload: VerifyRequest, client: Prisma = Depends(get_db)
):
    challenge = await client.walletchallenge.find_unique(where={"nonce": payload.nonce})
    now = dt.datetime.now(dt.timezone.utc)
    if (
        not challenge
        or challenge.walletAddress != payload.wallet_address
        or challenge.usedAt is not None
        or challenge.expiresAt <= now
    ):
        raise HTTPException(status_code=401, detail="Wallet challenge is invalid or expired.")

    try:
        public_key = bytes(Pubkey.from_string(payload.wallet_address))
        signature = base64.b64decode(payload.signature, validate=True)
        VerifyKey(public_key).verify(challenge.message.encode("utf-8"), signature)
    except (ValueError, BadSignatureError, TypeError) as exc:
        raise HTTPException(status_code=401, detail="Wallet signature verification failed.") from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid wallet signature.") from exc

    # Atomically consume the one-time nonce so concurrent/replayed verifies cannot mint tokens.
    consumed = await client.walletchallenge.update_many(
        where={"nonce": payload.nonce, "usedAt": None, "expiresAt": {"gt": now}},
        data={"usedAt": now},
    )
    if consumed.count != 1:
        raise HTTPException(status_code=401, detail="Wallet challenge was already used.")

    return {"access_token": _issue_token(payload.wallet_address), "token_type": "bearer",
            "expires_in": TOKEN_TTL_SECONDS}
