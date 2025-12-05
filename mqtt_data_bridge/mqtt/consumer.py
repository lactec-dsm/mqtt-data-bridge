"""
consumer.py

Consumer MQTT do projeto mqtt-data-bridge.

Responsável por:
- Conectar ao broker MQTT.
- Assinar os tópicos definidos em settings.MQTT_TOPIC_ROOT.
- Receber mensagens com payload JSON no formato canônico.
- Validar e transformar o payload para o modelo de banco (Medicao).
- Inserir as medições na base usando SQLAlchemy.

Neste momento, o foco é o esqueleto: estrutura do fluxo e pontos
de integração. Otimizações (batch, backpressure, etc.) vêm depois.
"""

import json
import time
from datetime import datetime, timezone
from typing import List

from paho.mqtt import client as mqtt

from mqtt_data_bridge.config.settings import settings
from mqtt_data_bridge.database.modelagem_banco import Medicao
from mqtt_data_bridge.core.schemas import MedicaoMensagem
from mqtt_data_bridge.database.repositorio import MedicaoRepositorio
from mqtt_data_bridge.utils.logger import get_logger

logger = get_logger(__name__)


class MedicaoBuffer:
    """
    Buffer simples para acumular medições antes de gravar no banco.

    - Acumula objetos Medicao (ORM).
    - Quando atinge BATCH_SIZE, dispara flush para o banco.
    """

    def __init__(self, batch_size: int, repositorio: MedicaoRepositorio):
        self.batch_size = batch_size
        self._buffer: List[Medicao] = []
        self.repositorio = repositorio

    def adicionar(self, medicao: Medicao):
        self._buffer.append(medicao)

    def tamanho(self) -> int:
        return len(self._buffer)

    def flush(self):
        """
        Envia o conteúdo do buffer para o banco, em uma transação.
        Após sucesso, limpa o buffer.
        """
        if not self._buffer:
            return

        delay = settings.DB_FLUSH_BACKOFF_BASE
        max_retries = settings.DB_FLUSH_MAX_RETRIES

        for attempt in range(1, max_retries + 1):
            try:
                gravadas = self.repositorio.salvar_em_batch(self._buffer)
                logger.info("Gravadas %s medições no banco.", gravadas)
                self._buffer.clear()
                return
            except Exception:
                if attempt >= max_retries:
                    logger.exception(
                        "Falha ao salvar medições após %s tentativas; buffer será mantido.",
                        attempt,
                    )
                    # Mantém o buffer para possível reprocessamento futuro.
                    return

                logger.warning(
                    "Erro ao salvar medições (tentativa %s/%s). Retentando em %.2fs.",
                    attempt,
                    max_retries,
                    delay,
                    exc_info=True,
                )
                time.sleep(delay)
                delay *= 2  # backoff exponencial

def converter_payload_para_medicoes(raw_payload: str) -> List[Medicao]:
    """
    Converte a string JSON recebida via MQTT em uma lista de objetos Medicao.

    Regras:
    - Espera um JSON representando uma lista de objetos.
    - Cada objeto deve seguir o schema MedicaoMensagem (Pydantic).
    - Campos inválidos geram log e são ignorados, não derrubam o consumer.
    - Em caso de JSON inválido ou formato não-lista, retorna lista vazia.
    """

    try:
        dados = json.loads(raw_payload)
    except json.JSONDecodeError as exc:
        logger.warning("Erro ao decodificar JSON: %s", exc)
        return []

    if not isinstance(dados, list):
        logger.warning("Payload inválido: esperado uma lista de medições.")
        return []

    medicoes: List[Medicao] = []

    for item in dados:
        try:
            # Validação e parsing via Pydantic (Pydantic v2)
            msg = MedicaoMensagem.model_validate(item)
        except Exception as exc:
            logger.warning("Payload inválido para MedicaoMensagem: %s", exc)
            continue

        # Converte epoch ms → datetime UTC
        ts = datetime.fromtimestamp(msg.timestamp / 1000.0, tz=timezone.utc)

        medicao = Medicao(
            device_id=msg.deviceId,
            measurement_id=msg.measurementId,
            measurement_index=msg.measurementIndex,
            timestamp=ts,
            value=msg.value,
            raw_payload=raw_payload if settings.SAVE_RAW_PAYLOAD else None,
        )

        medicoes.append(medicao)

    return medicoes

