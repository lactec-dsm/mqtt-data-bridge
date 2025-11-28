"""
settings.py

Responsável por:
- Definir a configuração central do projeto (Settings).
- Ler variáveis de ambiente (ou .env) de forma tipada e validada.
- Oferecer um ponto único de acesso às configurações.

Uso típico em outros módulos:

    from mqtt_data_bridge.config.settings import settings

    engine = create_engine(settings.DB_URL)
"""

from functools import lru_cache
from typing import List

from pydantic import BaseSettings, Field, field_validator


class Settings(BaseSettings):
    """
    Classe de configuração principal do projeto.

    Herda de BaseSettings, o que faz com que:
    - valores padrão possam ser definidos aqui no código;
    - variáveis de ambiente (ou arquivo .env) possam sobrescrever esses valores;
    - todos os campos sejam validados e convertidos para os tipos corretos.
    """

    # ---------------------------------------------------------
    # BANCO DE DADOS
    # ---------------------------------------------------------
    # URL de conexão com o banco usada pelo SQLAlchemy.
    # Exemplo:
    #   sqlite:///mqtt_store.db
    #   postgresql+psycopg2://user:pass@host:5432/mqtt_store
    DB_URL: str = Field(
        "sqlite:///mqtt_store.db",
        description="String de conexão do banco de dados (SQLAlchemy).",
    )

    # ---------------------------------------------------------
    # MQTT — BROKER
    # ---------------------------------------------------------
    MQTT_BROKER_HOST: str = Field(
        "localhost",
        description="Host do broker MQTT.",
    )

    MQTT_BROKER_PORT: int = Field(
        1883,
        description="Porta do broker MQTT.",
    )

    # Raiz dos tópicos que o consumer vai assinar.
    # Pode ser '#', ou algo como 'SMA-+/data', dependendo do broker.
    MQTT_TOPIC_ROOT: str = Field(
        "#",
        description="Raiz dos tópicos MQTT monitorados pelo coletor.",
    )

    # ---------------------------------------------------------
    # CONSUMER MQTT
    # ---------------------------------------------------------
    CONSUMER_RATE_LIMIT: int = Field(
        200,
        description="Quantidade máxima de mensagens processadas por segundo.",
    )

    SAVE_RAW_PAYLOAD: bool = Field(
        True,
        description="Se verdadeiro, salva o payload bruto JSON no banco.",
    )

    BATCH_SIZE: int = Field(
        100,
        description="Quantidade de registros por commit (inserts em batch).",
    )

    # ---------------------------------------------------------
    # SIMULADOR MQTT
    # ---------------------------------------------------------
    SIMULATOR_DEVICE_COUNT: int = Field(
        5,
        description="Quantidade de dispositivos simulados publicando dados.",
    )

    # Vamos armazenar como lista de strings, preenchida a partir
    # de uma variável de ambiente do tipo:
    #   SIMULATOR_MEASUREMENT_IDS=pAcGrid,vAcGrid,iAcGrid
    SIMULATOR_MEASUREMENT_IDS: List[str] = Field(
        default_factory=lambda: ["pAcGrid", "vAcGrid", "iAcGrid"],
        description="Lista de measurementIds simulados.",
    )

    SIMULATOR_INTERVAL_SECONDS: int = Field(
        5,
        description="Intervalo (em segundos) entre publicações do simulador.",
    )

    SIMULATOR_DEVICE_PREFIX: str = Field(
        "SMA-SIM-DEVICE",
        description="Prefixo do deviceId usado pelos simuladores.",
    )

    # ---------------------------------------------------------
    # LOGGING
    # ---------------------------------------------------------
    LOG_LEVEL: str = Field(
        "INFO",
        description="Nível de log padrão: DEBUG, INFO, WARNING, ERROR.",
    )

    class Config:
        """
        Config interna do Pydantic para a classe Settings.

        - env_file: indica que, em ambiente de desenvolvimento, deve ler
          automaticamente o arquivo .env (se existir).
        - env_file_encoding: encoding do arquivo .env.
        """

        env_file = ".env"
        env_file_encoding = "utf-8"

    # ---------------------------------------------------------
    # VALIDADORES — VERSÃO PYDANTIC V2
    # ---------------------------------------------------------

    @field_validator("SIMULATOR_MEASUREMENT_IDS", mode="before")
    def split_measurement_ids(cls, v):
        """
        Converte 'pAcGrid,vAcGrid,iAcGrid' → ['pAcGrid','vAcGrid','iAcGrid']
        Se já for lista, retorna como está.
        """
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v

    @field_validator("LOG_LEVEL")
    def normalize_log_level(cls, v: str) -> str:
        """
        Normaliza nível de log (p.ex., "info" → "INFO") e garante valores válidos.
        """
        nivel = v.upper()
        niveis_validos = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}

        if nivel not in niveis_validos:
            # fallback seguro
            return "INFO"

        return nivel


# ---------------------------------------------------------
# Singleton de configurações
# ---------------------------------------------------------
@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()