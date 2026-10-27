"""
Autenticação via Supabase Auth.

O login acontece inteiro no frontend (supabase-js). O backend só recebe o
access token em `Authorization: Bearer <token>` e valida:

- Projetos com chaves de assinatura assimétricas (ES256/RS256, padrão atual do
  Supabase): validação local contra o JWKS público do projeto. Sem chamada de
  rede por request (as chaves ficam em cache).
- Projetos com o segredo HS256 legado: pergunta ao próprio Supabase Auth
  (`GET /auth/v1/user`), como recomenda a documentação, com cache curto
  para não repetir a chamada a cada mensagem.

Variáveis de ambiente:
    SUPABASE_URL       ex.: https://abcdefgh.supabase.co
    SUPABASE_ANON_KEY  chave pública (publishable/anon) — só usada no modo legado
"""
import json
import logging
import os
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = logging.getLogger(__name__)

AUDIENCE = "authenticated"
_LEEWAY_SECONDS = 30
_LEGACY_CACHE_TTL = 60  # segundos

_bearer = HTTPBearer(auto_error=False)
_jwks_client: Optional[jwt.PyJWKClient] = None
_legacy_cache: dict[str, tuple[float, "AuthUser"]] = {}
_lock = threading.Lock()


@dataclass(frozen=True)
class AuthUser:
    id: str
    email: Optional[str] = None


def _supabase_url() -> str:
    # Lido sob demanda: o main.py carrega o .env depois dos imports.
    return os.getenv("SUPABASE_URL", "").rstrip("/")


def auth_configured() -> bool:
    return bool(_supabase_url())


def _issuer() -> str:
    return f"{_supabase_url()}/auth/v1"


def _get_jwks_client() -> jwt.PyJWKClient:
    global _jwks_client
    with _lock:
        if _jwks_client is None:
            # lifespan < 20 min, conforme a recomendação do Supabase p/ rotação
            _jwks_client = jwt.PyJWKClient(
                f"{_issuer()}/.well-known/jwks.json",
                cache_jwk_set=True,
                lifespan=600,
            )
        return _jwks_client


def _unauthorized(detail: str = "Token inválido ou expirado.") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _verify_asymmetric(token: str) -> AuthUser:
    signing_key = _get_jwks_client().get_signing_key_from_jwt(token)
    claims = jwt.decode(
        token,
        signing_key.key,
        algorithms=["ES256", "RS256"],
        audience=AUDIENCE,
        issuer=_issuer(),
        leeway=_LEEWAY_SECONDS,
        options={"require": ["exp", "sub", "aud", "iss"]},
    )
    return AuthUser(id=claims["sub"], email=claims.get("email"))


def _verify_legacy(token: str) -> AuthUser:
    now = time.time()
    cached = _legacy_cache.get(token)
    if cached and cached[0] > now:
        return cached[1]

    req = urllib.request.Request(
        f"{_issuer()}/user",
        headers={"Authorization": f"Bearer {token}", "apikey": os.getenv("SUPABASE_ANON_KEY", "")},
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            raise _unauthorized()
        logger.error("Supabase Auth respondeu %s ao validar token", exc.code)
        raise HTTPException(status_code=503, detail="Serviço de autenticação indisponível.")
    except (urllib.error.URLError, TimeoutError) as exc:
        logger.error("Falha ao contatar Supabase Auth: %s", exc)
        raise HTTPException(status_code=503, detail="Serviço de autenticação indisponível.")

    user = AuthUser(id=data["id"], email=data.get("email"))
    # Nunca guardar além do exp do próprio token
    try:
        exp = jwt.decode(token, options={"verify_signature": False}).get("exp", now)
    except jwt.PyJWTError:
        exp = now
    with _lock:
        if len(_legacy_cache) > 1000:
            _legacy_cache.clear()
        _legacy_cache[token] = (min(now + _LEGACY_CACHE_TTL, exp), user)
    return user


def verify_token(token: str) -> AuthUser:
    if not auth_configured():
        raise HTTPException(status_code=501, detail="Login não configurado no servidor (SUPABASE_URL).")
    try:
        alg = jwt.get_unverified_header(token).get("alg")
    except jwt.PyJWTError:
        raise _unauthorized()

    try:
        if alg in ("ES256", "RS256"):
            return _verify_asymmetric(token)
        if alg == "HS256":
            return _verify_legacy(token)
    except jwt.PyJWTError as exc:
        logger.info("Token rejeitado: %s", exc)
        raise _unauthorized()
    raise _unauthorized()


def get_current_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> AuthUser:
    """Dependência para rotas que EXIGEM login."""
    if creds is None:
        raise _unauthorized("Faça login para acessar este recurso.")
    return verify_token(creds.credentials)


def get_optional_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> Optional[AuthUser]:
    """
    Dependência para rotas onde o login é OPCIONAL (ex.: /chat).
    Sem token -> None. Token inválido -> 401, para o frontend saber que a
    sessão expirou em vez de silenciosamente perder a personalização.
    """
    if creds is None or not auth_configured():
        return None
    return verify_token(creds.credentials)