def on_message(client: mqtt.Client, userdata, msg: mqtt.MQTTMessage):
    """
    Callback chamada toda vez que uma mensagem é recebida.

    - Decodifica o payload.
    - Converte para objetos Medicao.
    - Adiciona ao buffer.
    - Faz flush se o tamanho do buffer atingir o BATCH_SIZE.
    """
    buffer: MedicaoBuffer = userdata["buffer"]

    try:
        payload_str = msg.payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        logger.warning("Erro ao decodificar payload como UTF-8: %s", exc)
        return

    logger.debug("Mensagem recebida em %s: %s", msg.topic, payload_str)

    medicoes = converter_payload_para_medicoes(payload_str)

    for medicao in medicoes:
        buffer.adicionar(medicao)

    if buffer.tamanho() >= settings.BATCH_SIZE:
        buffer.flush()


def _conectar_com_retries(client: mqtt.Client):
    """
    Tenta conectar ao broker com retries e backoff exponencial.
    """
    delay = settings.MQTT_CONNECT_BACKOFF_BASE
    max_retries = settings.MQTT_CONNECT_MAX_RETRIES

    for attempt in range(1, max_retries + 1):
        try:
            client.connect(
                settings.MQTT_BROKER_HOST,
                settings.MQTT_BROKER_PORT,
                keepalive=60,
            )
            return
        except Exception:
            if attempt >= max_retries:
                logger.exception(
                    "Falha ao conectar ao broker MQTT após %s tentativas.",
                    attempt,
                )
                raise

            logger.warning(
                "Erro ao conectar ao broker MQTT (tentativa %s/%s). Retentando em %.2fs.",
                attempt,
                max_retries,
                delay,
                exc_info=True,
            )
            time.sleep(delay)
            delay *= 2

def criar_cliente_mqtt(buffer: MedicaoBuffer) -> mqtt.Client:
    """
    Cria e configura o cliente MQTT para o consumer.

    - Define callbacks de conexão, desconexão e mensagem.
    - Configura userdata para carregar o buffer de medições.
    - Conecta ao broker com os parâmetros de settings.
    """

    client = mqtt.Client()

    def on_connect(client, userdata, flags, rc):
        logger.info("Conectado ao broker MQTT. RC=%s", rc)
        # Ao conectar, assinamos o root configurado
        topic_root = settings.MQTT_TOPIC_ROOT
        client.subscribe(topic_root)
        logger.info("Assinado tópico raiz: %s", topic_root)

    def on_disconnect(client, userdata, rc):
        logger.warning("Desconectado do broker MQTT. RC=%s", rc)

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message

    # Passamos o buffer via userdata para estar acessível na callback
    client.user_data_set({"buffer": buffer})

    # Conecta usando host/porta do settings
    _conectar_com_retries(client)

    return client

def run_consumer():
    """
    Função principal do consumer MQTT.

    Agora:
    - cria o repositório de Medicao;
    - cria o buffer vinculado a esse repositório;
    - cria o cliente MQTT e entra no loop.
    """

    repositorio = MedicaoRepositorio()
    buffer = MedicaoBuffer(
        batch_size=settings.BATCH_SIZE,
        repositorio=repositorio,
    )
    client = criar_cliente_mqtt(buffer)

    logger.info(
        "Iniciando consumer. Broker=%s:%s, Tópico raiz=%s, Batch size=%s",
        settings.MQTT_BROKER_HOST,
        settings.MQTT_BROKER_PORT,
        settings.MQTT_TOPIC_ROOT,
        settings.BATCH_SIZE,
    )

    try:
        client.loop_forever()
    except KeyboardInterrupt:
        logger.info("Encerrando consumer (Ctrl+C).")
    finally:
        client.disconnect()


if __name__ == "__main__":
    run_consumer()
