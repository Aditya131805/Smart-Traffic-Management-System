import cv2
import numpy as np
from collections import deque
from dataclasses import dataclass
from typing import List

@dataclass
class PoliceAssessment:
    needed:   bool
    score:    float
    priority: str
    reasons:  List[str]

class PoliceAssessor:
    def __init__(self):
        self.history_size  = 30
        self.score_history = deque(maxlen=self.history_size)  # ✅ deque
        print("✅ Police Assessor loaded")

    def assess(self, data: dict) -> PoliceAssessment:
        score   = 0.0
        reasons = []

        # Factor 1 - Congestion level
        congestion_scores = {"LOW": 0.0, "MEDIUM": 0.15, "HIGH": 0.35}
        c_score = congestion_scores.get(data.get("congestion", "LOW"), 0)
        if c_score > 0:
            score += c_score
            reasons.append(f"{data['congestion']} congestion detected")

        # Factor 2 - Accident detected
        if data.get("accident"):
            score += 0.45
            reasons.append("Accident detected on road")

        # Factor 3 - Emergency vehicle stuck
        if data.get("emergency_stuck"):
            score += 0.25
            reasons.append("Emergency vehicle blocked")

        # Factor 4 - Signal not working
        if not data.get("signal_working", True):
            score += 0.20
            reasons.append("Traffic signal malfunction")

        # Factor 5 - High vehicle count
        count = data.get("vehicle_count", 0)
        if count > 20:
            score += 0.15
            reasons.append(f"High vehicle count: {count}")
        elif count > 12:
            score += 0.08
            reasons.append(f"Elevated vehicle count: {count}")

        # Factor 6 - Multiple incidents
        incidents = data.get("incident_count", 0)
        if incidents >= 3:
            score += 0.15
            reasons.append(f"Multiple incidents: {incidents}")
        elif incidents >= 1:
            score += 0.05

        score = min(score, 1.0)

        self.score_history.append(score)                          # ✅ deque auto-trims
        smoothed = min(                                           # ✅ cap smoothed too
            sum(self.score_history) / len(self.score_history),
            1.0
        )

        if smoothed >= 0.6:
            priority, needed = "CRITICAL", True
        elif smoothed >= 0.35:
            priority, needed = "HIGH",     True
        elif smoothed >= 0.20:
            priority, needed = "MEDIUM",   False
        else:
            priority, needed = "LOW",      False

        return PoliceAssessment(
            needed   = needed,
            score    = round(smoothed, 3),
            priority = priority,
            reasons  = reasons if reasons else ["Normal traffic conditions"]
        )

    def draw(self, frame, assessment: PoliceAssessment) -> np.ndarray:  # ✅ annotation + no import inside
        h, w = frame.shape[:2]
        x, y = 10, h - 100

        overlay = frame.copy()
        cv2.rectangle(overlay, (x, y - 20), (x + 280, h - 5), (20, 20, 20), -1)
        cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

        bar_w  = 260
        filled = int(bar_w * assessment.score)
        color  = (0, 200, 0)   if assessment.score < 0.35 else \
                 (0, 165, 255) if assessment.score < 0.6  else \
                 (0, 0, 255)

        cv2.putText(frame, f"Police Score: {assessment.score:.2f}",
                    (x + 5, y + 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        cv2.rectangle(frame, (x + 5, y + 15),
                      (x + 5 + bar_w, y + 30), (60, 60, 60), -1)
        cv2.rectangle(frame, (x + 5, y + 15),
                      (x + 5 + filled, y + 30), color, -1)

        status = "NEEDED" if assessment.needed else "NOT NEEDED"
        cv2.putText(frame, f"Priority: {assessment.priority} | {status}",
                    (x + 5, y + 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1)

        if assessment.reasons:
            cv2.putText(frame, assessment.reasons[0][:35],
                        (x + 5, y + 70),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (180, 180, 180), 1)

        if assessment.needed:
            cv2.rectangle(frame, (0, 100), (w, 150), (0, 0, 150), -1)
            cv2.putText(frame, "TRAFFIC POLICE REQUIRED AT THIS INTERSECTION",
                        (10, 135), cv2.FONT_HERSHEY_SIMPLEX,
                        0.65, (255, 255, 255), 2)

        return frame