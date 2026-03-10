"""MES 더미 데이터 시딩 — 정상 상태의 FAB 데이터."""

from __future__ import annotations

import logging
import random
from datetime import datetime, timedelta

from simulator.sqlite_backend import get_conn

logger = logging.getLogger(__name__)

LINES = ["LINE01", "LINE02", "LINE03", "LINE04"]
ZONES = ["ZONE-A", "ZONE-B", "ZONE-C", "ZONE-D"]
PROCESSES = ["TFT", "CELL", "MODULE"]
STEPS = {
    "TFT": [("TFT-01", "세정"), ("TFT-02", "증착"), ("TFT-03", "포토"), ("TFT-04", "식각"), ("TFT-05", "검사")],
    "CELL": [("CELL-01", "배향"), ("CELL-02", "합착"), ("CELL-03", "절단"), ("CELL-04", "검사")],
    "MODULE": [("MOD-01", "편광판"), ("MOD-02", "구동IC"), ("MOD-03", "조립"), ("MOD-04", "최종검사")],
}
PRODUCTS = ["PROD-A", "PROD-B", "PROD-C"]


def seed_all() -> None:
    """정상 상태 FAB 데이터 시딩."""
    logger.info("Seeding MES dummy data...")
    conn = get_conn()

    _seed_conveyors(conn)
    _seed_vehicles(conn)
    _seed_wip(conn)
    _seed_equipment(conn)
    _seed_lots(conn)
    _seed_transfer_logs(conn)
    _seed_wip_snapshots(conn)
    _seed_equipment_history(conn)
    _seed_sample_rules(conn)

    conn.commit()
    logger.info("MES dummy data seeded successfully")


def _seed_conveyors(conn):
    """컨베이어: 정상 부하율 40~70%."""
    for line in LINES:
        for zone in ZONES:
            cap = random.randint(80, 120)
            load_pct = random.uniform(0.4, 0.7)
            conn.execute(
                "INSERT OR REPLACE INTO mes_conveyor_status (zone_id, line_id, carrier_count, capacity) VALUES (?, ?, ?, ?)",
                (f"{line}-{zone}", line, int(cap * load_pct), cap),
            )


def _seed_vehicles(conn):
    """AGV/OHT: 대부분 RUN 또는 IDLE."""
    statuses = ["RUN"] * 6 + ["IDLE"] * 3 + ["CHARGING"]
    for i in range(20):
        vtype = "AGV" if i < 12 else "OHT"
        conn.execute(
            "INSERT OR REPLACE INTO mes_vehicle_status (vehicle_id, vehicle_type, status) VALUES (?, ?, ?)",
            (f"{vtype}-{i+1:03d}", vtype, random.choice(statuses)),
        )


def _seed_wip(conn):
    """WIP: 목표 대비 80~110% 정상 범위."""
    for proc, steps in STEPS.items():
        for step_id, step_name in steps:
            target = random.randint(80, 150)
            current = int(target * random.uniform(0.8, 1.1))
            conn.execute(
                "INSERT OR REPLACE INTO mes_wip_summary (process, step_id, step_name, current_wip, target_wip) VALUES (?, ?, ?, ?, ?)",
                (proc, step_id, step_name, current, target),
            )
            conn.execute(
                "INSERT OR REPLACE INTO mes_queue_status (step_id, step_name, queue_count, avg_wait_min, max_wait_min) VALUES (?, ?, ?, ?, ?)",
                (step_id, step_name, random.randint(2, 15), random.uniform(5, 30), random.uniform(30, 60)),
            )

    # WIP 흐름 (최근 4시간, 유입=유출 밸런스)
    now = datetime.now()
    for proc, steps in STEPS.items():
        for step_id, _ in steps:
            for h in range(4):
                t = (now - timedelta(hours=h)).isoformat()
                qty = random.randint(5, 20)
                conn.execute(
                    "INSERT INTO mes_wip_flow (process, step_id, direction, qty, flow_time) VALUES (?, ?, 'IN', ?, ?)",
                    (proc, step_id, qty, t),
                )
                conn.execute(
                    "INSERT INTO mes_wip_flow (process, step_id, direction, qty, flow_time) VALUES (?, ?, 'OUT', ?, ?)",
                    (proc, step_id, qty + random.randint(-3, 3), t),
                )


