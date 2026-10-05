"""
Horário do campus (D7): o sistema guarda "hora de parede" sem fuso, no horário de
Brasília, exatamente como a pessoa digitou. Nada é convertido na exibição.
"""
from datetime import datetime
from zoneinfo import ZoneInfo

FUSO_CAMPUS = ZoneInfo("America/Sao_Paulo")


def agora_local() -> datetime:
    """Data/hora atual no campus, sem fuso (naive)."""
    return datetime.now(FUSO_CAMPUS).replace(tzinfo=None)
