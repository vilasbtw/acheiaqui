"""
Área da CAE (D5/D6/D21): todas as rotas daqui exigem login E vínculo com um campus em `cae_membros`.
A proteção é aplicada ao router inteiro, então uma rota nova nunca fica aberta por esquecimento.
Cada rota só enxerga o campus da pessoa logada; item de outro campus responde 404, como se não existisse.
"""
from datetime import date, datetime, time, timedelta
from typing import Literal, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload, sessionmaker

from app.auth import exigir_cae
from app.database import obter_sessao
from app.models.cae_membro import CaeMembro
from app.models.categoria import Categoria
from app.models.devolucao import Devolucao
from app.models.item import Item
from app.models.item_foto import ItemFoto
from app.models.perdido import Perdido
from app.schemas.campus import CampusPublico
from app.schemas.devolucao import DevolucaoCriar
from app.schemas.item import CorrigirCategoria, ItemCAE
from app.schemas.perdido import ConfirmarCorrespondencia, PerdidoCAE, SugestaoCAE
from app.services.aviso import enviar_aviso
from app.services.correspondencia import sugerir
from app.tempo import agora_local

router = APIRouter(
    prefix="/cae",
    tags=["cae"],
    dependencies=[Depends(exigir_cae)],
)


@router.get("/campus", response_model=CampusPublico)
def campus_da_cae(membro: CaeMembro = Depends(exigir_cae)):
    """Campus da pessoa logada: o painel mostra o nome dele."""
    return membro.campus


@router.get("/itens", response_model=list[ItemCAE])
def historico_de_itens(
    status: Optional[Literal["disponivel", "devolvido", "arquivado"]] = None,
    data_inicio: Optional[date] = Query(default=None, description="Início do período (data em que foi encontrado)"),
    data_fim: Optional[date] = Query(default=None, description="Fim do período, inclusive"),
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    membro: CaeMembro = Depends(exigir_cae),
    sessao: Session = Depends(obter_sessao),
):
    """RF08/RF09: histórico do campus da pessoa, com filtros de status e período."""
    if data_inicio and data_fim and data_inicio > data_fim:
        raise HTTPException(status_code=422, detail="A data inicial não pode ser depois da data final.")

    consulta = (
        sessao.query(Item)
        .options(
            joinedload(Item.categoria),
            joinedload(Item.categoria_ia),
            joinedload(Item.campus),
            joinedload(Item.devolucao),
            joinedload(Item.foto),  # só para saber se tem foto: a imagem é deferred e não vem junto
        )
        .filter(Item.campus_id == membro.campus_id)
    )
    if status:
        consulta = consulta.filter(Item.status == status)
    if data_inicio:
        consulta = consulta.filter(Item.encontrado_em >= datetime.combine(data_inicio, time.min))
    if data_fim:
        consulta = consulta.filter(Item.encontrado_em < datetime.combine(data_fim + timedelta(days=1), time.min))
    return consulta.order_by(Item.criado_em.desc(), Item.id.desc()).offset(offset).limit(limit).all()


def _item_do_campus(sessao: Session, item_id: int, membro: CaeMembro) -> Item:
    """Item de outro campus responde 404, como se não existisse (D21)."""
    item = sessao.get(Item, item_id)
    if item is None or item.campus_id != membro.campus_id:
        raise HTTPException(status_code=404, detail="Item não encontrado.")
    return item


@router.post("/itens/{item_id}/categoria", response_model=ItemCAE)
def corrigir_categoria(
    item_id: int,
    dados: CorrigirCategoria,
    membro: CaeMembro = Depends(exigir_cae),
    sessao: Session = Depends(obter_sessao),
):
    """A CAE corrige a categoria (por exemplo, quando a IA errou). A sugestão original da IA fica guardada
    em categoria_ia_id, para medir a acurácia com dados reais."""
    item = _item_do_campus(sessao, item_id, membro)
    if dados.categoria_id is not None and sessao.get(Categoria, dados.categoria_id) is None:
        raise HTTPException(status_code=400, detail="Categoria inexistente.")
    if dados.categoria_id != item.categoria_id:
        item.categoria_id = dados.categoria_id
        item.categoria_corrigida_em = agora_local()
        sessao.commit()
    sessao.refresh(item)
    return item


