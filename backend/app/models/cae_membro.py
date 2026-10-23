from sqlalchemy import Column, DateTime, ForeignKey, Integer, Uuid
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class CaeMembro(Base):
    """Pessoa da CAE e o campus a que pertence (D21). Uma pessoa, um campus."""

    __tablename__ = "cae_membros"

    id = Column(Integer, primary_key=True)
    user_id = Column(Uuid, nullable=False, unique=True)  # id do usuário no Supabase Auth
    campus_id = Column(Integer, ForeignKey("campi.id"), nullable=False)
    criado_em = Column(DateTime, server_default=func.now())

    campus = relationship("Campus")
