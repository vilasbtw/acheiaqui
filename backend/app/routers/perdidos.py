"""
Itens perdidos, área pública (Etapa 6, D26/D27).

Quem perdeu registra sem conta e recebe um segredo, que o site coloca no link depois do `#`
(perdido.html#t=...). O que vem depois do `#` nunca sai do navegador: não aparece nos logs do servidor
nem no cabeçalho Referer. Por isso o acompanhamento é POST com o segredo no corpo, e não GET com ?token=.
O banco guarda só o SHA-256 do segredo.
"""
import hashlib
import secrets
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import obter_sessao
from app.models.campus import Campus
from app.models.categoria import Categoria
from app.models.perdido import Perdido
from app.schemas.perdido import PerdidoAcompanhamento, PerdidoCriado, PerdidoCriar, PerdidoToken
from app.services.ia_categoria import sugerir_categoria
from app.services.limites import exigir_limite_diario_perdidos, exigir_limite_por_ip

router = APIRouter(prefix="/perdidos", tags=["perdidos"])


def hash_do_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _categoria_sugerida(descricao: str, categorias: list[Categoria]) -> Optional[int]:
    """Igual ao registro de achados: qualquer falha vira None (D2)."""
    try:
        nome = sugerir_categoria(descricao, [c.nome for c in categorias])
    except Exception:
        return None
    return next((c.id for c in categorias if nome and c.nome.lower() == nome.strip().lower()), None)


def _pelo_token(sessao: Session, token: str) -> Perdido:
    perdido = sessao.query(Perdido).filter(Perdido.token_hash == hash_do_token(token)).one_or_none()
    if perdido is None:
        raise HTTPException(status_code=404, detail="Link inválido. Confira se copiou o endereço inteiro.")
    return perdido


def _acompanhamento(perdido: Perdido) -> PerdidoAcompanhamento:
    return PerdidoAcompanhamento(
        descricao=perdido.descricao,
        perdido_em=perdido.perdido_em,
        status=perdido.status,
        campus=perdido.campus,
        criado_em=perdido.criado_em,
        item_encontrado=perdido.item.descricao if perdido.status in ("encontrado", "entregue") and perdido.item else None,
    )


@router.post("", response_model=PerdidoCriado, status_code=201, dependencies=[Depends(exigir_limite_por_ip)])
def registrar_perdido(dados: PerdidoCriar, sessao: Session = Depends(obter_sessao)):
    """D26: qualquer pessoa registra um item perdido, sem conta. Limites contra abuso como no POST /itens."""
    campus = sessao.query(Campus).filter(Campus.sigla == dados.campus, Campus.ativo.is_(True)).one_or_none()
    if campus is None:
        raise HTTPException(status_code=400, detail="Campus inexistente ou inativo.")
    exigir_limite_diario_perdidos(sessao)  # antes da IA

    token = secrets.token_urlsafe(32)
    perdido = Perdido(
        campus_id=campus.id,
        descricao=dados.descricao,
        local_perdido=dados.local_perdido,
        perdido_em=dados.perdido_em,
        contato=dados.contato,
        aviso_consentido=dados.aviso_consentido,
        email_aviso=dados.email_aviso,
        categoria_id=_categoria_sugerida(dados.descricao, sessao.query(Categoria).all()),
        token_hash=hash_do_token(token),
    )
    sessao.add(perdido)
    sessao.commit()
    return PerdidoCriado(token=token, status=perdido.status)


@router.post("/acompanhar", response_model=PerdidoAcompanhamento)
def acompanhar(dados: PerdidoToken, sessao: Session = Depends(obter_sessao)):
    """D27: quem perdeu vê só o status. O achado só aparece depois que a CAE confirmou."""
    return _acompanhamento(_pelo_token(sessao, dados.token))


@router.post("/encerrar", response_model=PerdidoAcompanhamento)
def encerrar(dados: PerdidoToken, sessao: Session = Depends(obter_sessao)):
    """Quem perdeu avisa que achou por conta própria (ou desistiu): sai da lista da CAE."""
    perdido = _pelo_token(sessao, dados.token)
    if perdido.status != "procurando":
        raise HTTPException(status_code=409, detail="Este pedido não está mais em busca.")
    perdido.status = "encerrado"
    sessao.commit()
    sessao.refresh(perdido)
    return _acompanhamento(perdido)
