"""
Testes para a função converter_payload_para_medicoes.

Objetivo:
- Garantir que o JSON correto vira objetos Medicao corretos.
- Garantir que JSON inválido não derruba o fluxo (retorna lista vazia).
- Garantir que itens inválidos dentro de uma lista não impedem os válidos.
"""

import json
from datetime import datetime, timezone

from mqtt_data_bridge.mqtt.consumer import converter_payload_para_medicoes
from mqtt_data_bridge.database.modelagem_banco import Medicao

def test_converter_payload_medicao_unica_valida():
    # Arrange: payload com uma única medição válida
    payload = [
        {
            "timestamp": 1746085310003,
            "deviceId": "SMA-SIM-DEVICE-001",
            "measurementId": "pAcGrid",
            "measurementIndex": 1,
            "value": 123.45,
        }
    ]
    raw_payload = json.dumps(payload)

    # Act
    medicoes = converter_payload_para_medicoes(raw_payload)

    # Assert
    assert len(medicoes) == 1
    m = medicoes[0]
    assert isinstance(m, Medicao)
    assert m.device_id == "SMA-SIM-DEVICE-001"
    assert m.measurement_id == "pAcGrid"
    assert m.measurement_index == 1
    assert m.value == 123.45

    # Confere se o timestamp foi convertido para datetime com timezone UTC
    assert isinstance(m.timestamp, datetime)
    assert m.timestamp.tzinfo is not None
    # Epoch 1746085310003 ms → checamos só se é maior que 0 (evitar hardcode)
    assert m.timestamp.timestamp() > 0


def test_converter_payload_varias_medicoes_validas():
    payload = [
        {
            "timestamp": 1746085310003,
            "deviceId": "SMA-SIM-DEVICE-001",
            "measurementId": "pAcGrid",
            "measurementIndex": 1,
            "value": 100.0,
        },
        {
            "timestamp": 1746085310003,
            "deviceId": "SMA-SIM-DEVICE-001",
            "measurementId": "vAcGrid",
            "measurementIndex": 1,
            "value": 230.0,
        },
    ]
    raw_payload = json.dumps(payload)

    medicoes = converter_payload_para_medicoes(raw_payload)

    assert len(medicoes) == 2
    ids = {(m.measurement_id, m.value) for m in medicoes}
    assert ("pAcGrid", 100.0) in ids
    assert ("vAcGrid", 230.0) in ids

def test_converter_payload_json_invalido():
    raw_payload = "{não é um json válido}"

    medicoes = converter_payload_para_medicoes(raw_payload)

    # Deve apenas retornar lista vazia, sem levantar exceção
    assert medicoes == []

def test_converter_payload_nao_e_lista():
    # Um único objeto em vez de lista
    payload = {
        "timestamp": 1746085310003,
        "deviceId": "SMA-SIM-DEVICE-001",
        "measurementId": "pAcGrid",
        "measurementIndex": 1,
        "value": 123.45,
    }
    raw_payload = json.dumps(payload)

    medicoes = converter_payload_para_medicoes(raw_payload)

    assert medicoes == []

def test_converter_payload_com_itens_invalidos_na_lista():
    payload = [
        # Item inválido: sem measurementId
        {
            "timestamp": 1746085310003,
            "deviceId": "SMA-SIM-DEVICE-001",
            "measurementIndex": 1,
            "value": 123.45,
        },
        # Item válido
        {
            "timestamp": 1746085310003,
            "deviceId": "SMA-SIM-DEVICE-002",
            "measurementId": "pAcGrid",
            "measurementIndex": 1,
            "value": 200.0,
        },
    ]
    raw_payload = json.dumps(payload)

    medicoes = converter_payload_para_medicoes(raw_payload)

    # Esperado: apenas o item válido vira Medicao
    assert len(medicoes) == 1
    m = medicoes[0]
    assert m.device_id == "SMA-SIM-DEVICE-002"
    assert m.value == 200.0

def test_converter_payload_timestamp_zero():
    payload = [
        {
            "timestamp": 0,
            "deviceId": "SMA-SIM-DEVICE-001",
            "measurementId": "pAcGrid",
            "measurementIndex": 1,
            "value": 10.0,
        }
    ]
    raw_payload = json.dumps(payload)

    medicoes = converter_payload_para_medicoes(raw_payload)

    assert len(medicoes) == 1
    m = medicoes[0]
    assert isinstance(m.timestamp, datetime)
    # Epoch 0 em UTC:
    assert m.timestamp == datetime.fromtimestamp(0, tz=timezone.utc)
