"""
Autenticação da CAE via Supabase Auth (D6).

O frontend faz o login com o supabase-js e envia o token no header
`Authorization: Bearer <token>`. Aqui só perguntamos ao Supabase se o token é válido.
Como o cadastro (sign-up) está desativado e as contas da CAE são criadas à mão no
painel do Supabase, qualquer usuário autenticado é considerado da CAE.
"""
import os

import httpx
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

_esquema = HTTPBearer(auto_error=False)


def exigir_autenticacao_cae(
    credenciais: HTTPAuthorizationCredentials | None = Depends(_esquema),
) -> dict:
    if credenciais is None or not credenciais.credentials:
        raise HTTPException(
            status_code=401,
            detail="Autenticação necessária.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    url = os.getenv("SUPABASE_URL", "").rstrip("/")
    chave = os.getenv("SUPABASE_ANON_KEY", "")
    if not url or not chave:
        raise HTTPException(status_code=500, detail="Autenticação não configurada no servidor.")

    try:
        resposta = httpx.get(
            f"{url}/auth/v1/user",
            headers={"apikey": chave, "Authorization": f"Bearer {credenciais.credentials}"},
            timeout=10,
        )
    except httpx.HTTPError:
        raise HTTPException(status_code=503, detail="Serviço de autenticação indisponível.")

    if resposta.status_code != 200:
        raise HTTPException(
            status_code=401,
            detail="Token inválido ou expirado.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return resposta.json()
