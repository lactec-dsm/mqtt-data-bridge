"""
repositorio.py

Camada de acesso a dados (Repository) para o modelo Medicao.

Objetivos:
- Isolar a lógica de persistência (inserts, batch, tratamento de erro).
- Evitar espalhar 'criar_sessao()' por todo o código.
- Facilitar testes unitários (podemos mockar o repositório).
"""

from typing import Iterable, List
from sqlalchemy import select, func
from sqlalchemy.exc import SQLAlchemyError
from mqtt_data_bridge.database.modelagem_banco import criar_sessao, Medicao


class MedicaoRepositorio:
    """
    Repositório responsável por operações de escrita
    relacionadas à entidade Medicao.
    """
    # ---------------- GRAVAÇÃO ---------------- #

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
            print(f"[REPOSITORIO] Erro ao salvar medicoes em batch: {exc}")
            raise
        finally:
            sessao.close()
    
    # ---------------- LEITURA ---------------- #

    def listar_ultimas(self, limite: int = 100) -> List[Medicao]:
        """
        Retorna as últimas 'limite' medições, ordenadas por id desc.
        """
        sessao = criar_sessao()
        try:
            stmt = (
                select(Medicao)
                .order_by(Medicao.id.desc())
                .limit(limite)
            )
            return list(sessao.execute(stmt).scalars().all())
        finally:
            sessao.close()

    def listar_ultimas_por_device(self, device_id: str, limite: int = 100) -> List[Medicao]:
        """
        Retorna as últimas medições de um dispositivo específico.
        """
        sessao = criar_sessao()
        try:
            stmt = (
                select(Medicao)
                .where(Medicao.device_id == device_id)
                .order_by(Medicao.id.desc())
                .limit(limite)
            )
            return list(sessao.execute(stmt).scalars().all())
        finally:
            sessao.close()

    def listar_por_measurement(
        self,
        measurement_id: str,
        device_id: str | None = None,
        limite: int = 500,
    ) -> List[Medicao]:
        """
        Retorna uma série temporal para um measurementId,
        opcionalmente filtrado por device_id.
        """
        sessao = criar_sessao()
        try:
            stmt = (
                select(Medicao)
                .where(Medicao.measurement_id == measurement_id)
            )

            if device_id:
                stmt = stmt.where(Medicao.device_id == device_id)

            # Aqui faz mais sentido ordenar por timestamp ascendente
            stmt = stmt.order_by(Medicao.timestamp.asc()).limit(limite)

            return list(sessao.execute(stmt).scalars().all())
        finally:
            sessao.close()

    def listar_dispositivos(self) -> List[str]:
        """
        Retorna a lista de device_id distintos presentes na tabela.
        """
        sessao = criar_sessao()
        try:
            stmt = select(func.distinct(Medicao.device_id))
            result = sessao.execute(stmt).all()
            return [row[0] for row in result]
        finally:
            sessao.close()