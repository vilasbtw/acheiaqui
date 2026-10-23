from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Item(Base):
    __tablename__ = "itens"

    id = Column(Integer, primary_key=True)
    descricao = Column(Text, nullable=False)
    categoria_id = Column(Integer, ForeignKey("categorias.id"))
    # Nulo por enquanto: a trava NOT NULL vem depois que o backend passar a informar o campus (Etapa 1).
    campus_id = Column(Integer, ForeignKey("campi.id"))
    local_encontrado = Column(String(100), nullable=False)
    encontrado_em = Column(DateTime, nullable=False)  # hora local, sem fuso (D7)
    contato_achador = Column(String(100))  # opcional; só a CAE pode ver (D5)
    foto_url = Column(Text)  # reservado, não usado no MVP (D4)
    status = Column(String(20), nullable=False, default="disponivel")
    criado_em = Column(DateTime, server_default=func.now())

    categoria = relationship("Categoria")
    devolucao = relationship("Devolucao", back_populates="item", uselist=False)
