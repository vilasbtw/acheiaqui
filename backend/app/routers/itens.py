from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, contains_eager

from app.database import obter_sessao
from app.models.categoria import Categoria
from app.models.item import Item
from app.schemas.item import ItemCriar, ItemPublico
from app.services.busca import aplicar_busca
from app.services.ia_categoria import sugerir_categoria

router = APIRouter(prefix="/itens", tags=["itens"])


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
    """RF01/RF02: qualquer pessoa registra um item encontrado, sem conta."""
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
    )
    sessao.add(item)
    sessao.commit()
    sessao.refresh(item)
    return item


@router.get("", response_model=list[ItemPublico])
def buscar_itens(
    q: Optional[str] = Query(default=None, max_length=100, description="Palavras da busca"),
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    sessao: Session = Depends(obter_sessao),
):
    """RF03/RF04: busca pública. Só mostra itens disponíveis, sem dados pessoais."""
    consulta = (
        sessao.query(Item)
        .outerjoin(Categoria, Item.categoria_id == Categoria.id)
        .options(contains_eager(Item.categoria))
        .filter(Item.status == "disponivel")
    )
    if q and q.strip():
        consulta = aplicar_busca(consulta, q)
    else:
        consulta = consulta.order_by(Item.criado_em.desc(), Item.id.desc())
    return consulta.offset(offset).limit(limit).all()


@router.get("/{item_id}", response_model=ItemPublico)
def detalhar_item(item_id: int, sessao: Session = Depends(obter_sessao)):
    item = sessao.get(Item, item_id)
    if item is None or item.status != "disponivel":
        raise HTTPException(status_code=404, detail="Item não encontrado.")
    return item
