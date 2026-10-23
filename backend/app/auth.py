"""
Autenticação da CAE via Supabase Auth (D6) e vínculo com o campus (D21).

O frontend faz o login com o supabase-js e envia o token no header
`Authorization: Bearer <token>`.
- `exigir_autenticacao` pergunta ao Supabase se o token é válido e devolve o id do usuário.
- `exigir_cae` exige, além do login, uma linha em `cae_membros`: é ela que diz de qual
  campus a pessoa é. Sem login = 401; logado mas sem campus = 403.
"""
import os
import uuid

import httpx
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session, joinedload

from app.database import obter_sessao
from app.models.cae_membro import CaeMembro

_esquema = HTTPBearer(auto_error=False)


def _nao_autenticado(detalhe: str) -> HTTPException:
    return HTTPException(status_code=401, detail=detalhe, headers={"WWW-Authenticate": "Bearer"})


def exigir_autenticacao(
    credenciais: HTTPAuthorizationCredentials | None = Depends(_esquema),
) -> uuid.UUID:
    if credenciais is None or not credenciais.credentials:
        raise _nao_autenticado("Autenticação necessária.")

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
        raise HTTPException(status_code=503, detail="Serviço de autenticação indisponível.") from None

    if resposta.status_code != 200:
        raise _nao_autenticado("Token inválido ou expirado.")
    try:
        return uuid.UUID(str(resposta.json()["id"]))
    except (ValueError, KeyError, TypeError):
        raise _nao_autenticado("Token inválido ou expirado.") from None


def exigir_cae(
    usuario_id: uuid.UUID = Depends(exigir_autenticacao),
    sessao: Session = Depends(obter_sessao),
) -> CaeMembro:
    membro = (
        sessao.query(CaeMembro)
        .options(joinedload(CaeMembro.campus))
        .filter(CaeMembro.user_id == usuario_id)
        .one_or_none()
    )
    if membro is None:
        raise HTTPException(
            status_code=403,
            detail="Sua conta não está vinculada à CAE de nenhum campus. Fale com quem administra o sistema.",
        )
    return membro
