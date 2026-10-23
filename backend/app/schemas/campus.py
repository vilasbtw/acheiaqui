from pydantic import BaseModel, ConfigDict


class CampusPublico(BaseModel):
    """O que o público vê de um campus: o seletor usa a sigla e o texto de retirada substitui o antigo INFO_CAE."""

    model_config = ConfigDict(from_attributes=True)

    sigla: str
    nome: str
    cidade: str
    info_retirada: str
