from datetime import date
from pydantic import BaseModel, ConfigDict, Field


class DevolucaoCriar(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    nome_retirante: str = Field(min_length=2, max_length=100)


class DevolucaoResposta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    nome_retirante: str
    data_devolucao: date
