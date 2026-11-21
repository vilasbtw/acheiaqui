from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, String, Text, event
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Perdido(Base):
    """Item perdido (Etapa 6, D26/D27). Quem perdeu acompanha por um link secreto; a CAE confirma o achado."""

    __tablename__ = "perdidos"

    id = Column(Integer, primary_key=True)
    campus_id = Column(Integer, ForeignKey("campi.id"), nullable=False)
    descricao = Column(Text, nullable=False)
    local_perdido = Column(String(100))  # opcional
    perdido_em = Column(Date, nullable=False)  # dia aproximado, data local (D7)
    contato = Column(String(100), nullable=False)  # só a CAE vê (D5)
    categoria_id = Column(Integer, ForeignKey("categorias.id"))  # sugerida pela IA (D2)
    texto_busca = Column(Text)  # minúsculas e sem acento (D24); preenchido abaixo
    token_hash = Column(String(64), nullable=False, unique=True)  # SHA-256 do segredo do link
    status = Column(String(20), nullable=False, default="procurando")  # procurando, encontrado ou encerrado
    item_id = Column(Integer, ForeignKey("itens.id"))  # o achado que a CAE confirmou
    confirmado_em = Column(DateTime)
    # Etapa 7 (D28): aviso por e-mail. O e-mail só é gravado com consentimento (CHECK na migração 0008).
    email_aviso = Column(String(254))
    aviso_consentido = Column(Boolean, nullable=False, default=False)
    aviso_enviado_em = Column(DateTime)
    aviso_erro = Column(String(200))
    criado_em = Column(DateTime, server_default=func.now())

    campus = relationship("Campus")
    categoria = relationship("Categoria")
    item = relationship("Item")


class Correspondencia(Base):
    """Nota que a IA deu a um par (perdido, achado). Guardada para não gastar a cota de novo."""

    __tablename__ = "correspondencias"

    perdido_id = Column(Integer, ForeignKey("perdidos.id", ondelete="CASCADE"), primary_key=True)
    item_id = Column(Integer, ForeignKey("itens.id", ondelete="CASCADE"), primary_key=True)
    nota_ia = Column(String(10), nullable=False)  # alta, media ou baixa
    criado_em = Column(DateTime, server_default=func.now())


@event.listens_for(Perdido, "before_insert")
def _preencher_texto_busca(mapper, conexao, perdido):
    from app.services.busca import texto_de_busca

    perdido.texto_busca = texto_de_busca(perdido.descricao or "", perdido.local_perdido or "")
