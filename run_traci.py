import os
import sys
import glob
import traci
import cv2

# Add parent directory to path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from traffic_signal import SignalController
from alerts import AlertSystem
from database import TrafficDatabase
from police import PoliceAssessor
from datetime import datetime

# ✅ Auto-detect if running standalone or called from demo
IS_STANDALONE = "--headless" not in sys.argv

# ── SUMO edges we monitor (incoming lanes only) ───────────
LANE_EDGES = {
    "NORTH": "north_in",
    "SOUTH": "south_in",
    "EAST":  "east_in",
    "WEST":  "west_in",
}

TL_ID = "center"

# Phase 0: NORTH+SOUTH green | Phase 2: EAST+WEST green
DIRECTION_TO_PHASE = {
    "NORTH": 0,
    "SOUTH": 0,
    "EAST":  2,
    "WEST":  2,
}

def get_lane_counts() -> dict:
    """Waiting vehicle count per lane — fairer for signal control"""
    counts = {}
    for direction, edge in LANE_EDGES.items():
        vehicle_ids = traci.edge.getLastStepVehicleIDs(edge)
        waiting = sum(
            1 for vid in vehicle_ids
            if traci.vehicle.getWaitingTime(vid) > 0
        )
        counts[direction] = waiting
    return counts

def get_total_vehicles() -> int:
    """Total vehicles across all lanes for congestion assessment"""
    return sum(
        traci.edge.getLastStepVehicleNumber(edge)
        for edge in LANE_EDGES.values()
    )

def apply_signal_to_sumo(direction: str, duration: int):
    """Sync our direction decision back to SUMO traffic light"""
    phase = DIRECTION_TO_PHASE.get(direction, 0)
    try:
        current_phase = traci.trafficlight.getPhase(TL_ID)
        if current_phase != phase:
            traci.trafficlight.setPhase(TL_ID, phase)
        traci.trafficlight.setPhaseDuration(TL_ID, duration)
    except Exception as e:
        print(f"⚠️  TraCI signal error: {e}")

def compute_green_duration(vehicle_count: int) -> int:
    """More vehicles = longer green, capped between 10-60s"""
    return max(10, min(60, 10 + vehicle_count * 2))

def frames_to_video(frames_dir: str, output_path: str, fps: int = 15):
    """Convert screenshot frames to video"""
    frames = sorted(glob.glob(os.path.join(frames_dir, "*.png")))
    if not frames:
        print("❌ No frames found for video export")
        return

    first = cv2.imread(frames[0])
    if first is None:
        print("❌ Could not read first frame")
        return

    h, w   = first.shape[:2]
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    writer = cv2.VideoWriter(output_path, fourcc, fps, (w, h))

    for f in frames:
        img = cv2.imread(f)
        if img is not None:
            writer.write(img)

    writer.release()
    print(f"✅ SUMO video saved: {output_path} ({len(frames)} frames)")

