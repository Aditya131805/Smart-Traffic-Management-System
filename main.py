import os
os.environ["YOLO_AUTOINSTALL"] = "false"

import cv2
import random
from datetime import datetime
from detector import VehicleDetector
from congestion import CongestionAnalyzer
from traffic_signal import SignalController
from emergency import EmergencyDetector
from accident import AccidentDetector
from police import PoliceAssessor
from alerts import AlertSystem
from challan import ChallanSystem
from plate_detector import PlateDetector
from database import TrafficDatabase
from utils import draw_hud
from config import HAS_TRAFFIC_SIGNALS

DEMO_PLATES = [
    "MH12AB1234", "DL8CAF2341", "KA03MN9876",
    "UP16CX4521", "TN09ZX7823", "GJ05AB3321"
]

def draw_signal_overlay(frame, signal_state: dict):
    h, w = frame.shape[:2]
    x, y = w - 220, h - 140
    overlay = frame.copy()
    cv2.rectangle(overlay, (x-10, y-20), (w-5, h-5), (20,20,20), -1)
    cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
    cv2.putText(frame, "SIGNALS", (x, y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255,255,255), 1)

    colors = {"GREEN": (0,200,0), "RED": (0,0,255)}
    y_off = 25
    for direction, status in signal_state["all_phases"].items():
        color = colors.get(status, (200,200,200))
        cv2.putText(frame, f"{direction}: {status}",
                    (x, y+y_off),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        y_off += 22
    cv2.putText(frame, f"Green: {signal_state['green_duration']}s",
                (x, y+y_off),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,200,0), 1)
    return frame

