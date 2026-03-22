import easyocr
import cv2
import re
import datetime
import os
from collections import deque
from config import (
    SPEED_LIMIT_KMH,
    DEFAULT_FPS,
    PIXEL_TO_METER_RATIO,
    SPEED_JITTER_THRESHOLD,
    CHALLAN_COOLDOWN_FRAMES,
    FINE_OVERSPEEDING,
    FINE_RED_LIGHT_JUMP,
    PLATE_OCR_CONFIDENCE,
    PLATE_MIN_CHARS
)

class OCRReader:
    def __init__(self):
        self.reader = easyocr.Reader(['en'], gpu=True)
        print("✅ OCR Reader loaded")

    def read_plate(self, plate_img) -> str:
        if plate_img is None:
            return None
        results = self.reader.readtext(plate_img)
        if not results:
            return None
        best = max(results, key=lambda x: x[2])
        text, conf = best[1], best[2]
        if conf < PLATE_OCR_CONFIDENCE:     # ✅ from config
            return None
        plate = self.clean_plate(text)
        return plate if plate else None

    def clean_plate(self, text: str) -> str:
        cleaned = re.sub(r'[^A-Z0-9]', '', text.upper())
        return cleaned if len(cleaned) >= PLATE_MIN_CHARS else None  # ✅ from config


class ViolationDetector:
    def __init__(self):
        self.speed_limit         = SPEED_LIMIT_KMH
        self.fps                 = DEFAULT_FPS
        self.pixel_to_meter      = PIXEL_TO_METER_RATIO
        self.jitter              = SPEED_JITTER_THRESHOLD
        self.speed_history       = {}  # fix 5: track_id → deque of speeds
        self.vehicle_frame_count = {}  # fix 4: track_id → frames seen

    def estimate_speed(self, vehicle_id, bbox: tuple,
                       prev_bbox: tuple, fps: int = None) -> float:
        fps = fps or self.fps
        x1, y1, x2, y2     = bbox
        px1, py1, px2, py2  = prev_bbox
        cx,  cy             = (x1+x2)//2,  (y1+y2)//2
        pcx, pcy            = (px1+px2)//2, (py1+py2)//2

        pixel_dist = ((cx-pcx)**2 + (cy-pcy)**2) ** 0.5

        if pixel_dist < self.jitter:
            return 0.0

        meters    = pixel_dist * self.pixel_to_meter
        speed_ms  = meters * fps
        speed_kmh = round(speed_ms * 3.6, 1)

        # fix 5 — smooth speed over last 10 frames per vehicle
        if vehicle_id not in self.speed_history:
            self.speed_history[vehicle_id] = deque(maxlen=10)
        self.speed_history[vehicle_id].append(speed_kmh)
        smoothed = round(
            sum(self.speed_history[vehicle_id]) /
            len(self.speed_history[vehicle_id]), 1
        )
        return smoothed

    def check_violations(self, vehicle: dict,
                         prev_vehicle: dict,
                         on_red: bool = False) -> list:
        violations = []
        track_id   = vehicle.get("track_id")

        # fix 4 — need at least 10 frames of history before issuing challan
        if track_id is not None:
            self.vehicle_frame_count[track_id] = \
                self.vehicle_frame_count.get(track_id, 0) + 1
            if self.vehicle_frame_count[track_id] < 10:
                return []  # too new, not enough history yet

        if prev_vehicle:
            speed = self.estimate_speed(
                track_id, vehicle["bbox"], prev_vehicle["bbox"]
            )
            if speed > self.speed_limit:
                violations.append({
                    "type":   "OVERSPEEDING",
                    "fine":   FINE_OVERSPEEDING,
                    "detail": f"Speed: {speed} km/h (limit: {self.speed_limit})"
                })
        if on_red:
            violations.append({
                "type":   "RED_LIGHT_JUMP",
                "fine":   FINE_RED_LIGHT_JUMP,
                "detail": "Crossed signal on red"
            })
        return violations


class ChallanSystem:
    def __init__(self, output_dir="outputs/challans"):
        self.ocr             = OCRReader()
        self.violation       = ViolationDetector()
        self.challans        = []
        self.output_dir      = output_dir
        self.last_challan    = {}
        self.cooldown_frames = CHALLAN_COOLDOWN_FRAMES  # ✅ from config (900)
        os.makedirs(output_dir, exist_ok=True)
        print("✅ Challan System loaded")

    def issue(self, plate: str, violations: list,
              frame, frame_id: int) -> dict:
        if not violations or not plate:
            return None

        filtered = []
        for v in violations:
            key  = (plate, v["type"])
            last = self.last_challan.get(key, -999)
            if frame_id - last >= self.cooldown_frames:
                filtered.append(v)
                self.last_challan[key] = frame_id

        if not filtered:
            return None

        violations = filtered
        total_fine = sum(v["fine"] for v in violations)

        challan_id = (
            f"CH{datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')[:19]}"
            f"_{frame_id}"
        )

        challan = {
            "challan_id": challan_id,
            "plate":      plate,
            "timestamp":  datetime.datetime.now().isoformat(),
            "violations": violations,
            "total_fine": total_fine,
            "frame_id":   frame_id,
            "status":     "PENDING"
        }

        self.challans.append(challan)

        evidence_path = f"{self.output_dir}/{challan_id}_{plate}.jpg"
        cv2.imwrite(evidence_path, frame)

        print(f"\n📋 CHALLAN ISSUED!")
        print(f"   ID     : {challan_id}")
        print(f"   Plate  : {plate}")
        print(f"   Fines  : {[v['type'] for v in violations]}")
        print(f"   Total  : ₹{total_fine}")
        print(f"   Evidence: {evidence_path}")

        return challan

    def get_summary(self) -> dict:
        total  = len(self.challans)
        amount = sum(c["total_fine"] for c in self.challans)
        saved  = sum(1 for c in self.challans if c.get("status") == "SAVED")
        return {
            "total_challans": total,
            "total_amount":   amount,
            "db_saved":       saved,
            "pending":        total - saved,
            "challans":       self.challans
        }

    def draw(self, frame, challans_today: int, amount_today: int):
        h, w = frame.shape[:2]
        x, y = 10, 170
        overlay = frame.copy()
        cv2.rectangle(overlay, (x, y), (x+280, y+55), (20, 20, 20), -1)
        cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
        cv2.putText(frame, f"Challans: {challans_today}",
                    (x+5, y+20), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255,255,255), 1)
        cv2.putText(frame, f"Amount : Rs.{amount_today}",
                    (x+5, y+45), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0,200,255), 1)
        return frame