"""
하나의 설비를 나타내는 클래스.
여러 센서를 가지며, 전체 센서의 데이터를 한 번에 읽을 수 있습니다.
"""
import random
from datetime import datetime, timezone
from sensor import Sensor
from config import ANOMALY_CONFIG


class Machine:
    """공장 설비 한 대를 시뮬레이션합니다."""
    
    def __init__(self, machine_id: str, machine_config: dict):
        self.machine_id = machine_id
        self.machine_type = machine_config["type"]
        self.location = machine_config["location"]
        self.status = "RUNNING"
        
        # 센서 인스턴스 생성
        self.sensors = {}
        for sensor_name, sensor_config in machine_config["sensors"].items():
            self.sensors[sensor_name] = Sensor(sensor_name, sensor_config)
    
    def read_all_sensors(self) -> dict:
        """모든 센서값을 읽어 JSON 형태로 반환합니다."""
        
        # 확률적으로 이상 주입
        self._maybe_inject_anomaly()
        
        # 전체 센서 읽기
        sensor_data = {}
        has_anomaly = False
        has_alert = False
        
        for name, sensor in self.sensors.items():
            reading = sensor.read()
            sensor_data[name] = reading["value"]
            if reading["is_anomaly"]:
                has_anomaly = True
            if reading["exceeds_alert"]:
                has_alert = True
        
        # 상태 업데이트
        if has_alert:
            self.status = "WARNING"
        elif has_anomaly:
            self.status = "ANOMALY"
        else:
            self.status = "RUNNING"
        
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "machine_id": self.machine_id,
            "machine_type": self.machine_type,
            "location": self.location,
            "sensors": sensor_data,
            "status": self.status,
            "has_anomaly": has_anomaly,
            "has_alert": has_alert
        }
    
    def _maybe_inject_anomaly(self):
        """확률적으로 랜덤 센서에 이상을 주입합니다."""
        if random.random() < ANOMALY_CONFIG["probability"]:
            # 랜덤 센서 선택
            sensor = random.choice(list(self.sensors.values()))
            duration = random.randint(*ANOMALY_CONFIG["duration_range"])
            severity = random.uniform(*ANOMALY_CONFIG["severity_range"])
            sensor.inject_anomaly(duration, severity)
