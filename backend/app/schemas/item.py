from datetime import datetime, timedelta
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.devolucao import DevolucaoResposta
from app.tempo import FUSO_CAMPUS, agora_local

# Folga para relógios de celular levemente adiantados.
TOLERANCIA_FUTURO = timedelta(minutes=5)


class ItemCriar(BaseModel):
    """Dados do formulário público de registro (RF01/RF02)."""

    model_config = ConfigDict(str_strip_whitespace=True)

    descricao: str = Field(min_length=3, max_length=1000)
    local_encontrado: str = Field(min_length=2, max_length=100)
    encontrado_em: datetime
    contato_achador: Optional[str] = Field(default=None, max_length=100)  # opcional (RF02)
    categoria_id: Optional[int] = None  # se vier vazio, a IA tenta sugerir (D2)

    @field_validator("contato_achador")
    @classmethod
    def _contato_vazio_vira_nulo(cls, valor):
        return valor or None

    @field_validator("encontrado_em")
    @classmethod
    def _nao_pode_ser_futuro(cls, valor: datetime):
        if valor.tzinfo is not None:  # se vier com fuso, converte para o horário do campus (D7)
            valor = valor.astimezone(FUSO_CAMPUS).replace(tzinfo=None)
        if valor > agora_local() + TOLERANCIA_FUTURO:
            raise ValueError("A data e o horário em que o item foi encontrado não podem estar no futuro.")
        return valor


class ItemPublico(BaseModel):
    """O que qualquer pessoa pode ver: SEM contato de quem achou (RNF03 / D5)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    descricao: str
    categoria: Optional[str] = None
    local_encontrado: str
    encontrado_em: datetime
    criado_em: Optional[datetime] = None

    @field_validator("categoria", mode="before")
    @classmethod
    def _nome_da_categoria(cls, valor):
        return getattr(valor, "nome", valor)


class ItemCAE(ItemPublico):
    """Visão da equipe da CAE: inclui status, contato e dados da devolução."""

    status: str
    contato_achador: Optional[str] = None
    devolucao: Optional[DevolucaoResposta] = None
