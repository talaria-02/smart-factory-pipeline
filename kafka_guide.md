# Kafka 총정리 가이드

> Smart Factory 프로젝트에서 사용하는 Kafka 개념을 처음부터 정리한 문서입니다.

---

## 1. Kafka란?

**대용량 데이터를 실시간으로 전달하는 메시지 시스템**입니다.

```
일반 택배 시스템에 비유:

[보내는 사람]  →  [물류 센터]  →  [받는 사람]
 (Producer)      (Broker)       (Consumer)
                    │
              여러 선반에 보관
              (Topic/Partition)
```

우리 프로젝트에서는:
```
[bridge.py]  →  [Kafka Broker]  →  [나중에 만들 Consumer]
 Producer         물류 센터            데이터 처리/DB 적재
```

---

## 2. 핵심 용어

### 2-1. Broker (브로커)

Kafka 서버 1대를 브로커라고 부릅니다. 물류 센터의 **창고 1동**에 해당합니다.

```
우리 환경: 브로커 1대 (factory-kafka 컨테이너)
실제 운영: 보통 3~5대 이상 (장애 대비)
```

### 2-2. Topic (토픽)

메시지를 **주제별로 분류**하는 폴더입니다.

```
우리 프로젝트의 토픽:
├── sensor-raw     ← 모든 센서 데이터
└── sensor-alert   ← WARNING/ANOMALY만
```

### 2-3. Partition (파티션)

토픽을 **쪼개서 병렬 처리**할 수 있게 하는 단위입니다.

```
sensor-raw 토픽 (파티션 1개):
  [msg0] [msg1] [msg2] [msg3] [msg4] ...
   ↑ offset=0          ↑ offset=3

실제 운영 시 파티션을 늘리면:
  파티션0: [CNC-001 데이터] [CNC-001] [CNC-001] ...
  파티션1: [PRS-001 데이터] [PRS-001] [PRS-001] ...
  파티션2: [CNV-001 데이터] [CNV-001] [CNV-001] ...
  → 3개 Consumer가 동시에 처리 가능!
```

### 2-4. Offset (오프셋)

파티션 내 메시지의 **순번**입니다. 0부터 시작하며 절대 줄어들지 않습니다.

```
파티션0: [msg0] [msg1] [msg2] [msg3] [msg4]
          ↑                    ↑       ↑
        offset=0           offset=3  offset=4 (최신)

Consumer A: "나는 offset=3까지 읽었어"
→ 다음에 접속하면 offset=4부터 읽기 시작
→ 이 "어디까지 읽었는지" 기록이 __consumer_offsets 토픽에 저장됨
```

### 2-5. Producer / Consumer

```
Producer (생산자): 메시지를 토픽에 보내는 쪽
  → 우리 프로젝트: bridge.py

Consumer (소비자): 토픽에서 메시지를 읽는 쪽
  → 우리 프로젝트: test.py (테스트용), 나중에 DB 적재 스크립트
```

### 2-6. Consumer Group (컨슈머 그룹)

여러 Consumer가 **팀을 이루어** 하나의 토픽을 나눠서 읽는 것입니다.

```
토픽: sensor-raw (파티션 3개)

Consumer Group "db-loader":
  Consumer A → 파티션0 담당
  Consumer B → 파티션1 담당
  Consumer C → 파티션2 담당
  → 3배 빠르게 처리!

Consumer Group "monitoring":
  Consumer D → 파티션0,1,2 전부 읽음 (혼자)
  → 별도로 모니터링 용도

두 그룹은 서로 독립! 같은 데이터를 각자 읽을 수 있음.
```

---

## 3. Kafka 운영 모드: Zookeeper vs KRaft

### 옛날 방식: Zookeeper 모드

```
[Zookeeper]  ←→  [Kafka Broker 1]
  (관리자)    ←→  [Kafka Broker 2]
              ←→  [Kafka Broker 3]

Zookeeper가 하는 일:
  - "브로커 1번이 살아있나?" 감시
  - "sensor-raw 토픽의 리더는 브로커 2번이야" 관리
  - 브로커 목록, 토픽 메타데이터 저장
```

