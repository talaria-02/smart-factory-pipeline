"""
센서 시뮬레이터 메인 실행 파일.
모든 설비의 센서 데이터를 1초마다 생성하여 콘솔에 출력합니다.

실행: python simulator/main.py
"""
import json
import time
import signal
import sys
from datetime import datetime
import paho.mqtt.client as mqtt

from config import MACHINES, SIMULATION_CONFIG
from machine import Machine


def main():
    print("=" * 60)
    print("🏭 Smart Factory Sensor Simulator")
    print(f"   설비 수: {len(MACHINES)}대")
    print(f"   데이터 생성 간격: {SIMULATION_CONFIG['interval_seconds']}초")
    print("=" * 60)
    print() #개요
    
    # 설비 인스턴스 생성
    machines = {}
    for machine_id, config in MACHINES.items():
        machines[machine_id] = Machine(machine_id, config)
        print(f"  ✅ {machine_id} ({config['type']}) 초기화 완료")
    
    print()
    print("▶ 데이터 생성 시작... (Ctrl+C로 중지)")
    print("-" * 60)
    
    # 종료 처리
    running = True
    def signal_handler(sig, frame):
        nonlocal running
        running = False
        print("\n\n⏹ 시뮬레이터 종료 중...")
    
    signal.signal(signal.SIGINT, signal_handler)
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.connect("localhost", 1883)

    # 메인 루프
    count = 0
    while running:
        count += 1
        
        for machine_id, machine in machines.items():
            data = machine.read_all_sensors()
            topic = f"factory/{machine_id}/sensors"
            client.publish(topic, json.dumps(data, ensure_ascii=False))

            # 콘솔 출력 (나중에 MQTT Publish로 교체)
            status_emoji = {
                "RUNNING": "🟢",
                "WARNING": "🟡",
                "ANOMALY": "🔴"
            }.get(data["status"], "⚪")
            
            print(f"[{data['timestamp'][:19]}] {status_emoji} {machine_id}: ", end="")
            
            # 센서 값 요약 출력
            sensor_summary = ", ".join(
                f"{k}={v}" for k, v in list(data["sensors"].items())[:3]
            )
            print(f"{sensor_summary} ...")
            
            # JSON 파일로도 저장 (디버깅 & 확인용)
            if count == 1:  # 첫 번째 데이터만 예쁘게 출력
                print(f"\n  📋 샘플 데이터 (전체 JSON):")
                print(f"  {json.dumps(data, indent=2, ensure_ascii=False)}")
                print()
        
        print()  # 설비 간 구분
        time.sleep(SIMULATION_CONFIG["interval_seconds"])
    
    print("✅ 시뮬레이터가 정상 종료되었습니다.")
    print(f"   총 {count}회 데이터 생성")


if __name__ == "__main__":
    main()
