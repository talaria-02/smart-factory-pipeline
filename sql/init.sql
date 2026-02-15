-- sql/init.sql
-- PostgreSQL 컨테이너가 처음 시작될 때 자동 실행됩니다.

-- 스키마 생성
CREATE SCHEMA IF NOT EXISTS factory;

-- 간단한 테스트 테이블
CREATE TABLE factory.machines (
    machine_id VARCHAR(20) PRIMARY KEY,
    machine_type VARCHAR(50) NOT NULL,
    location VARCHAR(100),
    install_date DATE,
    status VARCHAR(20) DEFAULT 'ACTIVE'
);

-- 테스트 데이터 삽입
INSERT INTO factory.machines (machine_id, machine_type, location, install_date) VALUES
    ('CNC-001', 'CNC_LATHE', 'A동 1라인', '2023-03-15'),
    ('PRS-001', 'PRESS', 'A동 2라인', '2022-07-20'),
    ('CNV-001', 'CONVEYOR', 'B동 1라인', '2024-01-10'),
    ('CLR-001', 'COOLER', 'B동 유틸리티', '2023-11-05'),
    ('PWR-001', 'POWER_MONITOR', 'A동 전력실', '2022-01-01');

-- 확인용
SELECT '✅ 초기화 완료: ' || count(*) || '개 설비 등록됨' FROM factory.machines;
