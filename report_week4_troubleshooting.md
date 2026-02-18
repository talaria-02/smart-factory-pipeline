# Week 4: Apache Kafka 통합 트러블슈팅 보고서

> **작성일**: 2026-02-19  
> **파이프라인**: Simulator → MQTT(Mosquitto) → Bridge → Kafka  
> **최종 상태**: ✅ 해결 완료

---

## 1. 개요

Smart Factory 센서 데이터 파이프라인에서 **Kafka 적재가 되지 않는 문제**를 진단하고 해결한 과정을 기록합니다.

### 파이프라인 구조
```
[main.py]           →  [Mosquitto MQTT]  →  [bridge.py]       →  [Kafka]
(센서 시뮬레이터)       (메시지 브로커)       (MQTT→Kafka 브릿지)    (데이터 적재)
  publish(factory/#)     port: 1883          subscribe(factory/#)    topic: sensor-raw
                                             produce(sensor-raw)     topic: sensor-alert
```

---

## 2. 발생 현상

| 구분                        | 상태          | 상세                                                |
| --------------------------- | ------------- | --------------------------------------------------- |
| `main.py` (Simulator)       | ✅ 정상        | MQTT로 센서 데이터 publish 성공                     |
| `subscriber.py` (MQTT 수신) | ✅ 정상        | MQTT 메시지 수신 확인됨                             |
| `bridge.py` (MQTT→Kafka)    | ⚠️ 표면상 정상 | 터미널에 `[→ Kafka]` 성공 메시지 출력               |
| `kafka-console-consumer`    | ❌ 실패        | **0 messages** — 데이터 없음                        |
| `test.py` Producer          | ✅ 성공        | Offset 반환됨                                       |
| `test.py` Consumer          | ❌ 실패        | **Group Coordinator Not Available** 에러, 무한 대기 |

---

## 3. 진단 과정

### 3-1. Docker 컨테이너 상태 확인

```powershell
docker ps -a --format "{{.Names}}|{{.Image}}|{{.Status}}"
```
- `factory-kafka` | `apache/kafka:3.7.0` | **Up** (실행 중)
- `factory-mosquitto` | `eclipse-mosquitto:2` | **Up** (실행 중)

→ 컨테이너 자체는 정상 실행 중.

### 3-2. Kafka 토픽 확인

```powershell
docker exec factory-kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9094 --list
```
```
sensor-alert
sensor-raw
```

→ 토픽은 존재함. 데이터가 들어가지만 Consumer가 읽지 못하는 상황.

### 3-3. `__consumer_offsets` 토픽 확인 (핵심 단서)

```powershell
docker exec factory-kafka /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server localhost:9094 --describe --topic __consumer_offsets
```
```
Error: Topic '__consumer_offsets' does not exist as expected
```

→ ❌ **`__consumer_offsets` 토픽이 존재하지 않음!**  
→ Consumer 그룹 관리의 핵심 토픽이 없어서 Consumer가 동작 불가.

### 3-4. Kafka 브로커 로그 분석

```powershell
docker logs factory-kafka --tail 50
```
```
[반복] INFO Sent auto-creation request for Set(__consumer_offsets) to the active controller.
[반복] INFO Sent auto-creation request for Set(__consumer_offsets) to the active controller.
[반복] INFO Sent auto-creation request for Set(__consumer_offsets) to the active controller.
...
```

→ `__consumer_offsets` **자동 생성 요청이 매 100ms마다 무한 반복**되고 있음.  
→ Controller가 요청을 받지만 실제 생성을 완료하지 못하는 상태.

### 3-5. docker-compose.yml 검증

```powershell
docker compose ps
```
```
validating ... services.services must be a mapping
```

→ ❌ **YAML 구조 자체에 에러가 있음.**

---

## 4. 원인 분석

### 근본 원인: docker-compose.yml에 5가지 설정 오류

#### 원인 ①: YAML 구조 오류 — `services:` 키 중복

```yaml
# ❌ 수정 전 (26번 줄)
  mosquitto:
    ...
    restart: unless-stopped
  services:          # ← 이 줄이 문제! services 키가 중복됨
  kafka:
    image: apache/kafka:3.7.0
```

`services:` 가 최상위에 이미 있는데, 내부에서 다시 `services:` 키를 사용하여 **kafka 서비스가 최상위 services 블록에 포함되지 않음**.

#### 원인 ②: `KAFKA_NODE_ID`와 `KAFKA_CONTROLLER_QUORUM_VOTERS` 불일치

