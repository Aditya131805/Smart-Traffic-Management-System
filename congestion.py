import cv2
import numpy as np
from dataclasses import dataclass

@dataclass
class CongestionResult:
    level: str
    vehicle_count: int
    density: float
    color: tuple
    recommendation: str

class CongestionAnalyzer:
    def __init__(self):
        self.thresholds = {
            "low":    {"count": 5,  "density": 0.10},
            "medium": {"count": 15, "density": 0.25},
        }

    def compute_density(self, vehicles: list, frame_shape: tuple) -> float:
        h, w = frame_shape[:2]
        frame_area = h * w
        vehicle_area = sum(
            (v["bbox"][2] - v["bbox"][0]) * (v["bbox"][3] - v["bbox"][1])
            for v in vehicles
        )
        return round(vehicle_area / frame_area, 4)

    def classify(self, vehicles: list, frame_shape: tuple) -> CongestionResult:
        count = len(vehicles)
        density = self.compute_density(vehicles, frame_shape)

        if (count <= self.thresholds["low"]["count"] and
            density < self.thresholds["low"]["density"]):
                return CongestionResult(
                level="LOW", vehicle_count=count, density=density,
                color=(0, 200, 0),
                recommendation="Traffic flowing normally"
            )
        elif (count <= self.thresholds["medium"]["count"] and
          density < self.thresholds["medium"]["density"]):
            return CongestionResult(
                level="MEDIUM", vehicle_count=count, density=density,
                color=(0, 165, 255),
                recommendation="Monitor closely, may worsen"
            )
        else:
            return CongestionResult(
                level="HIGH", vehicle_count=count, density=density,
                color=(0, 0, 255),
                recommendation="Intervention needed!"
            )

    def draw_heatmap(self, frame, vehicles: list):
        heatmap = np.zeros(frame.shape[:2], dtype=np.float32)
        for v in vehicles:
            x1, y1, x2, y2 = v["bbox"]
            heatmap[y1:y2, x1:x2] += 1.0

        if heatmap.max() > 0:
            heatmap = heatmap / heatmap.max()
        heatmap_colored = cv2.applyColorMap(
            (heatmap * 255).astype(np.uint8), cv2.COLORMAP_JET
        )
        blended = cv2.addWeighted(frame, 0.7, heatmap_colored, 0.3, 0)
        return blended