**문제점**: Kafka를 쓰려면 Zookeeper도 따로 설치·운영해야 해서 복잡했음.

### 현재 방식: KRaft 모드 (우리가 사용)

```
[Kafka Broker 1] ← Controller 역할 겸임!
[Kafka Broker 2]
[Kafka Broker 3]

Zookeeper 없이 Kafka끼리 알아서 관리.
```

**KRaft = Kafka Raft**의 줄임말. Raft는 "여러 서버가 합의하는 알고리즘"입니다.

우리 환경에서는 **브로커 1대가 broker와 controller를 동시에** 수행합니다:
```yaml
KAFKA_PROCESS_ROLES: "broker,controller"  # 두 역할 모두 수행
```

---

## 4. docker-compose.yml 설정 상세 해설

우리 프로젝트의 Kafka 설정을 한 줄씩 설명합니다.

### 4-1. 노드 식별 설정

```yaml
KAFKA_NODE_ID: "1"
```

이 브로커의 **고유 번호**입니다. 사람의 주민등록번호 같은 것.
브로커가 여러 대면 각각 `1`, `2`, `3` 등 다른 번호를 줍니다.

```yaml
KAFKA_PROCESS_ROLES: "broker,controller"
```

이 노드가 **어떤 역할**을 하는지 지정합니다.

| 역할         | 하는 일                          |
| ------------ | -------------------------------- |
| `broker`     | 메시지 저장/전달 (물류 창고)     |
| `controller` | 클러스터 관리/조율 (관리 사무실) |

우리는 1대뿐이니까 두 역할을 **혼자 다 함**.

```yaml
KAFKA_CONTROLLER_QUORUM_VOTERS: "1@localhost:9093"
```

**"투표에 참여하는 Controller 목록"**입니다.

```
형식: {노드ID}@{주소}:{포트}

"1@localhost:9093"의 의미:
  → 노드 1번이 localhost:9093에서 Controller로 참여한다

여러 대일 경우:
  → "1@broker1:9093,2@broker2:9093,3@broker3:9093"
```

> **⚠️ 원인 ②가 이것이었습니다:**
> ```yaml
> # ❌ 수정 전
> KAFKA_NODE_ID: "1"                           # 내 번호: 1
> KAFKA_CONTROLLER_QUORUM_VOTERS: "0@localhost:9091"  # 0번이 투표자
> ```
> "내 번호는 1번인데 투표자는 0번" → Kafka: "나는 투표자가 아니네??" → Controller 동작 불가

### 4-2. 리스너 설정 (가장 헷갈리는 부분!)

**리스너 = "어떤 포트에서 어떤 방식으로 연결을 받을지"** 설정입니다.

카페에 비유하면:
```
카페 (Kafka Broker)
├── 정문 (PLAINTEXT:9092)      ← 내부 직원 전용 (브로커끼리 통신)
├── 배달 창구 (EXTERNAL:9094)   ← 외부 손님용 (Python 클라이언트)
└── 사무실 (CONTROLLER:9093)   ← 매니저 전용 (Controller 통신)
```

#### KAFKA_LISTENERS

```yaml
KAFKA_LISTENERS: "PLAINTEXT://0.0.0.0:9092,EXTERNAL://0.0.0.0:9094,CONTROLLER://0.0.0.0:9093"
```

**"이 브로커가 어떤 포트에서 연결을 기다릴지"** — 서버 입장의 설정입니다.

```
PLAINTEXT://0.0.0.0:9092    → 9092 포트에서 내부 통신 대기
EXTERNAL://0.0.0.0:9094     → 9094 포트에서 외부 통신 대기
CONTROLLER://0.0.0.0:9093   → 9093 포트에서 Controller 통신 대기

0.0.0.0 = "모든 네트워크 인터페이스에서 받겠다"
```

> **⚠️ 원인 ③이 이것이었습니다:**
> ```yaml
> # ❌ 수정 전
> KAFKA_LISTENERS: PLAINTEXT://0.0.0.0:9094   # 하나뿐!
> ```
> CONTROLLER 리스너가 없으니 KRaft Controller가 통신할 포트가 없음 → 관리 기능 마비

#### KAFKA_ADVERTISED_LISTENERS

