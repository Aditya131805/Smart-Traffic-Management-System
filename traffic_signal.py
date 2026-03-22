import time
from collections import deque
from dataclasses import dataclass, field

@dataclass
class SignalPhase:
    name:           str
    direction:      str
    green_duration: int
    is_active:      bool = False

class SignalController:
    def __init__(self):
        self.phases = [
            SignalPhase("NORTH_GREEN", "NORTH", green_duration=30),
            SignalPhase("SOUTH_GREEN", "SOUTH", green_duration=30),
            SignalPhase("EAST_GREEN",  "EAST",  green_duration=30),
            SignalPhase("WEST_GREEN",  "WEST",  green_duration=30),
        ]
        self.current_phase_idx  = 0
        self.min_green          = 10
        self.max_green          = 60
        self.emergency_override     = False
        self.emergency_until_frame  = None      # ✅ auto-expiry
        self.waiting_frames     = {p.direction: 0 for p in self.phases}  # ✅ starvation
        self.starvation_limit   = 150           # ~5s at 30fps
        self.log                = deque(maxlen=500)   # ✅ bounded

    def compute_green_time(self, vehicle_count: int) -> int:
        return min(self.min_green + (vehicle_count * 2), self.max_green)

    def update(self, lane_counts: dict) -> dict:
    # Auto-expire emergency override
        if self.emergency_override and self.emergency_until_frame is not None:
            self.emergency_until_frame -= 1
            if self.emergency_until_frame <= 0:
                self.clear_emergency()
                print("✅ Emergency override expired")

        if self.emergency_override:
            return self._get_state()

        # ✅ Round robin — rotate through all directions in order
        # Duration is weighted by vehicle count in that lane
        directions = ["NORTH", "SOUTH", "EAST", "WEST"]

        # Move to next direction every update
        self.current_phase_idx = (self.current_phase_idx + 1) % len(self.phases)
        current_dir = directions[self.current_phase_idx]

        for i, phase in enumerate(self.phases):
            if phase.direction == current_dir:
                phase.is_active      = True
                phase.green_duration = self.compute_green_time(
                    lane_counts.get(current_dir, 0)
                )
            else:
                phase.is_active = False

        state = self._get_state()
        self.log.append({
            "direction":      current_dir,
            "vehicle_count":  lane_counts.get(current_dir, 0),
            "green_duration": state["green_duration"]
        })
        return state

    def force_green(self, direction: str, duration_frames: int = 150):
        self.emergency_override    = True
        self.emergency_until_frame = duration_frames   # ✅ auto-expiry countdown
        for phase in self.phases:
            phase.is_active = (phase.direction == direction)
            if phase.is_active:
                phase.green_duration = duration_frames // 30
        print(f"🚨 EMERGENCY OVERRIDE: {direction} GREEN for {duration_frames} frames")

    def clear_emergency(self):
        self.emergency_override    = False
        self.emergency_until_frame = None

    def _get_state(self) -> dict:
        active = self.phases[self.current_phase_idx]
        return {
            "active_direction": active.direction,
            "green_duration":   active.green_duration,
            "emergency":        self.emergency_override,
            "all_phases": {
                p.direction: "GREEN" if p.is_active else "RED"
                for p in self.phases
            }
        }

    def display_state(self, state: dict):
        print("\n--- SIGNAL STATE ---")
        for direction, status in state["all_phases"].items():
            print(f"  {direction:6} → {status}")
        print(f"  Green Duration: {state['green_duration']}s")
        if state["emergency"]:
            print("  EMERGENCY OVERRIDE ACTIVE")
        print("--------------------")