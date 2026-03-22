# ============================================================
#   Smart Traffic Management System — Central Configuration
# ============================================================

import os

# ── Paths ────────────────────────────────────────────────────
VIDEO_PATH        = "videos/india_square.mp4"
OUTPUT_VIDEO      = "outputs/result_week4.mp4"
DB_PATH           = "logs/traffic.db"
ALERTS_LOG        = "logs/alerts.csv"
SESSION_LOG       = "logs/session_log.csv"
CHALLAN_DIR       = "outputs/challans"
REPORT_PATH       = "outputs/project_report.png"
WEEK1_REPORT      = "outputs/week1_report.png"

# ── YOLO Model ───────────────────────────────────────────────
YOLO_MODEL        = "yolov8n.pt"       # swap to yolov8m.pt for better accuracy
YOLO_CONFIDENCE   = 0.4                # minimum detection confidence

# COCO class IDs for vehicles
VEHICLE_CLASSES   = {
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck"
}

# ── Video Processing ─────────────────────────────────────────
MAX_FRAMES        = 27000              # stop processing after this frame
PROCESS_EVERY_N   = 3                  # process 1 out of every N frames
DEFAULT_FPS       = 25                 # fallback if cap.get() returns 0

# ── Congestion Thresholds ────────────────────────────────────
CONGESTION_LOW_COUNT      = 5
CONGESTION_LOW_DENSITY    = 0.10
CONGESTION_MEDIUM_COUNT   = 15
CONGESTION_MEDIUM_DENSITY = 0.25

# ── Traffic Signal ───────────────────────────────────────────
SIGNAL_MIN_GREEN          = 10         # seconds
SIGNAL_MAX_GREEN          = 60         # seconds
SIGNAL_STARVATION_LIMIT   = 15         # frames before forced green (~5s at 30fps)
EMERGENCY_GREEN_FRAMES    = 150        # frames to hold green for emergency vehicle
SIGNAL_LOG_SIZE           = 500        # max signal log entries
HAS_TRAFFIC_SIGNALS = False

# ── Challan / Violations ─────────────────────────────────────
SPEED_LIMIT_KMH           = 80         # km/h
FINE_OVERSPEEDING         = 2000       # Rs.
FINE_RED_LIGHT_JUMP       = 1000       # Rs.
CHALLAN_COOLDOWN_FRAMES   = 900        # frames between same violation (~30s at 30fps)
PIXEL_TO_METER_RATIO      = 0.02       # calibrate per camera
SPEED_JITTER_THRESHOLD    = 3          # pixels — ignore movement below this

# Demo plates (used when OCR fails)
DEMO_PLATES = [
    "MH12AB1234", "DL8CAF2341", "KA03MN9876",
    "UP16CX4521", "TN09ZX7823", "GJ05AB3321"
]

# ── Plate Detection ──────────────────────────────────────────
PLATE_ASPECT_MIN          = 2.5
PLATE_ASPECT_MAX          = 5.0
PLATE_AREA_MIN            = 1500
PLATE_AREA_MAX_RATIO      = 0.03       # fraction of total frame area
PLATE_MIN_WIDTH           = 80
PLATE_MIN_HEIGHT          = 20
PLATE_MAX_HEIGHT          = 80
PLATE_MAX_CANDIDATES      = 10
PLATE_IDEAL_ASPECT        = 3.5        # used for sorting candidates
PLATE_OCR_CONFIDENCE      = 0.3        # minimum EasyOCR confidence
PLATE_MIN_CHARS           = 4          # minimum plate text length

# ── Accident Detection ───────────────────────────────────────
ACCIDENT_CONFIRM_BUFFER   = 15         # deque size
ACCIDENT_CONFIRM_THRESH   = 8          # detections needed out of buffer
ACCIDENT_COOLDOWN_FRAMES  = 30         # min frames between logged accidents
SUDDEN_STOP_PAST_SPEED    = 15         # px/frame — was moving fast
SUDDEN_STOP_CURR_SPEED    = 2          # px/frame — now nearly stopped
OVERLAP_THRESHOLD         = 0.6        # IoU for collision detection
WRONG_ORIENT_RATIO        = 2.5        # h/w ratio for overturned vehicle
WRONG_ORIENT_MIN_HEIGHT   = 80         # pixels

# ── Emergency Detection ──────────────────────────────────────
EMERGENCY_HISTORY_SIZE    = 10
EMERGENCY_CONFIRM_COUNT   = 3          # detections needed out of history
EMERGENCY_COLOR_THRESHOLD = 0.15       # fraction of pixels that must be red/blue

# ── Police Assessment ────────────────────────────────────────
POLICE_HISTORY_SIZE       = 30
POLICE_SCORE_CRITICAL     = 0.6
POLICE_SCORE_HIGH         = 0.35
POLICE_SCORE_MEDIUM       = 0.20

# Score weights
POLICE_WEIGHT_HIGH_CONGESTION   = 0.35
POLICE_WEIGHT_MEDIUM_CONGESTION = 0.15
POLICE_WEIGHT_ACCIDENT          = 0.45
POLICE_WEIGHT_EMERGENCY_STUCK   = 0.25
POLICE_WEIGHT_SIGNAL_DOWN       = 0.20
POLICE_WEIGHT_HIGH_COUNT        = 0.15   # vehicle_count > 20
POLICE_WEIGHT_MED_COUNT         = 0.08   # vehicle_count > 12
POLICE_WEIGHT_MULTI_INCIDENT    = 0.15   # incidents >= 3
POLICE_WEIGHT_SINGLE_INCIDENT   = 0.05   # incidents >= 1
POLICE_HIGH_COUNT_THRESHOLD     = 20
POLICE_MED_COUNT_THRESHOLD      = 12
POLICE_MULTI_INCIDENT_THRESHOLD = 3

# ── Alert System ─────────────────────────────────────────────
ALERT_COOLDOWN_SECONDS    = 30

# ── Motion Tracker ───────────────────────────────────────────
SPEED_HISTORY_SIZE        = 10
STOPPED_SPEED_THRESHOLD   = 1.5        # px/frame — below this = stopped

# ── Dashboard ────────────────────────────────────────────────
DASHBOARD_DB_PATH         = DB_PATH
TRAFFIC_LOG_LIMIT         = 500        # rows fetched for charts
INCIDENT_LOG_LIMIT        = 50

# ── Ensure required directories exist ───────────────────────
for _dir in ["logs", "outputs", CHALLAN_DIR, "videos"]:
    os.makedirs(_dir, exist_ok=True)