```yaml
# ❌ 수정 전
KAFKA_CONTROLLER_QUORUM_VOTERS: "0@localhost:9091"  # voter id=0, port=9091
KAFKA_NODE_ID: "1"                                   # broker id=1
```

NODE_ID는 `1`인데 QUORUM_VOTERS는 `0`번 노드를 가리키고 있어서 **Controller가 자기 자신을 찾지 못함**.

#### 원인 ③: CONTROLLER 리스너 미설정

KRaft 모드에서는 Controller 전용 리스너가 필수이지만, 기존 설정에는 PLAINTEXT 하나만 있었음:

```yaml
# ❌ 수정 전
KAFKA_LISTENERS: PLAINTEXT://0.0.0.0:9094
```

#### 원인 ④: 리스너 보안 프로토콜 맵 미설정

`KAFKA_LISTENER_SECURITY_PROTOCOL_MAP`, `KAFKA_CONTROLLER_LISTENER_NAMES`, `KAFKA_INTER_BROKER_LISTENER_NAME` 등 KRaft 필수 설정 누락.

#### 원인 ⑤: Replication Factor 미설정

단일 브로커 환경에서 `__consumer_offsets`의 기본 replication factor가 3이므로, 가용 브로커 수(1)보다 커서 생성 실패.

### 인과 관계 흐름도

```
[docker-compose.yml 설정 오류]
    │
    ├─→ QUORUM_VOTERS 불일치 → Controller ID 불일치
    ├─→ CONTROLLER 리스너 누락 → Controller 통신 불가
    ├─→ Replication Factor 기본값(3) > 브로커 수(1)
    │
    └─→ __consumer_offsets 토픽 생성 실패
            │
            └─→ Group Coordinator 사용 불가
                    │
                    └─→ Consumer 무한 대기 / 데이터 수신 실패
```

---

## 5. 해결 방법

### 5-1. docker-compose.yml 수정

```yaml
# ✅ 수정 후
services:
  postgres:
    # ... (기존과 동일)
  mosquitto:
    # ... (기존과 동일)
  kafka:
    image: apache/kafka:3.7.0
    container_name: factory-kafka
    environment:
      KAFKA_NODE_ID: "1"
      KAFKA_PROCESS_ROLES: "broker,controller"
      KAFKA_CONTROLLER_QUORUM_VOTERS: "1@localhost:9093"
      KAFKA_LISTENERS: "PLAINTEXT://0.0.0.0:9092,EXTERNAL://0.0.0.0:9094,CONTROLLER://0.0.0.0:9093"
      KAFKA_ADVERTISED_LISTENERS: "PLAINTEXT://kafka:9092,EXTERNAL://localhost:9094"
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: "CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT,EXTERNAL:PLAINTEXT"
      KAFKA_CONTROLLER_LISTENER_NAMES: "CONTROLLER"
      KAFKA_INTER_BROKER_LISTENER_NAME: "PLAINTEXT"
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
      KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR: 1
      KAFKA_TRANSACTION_STATE_LOG_MIN_ISR: 1
    ports:
      - "9094:9094"
    volumes:
      - kafka_data:/var/lib/kafka/data
    restart: unless-stopped
```

**주요 변경 사항:**

| 항목                               | 수정 전                      | 수정 후                                    | 이유                 |
| ---------------------------------- | ---------------------------- | ------------------------------------------ | -------------------- |
| `services:` 중복                   | 26번 줄에 중복 존재          | 제거                                       | YAML 구조 오류 해결  |
| `QUORUM_VOTERS`                    | `0@localhost:9091`           | `1@localhost:9093`                         | NODE_ID=1과 일치시킴 |
| `LISTENERS`                        | `PLAINTEXT://0.0.0.0:9094`   | 3개 분리 (PLAINTEXT, EXTERNAL, CONTROLLER) | KRaft 필수           |
| `ADVERTISED_LISTENERS`             | `PLAINTEXT://localhost:9094` | 내부/외부 분리                             | 내부용/외부접속 구분 |
| `OFFSETS_TOPIC_REPLICATION_FACTOR` | 미설정 (기본 3)              | `1`                                        | 단일 브로커 환경     |
| `container_name`                   | 미설정                       | `factory-kafka`                            | 컨테이너 식별 용이   |
| `volumes`                          | 미설정                       | `kafka_data:/var/lib/kafka/data`           | 데이터 영속성        |

### 5-2. Kafka 컨테이너 재시작 (볼륨 초기화)

기존 볼륨에 손상된 메타데이터가 남아있을 수 있으므로 깨끗하게 재시작:

```powershell
docker stop factory-kafka
docker rm factory-kafka
docker volume rm smart-factory-pipeline_kafka_data
docker compose up -d kafka
```

