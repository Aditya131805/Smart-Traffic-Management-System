import cv2
import numpy as np
from datetime import datetime

def draw_hud(frame, congestion_result, vehicles: list) -> np.ndarray:  # ✅ annotation
    h, w = frame.shape[:2]

    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, 160), (20, 20, 20), -1)
    cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

    color = congestion_result.color

    cv2.putText(frame, "TRAFFIC MONITOR v1.0", (20, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cv2.putText(frame, ts, (w - 240, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (180, 180, 180), 1)

    cv2.putText(frame, f"CONGESTION: {congestion_result.level}",
                (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 1.1, color, 3)

    cv2.putText(frame, f"Vehicles: {congestion_result.vehicle_count}",
                (20, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)
    cv2.putText(frame, f"Density: {congestion_result.density:.1%}",
                (220, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)
    cv2.putText(frame, congestion_result.recommendation,
                (20, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 1)

    # ✅ Overflow-safe vehicle type breakdown
    counts = {}
    for v in vehicles:
        counts[v["label"]] = counts.get(v["label"], 0) + 1

    x_pos = 20
    for label, cnt in counts.items():
        text   = f"{label}: {cnt}"
        text_w = len(text) * 11
        if x_pos + text_w > w:    # ✅ stop before overflow
            break
        cv2.putText(frame, text, (x_pos, h - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1)
        x_pos += 160

    return frame