```yaml
KAFKA_ADVERTISED_LISTENERS: "PLAINTEXT://kafka:9092,EXTERNAL://localhost:9094"
```

**"클라이언트에게 알려줄 접속 주소"** — 클라이언트 입장의 주소입니다.

```
왜 LISTENERS와 따로 필요한가?

Docker 컨테이너 내부에서:
  서버는 0.0.0.0:9094에서 대기 (모든 IP)

하지만 클라이언트가 접속할 때:
  - 컨테이너 내부 → "kafka:9092"로 접속 (Docker 네트워크 이름)
  - Windows에서   → "localhost:9094"로 접속 (포트포워딩)

[Python bridge.py] --(localhost:9094)-→ [Docker] --(0.0.0.0:9094)-→ [Kafka]
  (Windows)           외부 접속            포트포워딩           실제 서버
```

> **💡 참고**: CONTROLLER는 `advertised_listeners`에 넣지 않습니다.
> Controller 통신은 브로커 내부에서만 일어나니까 외부에 알려줄 필요 없음.

#### KAFKA_LISTENER_SECURITY_PROTOCOL_MAP

```yaml
KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: "CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT,EXTERNAL:PLAINTEXT"
```

**"각 리스너 이름에 어떤 보안 프로토콜을 쓸지"** 매핑입니다.

```
CONTROLLER → PLAINTEXT (암호화 없음)
PLAINTEXT  → PLAINTEXT (암호화 없음)
EXTERNAL   → PLAINTEXT (암호화 없음)

실제 운영에서는:
EXTERNAL → SSL (암호화 통신)
INTERNAL → SASL_PLAINTEXT (인증 + 평문)
등으로 보안 설정 가능
```

> **⚠️ 원인 ④가 이것이었습니다:**
> 이 설정이 없으면 Kafka가 "EXTERNAL", "CONTROLLER"라는 리스너 이름을
> 어떤 프로토콜로 처리해야 하는지 몰라서 에러 발생

#### KAFKA_CONTROLLER_LISTENER_NAMES

```yaml
KAFKA_CONTROLLER_LISTENER_NAMES: "CONTROLLER"
```

**"위 리스너 중 어느 것이 Controller용인지"** 지정합니다.

```
리스너가 3개 있는데 (PLAINTEXT, EXTERNAL, CONTROLLER)
→ "CONTROLLER라는 이름의 리스너가 Controller 전용이야"
→ 이걸 안 적으면 Kafka가 어느 포트로 Controller 통신을 해야 할지 모름
```

#### KAFKA_INTER_BROKER_LISTENER_NAME

```yaml
KAFKA_INTER_BROKER_LISTENER_NAME: "PLAINTEXT"
```

**"브로커끼리 통신할 때 어떤 리스너를 쓸지"** 지정합니다.

```
브로커가 여러 대일 때:
  Broker1 ←(PLAINTEXT:9092)→ Broker2
  이 통신에 PLAINTEXT 리스너를 사용하겠다는 뜻

우리는 1대뿐이지만, 이 설정이 없으면 Kafka가 기본값으로
잘못된 리스너를 선택할 수 있음
```

### 4-3. Replication Factor 설정

```yaml
KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR: 1
KAFKA_TRANSACTION_STATE_LOG_MIN_ISR: 1
```

#### Replication Factor (복제 계수)란?

**"같은 데이터를 몇 개의 브로커에 복사할지"** 설정입니다.

```
Replication Factor = 3일 때 (기본값):

  Broker1: [sensor-raw 파티션0] ← Leader (원본)
  Broker2: [sensor-raw 파티션0] ← Follower (복사본1)
  Broker3: [sensor-raw 파티션0] ← Follower (복사본2)

  → Broker1이 죽어도 Broker2가 대신 서비스 (고가용성!)
```

```
Replication Factor = 1일 때 (우리 환경):

  Broker1: [sensor-raw 파티션0] ← 원본이자 유일한 복사본

  → Broker1이 죽으면 데이터 손실 (학습용이니 OK)
```

> **⚠️ 원인 ⑤가 이것이었습니다:**
> ```
> __consumer_offsets 기본 replication factor = 3
> 우리 브로커 = 1대
>
> Kafka: "3개 복사본을 만들어야 하는데 브로커가 1대뿐이야..."
>       → 생성 포기 → __consumer_offsets 없음 → Consumer 동작 불가
> ```

