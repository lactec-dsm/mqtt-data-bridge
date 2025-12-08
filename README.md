## mqtt-data-bridge

Sistema modular para coleta, ingestão e armazenamento de dados provenientes de dispositivos IoT via MQTT.

## Visão Geral

O **mqtt-data-bridge** conecta dispositivos (ou simuladores) a um banco de dados através de:

1. Publicação MQTT.
2. Consumer MQTT validando e transformando dados.
3. Persistência via SQLAlchemy
4. Repository Pattern para desacoplar armazenamento. 

Esse projeto pode servir como:

* Coletor MQTT real para sensores/IoT
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

O Projeto armazena as medições em uma tabela única normalizada:

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

Publica payloads canônicos em tópicos `<deviceId>/data`, permitindo testar toda a arquitetura sem depender de hardware real.

## Consumer MQTT

Recebe mensagens, valida, converte para ORM e grava no banco usando batch e repositório.

## Repositório (Repository Pattern)

Camada de acesso ao banco desacoplado do consumer

## API de Consulta

A API fornece endpoints para que dashboards e sistemas externos consultem:
* valores recentes
* histórico de grandeza
* últimos N pontos por dispositivo.
* Médias e agregações simples (futuro)

## Configuração Centralizada (settings.py)

Usa Pydantic v2 para carregar e validar configurações via .env.

## Testes Automatizados (pytest).

Testes Unitários para o repositório e conversor de payload. 

## 📦 Instalação e configuração rápida

1. Instalar dependências com poetry:
   ```bash
   poetry install
   ```
2. Criar o `.env`:
   ```bash
   cp .env.example .env
   ```
   Ajuste broker MQTT, `DB_URL`, nível de log etc.
3. Criar o banco e tabelas (Postgres padrão em `DB_URL`; se preferir SQLite, ajuste o `.env`):
   ```bash
   poetry run alembic upgrade head
   ```
4. Configurações úteis (em `.env`):
   - `LOG_LEVEL` (DEBUG/INFO/…)
   - `LOG_JSON` (True para logs em JSON)
   - `MQTT_CONNECT_MAX_RETRIES` / `MQTT_CONNECT_BACKOFF_BASE`
   - `MQTT_PUBLISH_MAX_RETRIES` / `MQTT_PUBLISH_BACKOFF_BASE`
   - `DB_FLUSH_MAX_RETRIES` / `DB_FLUSH_BACKOFF_BASE`

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

## Fluxo de execução

Abaixo o passo a passo recomendado para rodar todo pipeline. 

1. Executar o simulador MQTT
O simulador publica em intervalos configuráveis no .env

```bash
poetry run python -m mqtt_data_bridge.mqtt.simulator.publisher
```
Para Observar as mensagens no broker:

```bash
mosquitto_sub -h localhost -t "#" -v
```

2. Executar o Consumer MQTT

O Consumer: 
* conecta ao broker
* recebe payloads canônicos
* valida via Pydantic
* converte para ORM
* salva no banco via repositório.

Execute:

```bash
poetry run python -m mqtt_data_bridge.mqtt.consumer
```

Será exibido mensagens como:

```csharp
[CONSUMER] Recebido payload de SMA-SIM-DEVICE-001
[CONSUMER] Gravadas 5 medições no banco.
```

3. Verificar Banco
Modo SQLite CLI

```bash
sqlite3 mqtt_store.db
.tables
SELECT * FROM medicoes LIMIT 10;
```

3. Subir a API de leitura (FastAPI + Uvicorn)
   ```bash
   poetry run uvicorn mqtt_data_bridge.api.main:app --reload --host 0.0.0.0 --port 8000
   ```
   - Documentação interativa: http://localhost:8000/docs
   - Exemplos:
     - `curl http://localhost:8000/ping`
     - `curl "http://localhost:8000/medicoes/recentes?limite=10"`
     - `curl "http://localhost:8000/serie/pAcGrid?device_id=SMA-SIM-DEVICE-001&limite=50"`

4. Verificar Banco
Modo psql (Postgres) ou SQLite, dependendo do `DB_URL`.

Exemplo Postgres:
```bash
psql postgresql://mqtt_bridge:mqtt_bridge_pwd@localhost:5432/mqtt_bridge_db -c "SELECT * FROM medicoes LIMIT 10;"
```

5. Executar os testes
Os testes rodam usando um SQLite em memória, sem afetar o banco real. 

```bash
poetry run pytest
```

## Notas de logging

- Logs são centralizados (`mqtt_data_bridge.utils.logger`) e respeitam `LOG_LEVEL`.
- Para JSON estruturado, defina `LOG_JSON=true` no `.env`.
