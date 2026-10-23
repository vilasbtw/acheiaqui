from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import obter_sessao
from app.models.campus import Campus
from app.schemas.campus import CampusPublico

router = APIRouter(prefix="/campi", tags=["campi"])


@router.get("", response_model=list[CampusPublico])
def listar_campi(sessao: Session = Depends(obter_sessao)):
    """Lista pública para o seletor de campus (D22). Só os ativos; os campi são criados por SQL."""
    return sessao.query(Campus).filter(Campus.ativo.is_(True)).order_by(Campus.nome).all()
