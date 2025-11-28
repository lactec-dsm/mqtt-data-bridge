## mqtt-data-brigge 

Sistema modular para coleta, ingestão e armazenamento de dados provenientes de dispositivos IoT via MQTT.

## Visão Geral

O **mqtt-data-bridge** é um software projetado para:

1. Receber mensagens MQTT de vários dispositivos de campo (por exemplo, Raspberry PI lendo ModBus).
2. Validar e normalizar o payload usando um modelo canônico estruturado.
3. Persistir os dados em um banco de dados relacional preparado para consultas analíticas.
4. Servir esse conteúdo para dashboards, aplicações e serviços de análise. 

## Fluxo de Dados (Alto Nível)

'''
[Equipamento/Simulador MQTT] 
        → MQTT Broker 
                → Consumer MQTT (validação + ingestão)
                        → Banco de Dados (medições normalizadas)
                                → API (consulta)
                                        → Dashboards / Aplicações externas

'''

## Estrutura do projeto

A estrutura foi desenhada para separar responsabilidades e facilitar a evolução: 

'''
mqtt-data-bridge/
│
├── mqtt_data_bridge/              # pacote principal
│   ├── config/                    # leitura de variáveis, settings centralizados
│   ├── core/                      # schemas e modelos canônicos (Pydantic)
│   ├── database/                  # SQLAlchemy: tabelas, engine, repositórios
│   ├── mqtt/                      # consumer MQTT e simuladores
│   ├── api/                       # API para dashboards (Flask/FastAPI)
│   └── utils/                     # logs, helpers
│
├── scripts/                       # scripts CLI para rodar módulos
├── tests/                         # testes unitários
└── docs/                          # documentação
'''

## Modelo Canônico do Payload MQTT

Todas as mensagens que chegam ao sistema devem seguir o formato:

'''
[
  {
    "timestamp": 1746085310003,
    "deviceId": "SMA-1234567890",
    "measurementId": "pAcGrid",
    "measurementIndex": 1,
    "value": 123.45
  }
]

'''

**Campos**

| Campo            | Tipo   | Descrição                                                   |
|------------------|--------|-------------------------------------------------------------|
| timestamp        | int    | Epoch em milissegundos (UTC)                                |
| deviceId         | string | Identificador único do equipamento                          |
| measurementId    | string | Nome da grandeza medida (ex: tensão, fase, potência)        |
| measurementIndex | int    | Índice da medição (ex: fase L1, L2, L3)                     |
| value            | float  | Valor medido                                                |


## Modelo de Banco (SQLAlchemy)

O Projeto armazenada as medições em uma tabela única normalizada:

* device_id
* measurement_id
* measurement_index
* timestamp
* value
* ingested_at
* raw_payload (opcional)

Esse design facilita agregações por:

* equipamento
* fase
* grandeza
* período
* janelas temporais deslizantes

## Simulador MQTT

Um conjunto de scripts gera dados sintéticos compatíveis com equipamentos reais.
Ele publica no broker MQTT o payload canônico definido acima.

Ideal para testes iniciais enquanto os dispositivos reais ainda não estão disponíveis. 

## Consumer MQTT

O Coletor MQTT:

1. Se inscreve em tópicos MQTT dos dispositivos.
2. Valida cada mensagem usando o schema pydantic.
3. Transforma o timestamp para datetime. 
4. Persiste a medição no banco via SQLAlchemy.

## API de Consulta

A API fornece endpoints para que dashboards e sistemas externos consultem:
* valores recentes
* histórico de grandeza
* últimos N pontos por dispositivo.
* Médias e agregações simmples (futuro)

