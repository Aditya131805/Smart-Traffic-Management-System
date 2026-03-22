import sqlite3
import datetime
import os

class TrafficDatabase:
    def __init__(self, db_path="logs/traffic.db"):
        os.makedirs("logs", exist_ok=True)
        self.db_path = db_path          # ✅ store path, not connection
        self._init_db()
        print("✅ Database loaded")

    def _get_conn(self):
        """Create a fresh connection (thread-safe)"""  # ✅
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def _init_db(self):
        """One-time table creation"""
        with self._get_conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS challans (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    challan_id    TEXT UNIQUE,
                    plate         TEXT,
                    violations    TEXT,
                    total_fine    INTEGER,
                    timestamp     TEXT,
                    frame_id      INTEGER,
                    status        TEXT DEFAULT 'PENDING',
                    evidence_path TEXT
                );

                CREATE TABLE IF NOT EXISTS incidents (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    type       TEXT,
                    severity   TEXT,
                    timestamp  TEXT,
                    frame_id   INTEGER,
                    resolved   INTEGER DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS traffic_log (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp     TEXT,
                    frame_id      INTEGER,
                    vehicle_count INTEGER,
                    congestion    TEXT,
                    density       REAL,
                    green_dir     TEXT,
                    green_dur     INTEGER,
                    police_score  REAL,
                    accidents     INTEGER
                );
            """)

    def save_challan(self, challan: dict):
        try:
            with self._get_conn() as conn:           # ✅ fresh connection
                conn.execute("""
                    INSERT OR IGNORE INTO challans
                    (challan_id, plate, violations, total_fine,
                     timestamp, frame_id, status, evidence_path)
                    VALUES (?,?,?,?,?,?,?,?)""", (
                    challan["challan_id"],
                    challan["plate"],
                    str([v["type"] for v in challan["violations"]]),
                    challan["total_fine"],
                    challan["timestamp"],
                    challan["frame_id"],
                    challan["status"],
                    f"outputs/challans/{challan['challan_id']}_{challan['plate']}.jpg"  # ✅ fixed path
                ))
        except Exception as e:
            print(f"DB error (challan): {e}")

    def save_incident(self, inc_type: str, severity: str, frame_id: int):
        try:                                         # ✅ error handling added
            with self._get_conn() as conn:
                conn.execute("""
                    INSERT INTO incidents
                    (type, severity, timestamp, frame_id)
                    VALUES (?,?,?,?)""", (
                    inc_type, severity,
                    datetime.datetime.now().isoformat(),
                    frame_id
                ))
        except Exception as e:
            print(f"DB error (incident): {e}")

    def save_traffic_log(self, data: dict):
        try:                                         # ✅ error handling added
            with self._get_conn() as conn:
                conn.execute("""
                    INSERT INTO traffic_log
                    (timestamp, frame_id, vehicle_count, congestion,
                     density, green_dir, green_dur, police_score, accidents)
                    VALUES (?,?,?,?,?,?,?,?,?)""", (
                    data["time"],        data["frame_id"],
                    data["vehicles"],    data["congestion"],
                    data["density"],     data["green_dir"],
                    data["green_dur"],   data["police_score"],
                    data["accidents"]
                ))
        except Exception as e:
            print(f"DB error (traffic_log): {e}")

    def get_challan_summary(self) -> dict:
        try:
            with self._get_conn() as conn:           # ✅ thread-safe
                c = conn.cursor()
                c.execute("SELECT COUNT(*), SUM(total_fine) FROM challans")
                row = c.fetchone()
            return {
                "total_challans": row[0] or 0,
                "total_amount":   row[1] or 0
            }
        except Exception as e:
            print(f"DB error (summary): {e}")
            return {"total_challans": 0, "total_amount": 0}

    def get_recent_challans(self, limit=10) -> list:
        try:
            with self._get_conn() as conn:           # ✅ thread-safe
                c = conn.cursor()
                c.execute("""SELECT challan_id, plate, violations,
                             total_fine, timestamp, status
                             FROM challans
                             ORDER BY id DESC LIMIT ?""", (limit,))
                rows = c.fetchall()
            return [{"challan_id": r[0], "plate": r[1],
                     "violations": r[2], "total_fine": r[3],
                     "timestamp":  r[4], "status":     r[5]}
                    for r in rows]
        except Exception as e:
            print(f"DB error (recent challans): {e}")
            return []

    def get_incident_count(self) -> dict:
        try:
            with self._get_conn() as conn:           # ✅ thread-safe
                c = conn.cursor()
                c.execute("SELECT type, COUNT(*) FROM incidents GROUP BY type")
                return dict(c.fetchall())
        except Exception as e:
            print(f"DB error (incident count): {e}")
            return {}

    def close(self):
        pass  # ✅ no persistent connection to close anymore

    def clear_session(self):
        try:
            with self._get_conn() as conn:
                conn.execute("DELETE FROM challans")
                conn.execute("DELETE FROM incidents")
                conn.execute("DELETE FROM traffic_log")
                conn.execute(              # ✅ reset autoincrement counters
                    "DELETE FROM sqlite_sequence WHERE name IN "
                    "('challans','incidents','traffic_log')"
                )
            print("✅ Database cleared for new session")
        except Exception as e:
            print(f"DB error (clear): {e}")