def _seed_equipment(conn):
    """설비: 대부분 RUN, 일부 IDLE."""
    eq_id = 1
    for line in LINES:
        for proc, steps in STEPS.items():
            for step_id, step_name in steps:
                status = random.choices(["RUN", "IDLE", "RUN", "RUN"], k=1)[0]
                eid = f"EQ-{eq_id:03d}"
                conn.execute(
                    "INSERT OR REPLACE INTO mes_equipment_status (equipment_id, equipment_name, line_id, process, status, current_recipe) VALUES (?, ?, ?, ?, ?, ?)",
                    (eid, f"{step_name} 설비", line, proc, status, f"RECIPE-{proc}-{random.randint(1,5):02d}"),
                )
                eq_id += 1

    # PM 일정 (미래)
    now = datetime.now()
    for i in range(5):
        eid = f"EQ-{random.randint(1, eq_id-1):03d}"
        conn.execute(
            "INSERT INTO mes_pm_schedule (equipment_id, equipment_name, line_id, pm_type, scheduled_date, status) VALUES (?, ?, ?, ?, ?, 'PENDING')",
            (eid, "설비", random.choice(LINES), random.choice(["DAILY", "WEEKLY", "MONTHLY"]),
             (now + timedelta(days=random.randint(1, 7))).strftime("%Y-%m-%d")),
        )


def _seed_lots(conn):
    """LOT: 정상 체류 시간 (1~8시간)."""
    now = datetime.now()
    for i in range(50):
        proc = random.choice(PROCESSES)
        step_id, step_name = random.choice(STEPS[proc])
        hours_in = random.uniform(1, 8)
        conn.execute(
            "INSERT OR REPLACE INTO mes_lot_status (lot_id, product_id, current_step, step_name, step_in_time, hold_flag) VALUES (?, ?, ?, ?, ?, 0)",
            (f"LOT-{i+1:04d}", random.choice(PRODUCTS), step_id, step_name,
             (now - timedelta(hours=hours_in)).isoformat()),
        )


def _seed_transfer_logs(conn):
    """반송 로그: 최근 2시간, 정상 반송 시간 30~90초."""
    now = datetime.now()
    for i in range(200):
        line = random.choice(LINES)
        from_zone = f"{line}-{random.choice(ZONES)}"
        to_zone = f"{line}-{random.choice(ZONES)}"
        t = (now - timedelta(minutes=random.randint(0, 120))).isoformat()
        conn.execute(
            "INSERT INTO mes_transfer_log (carrier_id, from_zone, to_zone, line_id, transfer_time, transfer_time_sec, status) VALUES (?, ?, ?, ?, ?, ?, 'COMPLETED')",
            (f"CR-{random.randint(1,500):04d}", from_zone, to_zone, line, t, random.uniform(30, 90)),
        )


def _seed_wip_snapshots(conn):
    """WIP 스냅샷: 최근 24시간 시간별."""
    now = datetime.now()
    for proc in PROCESSES:
        base_wip = {"TFT": 400, "CELL": 300, "MODULE": 200}[proc]
        for h in range(24):
            t = (now - timedelta(hours=h)).replace(minute=0, second=0).isoformat()
            wip = base_wip + random.randint(-30, 30)
            conn.execute(
                "INSERT INTO mes_wip_snapshot (snapshot_time, process, wip_count) VALUES (?, ?, ?)",
                (t, proc, wip),
            )


