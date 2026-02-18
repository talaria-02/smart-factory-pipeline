import time
from kafka import KafkaProducer, KafkaConsumer
import json

TOPIC = 'sensor-raw'
BOOTSTRAP_SERVERS = ['127.0.0.1:9094']  # Windows 외부 접속용

print("🔍 Kafka 연결 테스트 시작...")

# 1. Producer 테스트
try:
    print(f"1️⃣ Producer 연결 시도 ({BOOTSTRAP_SERVERS})...")
    producer = KafkaProducer(
        bootstrap_servers=BOOTSTRAP_SERVERS,
        value_serializer=lambda x: json.dumps(x).encode('utf-8'),
        api_version=(2, 5, 0)
    )
    
    test_msg = {"machine_id": "TEST-MK-001", "status": "CHECK", "timestamp": time.time()}
    future = producer.send(TOPIC, value=test_msg)
    result = future.get(timeout=10) # 10초 대기
    print(f"✅ 데이터 전송 성공! (Offset: {result.offset})")
    producer.flush()
    producer.close()
except Exception as e:
    print(f"❌ Producer 실패: {e}")
    exit(1)

import logging

# 로깅 설정 (DEBUG 레벨로 자세히 출력)
logging.basicConfig(level=logging.DEBUG)

print(f"2️⃣ Consumer 연결 시도 ({BOOTSTRAP_SERVERS})...")
try:
    consumer = KafkaConsumer(
        TOPIC,
        bootstrap_servers=BOOTSTRAP_SERVERS,
        auto_offset_reset='earliest', # 처음부터 읽기
        enable_auto_commit=True,
        group_id='checker-group-v1',
        value_deserializer=lambda x: json.loads(x.decode('utf-8')),
        consumer_timeout_ms=5000, # 5초 동안 데이터 없으면 종료
        api_version=(2, 5, 0),
        session_timeout_ms=6000, # 세션 타임아웃 6초 (request_timeout_ms보다 작아야 함)
        request_timeout_ms=10000, # 요청 타임아웃 10초
        connections_max_idle_ms=20000 # 유휴 연결 타임아웃 20초 (request_timeout_ms보다 커야 함)
    )
    
    print("   👉 Consumer 인스턴스 생성 완료. 데이터 폴링 시작...")
    
    # 파티션 할당 확인
    print(f"   👉 할당된 파티션: {consumer.assignment()}")
    
    msgs = []
    # poll() 메서드로 직접 데이터 가져오기 시도 (무한 대기 방지)
    raw_msgs = consumer.poll(timeout_ms=5000)
    
    if not raw_msgs:
        print("   ⚠️ poll() 결과 데이터 없음.")
    else:
        for tp, messages in raw_msgs.items():
            for msg in messages:
                print(f"   📩 수신: {msg.value}")
                msgs.append(msg)
                break # 1개만 받고 종료
            if msgs: break

    if len(msgs) > 0:
        print(f"✅ 데이터 수신 성공! ({len(msgs)}건)")
    else:
        print("❌ 데이터 수신 실패 (타임아웃 또는 데이터 없음)")
        
    consumer.close()

except Exception as e:
    print(f"❌ Consumer 실패 (예외 발생): {e}")
    import traceback
    traceback.print_exc()

print("🏁 테스트 종료")