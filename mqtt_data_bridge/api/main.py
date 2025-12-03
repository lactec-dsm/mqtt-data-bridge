"""
main.py

API de leitura do mqtt-data-bridge usando FastAPI.

Rotas principais:
- GET /ping
- GET /medicoes/recentes
- GET /medicoes/{device_id}/ultimas
- GET /serie/{measurement_id}
- GET /dispositivos
"""

from fastapi import FastAPI, Query
from typing import List, Optional

from mqtt_data_bridge.database.repositorio import MedicaoRepositorio
from mqtt_data_bridge.api.schemas import MedicaoOut, DispositivoOut

app = FastAPI(
    title="mqtt-data-bridge API",
    version="0.1.0",
    description="API de leitura das medições armazenadas pelo mqtt-data-bridge.",
)


def get_repositorio() -> MedicaoRepositorio:
    """
    Factory simples para criar o repositório.

    Em projetos maiores, poderíamos usar injeção de dependência mais sofisticada,
    mas aqui é suficiente criar uma instância por requisição.
    """
    return MedicaoRepositorio()


# ------------------- HEALTHCHECK ------------------- #


@app.get("/ping")
def ping():
    """
    Endpoint simples para healthcheck.
    """
    return {"status": "ok"}


# ------------------- MEDIÇÕES ------------------- #


@app.get(
    "/medicoes/recentes",
    response_model=List[MedicaoOut],
    summary="Lista as últimas medições",
)
def listar_medicoes_recentes(
    limite: int = Query(100, ge=1, le=1000, description="Quantidade de medições"),
):
    """
    Retorna as últimas `limite` medições registradas no banco.
    """
    repo = get_repositorio()
    medicoes = repo.listar_ultimas(limite=limite)
    return medicoes


@app.get(
    "/medicoes/{device_id}/ultimas",
    response_model=List[MedicaoOut],
    summary="Lista as últimas medições de um dispositivo",
)
def listar_medicoes_por_device(
    device_id: str,
    limite: int = Query(100, ge=1, le=1000, description="Quantidade de medições"),
):
    """
    Retorna as últimas medições de um dispositivo específico.
    """
    repo = get_repositorio()
    medicoes = repo.listar_ultimas_por_device(device_id=device_id, limite=limite)
    return medicoes


@app.get(
    "/serie/{measurement_id}",
    response_model=List[MedicaoOut],
    summary="Retorna série temporal para um measurementId",
)
def listar_serie_por_measurement(
    measurement_id: str,
    device_id: Optional[str] = Query(
        None, description="Opcional: filtra por device_id"
    ),
    limite: int = Query(
        500,
        ge=1,
        le=5000,
        description="Máximo de pontos retornados",
    ),
):
    """
    Retorna uma série temporal para um measurementId,
    opcionalmente filtrando por device_id.
    """
    repo = get_repositorio()
    medicoes = repo.listar_por_measurement(
        measurement_id=measurement_id,
        device_id=device_id,
        limite=limite,
    )
    return medicoes


# ------------------- DISPOSITIVOS ------------------- #


@app.get(
    "/dispositivos",
    response_model=List[DispositivoOut],
    summary="Lista dispositivos conhecidos",
)
def listar_dispositivos():
    """
    Retorna a lista de device_id distintos presentes na base.
    """
    repo = get_repositorio()
    ids = repo.listar_dispositivos()
    return [DispositivoOut(device_id=d) for d in ids]
