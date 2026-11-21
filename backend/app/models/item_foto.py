from sqlalchemy import Column, DateTime, ForeignKey, Integer, LargeBinary, String
from sqlalchemy.orm import deferred, relationship
from sqlalchemy.sql import func

from app.database import Base


class ItemFoto(Base):
    """Foto opcional do item (D4/D25). Só a CAE do campus do item vê."""

    __tablename__ = "item_fotos"

    item_id = Column(Integer, ForeignKey("itens.id", ondelete="CASCADE"), primary_key=True)
    tipo = Column(String(20), nullable=False)  # image/jpeg, image/png ou image/webp
    # deferred: carregar a linha (para saber se o item tem foto) não traz a imagem junto.
    conteudo = deferred(Column(LargeBinary, nullable=False))
    criado_em = Column(DateTime, server_default=func.now())

    item = relationship("Item", back_populates="foto")
