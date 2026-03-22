from ultralytics import YOLO
import cv2

VEHICLE_CLASSES = {
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck"
}

class VehicleDetector:
    def __init__(self, model_path="yolov8n.pt"):
        self.model = YOLO(model_path)
        print("✅ Vehicle Detector loaded")

    def detect(self, frame) -> list:
        results = self.model.track(         # ✅ use track() for stable IDs
            frame, persist=True, verbose=False
        )[0]
        vehicles = []

        for box in results.boxes:
            cls_id = int(box.cls)
            if cls_id not in VEHICLE_CLASSES:
                continue

            if box.xyxy is None or len(box.xyxy) == 0:  # ✅ guard
                continue

            conf = float(box.conf)
            if conf <= 0.4:
                continue

            x1, y1, x2, y2 = map(int, box.xyxy[0])
            track_id = int(box.id) if box.id is not None else None  # ✅

            vehicles.append({
                "label":      VEHICLE_CLASSES[cls_id],
                "confidence": conf,
                "bbox":       (x1, y1, x2, y2),
                "track_id":   track_id       # ✅ stable ID for motion tracker
            })

        return vehicles

    def draw_boxes(self, frame, vehicles: list):
        COLORS = {
            "car":        (0, 255, 0),
            "motorcycle": (255, 165, 0),
            "bus":        (0, 0, 255),
            "truck":      (255, 0, 255)
        }

        for v in vehicles:
            x1, y1, x2, y2 = v["bbox"]
            color      = COLORS.get(v["label"], (255, 255, 255))
            tid        = v.get("track_id")
            label_text = f'{v["label"]} {v["confidence"]:.2f}'
            if tid is not None:
                label_text += f' #{tid}'    # ✅ show track ID on frame

            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, label_text, (x1, y1 - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        return frame