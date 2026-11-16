import base64
import hashlib
import hmac
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from app.core.config import settings
from app.core.exceptions import ExternalServiceError, UnauthorizedError

logger = logging.getLogger(__name__)

try:
    import jwt as _pyjwt  # type: ignore[import-not-found]
except ImportError:
    _pyjwt = None


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def create_access_token(
    user_id: str,
    email: str,
    name: str | None = None,
    picture_url: str | None = None,
) -> tuple[str, int]:
    """
    Gera um JWT assinado (HS256) contendo a identidade do usuário.
    Retorna (token, expires_in_seconds).
    """
    now = datetime.now(timezone.utc)
    expires_delta = timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    expires_in = int(expires_delta.total_seconds())
    exp_ts = int((now + expires_delta).timestamp())
    iat_ts = int(now.timestamp())

    payload: dict[str, Any] = {
        "sub": user_id,
        "email": email,
        "name": name,
        "picture_url": picture_url,
        "iat": iat_ts,
        "exp": exp_ts,
    }

    if _pyjwt is not None:
        token = _pyjwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        if isinstance(token, bytes):
            token = token.decode("utf-8")
        return token, expires_in

    if settings.JWT_ALGORITHM != "HS256":
        raise UnauthorizedError("Algoritmo JWT não suportado sem PyJWT instalado.")

    header_b64 = _b64url_encode(
        json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode("utf-8")
    )
    payload_b64 = _b64url_encode(
        json.dumps(payload, separators=(",", ":")).encode("utf-8")
    )
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    signature = hmac.new(
        settings.JWT_SECRET_KEY.encode("utf-8"),
        signing_input,
        hashlib.sha256,
    ).digest()
    return f"{header_b64}.{payload_b64}.{_b64url_encode(signature)}", expires_in


def decode_access_token(token: str) -> dict[str, Any]:
    """Decodifica e valida assinatura e expiração de um JWT da aplicação."""
    if not token or not token.strip():
        raise UnauthorizedError("Token de autenticação ausente.")

    if _pyjwt is not None:
        try:
            payload = _pyjwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
            )
            return dict(payload)
        except Exception as exc:
            raise UnauthorizedError(f"Token inválido ou expirado: {exc}") from exc

    parts = token.split(".")
    if len(parts) != 3:
        raise UnauthorizedError("Formato de token JWT inválido.")

    header_b64, payload_b64, sig_b64 = parts
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    expected_sig = hmac.new(
        settings.JWT_SECRET_KEY.encode("utf-8"),
        signing_input,
        hashlib.sha256,
    ).digest()

    try:
        actual_sig = _b64url_decode(sig_b64)
        header = json.loads(_b64url_decode(header_b64))
        payload = json.loads(_b64url_decode(payload_b64))
    except Exception as exc:
        raise UnauthorizedError("Token JWT malformado.") from exc

    if header.get("alg") != "HS256":
        raise UnauthorizedError("Algoritmo JWT não suportado.")
    if not hmac.compare_digest(actual_sig, expected_sig):
        raise UnauthorizedError("Assinatura do token JWT inválida.")

    exp = payload.get("exp")
    if exp is None or datetime.now(timezone.utc).timestamp() >= float(exp):
        raise UnauthorizedError("Token JWT expirado.")

    return payload


def _verify_google_id_token(token: str) -> dict[str, Any]:
    """Valida um Google ID Token usando google-auth ou endpoint tokeninfo."""
    try:
        from google.auth.transport import requests as google_requests  # type: ignore[import-not-found]
        from google.oauth2 import id_token as google_id_token  # type: ignore[import-not-found]

        audience = settings.GOOGLE_CLIENT_ID or None
        info = google_id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            audience=audience,
        )
        iss = info.get("iss")
        if iss not in ("accounts.google.com", "https://accounts.google.com"):
            raise UnauthorizedError("Emissor do token Google inválido.")
        return dict(info)
    except ImportError:
        pass
    except UnauthorizedError:
        raise
    except Exception as exc:
        raise UnauthorizedError(f"Google ID Token inválido: {exc}") from exc

    try:
        resp = httpx.get(
            "https://oauth2.googleapis.com/tokeninfo",
            params={"id_token": token},
            timeout=10.0,
        )
    except httpx.HTTPError as exc:
        raise ExternalServiceError(f"Falha ao contatar Google OAuth: {exc}") from exc

    if resp.status_code != 200:
        raise UnauthorizedError("Google ID Token inválido ou expirado.")

    data = resp.json()
    if settings.GOOGLE_CLIENT_ID and data.get("aud") != settings.GOOGLE_CLIENT_ID:
        raise UnauthorizedError("Google token não pertence ao GOOGLE_CLIENT_ID configurado.")

    return data


def _verify_google_access_token(token: str) -> dict[str, Any]:
    """Valida um Google OAuth2 Access Token via endpoint userinfo."""
    try:
        resp = httpx.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10.0,
        )
    except httpx.HTTPError as exc:
        raise ExternalServiceError(f"Falha ao contatar Google OAuth userinfo: {exc}") from exc

    if resp.status_code != 200:
        raise UnauthorizedError("Google access token inválido ou expirado.")

    return resp.json()


def verify_google_token(token: str) -> dict[str, str | None]:
    """
    Valida um token Google OAuth 2.0 (ID Token JWT ou Access Token) e retorna
    os campos normalizados: sub, email, name e picture.
    """
    clean_token = (token or "").strip()
    if not clean_token:
        raise UnauthorizedError("Token do Google não informado.")

    if len(clean_token.split(".")) == 3:
        data = _verify_google_id_token(clean_token)
    else:
        data = _verify_google_access_token(clean_token)

    email_verified = data.get("email_verified")
    if email_verified in (False, "false", "False"):
        raise UnauthorizedError("E-mail da conta Google ainda não foi verificado.")

    sub = data.get("sub")
    email = data.get("email")
    if not sub or not email:
        raise UnauthorizedError("Token Google não contém identificador (sub) e e-mail válidos.")

    return {
        "sub": str(sub),
        "email": str(email),
        "name": data.get("name"),
        "picture": data.get("picture"),
    }
