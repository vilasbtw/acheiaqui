from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, contains_eager, joinedload

from app.database import obter_sessao
from app.models.campus import Campus
from app.models.categoria import Categoria
from app.models.item import Item
from app.schemas.item import ItemCriar, ItemPublico
from app.services.busca import aplicar_busca
from app.services.ia_categoria import sugerir_categoria

router = APIRouter(prefix="/itens", tags=["itens"])


def _campus_ativo(sessao: Session, sigla: str) -> Optional[Campus]:
    return sessao.query(Campus).filter(Campus.sigla == sigla, Campus.ativo.is_(True)).one_or_none()


def _categoria_sugerida(descricao: str, categorias: list[Categoria]) -> Optional[int]:
    """Pede a sugestão à IA. Qualquer falha vira None: o registro nunca depende da IA (D2)."""
    try:
        nome = sugerir_categoria(descricao, [c.nome for c in categorias])
    except Exception:
        return None
    if not nome:
        return None
    for categoria in categorias:
        if categoria.nome.lower() == nome.strip().lower():
            return categoria.id
    return None


@router.post("", response_model=ItemPublico, status_code=201)
def registrar_item(dados: ItemCriar, sessao: Session = Depends(obter_sessao)):
    """RF01/RF02: qualquer pessoa registra um item encontrado, sem conta, no campus escolhido."""
    campus = _campus_ativo(sessao, dados.campus)
    if campus is None:  # antes da IA: um registro inválido não gasta a cota
        raise HTTPException(status_code=400, detail="Campus inexistente ou inativo.")

    categorias = sessao.query(Categoria).all()
    categoria_id = dados.categoria_id
    if categoria_id is not None and all(c.id != categoria_id for c in categorias):
        raise HTTPException(status_code=400, detail="Categoria inexistente.")
    if categoria_id is None:
        categoria_id = _categoria_sugerida(dados.descricao, categorias)

    item = Item(
        descricao=dados.descricao,
        local_encontrado=dados.local_encontrado,
        encontrado_em=dados.encontrado_em,
        contato_achador=dados.contato_achador,
        categoria_id=categoria_id,
        campus_id=campus.id,
    )
    sessao.add(item)
    sessao.commit()
    sessao.refresh(item)
    return item


@router.get("", response_model=list[ItemPublico])
def buscar_itens(
    campus: str = Query(max_length=10, description="Sigla do campus: o feed é sempre de um campus (D22)"),
    q: Optional[str] = Query(default=None, max_length=100, description="Palavras da busca"),
    categoria_id: Optional[int] = Query(default=None, ge=1, description="Filtra por categoria"),
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    sessao: Session = Depends(obter_sessao),
):
    """RF03/RF04: busca pública no feed do campus. Só mostra itens disponíveis, sem dados pessoais."""
    escolhido = _campus_ativo(sessao, campus)
    if escolhido is None:
        raise HTTPException(status_code=404, detail="Campus não encontrado.")

    consulta = (
        sessao.query(Item)
        .outerjoin(Categoria, Item.categoria_id == Categoria.id)
        .options(contains_eager(Item.categoria), joinedload(Item.campus))
        .filter(Item.campus_id == escolhido.id, Item.status == "disponivel")
    )
    if categoria_id is not None:
        consulta = consulta.filter(Item.categoria_id == categoria_id)
    if q and q.strip():
        consulta = aplicar_busca(consulta, q)
    else:
        consulta = consulta.order_by(Item.criado_em.desc(), Item.id.desc())
    return consulta.offset(offset).limit(limit).all()


@router.get("/{item_id}", response_model=ItemPublico)
def detalhar_item(item_id: int, sessao: Session = Depends(obter_sessao)):
    """Detalhe público (link compartilhável). Traz o campus, para quem chega sem ter escolhido um."""
    item = sessao.get(Item, item_id)
    if item is None or item.status != "disponivel":
        raise HTTPException(status_code=404, detail="Item não encontrado.")
    return item
