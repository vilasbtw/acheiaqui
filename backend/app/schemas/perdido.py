from datetime import date, datetime, timedelta
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.campus import CampusPublico
from app.schemas.item import ItemCAE, ItemPublico
from app.tempo import agora_local

MAX_DIAS_ATRAS = 365


class PerdidoCriar(BaseModel):
    """Formulário público "Perdi um item" (D26)."""

    model_config = ConfigDict(str_strip_whitespace=True)

    campus: str = Field(min_length=2, max_length=10, description="Sigla do campus")
    descricao: str = Field(min_length=3, max_length=1000)
    local_perdido: Optional[str] = Field(default=None, max_length=100)  # opcional: muita gente não sabe
    perdido_em: date = Field(description="Dia aproximado em que perdeu")
    contato: str = Field(min_length=3, max_length=100, description="Nome e e-mail ou telefone. Só a CAE vê")

    @field_validator("local_perdido")
    @classmethod
    def _local_vazio_vira_nulo(cls, valor):
        return valor or None

    @field_validator("perdido_em")
    @classmethod
    def _data_possivel(cls, valor: date):
        hoje = agora_local().date()
        if valor > hoje:
            raise ValueError("O dia em que perdeu não pode estar no futuro.")
        if valor < hoje - timedelta(days=MAX_DIAS_ATRAS):
            raise ValueError("Só dá para registrar itens perdidos no último ano.")
        return valor


class PerdidoCriado(BaseModel):
    """O segredo do link só aparece AQUI, uma vez. O banco guarda só o hash."""

    token: str
    status: str


class PerdidoToken(BaseModel):
    token: str = Field(min_length=20, max_length=100)


class PerdidoAcompanhamento(BaseModel):
    """O que quem perdeu vê pelo link (D27: só o status). Sem contato, sem sugestões."""

    model_config = ConfigDict(from_attributes=True)

    descricao: str
    perdido_em: date
    status: str
    campus: CampusPublico
    criado_em: Optional[datetime] = None
    item_encontrado: Optional[str] = None  # descrição do achado, só depois que a CAE confirmou


class PerdidoCAE(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    descricao: str
    local_perdido: Optional[str] = None
    perdido_em: date
    contato: str
    categoria: Optional[str] = None
    status: str
    item: Optional[ItemPublico] = None  # o achado confirmado
    confirmado_em: Optional[datetime] = None
    criado_em: Optional[datetime] = None

    @field_validator("categoria", mode="before")
    @classmethod
    def _nome_da_categoria(cls, valor):
        return getattr(valor, "nome", valor)


class SugestaoCAE(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    item: ItemCAE
    pontos: int
    nota_ia: Optional[str] = None  # alta, media, baixa ou None (IA indisponível)


class ConfirmarCorrespondencia(BaseModel):
    item_id: int = Field(ge=1)