@router.post("/itens/{item_id}/arquivar", response_model=ItemCAE)
def arquivar_item(
    item_id: int,
    membro: CaeMembro = Depends(exigir_cae),
    sessao: Session = Depends(obter_sessao),
):
    """D23: registro falso (spam) some da busca pública sem ser apagado. Pode ser desfeito."""
    item = _item_do_campus(sessao, item_id, membro)
    if item.status != "disponivel":
        raise HTTPException(status_code=409, detail="Só itens disponíveis podem ser arquivados.")
    item.status = "arquivado"
    sessao.commit()
    sessao.refresh(item)
    return item


@router.post("/itens/{item_id}/desarquivar", response_model=ItemCAE)
def desarquivar_item(
    item_id: int,
    membro: CaeMembro = Depends(exigir_cae),
    sessao: Session = Depends(obter_sessao),
):
    """D23: arquivou por engano? O item volta a aparecer na busca."""
    item = _item_do_campus(sessao, item_id, membro)
    if item.status != "arquivado":
        raise HTTPException(status_code=409, detail="Este item não está arquivado.")
    item.status = "disponivel"
    sessao.commit()
    sessao.refresh(item)
    return item


@router.get("/itens/{item_id}/foto", response_class=Response, responses={200: {"content": {"image/jpeg": {}}}})
def foto_do_item(
    item_id: int,
    membro: CaeMembro = Depends(exigir_cae),
    sessao: Session = Depends(obter_sessao),
):
    """Foto do item (D25): só a CAE do campus do item vê. Item de outro campus ou sem foto: 404."""
    foto = sessao.get(ItemFoto, item_id)
    if foto is None or foto.item.campus_id != membro.campus_id:
        raise HTTPException(status_code=404, detail="Foto não encontrada.")
    return Response(content=foto.conteudo, media_type=foto.tipo)


@router.post("/itens/{item_id}/devolucao", response_model=ItemCAE, status_code=201)
def registrar_devolucao(
    item_id: int,
    dados: DevolucaoCriar,
    membro: CaeMembro = Depends(exigir_cae),
    sessao: Session = Depends(obter_sessao),
):
    """RF05/RF06/RF07: registra quem retirou e marca o item como devolvido, na mesma transação."""
    item = _item_do_campus(sessao, item_id, membro)
    if item.status == "arquivado":
        raise HTTPException(status_code=409, detail="Este item está arquivado. Desarquive antes de registrar a devolução.")
    if item.status != "disponivel":
        raise HTTPException(status_code=409, detail="Este item já foi devolvido.")

    item.status = "devolvido"
    # Etapa 6: quem perdeu e teve este achado confirmado passa a ver "entregue" pelo link (0009).
    sessao.query(Perdido).filter(Perdido.item_id == item.id, Perdido.status == "encontrado").update(
        {Perdido.status: "entregue"}, synchronize_session=False
    )
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
        raise HTTPException(status_code=409, detail="Este item já foi devolvido.") from None
    sessao.refresh(item)
    return item


# ---------- Itens perdidos (Etapa 6, D26/D27): a CAE vê as sugestões e confirma ----------

def _perdido_do_campus(sessao: Session, perdido_id: int, membro: CaeMembro) -> Perdido:
    perdido = sessao.get(Perdido, perdido_id)
    if perdido is None or perdido.campus_id != membro.campus_id:
        raise HTTPException(status_code=404, detail="Pedido não encontrado.")
    return perdido


@router.get("/perdidos", response_model=list[PerdidoCAE])
def listar_perdidos(
    status: Optional[Literal["procurando", "encontrado", "entregue", "encerrado"]] = None,
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    membro: CaeMembro = Depends(exigir_cae),
    sessao: Session = Depends(obter_sessao),
):
    """Itens perdidos do campus da pessoa, com o contato de quem perdeu (só a CAE vê)."""
    consulta = (
        sessao.query(Perdido)
        .options(joinedload(Perdido.categoria), joinedload(Perdido.item).joinedload(Item.campus))
        .filter(Perdido.campus_id == membro.campus_id)
    )
    if status:
        consulta = consulta.filter(Perdido.status == status)
    return consulta.order_by(Perdido.criado_em.desc(), Perdido.id.desc()).offset(offset).limit(limit).all()


