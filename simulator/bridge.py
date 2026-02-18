import json
import paho.mqtt.client as mqtt
from kafka import KafkaProducer

# ① Kafka Producer 생성
producer = KafkaProducer(
    bootstrap_servers=['127.0.0.1:9094'],
    value_serializer=lambda x: json.dumps(x).encode('utf-8'),
    api_version=(2, 5, 0)
)

# ② MQTT 연결 시
def on_connect(client, userdata, flags, rc, properties):
    print("MQTT 연결 성공!")
    client.subscribe("factory/#")

# ③ MQTT 메시지 수신 시 → Kafka로 전달
def on_message(client, userdata, msg):
    data = json.loads(msg.payload)
    
    try:
        future = producer.send('sensor-raw', value=data)
        result = future.get(timeout=5)  # 결과를 기다림 (에러 시 바로 표시)
        
        if data["status"] in ["WARNING","ANOMALY"]:
            producer.send('sensor-alert', value=data).get(timeout=5)
        
        print(f"[→ Kafka] {data['machine_id']} - {data['status']}")
    except Exception as e:
        print(f"[ERROR] Kafka 전송 실패: {e}")

# ④ MQTT 클라이언트 (subscriber.py와 동일)
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.on_message = on_message
client.connect("localhost", 1883)

print("MQTT-Kafka Bridge 시작!")
client.loop_forever()