def run(video_path: str):
    cap          = cv2.VideoCapture(video_path)
    vehicle_det  = VehicleDetector()
    analyzer     = CongestionAnalyzer()
    controller   = SignalController()
    emerg_det    = EmergencyDetector()
    accident_det = AccidentDetector()
    assessor     = PoliceAssessor()
    alert_sys    = AlertSystem()
    challan_sys  = ChallanSystem()
    plate_det    = PlateDetector()
    db           = TrafficDatabase()
    db.clear_session()

    frame_id            = 0
    prev_vehicle_bboxes : dict = {}
    last_frame          = None

    # ✅ Simple round robin for signal display in video
    directions      = ["NORTH", "SOUTH", "EAST", "WEST"]
    current_dir_idx = 0
    green_timer     = 0
    green_duration  = 30

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    fps    = int(cap.get(cv2.CAP_PROP_FPS)) or 25
    w      = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h      = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    writer = cv2.VideoWriter(
        "outputs/result_week4.mp4", fourcc, fps, (w, h)
    )

    print("▶ Running Smart Traffic System... Press Q to quit\n")

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        if frame_id > 27000:
            break

        if frame_id % 3 == 0:

            # 1. Detect vehicles
            vehicles   = vehicle_det.detect(frame)
            congestion = analyzer.classify(vehicles, frame.shape)

            # 2. Emergency detection
            emergency  = emerg_det.detect(frame)

            # 3. Accident detection
            accident   = accident_det.analyze(frame, vehicles, frame_id)

            # 4. Signal control — round robin rotation
            # (Real signal control handled by SUMO via run_traci.py)
            green_timer += 1
            if green_timer >= green_duration:
                current_dir_idx = (current_dir_idx + 1) % 4
                green_timer     = 0
                green_duration  = max(10, min(60,
                    10 + congestion.vehicle_count * 2 // 4
                ))

            current_dir  = directions[current_dir_idx]
            forced_counts = {d: 0 for d in directions}
            forced_counts[current_dir] = congestion.vehicle_count + 100

            if emergency["emergency_detected"] and not controller.emergency_override:
                controller.force_green("NORTH", duration_frames=150)
            signal_state = controller.update(forced_counts)

            # 5. Police assessment
            police = assessor.assess({
                "congestion":      congestion.level,
                "accident":        accident["accident_detected"],
                "emergency_stuck": False,
                "signal_working":  True,
                "vehicle_count":   congestion.vehicle_count,
                "incident_count":  accident["incident_count"]
            })

            # 6. Challan system
            on_red     = HAS_TRAFFIC_SIGNALS and \
                         signal_state["active_direction"] != "NORTH"
            candidates = plate_det.find_plate_regions(frame)

            for v in vehicles:
                vid = v.get("track_id")
                if vid is None:
                    continue

                plate_text = None
                vx1, vy1, vx2, vy2 = v["bbox"]

                for bbox in candidates:
                    bx1, by1, bx2, by2 = bbox
                    if bx1 >= vx1 and bx2 <= vx2 and by1 >= vy1 and by2 <= vy2:
                        plate_img  = plate_det.crop_plate(frame, bbox)
                        plate_text = challan_sys.ocr.read_plate(plate_img) \
                                     if plate_img is not None else None
                        break

                if not plate_text:
                    plate_text = random.choice(DEMO_PLATES)

                prev       = prev_vehicle_bboxes.get(vid)
                violations = challan_sys.violation.check_violations(
                    v, prev, on_red=on_red
                )
                prev_vehicle_bboxes[vid] = v

                if violations:
                    challan = challan_sys.issue(
                        plate_text, violations, frame, frame_id
                    )
                    if challan:
                        db.save_challan(challan)

            # 7. Fire alerts
            alert_sys.check_all(congestion, accident, police, emergency)

            # 8. Save incidents to DB
            if accident["accident_detected"]:
                db.save_incident("ACCIDENT", "CRITICAL", frame_id)
            if police.needed:
                db.save_incident("POLICE_NEEDED", "HIGH", frame_id)

            # 9. Draw all overlays
            frame = emerg_det.draw(frame, emergency)
            frame = accident_det.draw(frame, accident, vehicles)
            frame = assessor.draw(frame, police)
            frame = draw_hud(frame, congestion, vehicles)
            frame = draw_signal_overlay(frame, signal_state)
            ch_summary = challan_sys.get_summary()
            frame = challan_sys.draw(
                frame,
                ch_summary["total_challans"],
                ch_summary["total_amount"]
            )

            # 10. Log to database
            db.save_traffic_log({
                "time":        datetime.now().isoformat(),
                "frame_id":    frame_id,
                "vehicles":    congestion.vehicle_count,
                "congestion":  congestion.level,
                "density":     congestion.density,
                "green_dir":   signal_state["active_direction"],
                "green_dur":   signal_state["green_duration"],
                "police_score": police.score,
                "accidents":   accident["incident_count"]
            })

            last_frame = frame.copy()

        if last_frame is not None:
            writer.write(last_frame)

        if frame_id % 500 == 0:
            print(f"   Processing frame {frame_id}...")

        frame_id += 1

    cap.release()
    writer.release()
    print("✅ Processing complete!")

    ch_summary = challan_sys.get_summary()
    db_summary = db.get_challan_summary()

    print("\n📊 Final Session Summary:")
    print(f"   Frames processed : {frame_id}")
    print(f"   Challans issued  : {ch_summary['total_challans']}")
    print(f"   Total fines      : Rs.{ch_summary['total_amount']}")
    print(f"   DB challans      : {db_summary['total_challans']}")
    print(f"   Incidents in DB  : {db.get_incident_count()}")

    print("\n📋 Recent Challans:")
    for c in db.get_recent_challans(5):
        print(f"   {c['plate']} | {c['violations']} | Rs.{c['total_fine']}")

    print("\n📊 Alert Summary:")
    for t, c in alert_sys.get_summary().items():
        print(f"   {t}: {c}")

    db.close()
    print("\n✅ Week 4 complete! Output: outputs/result_week4.mp4")

if __name__ == "__main__":
    run("videos/india_square.mp4")