def run():
    mode = "STANDALONE (GUI)" if IS_STANDALONE else "DEMO (Headless)"
    print(f"🚦 Starting SUMO + TraCI integration [{mode}]...\n")

    # ── Initialize modules ────────────────────────────────
    controller = SignalController()
    alert_sys  = AlertSystem()
    db         = TrafficDatabase()
    assessor   = PoliceAssessor()

    # ── Create frames directory ───────────────────────────
    frames_dir = os.path.join(os.path.dirname(__file__), "frames")
    os.makedirs(frames_dir, exist_ok=True)

    # ── Start SUMO — GUI or headless based on caller ──────
    if IS_STANDALONE:
        # Running directly — open GUI so you can watch it
        sumo_cmd = [
            "sumo-gui",
            "-c", os.path.join(os.path.dirname(__file__), "simulation.sumocfg"),
            "--start",
            "--delay", "80",
            "--quit-on-end",
        ]
        print("🖥️  Opening SUMO GUI...")
    else:
        # Called from demo.py — run headless, no window
        sumo_cmd = [
            "sumo",
            "-c", os.path.join(os.path.dirname(__file__), "simulation.sumocfg"),
            "--quit-on-end",
        ]
        print("⚡ Running SUMO headless (called from demo.py)...")

    traci.start(sumo_cmd)
    print("✅ SUMO started via TraCI\n")
    print(f"{'Step':>6} | {'N(w)':>5} {'S(w)':>5} {'E(w)':>5} {'W(w)':>5} | "
          f"{'Total':>5} | {'Green':>12} | Police")
    print("-" * 72)

    # ── Round robin state ─────────────────────────────────
    directions      = ["NORTH", "SOUTH", "EAST", "WEST"]
    current_dir_idx = 0
    green_timer     = 0
    green_duration  = 30

    step      = 0
    frame_id  = 100000
    log_every = 10

    while traci.simulation.getMinExpectedNumber() > 0:
        traci.simulationStep()

        # ── Get counts ────────────────────────────────────
        lane_counts = get_lane_counts()
        total       = get_total_vehicles()

        # ── Timer-based rotation ──────────────────────────
        green_timer += 1
        if green_timer >= green_duration:
            current_dir_idx = (current_dir_idx + 1) % 4
            green_timer     = 0
            current_dir     = directions[current_dir_idx]
            green_duration  = compute_green_duration(
                lane_counts.get(current_dir, 0)
            )

        current_dir = directions[current_dir_idx]

        # ── Force signal controller to pick current direction
        forced_counts = {d: 0 for d in directions}
        forced_counts[current_dir] = lane_counts.get(current_dir, 0) + 100
        signal_state = controller.update(forced_counts)

        # ── Sync to SUMO ──────────────────────────────────
        apply_signal_to_sumo(current_dir, green_duration)

        # ── Screenshots only in GUI/standalone mode ───────
        if IS_STANDALONE and step % 2 == 0:
            screenshot_path = os.path.join(
                frames_dir, f"frame_{step:05d}.png"
            )
            try:
                traci.gui.screenshot("View #0", screenshot_path)
            except Exception:
                pass

        # ── Police assessment ──────────────────────────────
        police = assessor.assess({
            "congestion":      "HIGH"   if total > 20 else
                               "MEDIUM" if total > 10 else "LOW",
            "accident":        False,
            "emergency_stuck": False,
            "signal_working":  True,
            "vehicle_count":   total,
            "incident_count":  0
        })

        # ── Alerts ────────────────────────────────────────
        if total > 20:
            alert_sys.send("HIGH_CONGESTION",
                           f"High congestion: {total} vehicles",
                           severity="HIGH")
        if police.needed:
            alert_sys.send("POLICE",
                           "Police needed at intersection",
                           severity="HIGH")

        # ── Print every 10 steps ──────────────────────────
        if step % 10 == 0:
            print(f"{step:>6} | "
                  f"{lane_counts['NORTH']:>5} "
                  f"{lane_counts['SOUTH']:>5} "
                  f"{lane_counts['EAST']:>5} "
                  f"{lane_counts['WEST']:>5} | "
                  f"{total:>5} | "
                  f"🟢 {current_dir:<6} {green_duration:>2}s | "
                  f"{police.priority}")

        # ── Log to DB ─────────────────────────────────────
        if step % log_every == 0:
            congestion_level = ("HIGH"   if total > 20 else
                                "MEDIUM" if total > 10 else "LOW")
            db.save_traffic_log({
                "time":        datetime.now().isoformat(),
                "frame_id":    frame_id,
                "vehicles":    total,
                "congestion":  congestion_level,
                "density":     round(total / 50, 4),
                "green_dir":   current_dir,
                "green_dur":   green_duration,
                "police_score": police.score,
                "accidents":   0
            })
            frame_id += 1

        step += 1

    traci.close()

    # ── Convert frames to video (standalone only) ─────────
    if IS_STANDALONE:
        print("\n🎬 Converting screenshots to video...")
        frames_to_video(
            frames_dir=frames_dir,
            output_path=os.path.join(
                os.path.dirname(__file__), "..", "outputs", "sumo_result.mp4"
            ),
            fps=15  # smooth playback
        )

    # ── Final summary ─────────────────────────────────────
    print("\n" + "="*72)
    print("📊 SUMO Simulation Complete!")
    print("="*72)
    print(f"   Total steps   : {step}")
    print(f"   DB logs saved : {frame_id}")
    if IS_STANDALONE:
        print(f"   Screenshots   : {step // 2}")
    print(f"\n📊 Alert Summary:")
    for t, c in alert_sys.get_summary().items():
        print(f"   {t}: {c}")
    print("\n✅ Signal data saved to logs/traffic.db")
    if IS_STANDALONE:
        print("✅ Video saved to outputs/sumo_result.mp4")
    print("▶  Now run: python -m streamlit run dashboard.py")

if __name__ == "__main__":
    run()