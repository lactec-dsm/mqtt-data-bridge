"""
modelagem_banco.py

Responsável por:
- Criar o engine do SQLAlchemy usando settings.DB_URL.
- Definir o modelo de dados canônico (tabela 'medicoes').
- Expor funções para criar sessão e inicializar o banco.

"""

from datetime import datetime

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,
    DateTime,
    Text,
    func,
)
from sqlalchemy.orm import declarative_base, sessionmaker

# Importa as configurações centralizadas
from mqtt_data_bridge.config.settings import settings

# --------------------------------------------------------------------
# Engine e Base
# --------------------------------------------------------------------

# Cria o engine do SQLAlchemy usando a DB_URL vinda do settings.
# Exemplo:
#   sqlite:///mqtt_store.db
#   postgresql+psycopg2://user:pass@host:5432/mqtt_store
engine = create_engine(settings.DB_URL, echo=False, future=True)

# Base declarativa a partir da qual as classes de modelo serão definidas
Base = declarative_base()

# Factory de sessão: cada sessão é uma "conversa" com o banco
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def criar_sessao():
    """
    Cria e retorna uma nova sessão de banco de dados.

    Uso típico:

        sessao = criar_sessao()
        try:
            # operações com o banco
        finally:
            sessao.close()
    """
    return SessionLocal()


# --------------------------------------------------------------------
# Modelo canônico de medições
# --------------------------------------------------------------------


class Medicao(Base):
    """
    Modelo canônico para armazenar uma medição recebida via MQTT.

    Mapeia diretamente o payload JSON canônico:

        [
          {
            "timestamp": 1746085310003,
            "deviceId": "SMA-3008628305-EDMM",
            "measurementId": "pAcGrid",
            "measurementIndex": 1,
            "value": -770.0
          }
        ]

    Campos principais:

    - device_id: identifica o equipamento de origem.
    - measurement_id: identifica a grandeza (potência, tensão, etc.).
    - measurement_index: diferencia fases/canais (1, 2, 3...).
    - timestamp: instante em que o valor foi medido (UTC).
    - value: valor numérico medido.
    - ingested_at: instante em que o registro entrou na nossa base.
    - raw_payload: opcional, armazena JSON bruto para auditoria/debug.
    """

    __tablename__ = "medicoes"

    # Chave primária simples (surrogate key)
    id = Column(Integer, primary_key=True, index=True)

    # ID lógico do dispositivo (ex.: "SMA-3008628305-EDMM")
    device_id = Column(String(100), nullable=False, index=True)

    # Identificador da grandeza medida (ex.: "pAcGrid", "vAcGrid", "iAcGrid")
    measurement_id = Column(String(100), nullable=False, index=True)

    # Índice da medição (ex.: 1, 2, 3 para fases/canais)
    measurement_index = Column(Integer, nullable=False)

    # Momento em que o valor foi medido pelo equipamento,
    # convertido de epoch ms (do JSON) para datetime (UTC).
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)

    # Valor medido (float). Ex.: potência, tensão, corrente, frequência.
    value = Column(Float, nullable=False)

    # Momento em que a linha foi inserida na base.
    # Usamos um default no servidor para registrar o instante da ingestão.
    ingested_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    # Campo opcional para armazenar o payload bruto recebido.
    # Pode ser útil para auditoria, reprocessamento ou debug.
    raw_payload = Column(Text, nullable=True)

    def __repr__(self) -> str:
        """
        Representação textual útil para logs e debugging.
        """
        return (
            f"<Medicao(id={self.id}, device_id={self.device_id}, "
            f"measurement_id={self.measurement_id}, "
            f"measurement_index={self.measurement_index}, "
            f"timestamp={self.timestamp}, value={self.value})>"
        )


# --------------------------------------------------------------------
# Inicialização do banco
# --------------------------------------------------------------------


def inicializar_banco():
    """
    Cria todas as tabelas definidas em Base.metadata, se ainda não existirem.

    Deve ser chamado uma única vez na inicialização da aplicação, por exemplo:
        - em um script separado (scripts/inicializar_banco.py)
        - ou no bootstrap do sistema de ingestão.
    """
    Base.metadata.create_all(engine)


# Permite rodar diretamente: `python -m mqtt_data_bridge.database.modelagem_banco`
if __name__ == "__main__":
    inicializar_banco()
    print("Tabelas criadas com sucesso em:", settings.DB_URL)
