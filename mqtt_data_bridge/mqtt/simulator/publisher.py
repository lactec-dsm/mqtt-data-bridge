"""
publisher.py

Simulador MQTT do projeto mqtt-data-bridge.

Responsável por:
- Criar um cliente MQTT.
- Simular dispositivos publicando medições em tópicos MQTT.
- Publicar mensagens no formato canônico definido pelo projeto.

Este módulo, por enquanto, implementa um esqueleto básico,
sem preocupação com ranges realistas de valores. A ideia é
garantir a estrutura e o fluxo, para depois refinarmos as regras
de geração de dados.
"""

import json
import time
import random
from typing import List

from paho.mqtt import client as mqtt

from mqtt_data_bridge.config.settings import settings
from mqtt_data_bridge.utils.logger import get_logger

logger = get_logger(__name__)

class MQTTDeviceSimulator:
    """
    Representa um dispositivo simulado que publica medições em um tópico MQTT.

    Cada instância desta classe:
    - possui um device_id próprio;
    - conhece a lista de measurementIds que deve simular;
    - usa o cliente MQTT compartilhado para publicar os dados.
    """

    def __init__(self, device_id: str, measurement_ids: List[str], client: mqtt.Client):
        self.device_id = device_id
        self.measurement_ids = measurement_ids
        self.client = client

        # Tópico no qual este dispositivo publicará.
        # Estamos seguindo o padrão:
        #   <deviceId>/data
        self.topic = f"{self.device_id}/data"

    def gerar_payload(self) -> List[dict]:
        """
        Gera um payload canônico com uma ou mais medições.

        Por enquanto, o esqueleto gera:
        - 1 medição por measurementId
        - measurementIndex fixo em 1

        Estrutura do payload:

        [
          {
            "timestamp": 1746085310003,
            "deviceId": "SMA-SIM-DEVICE-001",
            "measurementId": "pAcGrid",
            "measurementIndex": 1,
            "value": 123.45
          },
          ...
        ]
        """
        timestamp_ms = int(time.time() * 1000)

        medicoes = []
        for measurement_id in self.measurement_ids:
            # ESQUELETO: valor aleatório simples.
            # Depois podemos refinar para faixas por tipo de measurementId.
            valor = random.uniform(-1000.0, 1000.0)

            medicoes.append(
                {
                    "timestamp": timestamp_ms,
                    "deviceId": self.device_id,
                    "measurementId": measurement_id,
                    "measurementIndex": 1,  # por enquanto fixo
                    "value": valor,
                }
            )

        return medicoes

    def publicar(self):
        """
        Gera um payload e publica no broker MQTT usando o cliente fornecido.

        - Serializa a lista de medições como JSON (string).
        - Publica no tópico <deviceId>/data.
        """
        payload = self.gerar_payload()
        payload_str = json.dumps(payload)

        delay = settings.MQTT_PUBLISH_BACKOFF_BASE
        max_retries = settings.MQTT_PUBLISH_MAX_RETRIES

        for attempt in range(1, max_retries + 1):
            # Publicação MQTT (QoS 0 por enquanto, fire-and-forget)
            result = self.client.publish(self.topic, payload_str)

            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.debug("Publicado em %s: %s", self.topic, payload_str)
                return

            if attempt >= max_retries:
                logger.error(
                    "Falha ao publicar em %s após %s tentativas. RC=%s",
                    self.topic,
                    attempt,
                    result.rc,
                )
                return

            logger.warning(
                "Erro ao publicar em %s (tentativa %s/%s, RC=%s). Retentando em %.2fs.",
                self.topic,
                attempt,
                max_retries,
                result.rc,
                delay,
            )
            time.sleep(delay)
            delay *= 2


def _conectar_com_retries(client: mqtt.Client):
    """
    Tenta conectar ao broker MQTT com retries e backoff exponencial.
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
                    "Falha ao conectar simulador ao broker MQTT após %s tentativas.",
                    attempt,
                )
                raise

            logger.warning(
                "Erro ao conectar simulador ao broker MQTT (tentativa %s/%s). Retentando em %.2fs.",
                attempt,
                max_retries,
                delay,
                exc_info=True,
            )
            time.sleep(delay)
            delay *= 2


def criar_cliente_mqtt() -> mqtt.Client:
    """
    Cria e configura um cliente MQTT básico.

    Neste esqueleto:
    - usamos apenas host e porta do settings;
    - não configuramos usuário/senha/TLS;
    - registramos callbacks mínimos (log de conexão/desconexão).
    """

    client = mqtt.Client()

    def on_connect(client, userdata, flags, rc):
        logger.info("Simulador conectado ao broker MQTT. RC=%s", rc)

    def on_disconnect(client, userdata, rc):
        logger.warning("Simulador desconectado do broker MQTT. RC=%s", rc)

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect

    _conectar_com_retries(client)

    # Importante: inicia o loop de rede em background
    client.loop_start()

    return client


def criar_dispositivos_simulados(client: mqtt.Client) -> List[MQTTDeviceSimulator]:
    """
    Cria uma lista de dispositivos simulados com base nas configurações.

    - SIMULATOR_DEVICE_COUNT define quantos dispositivos teremos.
    - SIMULATOR_DEVICE_PREFIX define o prefixo do deviceId.
    - SIMULATOR_MEASUREMENT_IDS define as grandezas simuladas.
    """

    dispositivos = []

    for i in range(1, settings.SIMULATOR_DEVICE_COUNT + 1):
        device_id = f"{settings.SIMULATOR_DEVICE_PREFIX}-{i:03d}"

        simulador = MQTTDeviceSimulator(
            device_id=device_id,
            measurement_ids=settings.SIMULATOR_MEASUREMENT_IDS,
            client=client,
        )
        dispositivos.append(simulador)

    return dispositivos

def run_simulator():
    """
    Função principal do simulador MQTT.

    Fluxo:
    - cria cliente MQTT e conecta ao broker;
    - cria dispositivos simulados;
    - entra em um loop infinito, publicando mensagens
      a cada SIMULATOR_INTERVAL_SECONDS segundos.

    Em uma versão mais avançada, poderíamos:
    - usar sinais do sistema para encerrar;
    - rodar isso como serviço separado ou dentro de um scheduler.
    """

    client = criar_cliente_mqtt()
    dispositivos = criar_dispositivos_simulados(client)

    intervalo = settings.SIMULATOR_INTERVAL_SECONDS

    logger.info(
        "Iniciando simulador com %s dispositivos, %s measurementIds, intervalo %ss.",
        len(dispositivos),
        settings.SIMULATOR_MEASUREMENT_IDS,
        intervalo,
    )

    try:
        while True:
            for dispositivo in dispositivos:
                dispositivo.publicar()

            # Aguarda o intervalo definido antes da próxima rodada
            time.sleep(intervalo)

    except KeyboardInterrupt:
        logger.info("Encerrando simulador (Ctrl+C recebido).")
    finally:
        # Encerra o loop de rede MQTT de forma limpa
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    run_simulator()
