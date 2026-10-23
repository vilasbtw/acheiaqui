from sqlalchemy import Boolean, Column, Integer, String, Text, true
from app.database import Base


class Campus(Base):
    __tablename__ = "campi"

    id = Column(Integer, primary_key=True)
    sigla = Column(String(10), nullable=False, unique=True)  # a do endereço do site (ex.: hto)
    nome = Column(String(100), nullable=False)
    cidade = Column(String(100), nullable=False)
    ativo = Column(Boolean, nullable=False, default=True, server_default=true())
    info_retirada = Column(Text, nullable=False, default="", server_default="")  # sala e horário da CAE
