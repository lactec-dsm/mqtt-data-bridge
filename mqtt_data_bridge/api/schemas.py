"""
schemas.py

Modelos Pydantic usados nas respostas da API.
São independentes do modelo ORM (Medicao), mas compatíveis
para conversão via from_attributes.
"""

from datetime import datetime
from pydantic import BaseModel, ConfigDict


class MedicaoOut(BaseModel):
    """
    Representa uma medição retornada pela API.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    device_id: str
    measurement_id: str
    measurement_index: int
    timestamp: datetime
    value: float


class DispositivoOut(BaseModel):
    """
    Representa um dispositivo (apenas o ID) retornado pela API.
    """

    device_id: str
