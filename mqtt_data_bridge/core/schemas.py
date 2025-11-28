"""
schemas.py

Schemas Pydantic para validação do payload MQTT.
Compatível com Pydantic v2.
"""

from pydantic import BaseModel


class MedicaoMensagem(BaseModel):
    """
    Representa uma única medição recebida via MQTT.

    Compatível com o payload canônico:

        {
          "timestamp": 1746085310003,
          "deviceId": "SMA-SIM-DEVICE-001",
          "measurementId": "pAcGrid",
          "measurementIndex": 1,
          "value": 123.45
        }
    """

    timestamp: int
    deviceId: str
    measurementId: str
    measurementIndex: int
    value: float