def _seed_equipment_history(conn):
    """설비 이력: 최근 12시간, 대부분 RUN."""
    now = datetime.now()
    conn_db = conn
    cursor = conn_db.execute("SELECT equipment_id, equipment_name, line_id FROM mes_equipment_status")
    equips = cursor.fetchall()
    for eq in equips:
        for h in range(12):
            t = (now - timedelta(hours=h)).isoformat()
            status = random.choices(["RUN", "IDLE", "RUN", "RUN", "RUN"], k=1)[0]
            dur = random.uniform(40, 60)
            conn_db.execute(
                "INSERT INTO mes_equipment_history (equipment_id, equipment_name, line_id, status, duration_min, event_time) VALUES (?, ?, ?, ?, ?, ?)",
                (eq[0], eq[1], eq[2], status, dur, t),
            )



def _seed_sample_rules(conn):
    """샘플 감지 규칙 5개."""
    rules = [
        {
            "name": "컨베이어 부하율 과부하",
            "category": "logistics",
            "sub": "conveyor",
            "sql": "SELECT zone_id, line_id, carrier_count, capacity, ROUND(CAST(carrier_count AS REAL) / NULLIF(capacity, 0) * 100, 1) AS load_pct FROM mes_conveyor_status ORDER BY load_pct DESC LIMIT 1",
            "type": "threshold",
            "op": ">",
            "warn": 85,
            "crit": 95,
            "llm": 1,
            "prompt": "컨베이어 부하율이 높습니다. 해당 존의 반송 이력과 병목 여부를 확인하세요.",
        },
        {
            "name": "설비 비계획정지 발생",
            "category": "equipment",
            "sub": "unscheduled_down",
            "sql": "SELECT COUNT(*) AS down_count FROM mes_down_history WHERE down_type = 'UNSCHEDULED' AND start_time >= datetime('now', 'localtime', '-1 hour')",
            "type": "threshold",
            "op": ">",
            "warn": 0,
            "crit": 2,
            "llm": 1,
            "prompt": "비계획정지가 발생했습니다. 해당 설비의 알람 이력과 관련 WIP 영향을 확인하세요.",
        },
        {
            "name": "WIP 목표 초과",
            "category": "wip",
            "sub": "level",
            "sql": "SELECT process, step_id, step_name, current_wip, target_wip, ROUND(CAST(current_wip AS REAL) / NULLIF(target_wip, 0) * 100, 1) AS wip_ratio_pct FROM mes_wip_summary ORDER BY wip_ratio_pct DESC LIMIT 1",
            "type": "threshold",
            "op": ">",
            "warn": 130,
            "crit": 160,
            "llm": 1,
            "prompt": "WIP가 목표를 크게 초과했습니다. 흐름 밸런스와 설비 상태를 확인하세요.",
        },
        {
            "name": "에이징 LOT 발생",
            "category": "wip",
            "sub": "aging",
            "sql": "SELECT COUNT(*) AS aging_count FROM mes_lot_status WHERE (julianday('now', 'localtime') - julianday(step_in_time)) * 24 > 24",
            "type": "threshold",
            "op": ">",
            "warn": 3,
            "crit": 10,
            "llm": 0,
            "prompt": "",
        },
        {
            "name": "AGV 가동률 저하",
            "category": "logistics",
            "sub": "vehicle",
            "sql": "SELECT ROUND(CAST(SUM(CASE WHEN status = 'ERROR' THEN 1 ELSE 0 END) AS REAL) / NULLIF(COUNT(*), 0) * 100, 1) AS error_pct FROM mes_vehicle_status WHERE vehicle_type = 'AGV'",
            "type": "threshold",
            "op": ">",
            "warn": 15,
            "crit": 30,
            "llm": 0,
            "prompt": "",
        },
    ]

    for r in rules:
        conn.execute(
            """INSERT INTO detection_rules
               (rule_name, category, subcategory, query_template, check_type, threshold_op,
                warning_value, critical_value, llm_enabled, llm_prompt, enabled)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
            (r["name"], r["category"], r["sub"], r["sql"], r["type"], r["op"],
             r["warn"], r["crit"], r["llm"], r["prompt"]),
        )
    logger.info("Seeded %d sample rules", len(rules))
