"""
Área da CAE (D5/D6): todas as rotas daqui exigem login. A proteção é aplicada ao
router inteiro, então uma rota nova nunca fica aberta por esquecimento.
"""
from datetime import date, datetime, time, timedelta
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.auth import exigir_autenticacao_cae
from app.database import obter_sessao
from app.models.devolucao import Devolucao
from app.models.item import Item
from app.schemas.devolucao import DevolucaoCriar
from app.schemas.item import ItemCAE
from app.tempo import agora_local

router = APIRouter(
    prefix="/cae",
    tags=["cae"],
    dependencies=[Depends(exigir_autenticacao_cae)],
)


@router.get("/itens", response_model=list[ItemCAE])
def historico_de_itens(
    status: Optional[Literal["disponivel", "devolvido"]] = None,
    data_inicio: Optional[date] = Query(default=None, description="Início do período (data em que foi encontrado)"),
    data_fim: Optional[date] = Query(default=None, description="Fim do período, inclusive"),
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    sessao: Session = Depends(obter_sessao),
):
    """RF08/RF09: histórico com filtros de status e período."""
    if data_inicio and data_fim and data_inicio > data_fim:
        raise HTTPException(status_code=422, detail="A data inicial não pode ser depois da data final.")

    consulta = sessao.query(Item).options(joinedload(Item.categoria), joinedload(Item.devolucao))
    if status:
        consulta = consulta.filter(Item.status == status)
    if data_inicio:
        consulta = consulta.filter(Item.encontrado_em >= datetime.combine(data_inicio, time.min))
    if data_fim:
        consulta = consulta.filter(Item.encontrado_em < datetime.combine(data_fim + timedelta(days=1), time.min))
    return consulta.order_by(Item.criado_em.desc(), Item.id.desc()).offset(offset).limit(limit).all()


@router.post("/itens/{item_id}/devolucao", response_model=ItemCAE, status_code=201)
def registrar_devolucao(item_id: int, dados: DevolucaoCriar, sessao: Session = Depends(obter_sessao)):
    """RF05/RF06/RF07: registra quem retirou e marca o item como devolvido, na mesma transação."""
    item = sessao.get(Item, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item não encontrado.")
    if item.status != "disponivel":
        raise HTTPException(status_code=409, detail="Este item já foi devolvido.")

    item.status = "devolvido"
    sessao.add(
        Devolucao(
            item_id=item.id,
            nome_retirante=dados.nome_retirante,
            data_devolucao=agora_local().date(),
        )
    )
    try:
        sessao.commit()
    except IntegrityError:  # duas pessoas da CAE devolvendo o mesmo item ao mesmo tempo
        sessao.rollback()
        raise HTTPException(status_code=409, detail="Este item já foi devolvido.")
    sessao.refresh(item)
    return item
