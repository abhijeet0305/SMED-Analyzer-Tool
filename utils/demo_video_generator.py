"""
SMED Studio - Synthetic Shop-Floor Demo Video Generator
Generates realistic simulated stamping press die changeover videos (.mp4)
for baseline (BEFORE) and Kaizen-verified (AFTER) SMED trials.

Features:
- 100% Offline video synthesis using OpenCV (cv2) and NumPy.
- Real-time industrial HUD overlays:
  * Top bar: Machine name, Phase badge, Clip elapsed time, and Simulated shop-floor clock.
  * Center visual: Animated stamping press, bolster, die block, clamps, crane hoist,
    and laser crosshair alignment.
  * Border indicator: RED when simulated machine is STOPPED (Internal setup downtime),
    GREEN when machine is RUNNING (External setup or approved production).
  * Activity HUD: Step sequence, Standard Activity name, Internal/External badge,
    and shop-floor notes.
  * Bottom bar: Machine running state, target SMED badge, and dynamic progress bar.
- Fast generation: 640x360 @ 24 FPS (30s = 720 frames in ~2 seconds).
"""

import os
import math
from typing import Callable, Dict, List, Optional, Tuple
import cv2
import numpy as np

from database.db_manager import DatabaseManager, get_db
from database.seed_data import seed_sample_project


# Activity definitions for BEFORE (Unoptimized Baseline, ~40m 45s simulated)
BEFORE_ACTIVITIES = [
    {
        "name": "Retrieve new die & transport to press bed",
        "type": "External",
        "machine_running": True,
        "start_ratio": 0.00,
        "end_ratio": 0.10,
        "note": "Die retrieval occurring while press still runs previous batch.",
        "sim_start_sec": 0.0,
        "sim_end_sec": 290.0,
    },
    {
        "name": "Search for 24mm wrench and hex keys in toolbox",
        "type": "External",
        "machine_running": True,
        "start_ratio": 0.10,
        "end_ratio": 0.18,
        "note": "Operator walking to tool crib. 5S search waste detected.",
        "sim_start_sec": 290.0,
        "sim_end_sec": 485.0,
    },
    {
        "name": "Disconnect hydraulic lines, limit switches & sensors",
        "type": "Internal",
        "machine_running": False,
        "start_ratio": 0.18,
        "end_ratio": 0.28,
        "note": "Last good part finished. Press stopped. Lockout applied.",
        "sim_start_sec": 485.0,
        "sim_end_sec": 695.0,
    },
    {
        "name": "Unbolt 8 manual clamp bolts with breaker bar",
        "type": "Internal",
        "machine_running": False,
        "start_ratio": 0.28,
        "end_ratio": 0.45,
        "note": "Bottleneck! High torque manual unbolting with breaker bar.",
        "sim_start_sec": 695.0,
        "sim_end_sec": 1155.0,
    },
    {
        "name": "Crane hoist old die out to transport pallet",
        "type": "Internal",
        "machine_running": False,
        "start_ratio": 0.45,
        "end_ratio": 0.55,
        "note": "Overhead crane hoisting 12-ton old tooling out of bolster.",
        "sim_start_sec": 1155.0,
        "sim_end_sec": 1340.0,
    },
    {
        "name": "Crane hoist new die in & roughly position on bed",
        "type": "Internal",
        "machine_running": False,
        "start_ratio": 0.55,
        "end_ratio": 0.65,
        "note": "Lowering new die into bolster nest with rough positioning.",
        "sim_start_sec": 1340.0,
        "sim_end_sec": 1535.0,
    },
    {
        "name": "Align guide pins, dial indicator centering & clamp",
        "type": "Internal",
        "machine_running": False,
        "start_ratio": 0.65,
        "end_ratio": 0.80,
        "note": "Trial-and-error manual tapping & dial indicator centering.",
        "sim_start_sec": 1535.0,
        "sim_end_sec": 1925.0,
    },
    {
        "name": "Connect hydraulic lines & sensor harness",
        "type": "Internal",
        "machine_running": False,
        "start_ratio": 0.80,
        "end_ratio": 0.87,
        "note": "Manual tightening of separate fluid couplers & limit wiring.",
        "sim_start_sec": 1925.0,
        "sim_end_sec": 2070.0,
    },
    {
        "name": "Trial stamping: parts 1 to 5 (trial & error adjustments)",
        "type": "Internal",
        "machine_running": False,
        "start_ratio": 0.87,
        "end_ratio": 0.94,
        "note": "Defective scrap parts produced during manual tonnage tuning.",
        "sim_start_sec": 2070.0,
        "sim_end_sec": 2400.0,
    },
    {
        "name": "Produce 6th Consecutive OK Approval Part & QC signoff",
        "type": "Internal",
        "machine_running": False,
        "start_ratio": 0.94,
        "end_ratio": 1.00,
        "note": "SMED Cycle Boundary reached! 6 consecutive OK parts verified.",
        "sim_start_sec": 2400.0,
        "sim_end_sec": 2445.0,
    },
]

