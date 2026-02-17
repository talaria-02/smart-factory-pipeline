"""
개별 센서의 데이터를 생성하는 클래스.
정상 범위의 노이즈 + 간헐적 이상 패턴을 포함.
"""
import random
import math
from datetime import datetime


class Sensor:
    """단일 센서를 시뮬레이션합니다."""
    
    def __init__(self, name: str, config: dict):
        self.name = name
        self.unit = config["unit"]
        self.base = config["base"]
        self.noise = config["noise"]
        self.min_val = config["min"]
        self.max_val = config["max"]
        self.alert_threshold = config["alert"]
        
        # 이상 상태 관리
        self._anomaly_active = False
        self._anomaly_remaining = 0
        self._anomaly_severity = 1.0
        
        # 시간에 따른 미세 드리프트 (설비 노후화 시뮬레이션)
        self._drift = 0.0
        self._tick = 0
    
    def read(self) -> dict:
        """센서 값을 한 번 읽습니다."""
        self._tick += 1
        
        # 1. 기본값 + 미세 드리프트
        self._drift += random.gauss(0, 0.01)  # 아주 천천히 변화
        value = self.base + self._drift
        # 3. 약간의 주기성 (예: 낮/밤 온도 차이 시뮬레이션)
        cycle = math.sin(self._tick * 2 * math.pi / 3600) * (self.noise * 0.5)
        value += cycle
        
        # 4. 이상 패턴 적용
        is_anomaly = False
        if self._anomaly_active:
            value = self.base * self._anomaly_severity
            value += random.gauss(0, self.noise * 2)  # 이상 가우시안 노이즈 증가
            self._anomaly_remaining -= 1
            is_anomaly = True
            if self._anomaly_remaining <= 0:
                self._anomaly_active = False
        else:
            # 2. 정상 가우시안 노이즈 추가
            value += random.gauss(0, self.noise)
        # 5. 범위 제한
        value = max(self.min_val, min(self.max_val, value))
        
        return {
            "value": round(value, 2),
            "unit": self.unit,
            "is_anomaly": is_anomaly,
            "exceeds_alert": value > self.alert_threshold if self.alert_threshold > 0 else False
        }
    
    def inject_anomaly(self, duration: int, severity: float):
        """이상 패턴을 주입합니다."""
        self._anomaly_active = True
        self._anomaly_remaining = duration
        self._anomaly_severity = severity
