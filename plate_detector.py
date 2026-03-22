import cv2
import numpy as np
from typing import Optional

class PlateDetector:
    def __init__(self):
        print("✅ Plate Detector loaded")

    def preprocess(self, frame) -> np.ndarray:
        gray    = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blur    = cv2.GaussianBlur(gray, (5, 5), 0)
        edges   = cv2.Canny(blur, 50, 150)
        dilated = cv2.dilate(edges, np.ones((3,3), np.uint8), iterations=1)
        return dilated

    def find_plate_regions(self, frame) -> list[tuple]:
        processed = self.preprocess(frame)
        contours, _ = cv2.findContours(
            processed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        candidates = []
        h, w = frame.shape[:2]

        for cnt in contours:
            x, y, cw, ch = cv2.boundingRect(cnt)
            aspect_ratio = cw / ch if ch > 0 else 0
            area = cw * ch

            # ✅ Tighter filters — reduces false positives significantly
            if (2.5 < aspect_ratio < 5.0 and
                    1500 < area < (w * h * 0.03) and
                    cw > 80 and ch > 20 and
                    ch < 80):
                candidates.append((x, y, x+cw, y+ch))

        # ✅ Sort by closest to ideal plate aspect ratio (3.5), cap at 10
        candidates.sort(key=lambda c: abs((c[2]-c[0]) / max(c[3]-c[1], 1) - 3.5))
        return candidates[:10]

    def crop_plate(self, frame, bbox: tuple) -> Optional[np.ndarray]:
        x1, y1, x2, y2 = bbox
        pad = 5
        x1 = max(0, x1 - pad)
        y1 = max(0, y1 - pad)
        x2 = min(frame.shape[1], x2 + pad)
        y2 = min(frame.shape[0], y2 + pad)

        crop = frame[y1:y2, x1:x2]
        if crop.size == 0:
            return None

        crop  = cv2.resize(crop, None, fx=2, fy=2,
                           interpolation=cv2.INTER_CUBIC)
        gray  = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(
            gray, 0, 255,
            cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )
        return thresh

    def draw_candidates(self, frame, candidates: list) -> np.ndarray:
        output = frame.copy()   # ✅ don't modify original
        for (x1, y1, x2, y2) in candidates:
            cv2.rectangle(output, (x1, y1), (x2, y2), (255, 0, 255), 2)
            cv2.putText(output, "PLATE?", (x1, y1-5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 255), 1)
        return output