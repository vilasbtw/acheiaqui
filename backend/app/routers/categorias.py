from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import obter_sessao
from app.models.categoria import Categoria
from app.schemas.categoria import CategoriaResposta

router = APIRouter(prefix="/categorias", tags=["categorias"])


@router.get("", response_model=list[CategoriaResposta])
def listar_categorias(sessao: Session = Depends(obter_sessao)):
    """Lista pública e somente leitura. As categorias são criadas por SQL (seed)."""
    return sessao.query(Categoria).order_by(Categoria.nome).all()
