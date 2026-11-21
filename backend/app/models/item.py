from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Item(Base):
    __tablename__ = "itens"

    id = Column(Integer, primary_key=True)
    descricao = Column(Text, nullable=False)
    categoria_id = Column(Integer, ForeignKey("categorias.id"))
    campus_id = Column(Integer, ForeignKey("campi.id"), nullable=False)  # D20; NOT NULL desde a migração 0003
    local_encontrado = Column(String(100), nullable=False)
    encontrado_em = Column(DateTime, nullable=False)  # hora local, sem fuso (D7)
    contato_achador = Column(String(100))  # opcional; só a CAE pode ver (D5)
    foto_url = Column(Text)  # sem uso: a foto fica na tabela item_fotos (migração 0004)
    status = Column(String(20), nullable=False, default="disponivel")
    criado_em = Column(DateTime, server_default=func.now())

    categoria = relationship("Categoria")
    campus = relationship("Campus")
    devolucao = relationship("Devolucao", back_populates="item", uselist=False)
    foto = relationship("ItemFoto", back_populates="item", uselist=False, cascade="all, delete-orphan")

    @property
    def tem_foto(self) -> bool:
        """Só a visão da CAE usa (ItemCAE). A imagem em si não é carregada (coluna deferred)."""
        return self.foto is not None