# Activity definitions for AFTER (Kaizen Verified, ~13m 25s simulated)
AFTER_ACTIVITIES = [
    {
        "name": "Retrieve new die & transport to press bed",
        "type": "External",
        "machine_running": True,
        "start_ratio": 0.00,
        "end_ratio": 0.12,
        "note": "KAIZEN: Pre-staged on roller shuttle table. Zero press downtime.",
        "sim_start_sec": 0.0,
        "sim_end_sec": 30.0,
    },
    {
        "name": "Disconnect hydraulic lines, limit switches & sensors",
        "type": "Internal",
        "machine_running": False,
        "start_ratio": 0.12,
        "end_ratio": 0.23,
        "note": "KAIZEN: Single multi-coupler block disconnected in 1 motion.",
        "sim_start_sec": 30.0,
        "sim_end_sec": 120.0,
    },
    {
        "name": "Unbolt 8 manual clamp bolts with breaker bar",
        "type": "Internal",
        "machine_running": False,
        "start_ratio": 0.23,
        "end_ratio": 0.35,
        "note": "KAIZEN: Pneumatic quarter-turn quick-clamps release in 55s!",
        "sim_start_sec": 120.0,
        "sim_end_sec": 175.0,
    },
    {
        "name": "Crane hoist old die out to transport pallet",
        "type": "Internal",
        "machine_running": False,
        "start_ratio": 0.35,
        "end_ratio": 0.48,
        "note": "Standardized rigging & side roll-out table. Swift extraction.",
        "sim_start_sec": 175.0,
        "sim_end_sec": 350.0,
    },
    {
        "name": "Crane hoist new die in & roughly position on bed",
        "type": "Internal",
        "machine_running": False,
        "start_ratio": 0.48,
        "end_ratio": 0.62,
        "note": "Roller shuttle bed guides die directly into centering nest.",
        "sim_start_sec": 350.0,
        "sim_end_sec": 530.0,
    },
    {
        "name": "Align guide pins, dial indicator centering & clamp",
        "type": "Internal",
        "machine_running": False,
        "start_ratio": 0.62,
        "end_ratio": 0.74,
        "note": "KAIZEN: Hardened locator pins & laser centering lock instantly.",
        "sim_start_sec": 530.0,
        "sim_end_sec": 625.0,
    },
    {
        "name": "Connect hydraulic lines & sensor harness",
        "type": "Internal",
        "machine_running": False,
        "start_ratio": 0.74,
        "end_ratio": 0.83,
        "note": "Quick-click hydraulic multi-manifold engaged.",
        "sim_start_sec": 625.0,
        "sim_end_sec": 685.0,
    },
    {
        "name": "Trial stamping: parts 1 to 5 (trial & error adjustments)",
        "type": "Internal",
        "machine_running": False,
        "start_ratio": 0.83,
        "end_ratio": 0.91,
        "note": "KAIZEN: Digital recipe loaded from PLC. First part approved!",
        "sim_start_sec": 685.0,
        "sim_end_sec": 725.0,
    },
    {
        "name": "Produce 6th Consecutive OK Approval Part & QC signoff",
        "type": "Internal",
        "machine_running": True,
        "start_ratio": 0.91,
        "end_ratio": 1.00,
        "note": "SUCCESS: 6/6 OK Parts! -67.1% Setup reduction verified!",
        "sim_start_sec": 725.0,
        "sim_end_sec": 805.0,
    },
]


