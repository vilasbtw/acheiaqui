from sqlalchemy import Column, Integer, String, Date, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Devolucao(Base):
    __tablename__ = "devolucoes"

    id = Column(Integer, primary_key=True)
    item_id = Column(Integer, ForeignKey("itens.id"), nullable=False, unique=True)
    nome_retirante = Column(String(100), nullable=False)
    data_devolucao = Column(Date, nullable=False, server_default=func.current_date())

    item = relationship("Item", back_populates="devolucao")
