"""
repositorio.py

Camada de acesso a dados (Repository) para o modelo Medicao.

Objetivos:
- Isolar a lógica de persistência (inserts, batch, tratamento de erro).
- Evitar espalhar 'criar_sessao()' por todo o código.
- Facilitar testes unitários (podemos mockar o repositório).
"""

from typing import Iterable

from sqlalchemy.exc import SQLAlchemyError

from mqtt_data_bridge.database.modelagem_banco import criar_sessao, Medicao


class MedicaoRepositorio:
    """
    Repositório responsável por operações de escrita
    relacionadas à entidade Medicao.
    """

    def salvar_em_batch(self, medicoes: Iterable[Medicao]) -> int:
        """
        Salva uma coleção de objetos Medicao em uma única transação.

        Parâmetros:
            medicoes: coleção (lista, tupla, gerador) de instâncias de Medicao.

        Retorna:
            Quantidade de registros efetivamente persistidos.

        Comportamento:
            - Abre uma nova sessão.
            - Adiciona todas as instâncias ao contexto.
            - Faz commit se tudo der certo.
            - Em caso de erro, faz rollback e relança a exceção.
        """
        medicoes = list(medicoes)  # garante que podemos medir o tamanho
        if not medicoes:
            return 0

        sessao = criar_sessao()
        try:
            sessao.add_all(medicoes)
            sessao.commit()
            return len(medicoes)
        except SQLAlchemyError as exc:
            sessao.rollback()
            # Aqui poderíamos usar logging estruturado em vez de print.
            print(f"[REPOSITORIO] Erro ao salvar medicoes em batch: {exc}")
            # Em um sistema maior, poderíamos levantar uma exceção customizada.
            raise
        finally:
            sessao.close()