def _format_time_clock(seconds: float) -> str:
    """Format seconds into HH:MM:SS or MM:SS."""
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hrs > 0:
        return f"{hrs:02d}:{mins:02d}:{secs:02d}"
    return f"{mins:02d}:{secs:02d}"


def _get_active_activity(activities: List[Dict], ratio: float) -> Tuple[int, Dict]:
    """Find the current activity dictionary based on current progress ratio."""
    for idx, act in enumerate(activities, 1):
        if act["start_ratio"] <= ratio <= act["end_ratio"]:
            return idx, act
    # Default to last activity if at 1.0
    return len(activities), activities[-1]


def render_smed_frame(
    phase: str,
    frame_idx: int,
    total_frames: int,
    fps: int = 24,
    width: int = 640,
    height: int = 360,
    machine_name: str = "KOMATSU 800-TON TRANSFER PRESS #04",
) -> np.ndarray:
    """
    Render a single synthetic frame with full industrial HUD and dynamic visuals.
    Returns a BGR uint8 NumPy image (height x width x 3).
    """
    frame_ratio = min(1.0, max(0.0, frame_idx / max(1, total_frames - 1)))
    activities = BEFORE_ACTIVITIES if phase == "BEFORE" else AFTER_ACTIVITIES
    act_idx, act = _get_active_activity(activities, frame_ratio)

    is_machine_running = act["machine_running"]
    is_internal = (act["type"] == "Internal")
    current_clip_sec = frame_idx / fps
    total_clip_sec = total_frames / fps

    # Interpolate simulated shop-floor clock
    act_span = max(0.0001, act["end_ratio"] - act["start_ratio"])
    act_progress = (frame_ratio - act["start_ratio"]) / act_span
    sim_current_sec = act["sim_start_sec"] + act_progress * (act["sim_end_sec"] - act["sim_start_sec"])

    # Base Canvas: Dark Industrial Slate (#0B0F17)
    img = np.full((height, width, 3), (23, 15, 11), dtype=np.uint8)

    # 1. Subtle Shop-Floor Grid Pattern
    for y in range(60, height - 40, 24):
        cv2.line(img, (10, y), (width - 10, y), (30, 22, 18), 1)
    for x in range(30, width - 10, 40):
        cv2.line(img, (x, 60), (x, height - 40), (28, 20, 16), 1)

    # 2. Draw Simulated Press & Tooling Scene in Center
    _draw_press_scene(img, width, height, phase, frame_ratio, act_idx, act, is_machine_running)

    # 3. Activity Banner & Kaizen HUD (Upper Center)
    _draw_activity_hud(img, width, act_idx, len(activities), act, is_internal)

    # 4. Top Industrial HUD Header
    _draw_top_header(
        img, width, machine_name, phase,
        current_clip_sec, total_clip_sec, sim_current_sec
    )

    # 5. Bottom Status Bar & Progress
    _draw_bottom_bar(img, width, height, is_machine_running, frame_ratio, phase)

    # 6. Border Indicator (Red = Stopped / Internal downtime, Green = Running / External)
    border_color = (34, 197, 94) if is_machine_running else (34, 34, 239)
    cv2.rectangle(img, (0, 0), (width - 1, height - 1), border_color, 4)

    return img


