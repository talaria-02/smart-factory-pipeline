"""
공장 설비 및 센서 구성 정보.
실제 공장의 설비 사양을 참고하여 현실적인 범위로 설정.
"""

# 설비 정의
MACHINES = {
    "CNC-001": {
        "type": "CNC_LATHE",
        "location": "A동 1라인",
        "sensors": {
            "spindle_temp":     {"unit": "°C",  "base": 45.0, "noise": 2.0, "min": 20, "max": 120, "alert": 80},
            "vibration_x":      {"unit": "mm/s", "base": 0.8,  "noise": 0.15, "min": 0,  "max": 10,  "alert": 3.0},
            "vibration_y":      {"unit": "mm/s", "base": 0.9,  "noise": 0.15, "min": 0,  "max": 10,  "alert": 3.0},
            "spindle_rpm":      {"unit": "RPM",  "base": 3200, "noise": 50,   "min": 0,  "max": 5000,"alert": 4500},
            "power_consumption":{"unit": "kW",   "base": 12.5, "noise": 1.0,  "min": 0,  "max": 30,  "alert": 25},
            "coolant_temp":     {"unit": "°C",  "base": 22.0, "noise": 1.0, "min": 10, "max": 40,  "alert": 35},
        }
    },
    "PRS-001": {
        "type": "PRESS",
        "location": "A동 2라인",
        "sensors": {
            "hydraulic_pressure": {"unit": "bar", "base": 150, "noise": 5, "min": 0, "max": 300, "alert": 250},
            "oil_temp":           {"unit": "°C", "base": 55,  "noise": 3, "min": 20, "max": 100, "alert": 85},
            "vibration":          {"unit": "mm/s","base": 1.2, "noise": 0.2, "min": 0, "max": 15, "alert": 5.0},
            "cycle_count":        {"unit": "회",  "base": 0,   "noise": 0,  "min": 0, "max": 999999, "alert": -1},
            "power_consumption":  {"unit": "kW",  "base": 18,  "noise": 2, "min": 0, "max": 50, "alert": 40},
        }
    },
    "CNV-001": {
        "type": "CONVEYOR",
        "location": "B동 1라인",
        "sensors": {
            "belt_speed":       {"unit": "m/min", "base": 30, "noise": 1, "min": 0, "max": 60, "alert": 50},
            "motor_temp":       {"unit": "°C",   "base": 40, "noise": 2, "min": 15, "max": 90, "alert": 75},
            "motor_current":    {"unit": "A",    "base": 8,  "noise": 0.5, "min": 0, "max": 20, "alert": 15},
            "vibration":        {"unit": "mm/s", "base": 0.5, "noise": 0.1, "min": 0, "max": 8, "alert": 3.0},
        }
    },
    "CLR-001": {
        "type": "COOLER",
        "location": "B동 유틸리티",
        "sensors": {
            "inlet_temp":       {"unit": "°C", "base": 30, "noise": 1.5, "min": 5, "max": 50, "alert": 40},
            "outlet_temp":      {"unit": "°C", "base": 12, "noise": 1.0, "min": 0, "max": 30, "alert": 20},
            "compressor_pressure":{"unit":"bar","base": 8,  "noise": 0.3, "min": 0, "max": 15, "alert": 12},
            "refrigerant_level": {"unit": "%",  "base": 85, "noise": 2, "min": 0, "max": 100, "alert": 30},
            "power_consumption":{"unit": "kW",  "base": 5.5, "noise": 0.5, "min": 0, "max": 15, "alert": 12},
        }
    },
    "PWR-001": {
        "type": "POWER_MONITOR",
        "location": "A동 전력실",
        "sensors": {
            "total_power":    {"unit": "kW",  "base": 150, "noise": 10, "min": 0, "max": 500, "alert": 400},
            "power_factor":   {"unit": "",    "base": 0.92, "noise": 0.02, "min": 0, "max": 1, "alert": 0.8},
            "voltage_r":      {"unit": "V",   "base": 380, "noise": 3, "min": 340, "max": 420, "alert": 400},
            "voltage_s":      {"unit": "V",   "base": 380, "noise": 3, "min": 340, "max": 420, "alert": 400},
            "voltage_t":      {"unit": "V",   "base": 380, "noise": 3, "min": 340, "max": 420, "alert": 400},
            "frequency":      {"unit": "Hz",  "base": 60,  "noise": 0.1, "min": 59, "max": 61, "alert": 60.5},
        }
    }
}

# 이상 패턴 설정
ANOMALY_CONFIG = {
    "probability": 0.02,        # 매 초 2% 확률로 이상 발생
    "duration_range": (10, 60), # 이상 지속 시간: 10~60초
    "severity_range": (1.5, 4.0) # 정상 대비 1.5~4배 값 변동
}

# 시뮬레이션 설정
SIMULATION_CONFIG = {
    "interval_seconds": 1.0,    # 데이터 생성 간격
    "output_format": "json",    # json 또는 csv
}
