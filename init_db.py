"""DB 초기화 — 테이블 생성 + 정상 데이터 시딩 + 규칙 동기화.

실행: python init_db.py [--db simulator.db] [--reset]
"""

from __future__ import annotations

import argparse
import logging
import os


def main():
    parser = argparse.ArgumentParser(description="FAB 이상감지 DB 초기화")
    parser.add_argument("--db", default="simulator.db", help="SQLite DB 파일 (기본: simulator.db)")
    parser.add_argument("--reset", action="store_true", help="기존 DB 삭제 후 재생성")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger = logging.getLogger("init_db")

    # 기존 DB 처리
    if os.path.exists(args.db):
        if args.reset:
            os.remove(args.db)
            logger.info("기존 DB 삭제: %s", args.db)
        else:
            logger.info("DB가 이미 존재합니다: %s (--reset으로 초기화 가능)", args.db)
            return

    # 1. SQLite 초기화
    from simulator.sqlite_backend import init_sqlite, get_conn
    init_sqlite(args.db)

    # 2. 테이블 생성
    schema_path = os.path.join(os.path.dirname(__file__), "simulator", "mes_schema.sql")
    with open(schema_path) as f:
        sql = f.read()
    conn = get_conn()
    for stmt in sql.split(";"):
        stmt = stmt.strip()
        if stmt:
            conn.execute(stmt)
    conn.commit()
    logger.info("테이블 생성 완료")

    # 3. 정상 데이터 시딩
    from simulator.seeder import seed_all
    seed_all()

    # 4. 규칙 YAML → DB 동기화
    from rules.loader import sync_to_sqlite
    count = sync_to_sqlite(conn)
    logger.info("규칙 동기화: %d개", count)

    logger.info("=" * 50)
    logger.info("DB 초기화 완료: %s", args.db)
    logger.info("")
    logger.info("다음 단계:")
    logger.info("  서버 시작:   python main.py --sqlite %s", args.db)
    logger.info("  데이터 주입: python data_injector.py --db %s", args.db)
    logger.info("  대시보드:    streamlit run streamlit_app/app.py")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()
