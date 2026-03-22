import subprocess
import sys
import os
import time
import threading

def print_banner():
    print("""
╔══════════════════════════════════════════════════╗
║     🚦 SMART TRAFFIC MANAGEMENT SYSTEM 🚦        ║
║          Final Year College Project              ║
║     Built with YOLOv8 + OpenCV + Streamlit      ║
╚══════════════════════════════════════════════════╝
    """)

def check_files():
    required = [
        "main.py",           "dashboard.py",       "detector.py",
        "congestion.py",     "traffic_signal.py",  "emergency.py",
        "accident.py",       "police.py",          "challan.py",
        "plate_detector.py", "database.py",        "utils.py",
        "generate_report.py","config.py",
        "sumo_sim/run_traci.py",
        "sumo_sim/simulation.sumocfg",
        "sumo_sim/intersection.net.xml",
        "sumo_sim/routes.rou.xml",
    ]
    print("📁 Checking project files...")
    all_good = True
    for f in required:
        exists = os.path.exists(f)
        print(f"   {'✅' if exists else '❌'} {f}")
        if not exists:
            all_good = False
    return all_good

from config import VIDEO_PATH

def check_video():
    if os.path.exists(VIDEO_PATH):
        print(f"✅ Video file found: {VIDEO_PATH}")
        return True
    print(f"❌ Video not found at {VIDEO_PATH}")
    return False

# ── Thread targets ────────────────────────────────────────
sumo_done  = threading.Event()
main_done  = threading.Event()

def run_sumo():
    print("\n🚦 Starting SUMO simulation in background...")
    result = subprocess.run([sys.executable, "sumo_sim/run_traci.py"])
    if result.returncode == 0:
        print("✅ SUMO simulation complete!")
    else:
        print("❌ SUMO simulation failed!")
    sumo_done.set()

def run_main():
    print("\n🎬 Starting YOLO video processing...")
    result = subprocess.run([sys.executable, "main.py"])
    if result.returncode == 0:
        print("✅ Video processing complete!")
    else:
        print("❌ Video processing failed!")
    main_done.set()

# ── Main demo flow ────────────────────────────────────────
def run_demo():
    print_banner()

    print("=" * 52)
    print("STEP 1 — Checking project setup")
    print("=" * 52)
    if not check_files():
        print("\n❌ Some files missing! Check above.")
        return
    if not check_video():
        return
    print("\n✅ All checks passed!\n")

    print("=" * 52)
    print("STEP 2 — Starting SUMO Signal Simulation")
    print("=" * 52)
    # Start SUMO in background thread
    sumo_thread = threading.Thread(target=run_sumo, daemon=True)
    sumo_thread.start()
    print("✅ SUMO started in background thread")
    time.sleep(4)  # Give SUMO time to initialize before YOLO starts

    print("\n" + "=" * 52)
    print("STEP 3 — Processing Video with YOLO")
    print("=" * 52)
    # Run main.py in another thread so both run simultaneously
    main_thread = threading.Thread(target=run_main, daemon=True)
    main_thread.start()

    # Wait for both to finish
    print("\n⏳ Both systems running... waiting for completion\n")
    main_done.wait()   # wait for YOLO processing to finish
    sumo_done.wait()   # wait for SUMO to finish

    print("\n" + "=" * 52)
    print("STEP 4 — Generating Report")
    print("=" * 52)
    result = subprocess.run([sys.executable, "generate_report.py"])
    if result.returncode == 0:
        print("✅ Report generated: outputs/project_report.png")
    else:
        print("⚠️  Report generation failed — check generate_report.py")

    print("\n" + "=" * 52)
    print("STEP 5 — Launching Dashboard")
    print("=" * 52)
    print("Opening dashboard at http://localhost:8501")
    print("Press Ctrl+C to stop\n")
    subprocess.run([sys.executable, "-m", "streamlit", "run", "dashboard.py"])

if __name__ == "__main__":
    run_demo()