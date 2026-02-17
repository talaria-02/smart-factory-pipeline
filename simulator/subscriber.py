"""
MQTT Subscriber - 센서 데이터 수신기

main.py(Publisher)가 MQTT 브로커로 보낸 데이터를
이 스크립트(Subscriber)가 받아서 화면에 출력합니다.

흐름: main.py → MQTT 브로커(Mosquitto) → subscriber.py
"""
import json
import paho.mqtt.client as mqtt


# ============================================================
# 콜백 함수들 (이벤트가 발생하면 paho가 "자동으로" 호출해줌)
# 우리가 직접 호출하는 게 아님!
# ============================================================

def on_connect(client, userdata, flags, rc, properties):
    """
    브로커에 연결 성공하면 자동 호출되는 함수.
    
    매개변수 (paho가 자동으로 넣어줌, signal_handler의 sig, frame과 같은 원리):
      - client:     mqtt.Client 인스턴스 (자기 자신)
      - userdata:   사용자 정의 데이터 (거의 안 씀)
      - flags:      브로커 응답 플래그
      - rc:         연결 결과 코드 (0이면 성공)
      - properties: MQTT v5 속성
    
    여기서 subscribe하는 이유:
      연결이 끊겼다 재연결되면 on_connect가 다시 호출됨
      → subscribe도 다시 실행됨 → 구독이 유지됨!
      connect() 직후에 subscribe하면 재연결 시 구독이 사라짐
    """
    print("MQTT 연결 성공!")
    client.subscribe("factory/#")
    # "factory/#" 의미:
    #   factory/CNC-001/sensors  ← 매칭 ✅
    #   factory/PRS-001/sensors  ← 매칭 ✅
    #   factory/아무거나/뭐든지  ← 매칭 ✅
    #   other/topic              ← 매칭 ❌
    #   # = 와일드카드 (하위 모든 토픽)


def on_message(client, userdata, msg):
    """
    메시지가 도착하면 자동 호출되는 함수.
    main.py가 publish할 때마다 이 함수가 실행됨.
    
    매개변수:
      - client:   mqtt.Client 인스턴스
      - userdata: 사용자 정의 데이터
      - msg:      수신된 메시지 객체
                  - msg.topic:   토픽 (예: "factory/CNC-001/sensors")
                  - msg.payload: 메시지 내용 (bytes → json.loads로 딕셔너리 변환)
    """
    data = json.loads(msg.payload)
    print(f"[{msg.topic}] {data['machine_id']} - {data['status']}")


# ============================================================
# 실행 코드 (위에서 아래로 순서대로 실행)
# ============================================================

# 1. 클라이언트 생성
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

# 2. "이 이벤트가 발생하면 이 함수를 실행해라" 등록 (아직 실행 안 됨!)
#    signal.signal(signal.SIGINT, signal_handler)와 같은 원리
client.on_connect = on_connect   # 연결되면 → on_connect 실행
client.on_message = on_message   # 메시지 오면 → on_message 실행

# 3. 브로커에 연결 요청 (Docker의 Mosquitto, 포트 1883)
client.connect("localhost", 1883)

# 4. 시작 알림
print("MQTT Subscriber 시작! 대기 중...")

# 5. 무한 대기 루프 (메시지가 올 때마다 on_message 자동 호출)
#    main.py의 while 루프와 비슷하지만, paho가 알아서 관리해줌
#    Ctrl+C로 종료
client.loop_forever()