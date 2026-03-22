import datetime
import csv
import os

class AlertSystem:
    ALERT_TYPES = {
        "EMERGENCY":       "🚨",
        "HIGH_CONGESTION": "🔴",
        "ACCIDENT":        "💥",
        "POLICE":          "👮",
        "SIGNAL":          "🚦"
    }
    FIELDNAMES = ["timestamp", "type", "message", "severity"]  # ✅ fixed

    def __init__(self, log_path="logs/alerts.csv"):
        self.log_path     = log_path
        self.alert_counts = {}   # ✅ counter instead of growing list
        self.last_alerts  = {}
        self.cooldown     = 30

        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        if not os.path.exists(log_path):
            with open(log_path, "w", newline="") as f:
                csv.DictWriter(f, fieldnames=self.FIELDNAMES).writeheader()
        print("✅ Alert System loaded")

    def _can_alert(self, alert_type: str) -> bool:
        now = datetime.datetime.now()
        if alert_type in self.last_alerts:
            diff = (now - self.last_alerts[alert_type]).total_seconds()  # ✅ fixed
            if diff < self.cooldown:
                return False
        self.last_alerts[alert_type] = now
        return True

    def send(self, alert_type: str, message: str, severity="MEDIUM"):
        if not self._can_alert(alert_type):
            return None

        emoji = self.ALERT_TYPES.get(alert_type, "⚠️")
        ts    = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        alert = {
            "timestamp": ts,
            "type":      alert_type,
            "message":   message,
            "severity":  severity
        }

        self.alert_counts[alert_type] = \
            self.alert_counts.get(alert_type, 0) + 1  # ✅ count only

        print(f"\n{emoji} ALERT [{severity}] {ts}")
        print(f"   {message}")

        with open(self.log_path, "a", newline="") as f:
            csv.DictWriter(f, fieldnames=self.FIELDNAMES).writerow(alert)  # ✅ fixed fieldnames

        return alert

    def check_and_alert(self, data: dict):
        alerts_fired = []

        if data.get("emergency_detected"):
            a = self.send("EMERGENCY",
                          "Emergency vehicle detected! Green corridor activated.",
                          severity="CRITICAL")
            if a: alerts_fired.append(a)

        if data.get("congestion_level") == "HIGH":
            a = self.send("HIGH_CONGESTION",
                          "High congestion detected! Consider rerouting traffic.",
                          severity="HIGH")
            if a: alerts_fired.append(a)

        if data.get("accident_detected"):
            a = self.send("ACCIDENT",
                          "Possible accident detected! Dispatching response.",
                          severity="CRITICAL")
            if a: alerts_fired.append(a)

        if data.get("police_needed"):
            a = self.send("POLICE",
                          "Traffic police required at this intersection.",
                          severity="HIGH")
            if a: alerts_fired.append(a)

        return alerts_fired

    def get_summary(self) -> dict:
        return dict(self.alert_counts)  # ✅ simple counter dict

    def check_all(self, congestion, accident_result,
                  police_result, emergency_result):
        data = {                                        # ✅ fixed indentation
            "congestion_level":   congestion.level,
            "accident_detected":  accident_result["accident_detected"],
            "police_needed":      police_result.needed,
            "emergency_detected": emergency_result["emergency_detected"]
        }
        return self.check_and_alert(data)