import cv2
import numpy as np
from collections import deque
from ultralytics import YOLO

class MotionTracker:
    def __init__(self):
        self.prev_positions  = {}
        self.speed_history   = {}
        self.history_size    = 10
        self.stopped_frames  = {}

    def update(self, vehicles: list, frame_id: int) -> dict:
        current_positions = {}

        for v in vehicles:
            vid = v.get("track_id", v.get("id"))  # ✅ stable ID
            if vid is None:
                continue
            x1, y1, x2, y2 = v["bbox"]
            cx = (x1 + x2) // 2
            cy = (y1 + y2) // 2
            current_positions[vid] = (cx, cy)

        speeds = {}
        for vid, (cx, cy) in current_positions.items():
            if vid in self.prev_positions:
                px, py = self.prev_positions[vid]
                speed = np.sqrt((cx-px)**2 + (cy-py)**2)

                if vid not in self.speed_history:
                    self.speed_history[vid] = deque(maxlen=self.history_size)
                self.speed_history[vid].append(speed)

                self.stopped_frames[vid] = (
                    self.stopped_frames.get(vid, 0) + 1 if speed < 1.5 else 0
                )

                speeds[vid] = {
                    "speed":          speed,
                    "avg_speed":      np.mean(self.speed_history[vid]),
                    "stopped_frames": self.stopped_frames.get(vid, 0),
                    "position":       (cx, cy)
                }

        self.prev_positions = current_positions
        return speeds

    def detect_sudden_stop(self, speeds: dict) -> list:
        incidents = []
        for vid, data in speeds.items():
            history = list(self.speed_history.get(vid, []))
            if len(history) >= 5:
                recent_avg = np.mean(history[-3:])
                past_avg   = np.mean(history[:5])
                if past_avg > 15 and recent_avg < 2:
                    incidents.append({
                        "vehicle_id": vid,
                        "type":       "SUDDEN_STOP",
                        "past_speed": past_avg,
                        "curr_speed": recent_avg
                    })
        return incidents

    def detect_wrong_orientation(self, vehicles: list) -> list:
        incidents = []
        for v in vehicles:
            vid = v.get("track_id", v.get("id"))
            x1, y1, x2, y2 = v["bbox"]
            w, h = x2 - x1, y2 - y1
            if h > 0 and w > 0:
                ratio = h / w
                if ratio > 2.5 and h > 80:
                    incidents.append({
                        "vehicle_id": vid,
                        "type":       "WRONG_ORIENTATION",
                        "ratio":      ratio,
                        "bbox":       v["bbox"]
                    })
        return incidents

    def detect_overlap(self, vehicles: list) -> list:
        incidents = []
        for i in range(len(vehicles)):
            for j in range(i + 1, len(vehicles)):
                b1, b2 = vehicles[i]["bbox"], vehicles[j]["bbox"]
                ix1, iy1 = max(b1[0], b2[0]), max(b1[1], b2[1])
                ix2, iy2 = min(b1[2], b2[2]), min(b1[3], b2[3])
                if ix2 > ix1 and iy2 > iy1:
                    intersection = (ix2-ix1) * (iy2-iy1)
                    area1 = (b1[2]-b1[0]) * (b1[3]-b1[1])
                    area2 = (b2[2]-b2[0]) * (b2[3]-b2[1])
                    overlap = intersection / min(area1, area2)
                    if overlap > 0.6:  # ✅ fixed comment: 60% overlap
                        incidents.append({
                            "vehicle_id": f"{i}&{j}",
                            "type":       "OVERLAP",
                            "overlap":    overlap
                        })
        return incidents


class AccidentDetector:
    def __init__(self):
        self.model          = YOLO("yolov8n.pt")
        self.tracker        = MotionTracker()
        self.accident_log   = []
        self.confirm_buf    = deque(maxlen=15)
        self.confirm_thresh = 8   # ✅ relaxed from 14 → 8 (more realistic)
        self._last_incident_type = "UNKNOWN"  # ✅ capture type when it happens
        print("✅ Accident Detector loaded")

    def analyze(self, frame, vehicles: list, frame_id: int) -> dict:
        speeds    = self.tracker.update(vehicles, frame_id)
        incidents = self.tracker.detect_sudden_stop(speeds)

        if incidents:
            self._last_incident_type = incidents[0]["type"]  # ✅ capture while fresh

        self.confirm_buf.append(len(incidents) > 0)
        confirmed = sum(self.confirm_buf) >= self.confirm_thresh

        result = {
            "accident_detected": confirmed,
            "raw_incidents":     incidents,
            "incident_count":    len(incidents),
            "speeds":            speeds
        }

        if confirmed and (not self.accident_log or
                frame_id - self.accident_log[-1]["frame"] > 30):
            self.accident_log.append({
                "frame": frame_id,
                "type":  self._last_incident_type,  # ✅ always has a valid type
                "count": len(incidents)
            })

        return result

    def draw(self, frame, result: dict, vehicles: list) -> np.ndarray:  # ✅ fixed return type
        if result["accident_detected"]:
            h, w = frame.shape[:2]
            cv2.rectangle(frame, (0, 0), (w, h), (0, 0, 255), 8)
            cv2.rectangle(frame, (0, 50), (frame.shape[1], 100), (0, 0, 180), -1)
            cv2.putText(frame, "ACCIDENT DETECTED - ALERTING AUTHORITIES",
                        (10, 85), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        for vid, data in result["speeds"].items():
            # Find vehicle with matching track_id
            matched = next((v for v in vehicles if v.get("track_id") == vid), None)
            if matched:
                x1, y1, x2, y2 = matched["bbox"]
                speed_text = f"{data['speed']:.1f}px/f"
                color = (0, 0, 255) if data["speed"] > 20 else (0, 255, 0)
                cv2.putText(frame, speed_text, (x1, y2 + 15),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

        return frame