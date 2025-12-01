"""
conftest.py

Configuração de testes para o projeto mqtt-data-bridge.

Aqui:
- Criamos um banco SQLite em memória para os testes.
- Reconfiguramos o engine e o SessionLocal do módulo modelagem_banco
  para usar esse banco de teste.
- Criamos as tabelas antes dos testes rodarem.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

#from mqtt_data_bridge.database import modelagem_banco as db
from mqtt_data_bridge.database import modelagem_banco as db


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """
    Fixture de sessão de testes que:

    - Cria um engine SQLite em memória (sqlite:///:memory:).
    - Substitui o engine e o SessionLocal do módulo modelagem_banco
      para apontar para esse engine de teste.
    - Cria todas as tabelas definidas em Base.metadata.
    - Garante que todos os testes usem esse banco isolado.

    A opção autouse=True faz com que isso seja aplicado automaticamente
    a todos os testes, sem precisar declarar explicitamente nas funções.
    """

    # Cria um novo engine em memória
    engine = create_engine("sqlite:///:memory:", echo=False, future=True)

    # Reconfigura o módulo modelagem_banco para usar este engine
    db.engine = engine
    db.SessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
    )

    # Cria as tabelas no banco de teste
    db.Base.metadata.create_all(engine)

    yield

    # Finalização (se precisar)
    engine.dispose()
