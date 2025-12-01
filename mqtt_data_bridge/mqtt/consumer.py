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
from datetime import datetime, timezone
from typing import List

from paho.mqtt import client as mqtt

from mqtt_data_bridge.config.settings import settings
from mqtt_data_bridge.database.modelagem_banco import Medicao
from mqtt_data_bridge.core.schemas import MedicaoMensagem
from mqtt_data_bridge.database.repositorio import MedicaoRepositorio


class MedicaoBuffer:
    """
    Buffer simples para acumular medições antes de gravar no banco.

    - Acumula objetos Medicao (ORM).
    - Quando atinge BATCH_SIZE, dispara flush para o banco.
    """

    def __init__(self, batch_size: int):
        self.batch_size = batch_size
        self._buffer: List[Medicao] = []

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

        sessao = criar_sessao()
        try:
            sessao.add_all(self._buffer)
            sessao.commit()
            print(f"[CONSUMER] Gravadas {len(self._buffer)} medições no banco.")
            self._buffer.clear()
        except Exception as exc:
            sessao.rollback()
            print(f"[CONSUMER] Erro ao salvar medições: {exc}")
            # Aqui é possível logar melhor ou enviar para uma DLQ.
        finally:
            sessao.close()

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
        print(f"[CONSUMER] Erro ao decodificar JSON: {exc}")
        return []

    if not isinstance(dados, list):
        print("[CONSUMER] Payload inválido: esperado uma lista de medições.")
        return []

    medicoes: List[Medicao] = []

    for item in dados:
        try:
            # Validação e parsing via Pydantic (Pydantic v2)
            msg = MedicaoMensagem.model_validate(item)
        except Exception as exc:
            print(f"[CONSUMER] Payload inválido para MedicaoMensagem: {exc}")
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
        print(f"[CONSUMER] Erro ao decodificar payload como UTF-8: {exc}")
        return

    print(f"[CONSUMER] Mensagem recebida em {msg.topic}: {payload_str}")

    medicoes = converter_payload_para_medicoes(payload_str)

    for medicao in medicoes:
        buffer.adicionar(medicao)

    if buffer.tamanho() >= settings.BATCH_SIZE:
        buffer.flush()

def criar_cliente_mqtt(buffer: MedicaoBuffer) -> mqtt.Client:
    """
    Cria e configura o cliente MQTT para o consumer.

    - Define callbacks de conexão, desconexão e mensagem.
    - Configura userdata para carregar o buffer de medições.
    - Conecta ao broker com os parâmetros de settings.
    """

    client = mqtt.Client()

    def on_connect(client, userdata, flags, rc):
        print(f"[CONSUMER] Conectado ao broker MQTT. RC={rc}")
        # Ao conectar, assinamos o root configurado
        topic_root = settings.MQTT_TOPIC_ROOT
        client.subscribe(topic_root)
        print(f"[CONSUMER] Assinado tópico raiz: {topic_root}")

    def on_disconnect(client, userdata, rc):
        print(f"[CONSUMER] Desconectado do broker MQTT. RC={rc}")

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message

    # Passamos o buffer via userdata para estar acessível na callback
    client.user_data_set({"buffer": buffer})

    # Conecta usando host/porta do settings
    client.connect(settings.MQTT_BROKER_HOST, settings.MQTT_BROKER_PORT, keepalive=60)

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

    print(
        f"[CONSUMER] Iniciando consumer. "
        f"Broker={settings.MQTT_BROKER_HOST}:{settings.MQTT_BROKER_PORT}, "
        f"Tópico raiz={settings.MQTT_TOPIC_ROOT}, "
        f"Batch size={settings.BATCH_SIZE}"
    )

    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("[CONSUMER] Encerrando consumer (Ctrl+C).")
    finally:
        client.disconnect()


if __name__ == "__main__":
    run_consumer()
