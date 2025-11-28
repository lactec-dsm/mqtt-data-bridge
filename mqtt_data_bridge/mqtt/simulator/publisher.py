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

        # Publicação MQTT (QoS 0 por enquanto, fire-and-forget)
        result = self.client.publish(self.topic, payload_str)

        # Opcional: checar o resultado da publicação
        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            # Aqui poderíamos logar ou tomar alguma ação.
            # Como é esqueleto, apenas deixamos o código para referência.
            print(
                f"[SIMULADOR] Falha ao publicar em {self.topic}. "
                f"RC={result.rc}"
            )
        else:
            print(f"[SIMULADOR] Publicado em {self.topic}: {payload_str}")


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
        print(f"[SIMULADOR] Conectado ao broker MQTT com código RC={rc}")

    def on_disconnect(client, userdata, rc):
        print(f"[SIMULADOR] Desconectado do broker MQTT. RC={rc}")

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect

    client.connect(settings.MQTT_BROKER_HOST, settings.MQTT_BROKER_PORT, keepalive=60)

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

    print(
        f"[SIMULADOR] Iniciando simulador com "
        f"{len(dispositivos)} dispositivos, "
        f"{settings.SIMULATOR_MEASUREMENT_IDS} measurementIds, "
        f"intervalo de {intervalo}s."
    )

    try:
        while True:
            for dispositivo in dispositivos:
                dispositivo.publicar()

            # Aguarda o intervalo definido antes da próxima rodada
            time.sleep(intervalo)

    except KeyboardInterrupt:
        print("[SIMULADOR] Encerrando simulador (Ctrl+C recebido).")
    finally:
        # Encerra o loop de rede MQTT de forma limpa
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    run_simulator()
