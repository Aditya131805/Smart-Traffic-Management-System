from collections import deque
from ultralytics import YOLO
import cv2
import numpy as np

class EmergencyDetector:
    VEHICLE_CLASSES = {
        2: "car",
        3: "motorcycle",
        5: "bus",
        7: "truck"
    }

    def __init__(self):
        self.model             = YOLO("yolov8n.pt")
        self.history_size      = 10
        self.emergency_history = deque(maxlen=self.history_size)  # ✅ deque
        print("✅ Emergency Detector loaded")

    def detect_emergency_colors(self, vehicle_crop) -> bool:
        if vehicle_crop is None or vehicle_crop.size == 0:
            return False

        h = vehicle_crop.shape[0]
        top_half = vehicle_crop[:h//2, :]

        # BGR: Red = high R (channel 2)
        red_mask  = cv2.inRange(top_half,
                                np.array([0,   0,   180]),
                                np.array([80,  80,  255]))
        # BGR: Blue = high B (channel 0)
        blue_mask = cv2.inRange(top_half,
                                np.array([180, 0,   0  ]),
                                np.array([255, 80,  80 ]))

        total_pixels = top_half.shape[0] * top_half.shape[1]
        if total_pixels == 0:
            return False

        red_ratio  = np.sum(red_mask  > 0) / total_pixels
        blue_ratio = np.sum(blue_mask > 0) / total_pixels

        return red_ratio > 0.15 or blue_ratio > 0.15

    def detect(self, frame) -> dict:
        results = self.model(frame, verbose=False)[0]
        emergency_vehicles = []
        all_vehicles       = []
        h_f, w_f           = frame.shape[:2]

        for box in results.boxes:
            cls_id = int(box.cls)
            if cls_id not in self.VEHICLE_CLASSES:
                continue

            if box.xyxy is None or len(box.xyxy) == 0:
                continue

            conf = float(box.conf)
            if conf <= 0.4:                          # ✅ confidence filter
                continue

            x1, y1, x2, y2 = map(int, box.xyxy[0])

            # ✅ Clamp to frame bounds
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w_f, x2), min(h_f, y2)

            label = self.VEHICLE_CLASSES[cls_id]
            crop  = frame[y1:y2, x1:x2]
            is_emergency = self.detect_emergency_colors(crop)

            vehicle_info = {
                "label":        label,
                "confidence":   conf,
                "bbox":         (x1, y1, x2, y2),
                "is_emergency": is_emergency
            }
            all_vehicles.append(vehicle_info)
            if is_emergency:
                emergency_vehicles.append(vehicle_info)

        self.emergency_history.append(len(emergency_vehicles) > 0)  # ✅ deque auto-trims
        confirmed = sum(self.emergency_history) >= 3

        return {
            "emergency_detected": confirmed,
            "emergency_vehicles": emergency_vehicles,
            "all_vehicles":       all_vehicles,
            "raw_detection":      len(emergency_vehicles) > 0
        }

    def draw(self, frame, detection_result: dict) -> np.ndarray:  # ✅ fixed return type
        for v in detection_result["all_vehicles"]:
            x1, y1, x2, y2 = v["bbox"]
            if v["is_emergency"]:
                color = (0, 0, 255)
                label = f"EMERGENCY {v['confidence']:.2f}"
                cv2.rectangle(frame, (x1-3, y1-3), (x2+3, y2+3), color, 4)
            else:
                color = (0, 255, 0)
                label = f"{v['label']} {v['confidence']:.2f}"
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

            cv2.putText(frame, label, (x1, y1 - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        if detection_result["emergency_detected"]:
            cv2.rectangle(frame, (0, 0), (frame.shape[1], 50), (0, 0, 200), -1)
            cv2.putText(frame, "EMERGENCY VEHICLE — GREEN CORRIDOR ACTIVE",
                        (10, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        return frame