각 설정의 의미:

| 설정                                       | 대상                  | 의미                           |
| ------------------------------------------ | --------------------- | ------------------------------ |
| `OFFSETS_TOPIC_REPLICATION_FACTOR`         | `__consumer_offsets`  | Consumer 오프셋 정보의 복제 수 |
| `TRANSACTION_STATE_LOG_REPLICATION_FACTOR` | `__transaction_state` | 트랜잭션 상태의 복제 수        |
| `TRANSACTION_STATE_LOG_MIN_ISR`            | `__transaction_state` | 최소 동기화 복제본 수          |

---

## 5. 전체 구조 한눈에 보기

```
┌─────────────── Docker Container: factory-kafka ───────────────┐
│                                                                │
│  /opt/kafka/bin/  (프로그램)                                    │
│  ├── kafka-topics.sh                                           │
│  ├── kafka-console-consumer.sh                                 │
│  └── ...                                                       │
│                                                                │
│  /var/lib/kafka/data/  (데이터) ← kafka_data 볼륨에 연결됨      │
│  ├── sensor-raw-0/                                             │
│  ├── sensor-alert-0/                                           │
│  ├── __consumer_offsets-0~49/                                  │
│  └── __cluster_metadata-0/                                     │
│                                                                │
│  포트 수신 (LISTENERS):                                        │
│  ├── :9092 (PLAINTEXT) ← 브로커 간 통신                        │
│  ├── :9093 (CONTROLLER) ← KRaft Controller 통신                │
│  └── :9094 (EXTERNAL) ← 외부 클라이언트 접속 ──────────────────┼──→ Windows
│                                                                │
│  역할 (PROCESS_ROLES):                                         │
│  ├── Broker: 메시지 저장/전달                                   │
│  └── Controller: 클러스터 관리 (KRaft)                          │
│                                                                │
└────────────────────────────────────────────────────────────────┘
         ↑                              ↑
    docker-compose.yml              docker-compose.yml
    ports: "9094:9094"              volumes: kafka_data:
    (호스트:컨테이너)                  /var/lib/kafka/data
```

---

## 6. 데이터 흐름 요약 (우리 프로젝트)

```
① main.py (센서 시뮬레이터)
   → MQTT publish("factory/CNC-001/sensors", 데이터)
   
② Mosquitto (MQTT 브로커, :1883)
   → 메시지 전달
   
③ bridge.py (MQTT→Kafka 브릿지)
   → MQTT subscribe("factory/#")로 수신
   → KafkaProducer.send("sensor-raw", 데이터)
   → WARNING/ANOMALY면 추가로 send("sensor-alert", 데이터)
   
④ Kafka Broker (:9094)
   → sensor-raw 파티션0에 저장 (offset 증가)
   → sensor-alert 파티션0에 저장 (해당 시)
   
⑤ Consumer (아직 미구현)
   → KafkaConsumer("sensor-raw")로 읽기
   → PostgreSQL에 적재 예정
```

---

## 7. 자주 쓰는 명령어 정리

```powershell
# 토픽 목록 보기
docker exec factory-kafka /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server localhost:9094 --list

# 토픽 상세 정보 (파티션, 리더, 복제본 확인)
docker exec factory-kafka /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server localhost:9094 --describe --topic sensor-raw

# 실시간 메시지 모니터링 (Ctrl+C로 종료)
docker exec factory-kafka /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9094 --topic sensor-raw

# 처음부터 N건만 읽기
docker exec factory-kafka /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9094 --topic sensor-raw \
  --from-beginning --max-messages 5

# 토픽 수동 생성 (파티션 3개, 복제 1)
docker exec factory-kafka /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server localhost:9094 \
  --create --topic my-topic --partitions 3 --replication-factor 1

# Consumer 그룹 목록
docker exec factory-kafka /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server localhost:9094 --list

# Consumer 그룹 상세 (어디까지 읽었는지, 밀린 양)
docker exec factory-kafka /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server localhost:9094 --describe --group checker-group-v1
```