def _draw_top_header(
    img: np.ndarray,
    width: int,
    machine_name: str,
    phase: str,
    current_clip_sec: float,
    total_clip_sec: float,
    sim_current_sec: float,
):
    """Draw top industrial header with machine name, phase, and synchronized clocks."""
    # Banner background
    cv2.rectangle(img, (4, 4), (width - 4, 48), (20, 12, 8), -1)
    cv2.line(img, (4, 48), (width - 4, 48), (55, 45, 35), 1)

    # Left: Machine name & Phase
    cv2.putText(
        img, f"MACHINE: {machine_name}", (16, 22),
        cv2.FONT_HERSHEY_SIMPLEX, 0.44, (241, 245, 249), 1, cv2.LINE_AA
    )

    phase_label = f"PHASE: {phase} TRIAL #1 (BASELINE)" if phase == "BEFORE" else f"PHASE: {phase} TRIAL #1 (KAIZEN VERIFIED)"
    phase_color = (235, 165, 14) if phase == "BEFORE" else (16, 185, 129)
    cv2.putText(
        img, phase_label, (16, 40),
        cv2.FONT_HERSHEY_SIMPLEX, 0.40, phase_color, 1, cv2.LINE_AA
    )

    # Right: Dual Clocks (Clip elapsed & Simulated shop-floor clock)
    clip_txt = f"CLIP: {current_clip_sec:04.1f}s / {total_clip_sec:04.1f}s"
    cv2.putText(
        img, clip_txt, (width - 180, 22),
        cv2.FONT_HERSHEY_SIMPLEX, 0.38, (148, 163, 184), 1, cv2.LINE_AA
    )

    sim_txt = f"FLOOR CLOCK: {_format_time_clock(sim_current_sec)}"
    cv2.putText(
        img, sim_txt, (width - 180, 40),
        cv2.FONT_HERSHEY_SIMPLEX, 0.42, (56, 189, 248), 1, cv2.LINE_AA
    )


def _draw_activity_hud(
    img: np.ndarray,
    width: int,
    act_idx: int,
    total_acts: int,
    act: Dict,
    is_internal: bool,
):
    """Draw prominent activity card with Internal/External badge and notes."""
    hud_y = 54
    hud_h = 44

    # Background box
    cv2.rectangle(img, (12, hud_y), (width - 12, hud_y + hud_h), (26, 18, 14), -1)
    cv2.rectangle(img, (12, hud_y), (width - 12, hud_y + hud_h), (51, 65, 85), 1)

    # Badge for Type (INTERNAL vs EXTERNAL)
    if is_internal:
        badge_txt = "[ INTERNAL SETUP - MACHINE STOPPED ]"
        badge_color = (68, 68, 239)   # Red
    else:
        badge_txt = "[ EXTERNAL SETUP - MACHINE RUNNING ]"
        badge_color = (34, 197, 94)   # Green

    cv2.putText(
        img, badge_txt, (20, hud_y + 16),
        cv2.FONT_HERSHEY_SIMPLEX, 0.38, badge_color, 1, cv2.LINE_AA
    )

    # Step sequence & Activity name (truncate if too long)
    title = f"Step {act_idx}/{total_acts}: {act['name']}"
    if len(title) > 62:
        title = title[:59] + "..."
    cv2.putText(
        img, title, (20, hud_y + 34),
        cv2.FONT_HERSHEY_SIMPLEX, 0.43, (255, 255, 255), 1, cv2.LINE_AA
    )

    # Note on right side
    note = act.get("note", "")
    if len(note) > 42:
        note = note[:39] + "..."
    cv2.putText(
        img, note, (width - 310, hud_y + 25),
        cv2.FONT_HERSHEY_SIMPLEX, 0.35, (148, 163, 184), 1, cv2.LINE_AA
    )