---

## 6. 해결 확인

### 6-1. `__consumer_offsets` 토픽 생성 확인

Kafka 브로커 로그에서 50개 파티션 모두 정상 로딩 확인:
```
[GroupMetadataManager brokerId=1] Finished loading offsets and group metadata from __consumer_offsets-0
[GroupMetadataManager brokerId=1] Finished loading offsets and group metadata from __consumer_offsets-1
... (50개 파티션 모두 성공)
```

### 6-2. test.py 실행 결과

```
🔍 Kafka 연결 테스트 시작...
1️⃣ Producer 연결 시도 (['127.0.0.1:9094'])...
✅ 데이터 전송 성공! (Offset: 0)
2️⃣ Consumer 연결 시도 (['127.0.0.1:9094'])...
   📩 수신: {'machine_id': 'TEST-MK-001', 'status': 'CHECK', 'timestamp': 1771429235.98}
✅ 데이터 수신 성공! (1건)
🏁 테스트 종료
```

→ **Producer ✅ / Consumer ✅ 모두 성공!**

### 6-3. 실제 파이프라인 확인

```powershell
# sensor-raw 토픽 데이터 확인
docker exec factory-kafka /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9094 --topic sensor-raw --from-beginning --max-messages 5
```

```json
{"machine_id": "TEST-MK-001", "status": "CHECK", "timestamp": 1771429235.98}
{"timestamp": "2026-02-18T15:42:27", "machine_id": "CNC-001", "machine_type": "CNC_LATHE", "status": "RUNNING", ...}
{"timestamp": "2026-02-18T15:42:27", "machine_id": "PRS-001", "machine_type": "PRESS", "status": "RUNNING", ...}
{"timestamp": "2026-02-18T15:42:27", "machine_id": "CNV-001", "machine_type": "CONVEYOR", "status": "WARNING", ...}
{"timestamp": "2026-02-18T15:42:27", "machine_id": "CLR-001", "machine_type": "COOLER", "status": "WARNING", ...}
Processed a total of 5 messages
```

→ **5대 설비(CNC, PRESS, CONVEYOR, COOLER, POWER_MONITOR)의 센서 데이터가 Kafka에 정상 적재!**

### 6-4. sensor-alert 토픽 확인

WARNING/ANOMALY 상태 데이터도 `sensor-alert` 토픽에 정상 분기:

```powershell
docker exec factory-kafka /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9094 --topic sensor-alert --from-beginning
```

→ **WARNING, ANOMALY 상태 데이터 수신 확인 ✅**

---

## 7. 유용한 확인 명령어 모음

```powershell
# 토픽 목록 확인
docker exec factory-kafka /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server localhost:9094 --list

# 특정 토픽 상세 정보
docker exec factory-kafka /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server localhost:9094 --describe --topic sensor-raw

# 실시간 데이터 모니터링 (Ctrl+C로 종료)
docker exec factory-kafka /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9094 --topic sensor-raw

# 처음부터 N개 메시지만 확인
docker exec factory-kafka /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9094 --topic sensor-raw --from-beginning --max-messages 5

# 토픽별 메시지 개수(오프셋) 확인
docker exec factory-kafka /opt/kafka/bin/kafka-run-class.sh \
  kafka.tools.GetOffsetShell --broker-list localhost:9094 --topic sensor-raw
```

---

## 8. 배운 점

1. **KRaft 모드 Kafka는 설정이 까다롭다**: Zookeeper 모드와 달리 `CONTROLLER_QUORUM_VOTERS`, `CONTROLLER_LISTENER_NAMES` 등 추가 설정이 필수.
2. **YAML 구조 검증 습관**: `docker compose config`로 사전에 YAML 유효성을 검증하면 구조적 실수를 조기에 발견할 수 있다.
3. **`__consumer_offsets`의 중요성**: Consumer 그룹 관리의 핵심 토픽이며, 이 토픽이 없으면 Producer는 성공해도 Consumer는 동작하지 않는다.
4. **단일 브로커 환경의 함정**: `offsets.topic.replication.factor` 기본값이 3이므로, 단일 브로커에서는 반드시 1로 설정해야 한다.
5. **에러 로그의 부재도 단서다**: `bridge.py`가 에러 없이 동작하는데 Consumer가 안 되면, 브로커 내부 문제를 의심해야 한다.

---

## 9. 향후 계획

- [ ] Python Consumer 스크립트 작성 (Kafka → 데이터 처리)
- [ ] PostgreSQL DB 적재 파이프라인 구축
- [ ] 데이터 모니터링 대시보드 구축
