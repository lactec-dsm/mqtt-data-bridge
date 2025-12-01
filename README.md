## mqtt-data-brigge 

Sistema modular para coleta, ingestão e armazenamento de dados provenientes de dispositivos IoT via MQTT.

## Visão Geral

O **mqtt-data-bridge** conecta dispositivos (ou simuladores) a um banco de dados através de:

1. Publicação MQTT.
2. Consumer MQTT validando e transformando dados.
3. Persistência via SQLAlchemy
4. Repository Pattern para desacoplar armazenamento. 

Esse projeto pode servir como:

* Coletor MQTT real oara sensores/IoT
* base para arquitetura de telemetria industrial
* pipeline de exemplo para aplicar engenharia de dados
* substituto moderno para scripts MQTT -> DB.

## Fluxo de Dados (Alto Nível)

```java
[Equipamento/Simulador MQTT] 
        → MQTT Broker 
                → Consumer MQTT (validação + ingestão)
                        → Banco de Dados (medições normalizadas)
                                → API (consulta)
                                        → Dashboards / Aplicações externas

```

## Desenho da Arquitetura

![Arquitetura do sistema](docs/images/arquitetura_fundo_branco.png "Arquitetura do sistema")

## Estrutura do projeto

A estrutura foi desenhada para separar responsabilidades e facilitar a evolução: 

```bash
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
```

## Modelo Canônico do Payload MQTT

Todas as mensagens que chegam ao sistema devem seguir o formato:

```json
[
  {
    "timestamp": 1746085310003,
    "deviceId": "SMA-1234567890",
    "measurementId": "pAcGrid",
    "measurementIndex": 1,
    "value": 123.45
  }
]

```

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

## 📦 Instalação

O Projeto foi construído usando o poetry, o Poetry oferece uma solução completa e integrada para o fluxo de trabalho de projetos Python, desde a configuração inicial até a distribuição final, a principal função é simplificar o processo de gerenciamento de dependências, empacotamento e publicação, e configuração simplificada. 

1. Criar o ambiente poetry:

```bash
poetry install
```

2. Criar o .env
```bash
cp .env.example .env
```
Edite o .env conforme necessário. 

4. Criar o banco e tabelas
```bash
poetry run python -m mqtt_data_bridge.database.modelagem_banco
```
Isso criará o arquivo mqtt_store.db (SQLite padrão).

## Testando o Broker MQTT

Usando Mosquitto:

Instalação
Ubuntu/WSL:

```bash
sudo apt install mosquitto mosquitto-clients
```

Testar assinatura
```bash
mosquitto_sub -h localhost -t "#" -v
```

