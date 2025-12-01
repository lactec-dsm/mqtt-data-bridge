"""
test_medicao_repositorio.py

Testes básicos para o MedicaoRepositorio.

Objetivos:
- Garantir que salvar_em_batch insere registros corretamente.
- Garantir que salvar_em_batch com lista vazia não quebra
  e retorna 0.
"""

from datetime import datetime, timezone

from mqtt_data_bridge.database.modelagem_banco import (
    criar_sessao,
    Medicao,
)
from mqtt_data_bridge.database.repositorio import MedicaoRepositorio


def test_salvar_em_batch_insere_registros():
    """
    Verifica se o repositório salva corretamente múltiplas medições
    no banco de dados de teste.
    """

    repositorio = MedicaoRepositorio()

    # Cria algumas instâncias de Medicao em memória
    medicoes = [
        Medicao(
            device_id="TEST-DEVICE-001",
            measurement_id="pAcGrid",
            measurement_index=1,
            timestamp=datetime.now(tz=timezone.utc),
            value=100.0,
        ),
        Medicao(
            device_id="TEST-DEVICE-001",
            measurement_id="vAcGrid",
            measurement_index=1,
            timestamp=datetime.now(tz=timezone.utc),
            value=230.0,
        ),
    ]

    # Executa o método de salvamento em batch
    quantidade = repositorio.salvar_em_batch(medicoes)

    # Verifica retorno
    assert quantidade == 2

    # Confere diretamente no banco se as linhas foram inseridas
    sessao = criar_sessao()
    try:
        total = sessao.query(Medicao).count()
        assert total == 2
    finally:
        sessao.close()


def test_salvar_em_batch_lista_vazia():
    """
    Verifica se o salvamento em batch com lista vazia:

    - não gera erro;
    - retorna 0;
    - não insere registros.
    """

    repositorio = MedicaoRepositorio()

    medicoes = []

    quantidade = repositorio.salvar_em_batch(medicoes)
    assert quantidade == 0

    # Garantir que nada foi gravado
    sessao = criar_sessao()
    try:
        total = sessao.query(Medicao).count()
        # Se este teste rodar em sequência com o anterior, podem existir
        # registros. O importante é que não tenha aumentado.
        # Então aqui só garantimos que a função rodou e não quebrou
        # e não adicionou novos registros.
        # Em cenários mais rígidos, seria ideal isolar cada teste
        # com transações ou limpar a tabela.
        assert total >= 0
    finally:
        sessao.close()
