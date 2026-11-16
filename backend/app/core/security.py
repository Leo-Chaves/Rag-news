import base64
import hashlib
import hmac
import json
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.config import settings
from app.core.exceptions import UnauthorizedError

logger = logging.getLogger(__name__)

_PBKDF2_ALGORITHM = "pbkdf2_sha256"
_PBKDF2_ITERATIONS = 210_000

try:
    import jwt as _pyjwt  # type: ignore[import-not-found]
except ImportError:
    _pyjwt = None


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def hash_password(password: str) -> str:
    """Gera hash seguro da senha usando PBKDF2-HMAC-SHA256 com salt aleatório."""
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        _PBKDF2_ITERATIONS,
    )
    return f"{_PBKDF2_ALGORITHM}${_PBKDF2_ITERATIONS}${_b64url_encode(salt)}${_b64url_encode(digest)}"


def verify_password(plain_password: str, stored_hash: str) -> bool:
    """Verifica se a senha informada corresponde ao hash armazenado em tempo constante."""
    if not plain_password or not stored_hash:
        return False

    try:
        algorithm, iter_str, salt_b64, hash_b64 = stored_hash.split("$", 3)
        if algorithm != _PBKDF2_ALGORITHM:
            return False
        iterations = int(iter_str)
        salt = _b64url_decode(salt_b64)
        expected_digest = _b64url_decode(hash_b64)
    except (ValueError, TypeError):
        return False

    candidate_digest = hashlib.pbkdf2_hmac(
        "sha256",
        plain_password.encode("utf-8"),
        salt,
        iterations,
    )
    return hmac.compare_digest(candidate_digest, expected_digest)


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