@router.get("/perdidos/{perdido_id}/sugestoes", response_model=list[SugestaoCAE])
def sugestoes_do_perdido(
    perdido_id: int,
    membro: CaeMembro = Depends(exigir_cae),
    sessao: Session = Depends(obter_sessao),
):
    """D27: achados parecidos (regras + IA nos 5 melhores). A CAE decide; nada é confirmado sozinho."""
    perdido = _perdido_do_campus(sessao, perdido_id, membro)
    if perdido.status != "procurando":
        return []
    return sugerir(sessao, perdido)


@router.post("/perdidos/{perdido_id}/confirmar", response_model=PerdidoCAE)
def confirmar_correspondencia(
    perdido_id: int,
    dados: ConfirmarCorrespondencia,
    tarefas: BackgroundTasks,
    membro: CaeMembro = Depends(exigir_cae),
    sessao: Session = Depends(obter_sessao),
):
    """A CAE confirma que o achado é o item perdido. Quem perdeu passa a ver "encontrado" pelo link
    e, se pediu, recebe um e-mail em segundo plano (Etapa 7, D28)."""
    perdido = _perdido_do_campus(sessao, perdido_id, membro)
    if perdido.status != "procurando":
        raise HTTPException(status_code=409, detail="Este pedido não está mais em busca.")
    item = _item_do_campus(sessao, dados.item_id, membro)
    if item.status != "disponivel":
        raise HTTPException(status_code=409, detail="Só itens disponíveis podem ser confirmados.")
    perdido.status = "encontrado"
    perdido.item_id = item.id
    perdido.confirmado_em = agora_local()
    perdido.aviso_enviado_em = None
    perdido.aviso_erro = None
    sessao.commit()
    sessao.refresh(perdido)
    _agendar_aviso(tarefas, sessao, perdido)
    return perdido


def _agendar_aviso(tarefas: BackgroundTasks, sessao: Session, perdido: Perdido) -> None:
    if perdido.aviso_consentido:
        tarefas.add_task(enviar_aviso, sessionmaker(bind=sessao.get_bind()), perdido.id)


@router.post("/perdidos/{perdido_id}/reenviar-aviso", response_model=PerdidoCAE)
def reenviar_aviso(
    perdido_id: int,
    tarefas: BackgroundTasks,
    membro: CaeMembro = Depends(exigir_cae),
    sessao: Session = Depends(obter_sessao),
):
    """O envio falhou (ou o servidor reiniciou antes)? A CAE tenta de novo."""
    perdido = _perdido_do_campus(sessao, perdido_id, membro)
    if perdido.status != "encontrado":
        raise HTTPException(status_code=409, detail="Só dá para avisar depois de confirmar a correspondência.")
    if not perdido.aviso_consentido:
        raise HTTPException(status_code=409, detail="Quem perdeu não pediu aviso por e-mail.")
    _agendar_aviso(tarefas, sessao, perdido)
    return perdido


@router.post("/perdidos/{perdido_id}/encerrar", response_model=PerdidoCAE)
def encerrar_perdido(
    perdido_id: int,
    membro: CaeMembro = Depends(exigir_cae),
    sessao: Session = Depends(obter_sessao),
):
    """Pedido antigo, duplicado ou falso: sai da lista "procurando"."""
    perdido = _perdido_do_campus(sessao, perdido_id, membro)
    if perdido.status != "procurando":
        raise HTTPException(status_code=409, detail="Este pedido não está mais em busca.")
    perdido.status = "encerrado"
    sessao.commit()
    sessao.refresh(perdido)
    return perdido


@router.post("/perdidos/{perdido_id}/reabrir", response_model=PerdidoCAE)
def reabrir_perdido(
    perdido_id: int,
    membro: CaeMembro = Depends(exigir_cae),
    sessao: Session = Depends(obter_sessao),
):
    """Desfaz uma confirmação ou um encerramento feito por engano."""
    perdido = _perdido_do_campus(sessao, perdido_id, membro)
    if perdido.status == "procurando":
        raise HTTPException(status_code=409, detail="Este pedido já está em busca.")
    if perdido.status == "entregue":
        raise HTTPException(status_code=409, detail="O item já foi entregue a quem perdeu: não dá para reabrir.")
    perdido.status = "procurando"
    perdido.item_id = None
    perdido.confirmado_em = None
    sessao.commit()
    sessao.refresh(perdido)
    return perdido