def _draw_press_scene(
    img: np.ndarray,
    width: int,
    height: int,
    phase: str,
    frame_ratio: float,
    act_idx: int,
    act: Dict,
    is_machine_running: bool,
):
    """Render graphic representation of stamping press, die bolster, and active mechanism."""
    # Press Center Coordinates
    cx = width // 2
    ground_y = height - 60

    # 1. Press Steel Uprights (Left & Right Columns)
    col_w = 40
    col_h = 160
    # Left Column
    cv2.rectangle(img, (cx - 190, ground_y - col_h), (cx - 190 + col_w, ground_y), (45, 35, 30), -1)
    cv2.rectangle(img, (cx - 190, ground_y - col_h), (cx - 190 + col_w, ground_y), (80, 65, 55), 1)
    # Right Column
    cv2.rectangle(img, (cx + 150, ground_y - col_h), (cx + 150 + col_w, ground_y), (45, 35, 30), -1)
    cv2.rectangle(img, (cx + 150, ground_y - col_h), (cx + 150 + col_w, ground_y), (80, 65, 55), 1)

    # Crown Crossbeam
    cv2.rectangle(img, (cx - 200, ground_y - col_h - 22), (cx + 200, ground_y - col_h), (55, 42, 35), -1)
    cv2.rectangle(img, (cx - 200, ground_y - col_h - 22), (cx + 200, ground_y - col_h), (90, 75, 65), 1)
    cv2.putText(
        img, "KOMATSU 800T PRESS BED", (cx - 95, ground_y - col_h - 6),
        cv2.FONT_HERSHEY_SIMPLEX, 0.40, (180, 160, 150), 1, cv2.LINE_AA
    )

    # Lower Bolster Plate
    cv2.rectangle(img, (cx - 150, ground_y - 24), (cx + 150, ground_y), (50, 40, 32), -1)
    cv2.rectangle(img, (cx - 150, ground_y - 24), (cx + 150, ground_y), (100, 85, 75), 1)

    # 2. Moving Press Ram / Die State Animation
    ram_base_y = ground_y - col_h + 10
    ram_offset = 0

    # If machine running or trial stamping, animate ram oscillation
    if is_machine_running or "stamping" in act["name"].lower():
        # Pulsing stroke
        pulse = math.sin(frame_ratio * 40 * math.pi)
        ram_offset = int(18 + 14 * pulse)
    else:
        ram_offset = 12

    # Draw Ram
    ram_y = ram_base_y + ram_offset
    cv2.rectangle(img, (cx - 120, ram_y), (cx + 120, ram_y + 36), (65, 52, 42), -1)
    cv2.rectangle(img, (cx - 120, ram_y), (cx + 120, ram_y + 36), (120, 100, 85), 1)
    cv2.putText(
        img, "UPPER SLIDE / RAM", (cx - 65, ram_y + 22),
        cv2.FONT_HERSHEY_SIMPLEX, 0.38, (210, 200, 190), 1, cv2.LINE_AA
    )

    # 3. Die Block on Bolster
    die_w = 190
    die_h = 50
    die_x = cx - die_w // 2
    die_y = ground_y - 24 - die_h

    # Color changes based on Before/After & Activity
    if "hoist old" in act["name"].lower():
        # Old die lifting up
        lift_y = die_y - int(30 * (frame_ratio - act["start_ratio"]) / max(0.01, act["end_ratio"] - act["start_ratio"]))
        cv2.rectangle(img, (die_x, lift_y), (die_x + die_w, lift_y + die_h), (40, 40, 120), -1)
        # Crane Cables
        cv2.line(img, (die_x + 20, lift_y), (cx, ground_y - col_h - 10), (180, 180, 180), 2)
        cv2.line(img, (die_x + die_w - 20, lift_y), (cx, ground_y - col_h - 10), (180, 180, 180), 2)
        cv2.putText(img, "OLD DIE HOISTING", (die_x + 30, lift_y + 28), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (255, 255, 255), 1)
    elif "hoist new" in act["name"].lower():
        # New die lowering down
        lower_y = die_y - 30 + int(30 * (frame_ratio - act["start_ratio"]) / max(0.01, act["end_ratio"] - act["start_ratio"]))
        cv2.rectangle(img, (die_x, lower_y), (die_x + die_w, lower_y + die_h), (120, 70, 30), -1)
        cv2.line(img, (die_x + 20, lower_y), (cx, ground_y - col_h - 10), (180, 180, 180), 2)
        cv2.line(img, (die_x + die_w - 20, lower_y), (cx, ground_y - col_h - 10), (180, 180, 180), 2)
        cv2.putText(img, "NEW DIE LOWERING", (die_x + 26, lower_y + 28), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (255, 255, 255), 1)
    else:
        # Stationary Die on Bed
        die_color = (130, 80, 35) if phase == "AFTER" else (80, 70, 60)
        cv2.rectangle(img, (die_x, die_y), (die_x + die_w, die_y + die_h), die_color, -1)
        cv2.rectangle(img, (die_x, die_y), (die_x + die_w, die_y + die_h), (160, 140, 120), 1)
        cv2.putText(img, "AUTOMOTIVE HOOD DIE", (die_x + 14, die_y + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1)

    # 4. Animated Clamps (Bolt unbolting in BEFORE vs Pneumatic Quarter-Turn in AFTER)
    if "unbolt" in act["name"].lower() or "clamp" in act["name"].lower():
        if phase == "BEFORE":
            # Red warning manual bolts
            for bx in [die_x - 12, die_x + die_w + 2]:
                cv2.rectangle(img, (bx, die_y + 12), (bx + 10, die_y + 36), (30, 30, 220), -1)
                # Animate oscillating wrench angle
                angle = math.sin(frame_ratio * 30) * 20
                wx = int(bx + 5 + angle)
                cv2.line(img, (bx + 5, die_y + 24), (wx, die_y - 12), (180, 180, 180), 2)
            cv2.putText(img, "! 8 MANUAL BOLTS (460s) !", (cx - 80, die_y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (60, 60, 240), 1)
        else:
            # Green quick pneumatic clamps
            for bx in [die_x - 12, die_x + die_w + 2]:
                cv2.rectangle(img, (bx, die_y + 12), (bx + 10, die_y + 36), (34, 197, 94), -1)
            cv2.putText(img, "QUICK-CLAMP UNLOCKED (55s)", (cx - 95, die_y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (34, 197, 94), 1)

    # 5. Laser Alignment Crosshairs or Dial Indicator
    if "align" in act["name"].lower():
        if phase == "AFTER":
            # Laser Crosshairs
            cv2.line(img, (cx, die_y - 15), (cx, die_y + die_h + 10), (0, 255, 255), 1)
            cv2.line(img, (cx - 40, die_y + 25), (cx + 40, die_y + 25), (0, 255, 255), 1)
            cv2.circle(img, (cx, die_y + 25), 12, (0, 255, 255), 1)
            cv2.putText(img, "LASER PIN LOCK OK", (cx - 55, die_y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (0, 255, 255), 1)
        else:
            # Oscillating Dial Indicator
            needle_x = cx + int(15 * math.sin(frame_ratio * 50))
            cv2.circle(img, (cx, die_y - 10), 14, (200, 200, 200), -1)
            cv2.line(img, (cx, die_y - 10), (needle_x, die_y - 20), (30, 30, 200), 2)
            cv2.putText(img, "MANUAL DIAL TAPPING", (cx - 70, die_y - 28), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (180, 180, 180), 1)

    # 6. Quality Approval Part Gauge
    if "produce 6th" in act["name"].lower() or "ok" in act["name"].lower():
        # Highlighting quality boundary
        box_w = 260
        box_h = 32
        cv2.rectangle(img, (cx - box_w // 2, die_y + 6), (cx + box_w // 2, die_y + 6 + box_h), (16, 85, 45), -1)
        cv2.rectangle(img, (cx - box_w // 2, die_y + 6), (cx + box_w // 2, die_y + 6 + box_h), (52, 211, 153), 1)
        cv2.putText(
            img, "[ APPROVAL PART: 6/6 OK! ]", (cx - 96, die_y + 28),
            cv2.FONT_HERSHEY_SIMPLEX, 0.46, (240, 255, 240), 1, cv2.LINE_AA
        )


def _draw_bottom_bar(
    img: np.ndarray,
    width: int,
    height: int,
    is_machine_running: bool,
    frame_ratio: float,
    phase: str,
):
    """Draw bottom status bar showing machine state, SMED reduction badge, and progress bar."""
    bar_y = height - 36
    cv2.rectangle(img, (4, bar_y), (width - 4, height - 4), (18, 12, 8), -1)
    cv2.line(img, (4, bar_y), (width - 4, bar_y), (50, 40, 32), 1)

    # Machine State on bottom left
    if is_machine_running:
        status_txt = "● PRESS STATE: RUNNING [PRODUCTIVE]"
        status_color = (34, 197, 94)
    else:
        status_txt = "■ PRESS STATE: STOPPED [DOWNTIME LOSS]"
        status_color = (60, 60, 240)

    cv2.putText(
        img, status_txt, (14, bar_y + 18),
        cv2.FONT_HERSHEY_SIMPLEX, 0.38, status_color, 1, cv2.LINE_AA
    )

    # Target Reduction badge in middle
    target_txt = "TARGET: >= 50% SETUP REDUCTION (< 10 MIN)"
    cv2.putText(
        img, target_txt, (width // 2 - 130, bar_y + 18),
        cv2.FONT_HERSHEY_SIMPLEX, 0.36, (203, 213, 225), 1, cv2.LINE_AA
    )

    # Progress Bar at the very bottom
    prog_y = height - 8
    prog_w = width - 16
    cv2.rectangle(img, (8, prog_y), (8 + prog_w, prog_y + 4), (40, 30, 25), -1)
    filled_w = int(prog_w * frame_ratio)
    fill_color = (235, 165, 14) if phase == "BEFORE" else (34, 197, 94)
    if filled_w > 0:
        cv2.rectangle(img, (8, prog_y), (8 + filled_w, prog_y + 4), fill_color, -1)


def generate_smed_demo_video(
    phase: str = "BEFORE",
    output_path: str = "sample_videos/before_trial_01.mp4",
    duration_sec: float = 30.0,
    fps: int = 24,
    progress_callback: Optional[Callable[[int, str], None]] = None,
) -> str:
    """
    Generate an accelerated synthetic MP4 video demonstrating an industrial SMED trial.
    :param phase: "BEFORE" or "AFTER"
    :param output_path: Destination file path
    :param duration_sec: Video length in seconds (default 30.0s)
    :param fps: Frames per second (default 24)
    :param progress_callback: Optional callback receiving (progress_pct: int, message: str)
    :return: Absolute file path of generated video
    """
    output_abs = os.path.abspath(output_path)
    os.makedirs(os.path.dirname(output_abs), exist_ok=True)

    width = 640
    height = 360
    total_frames = int(duration_sec * fps)

    # Initialize OpenCV VideoWriter using mp4v
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(output_abs, fourcc, float(fps), (width, height))
    if not writer.isOpened():
        # Fallback to XVID / avi if mp4v fails on custom platform
        fourcc = cv2.VideoWriter_fourcc(*"XVID")
        writer = cv2.VideoWriter(output_abs, fourcc, float(fps), (width, height))

    if not writer.isOpened():
        raise RuntimeError(f"OpenCV failed to open VideoWriter for {output_abs}")

    try:
        for idx in range(total_frames):
            frame = render_smed_frame(
                phase=phase.upper(),
                frame_idx=idx,
                total_frames=total_frames,
                fps=fps,
                width=width,
                height=height,
            )
            writer.write(frame)

            if progress_callback and (idx % 24 == 0 or idx == total_frames - 1):
                pct = int(((idx + 1) / total_frames) * 100)
                progress_callback(pct, f"Synthesizing {phase} Demo Video: frame {idx + 1}/{total_frames} ({pct}%)")
    finally:
        writer.release()

    return output_abs


def generate_all_demo_videos(
    output_dir: str = "sample_videos",
    duration_sec: float = 30.0,
    fps: int = 24,
    progress_callback: Optional[Callable[[int, str], None]] = None,
) -> Dict[str, str]:
    """
    Generate both BEFORE and AFTER synthetic demo videos.
    :param output_dir: Directory to save generated videos
    :param duration_sec: Length of each video in seconds
    :param fps: Frames per second
    :param progress_callback: Optional progress reporter
    :return: Dictionary mapping {"BEFORE": abs_path, "AFTER": abs_path}
    """
    os.makedirs(output_dir, exist_ok=True)
    before_path = os.path.join(output_dir, "before_trial_01.mp4")
    after_path = os.path.join(output_dir, "after_trial_01.mp4")

    if progress_callback:
        progress_callback(10, "Generating BEFORE Baseline Demo Video...")
    gen_before = generate_smed_demo_video(
        phase="BEFORE",
        output_path=before_path,
        duration_sec=duration_sec,
        fps=fps,
        progress_callback=progress_callback,
    )

    if progress_callback:
        progress_callback(50, "Generating AFTER Kaizen Verification Demo Video...")
    gen_after = generate_smed_demo_video(
        phase="AFTER",
        output_path=after_path,
        duration_sec=duration_sec,
        fps=fps,
        progress_callback=progress_callback,
    )

    if progress_callback:
        progress_callback(100, "Demo Videos generated successfully!")

    return {"BEFORE": gen_before, "AFTER": gen_after}


def generate_and_seed_demo_project(
    db: DatabaseManager,
    output_dir: str = "sample_videos",
    progress_callback: Optional[Callable[[int, str], None]] = None,
) -> int:
    """
    Ensure the sample project exists in the database, generate both synthetic
    videos in `sample_videos/`, and link the actual video filepaths directly
    to the video_trials records in SQLite.
    :return: project_id
    """
    if progress_callback:
        progress_callback(5, "Checking sample project in database...")

    # 1. Generate the demo videos
    video_paths = generate_all_demo_videos(
        output_dir=output_dir,
        progress_callback=progress_callback,
    )

    # 2. Check if sample project already exists
    projects = db.get_all_projects()
    sample_proj = None
    for p in projects:
        if "Automotive Stamping Line 4" in p["name"]:
            sample_proj = p
            break

    if not sample_proj:
        # Seed it
        project_id = seed_sample_project(db)
    else:
        project_id = sample_proj["id"]

    # 3. Update the video file paths in database to point to actual generated files
    with db.get_connection() as conn:
        cursor = conn.cursor()
        # Update Before trials
        cursor.execute(
            """
            UPDATE video_trials
            SET file_path = ?
            WHERE project_id = ? AND phase = 'BEFORE' AND trial_number = 1;
            """,
            (video_paths["BEFORE"], project_id),
        )
        cursor.execute(
            """
            UPDATE video_trials
            SET file_path = ?
            WHERE project_id = ? AND phase = 'BEFORE' AND trial_number = 2;
            """,
            (video_paths["BEFORE"], project_id),
        )
        # Update After trial
        cursor.execute(
            """
            UPDATE video_trials
            SET file_path = ?
            WHERE project_id = ? AND phase = 'AFTER' AND trial_number = 1;
            """,
            (video_paths["AFTER"], project_id),
        )

    if progress_callback:
        progress_callback(100, f"Sample Project (ID #{project_id}) linked to demo videos!")

    return project_id
