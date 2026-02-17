"""
센서 시뮬레이터 실시간 시각화.
matplotlib로 센서 데이터를 실시간 그래프로 표시합니다.

실행: python simulator/visualize.py
"""
import warnings
warnings.filterwarnings("ignore", category=UserWarning)

import matplotlib.pyplot as plt
import matplotlib.animation as animation
from collections import deque

from config import MACHINES
from machine import Machine

# === 설정 ===
HISTORY_SIZE = 120      # 최근 120초(2분) 데이터 보여줌
TARGET_MACHINE = "CNC-001"  # 시각화할 설비
UPDATE_INTERVAL = 1000  # 1초마다 업데이트 (ms)

# 보고 싶은 센서 (최대 4개 추천)
TARGET_SENSORS = ["spindle_temp", "vibration_x", "spindle_rpm", "power_consumption"]


def main():
    # 설비 생성
    machine_config = MACHINES[TARGET_MACHINE]
    machine = Machine(TARGET_MACHINE, machine_config)

    # 데이터 저장소 (센서별 deque)
    history = {}
    alert_lines = {}
    for sensor_name in TARGET_SENSORS:
        history[sensor_name] = deque(maxlen=HISTORY_SIZE)
        alert_lines[sensor_name] = machine_config["sensors"][sensor_name]["alert"]

    time_ticks = deque(maxlen=HISTORY_SIZE)

    # === 그래프 설정 ===
    plt.style.use('dark_background')
    fig, axes = plt.subplots(len(TARGET_SENSORS), 1, figsize=(12, 8), sharex=True)
    fig.suptitle(f"[LIVE] {TARGET_MACHINE} ({machine_config['type']}) - Sensor Monitor",
                 fontsize=14, fontweight='bold', color='#00ff88')

    # 센서별 색상
    colors = ['#00ccff', '#ff6b6b', '#ffd93d', '#6bff6b']

    # 라인 객체 생성
    lines = {}
    for i, sensor_name in enumerate(TARGET_SENSORS):
        ax = axes[i]
        unit = machine_config["sensors"][sensor_name]["unit"]
        line, = ax.plot([], [], color=colors[i], linewidth=1.5, label=sensor_name)
        lines[sensor_name] = line

        # 경고 기준선
        alert_val = alert_lines[sensor_name]
        if alert_val > 0:
            ax.axhline(y=alert_val, color='red', linestyle='--', alpha=0.5, label=f'Alert: {alert_val}')

        ax.set_ylabel(f"{sensor_name}\n({unit})", fontsize=9, color=colors[i])
        ax.legend(loc='upper left', fontsize=8)
        ax.grid(True, alpha=0.2)
        ax.tick_params(colors='#888888')

    axes[-1].set_xlabel("Time (sec)", fontsize=10)

    # 상태 텍스트
    status_text = fig.text(0.95, 0.95, "", fontsize=12, ha='right', va='top',
                           fontweight='bold', fontfamily='monospace')

    # === 애니메이션 업데이트 함수 ===
    tick = [0]

    def update(frame):
        tick[0] += 1
        time_ticks.append(tick[0])

        # 센서 데이터 읽기
        data = machine.read_all_sensors()

        # 상태 업데이트
        status_map = {
            "RUNNING": ("[NORMAL]", "#00ff88"),
            "WARNING": ("[WARNING]", "#ffd93d"),
            "ANOMALY": ("[ANOMALY!]", "#ff4444")
        }
        status_label, status_color = status_map.get(data["status"], ("[UNKNOWN]", "white"))
        status_text.set_text(status_label)
        status_text.set_color(status_color)

        # 데이터 추가 & 그래프 업데이트
        for sensor_name in TARGET_SENSORS:
            value = data["sensors"][sensor_name]
            history[sensor_name].append(value)

            x_data = list(time_ticks)
            y_data = list(history[sensor_name])
            lines[sensor_name].set_data(x_data, y_data)

            # 축 범위 자동 조정
            ax = axes[TARGET_SENSORS.index(sensor_name)]
            ax.set_xlim(max(0, tick[0] - HISTORY_SIZE), tick[0] + 5)
            if y_data:
                y_min, y_max = min(y_data), max(y_data)
                margin = (y_max - y_min) * 0.2 or 1
                ax.set_ylim(y_min - margin, y_max + margin)

        return list(lines.values()) + [status_text]

    # === 애니메이션 시작 ===
    ani = animation.FuncAnimation(fig, update, interval=UPDATE_INTERVAL,
                                  blit=False, cache_frame_data=False)

    plt.tight_layout()
    plt.subplots_adjust(top=0.92)
    print(f"[LIVE] {TARGET_MACHINE} monitoring started! (Close window to stop)")
    plt.show()


if __name__ == "__main__":
    main()
