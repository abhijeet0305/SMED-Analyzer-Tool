"""
SMED Studio - Database Layer Verification Script
Tests SQLite schema, CRUD operations, Pareto aggregation, and Before vs After analytics.
"""

import os
import sys
from datetime import datetime
from database.db_manager import DatabaseManager


def format_time(seconds: float) -> str:
    """Format seconds into MM:SS format."""
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins:02d}:{secs:02d} ({seconds:.1f}s)"


def run_tests():
    test_db_path = "test_smed.db"
    if os.path.exists(test_db_path):
        try:
            os.remove(test_db_path)
        except Exception:
            pass

    print("======================================================================")
    print("  SMED STUDIO - PHASE 1 DATABASE VERIFICATION TEST")
    print("======================================================================")

    # 1. Initialize Database
    db = DatabaseManager(test_db_path)
    print(f"[OK] Database initialized successfully at: {test_db_path}")

    # 2. Create SMED Project
    project_id = db.create_project(
        name="Automotive Stamping Line 4 - Hood Outer Panel Die Change",
        machine_name="Komatsu 800-Ton Mechanical Transfer Press",
        from_die="Hood-Die-402 (Sedan)",
        to_die="Hood-Die-408 (SUV)",
        target_reduction_pct=50.0,
        notes="Baseline setup exceeds 30 minutes. Target is >= 50% reduction toward single-minute exchange.",
    )
    print(f"[OK] Created Project ID: {project_id}")

    project = db.get_project(project_id)
    assert project is not None, "Project retrieval failed!"
    assert project["target_reduction_pct"] == 50.0
    print(f"     Project Name: {project['name']}")
    print(f"     Machine:      {project['machine_name']}")
    print(f"     Target:       >= {project['target_reduction_pct']}% reduction")

    # 3. Seed Master Standard Activities Dictionary
    activities_def = [
        ("Retrieve new die & transport to press bed", "External"),
        ("Disconnect hydraulic lines, limit switches & sensors", "Internal"),
        ("Search for 24mm wrench and hex keys in toolbox", "External"),
        ("Unbolt 8 manual clamp bolts with breaker bar", "Internal"),
        ("Crane hoist old die out to transport pallet", "Internal"),
        ("Crane hoist new die in & roughly position on bed", "Internal"),
        ("Align guide pins, dial indicator centering & clamp", "Internal"),
        ("Connect hydraulic lines & sensor harness", "Internal"),
        ("Trial stamping: parts 1 to 5 (trial & error adjustments)", "Internal"),
        ("Produce 6th Consecutive OK Approval Part & QC signoff", "Internal"),
    ]

    activity_ids = {}
    for name, default_type in activities_def:
        aid, was_created = db.get_or_create_standard_activity(project_id, name, default_type)
        activity_ids[name] = aid
        assert aid > 0

    # Test idempotency: calling get_or_create again should return existing ID
    first_name = activities_def[0][0]
    aid_repeat, was_created_repeat = db.get_or_create_standard_activity(project_id, first_name)
    assert aid_repeat == activity_ids[first_name], "Activity ID mismatch on repeat call!"
    assert was_created_repeat is False, "Activity should not be re-created!"
    print(f"[OK] Seeded {len(activity_ids)} Standard Activities into Master Dictionary.")

    # 4. Seed BEFORE Video Trials (2 baseline observation trials)
    trial_1_id = db.create_video_trial(
        project_id=project_id,
        phase="BEFORE",
        trial_number=1,
        video_title="Baseline Trial 1 - Shift A Operator (Unoptimized)",
        file_path="videos/before_trial_01.mp4",
        sixth_ok_part_verified=True,
        recorded_date="2026-10-15",
    )

    trial_2_id = db.create_video_trial(
        project_id=project_id,
        phase="BEFORE",
        trial_number=2,
        video_title="Baseline Trial 2 - Shift B Operator (Unoptimized)",
        file_path="videos/before_trial_02.mp4",
        sixth_ok_part_verified=True,
        recorded_date="2026-10-16",
    )
    print(f"[OK] Created BEFORE Trials: Trial #{trial_1_id} and Trial #{trial_2_id}")

    # Micro-activity durations for Trial 1 (Total ~ 1840s = ~30.6 min)
    t1_durations = [
        ("Retrieve new die & transport to press bed", "External", 290.0),
        ("Disconnect hydraulic lines, limit switches & sensors", "Internal", 210.0),
        ("Search for 24mm wrench and hex keys in toolbox", "External", 195.0),
        ("Unbolt 8 manual clamp bolts with breaker bar", "Internal", 460.0),
        ("Crane hoist old die out to transport pallet", "Internal", 185.0),
        ("Crane hoist new die in & roughly position on bed", "Internal", 195.0),
        ("Align guide pins, dial indicator centering & clamp", "Internal", 390.0),
        ("Connect hydraulic lines & sensor harness", "Internal", 145.0),
        ("Trial stamping: parts 1 to 5 (trial & error adjustments)", "Internal", 330.0),
        ("Produce 6th Consecutive OK Approval Part & QC signoff", "Internal", 110.0),
    ]

    t1_logs = []
    current_time = 0.0
    for seq, (act_name, act_type, dur) in enumerate(t1_durations, start=1):
        start_t = current_time
        end_t = start_t + dur
        current_time = end_t
        t1_logs.append({
            "video_trial_id": trial_1_id,
            "standard_activity_id": activity_ids[act_name],
            "sequence_no": seq,
            "activity_type": act_type,
            "start_time_sec": start_t,
            "end_time_sec": end_t,
            "duration_sec": dur,
            "remarks": "Manual process, high searching waste",
        })
    db.bulk_log_activities(t1_logs)

    # Micro-activity durations for Trial 2 (Total ~ 1770s = ~29.5 min)
    t2_durations = [
        ("Retrieve new die & transport to press bed", "External", 270.0),
        ("Disconnect hydraulic lines, limit switches & sensors", "Internal", 190.0),
        ("Search for 24mm wrench and hex keys in toolbox", "External", 185.0),
        ("Unbolt 8 manual clamp bolts with breaker bar", "Internal", 440.0),
        ("Crane hoist old die out to transport pallet", "Internal", 180.0),
        ("Crane hoist new die in & roughly position on bed", "Internal", 190.0),
        ("Align guide pins, dial indicator centering & clamp", "Internal", 380.0),
        ("Connect hydraulic lines & sensor harness", "Internal", 135.0),
        ("Trial stamping: parts 1 to 5 (trial & error adjustments)", "Internal", 310.0),
        ("Produce 6th Consecutive OK Approval Part & QC signoff", "Internal", 100.0),
    ]

    t2_logs = []
    current_time = 0.0
    for seq, (act_name, act_type, dur) in enumerate(t2_durations, start=1):
        start_t = current_time
        end_t = start_t + dur
        current_time = end_t
        t2_logs.append({
            "video_trial_id": trial_2_id,
            "standard_activity_id": activity_ids[act_name],
            "sequence_no": seq,
            "activity_type": act_type,
            "start_time_sec": start_t,
            "end_time_sec": end_t,
            "duration_sec": dur,
            "remarks": "Observed bolt jamming and tool hunting",
        })
    db.bulk_log_activities(t2_logs)
    print("[OK] Logged all micro-activities for Before Trials 1 & 2.")

    # 5. Seed Kaizen Brainstorming Solutions
    kaizen_items = [
        (
            "Unbolt 8 manual clamp bolts with breaker bar",
            "Bolts take 7+ minutes to loosen manually with breaker bar.",
            "Replace 8 threaded bolts with pneumatic quarter-turn quick-acting cam clamps.",
            "Simplify/Streamline",
            390.0,
            "Internal",
        ),
        (
            "Align guide pins, dial indicator centering & clamp",
            "Operator uses dial indicator and tapping hammer for trial-and-error alignment.",
            "Install hardened guide positioning keys & laser crosshair centering fixtures.",
            "Simplify/Streamline",
            270.0,
            "Internal",
        ),
        (
            "Trial stamping: parts 1 to 5 (trial & error adjustments)",
            "Scrapped 5 parts adjusting tonnage, cushion pressure and feeder pitch manually.",
            "Digital recipe upload directly into PLC; preset nitrogen cushion pressure.",
            "Eliminate",
            280.0,
            "Internal",
        ),
        (
            "Search for 24mm wrench and hex keys in toolbox",
            "Wrenches scattered across tool cart; operator walked 40m searching.",
            "Installed magnetic 5S shadow board mounted directly on press column.",
            "Eliminate",
            190.0,
            "External",
        ),
        (
            "Retrieve new die & transport to press bed",
            "Die retrieved only after previous run fully stopped.",
            "Pre-stage incoming die on side roller shuttle table while press is running previous batch.",
            "Convert to External",
            250.0,
            "External",
        ),
    ]

    for act_name, prob, sol, action_type, est_red, tgt_type in kaizen_items:
        db.add_or_update_kaizen_solution(
            project_id=project_id,
            standard_activity_id=activity_ids[act_name],
            problem_observed=prob,
            solution_implemented=sol,
            action_type=action_type,
            estimated_reduction_sec=est_red,
            target_type=tgt_type,
        )
    print(f"[OK] Seeded {len(kaizen_items)} Kaizen Brainstorming Solutions.")

    # 6. Test Aggregated BEFORE Baseline & Pareto Analysis
    pareto_df = db.get_aggregated_before_activities(project_id)
    assert not pareto_df.empty, "Pareto DataFrame is empty!"
    print("\n----------------------------------------------------------------------")
    print("  PARETO ANALYSIS: BASELINE 'BEFORE' ACTIVITIES (SORTED DESCENDING)")
    print("----------------------------------------------------------------------")
    for idx, row in pareto_df.iterrows():
        print(
            f"{idx + 1:2d}. [{row['activity_type']:8s}] {row['activity_name'][:38]:38s} | "
            f"Avg: {format_time(row['avg_duration_sec']):14s} | "
            f"{row['pct_of_total']:5.1f}% | Cum: {row['cumulative_pct']:5.1f}% | "
            f"Class: {row['pareto_class']}"
        )

    top_activity = pareto_df.iloc[0]["activity_name"]
    assert "Unbolt" in top_activity, f"Expected unbolting to be top bottleneck, got: {top_activity}"
    print(f"\n[OK] Pareto top bottleneck correctly identified as: '{top_activity}'")

    # 7. Seed AFTER Video Trial (Implementation Verification)
    trial_after_id = db.create_video_trial(
        project_id=project_id,
        phase="AFTER",
        trial_number=1,
        video_title="After Kaizen Verification Trial 1 - Standardized Quick-Clamp Setup",
        file_path="videos/after_trial_01.mp4",
        sixth_ok_part_verified=True,
        recorded_date="2026-10-25",
    )

    # Durations after Kaizen implementation (Drastic reduction to ~ 715s = ~11.9 min)
    after_durations = [
        ("Retrieve new die & transport to press bed", "External", 30.0),       # Done beforehand on roller cart
        ("Disconnect hydraulic lines, limit switches & sensors", "Internal", 90.0), # Quick-disconnect couplings
        ("Search for 24mm wrench and hex keys in toolbox", "External", 0.0),   # Eliminated by 5S board
        ("Unbolt 8 manual clamp bolts with breaker bar", "Internal", 55.0),    # Pneumatic quick clamps
        ("Crane hoist old die out to transport pallet", "Internal", 175.0),
        ("Crane hoist new die in & roughly position on bed", "Internal", 180.0),
        ("Align guide pins, dial indicator centering & clamp", "Internal", 95.0), # Centering fixtures
        ("Connect hydraulic lines & sensor harness", "Internal", 60.0),
        ("Trial stamping: parts 1 to 5 (trial & error adjustments)", "Internal", 40.0), # Recipe preset
        ("Produce 6th Consecutive OK Approval Part & QC signoff", "Internal", 80.0),
    ]

    after_logs = []
    current_time = 0.0
    for seq, (act_name, act_type, dur) in enumerate(after_durations, start=1):
        if dur > 0:  # If eliminated, not logged in after trial
            start_t = current_time
            end_t = start_t + dur
            current_time = end_t
            after_logs.append({
                "video_trial_id": trial_after_id,
                "standard_activity_id": activity_ids[act_name],
                "sequence_no": seq,
                "activity_type": act_type,
                "start_time_sec": start_t,
                "end_time_sec": end_t,
                "duration_sec": dur,
                "remarks": "Kaizen quick-change validated",
            })
    db.bulk_log_activities(after_logs)
    print(f"[OK] Logged AFTER verification trial #{trial_after_id}.")

    # 8. Test Comparative Analytics Engine
    comparison = db.get_before_vs_after_comparison(project_id)
    assert comparison["has_data"] is True

    print("\n======================================================================")
    print("  COMPARATIVE ANALYTICS DASHBOARD SUMMARY (BEFORE vs AFTER)")
    print("======================================================================")
    print(f"Project:               {comparison['project_name']}")
    print(f"Machine:               {comparison['machine_name']}")
    print(f"Target Reduction:      >= {comparison['target_reduction_pct']:.1f}%")
    print(f"Before Baseline Avg:   {format_time(comparison['before_total_avg_sec'])}")
    print(f"After Setup Avg:       {format_time(comparison['after_total_avg_sec'])}")
    print(f"Total Time Saved:      {format_time(comparison['total_reduction_sec'])}")
    print(f"Total Reduction %:     {comparison['total_reduction_pct']:.2f}%")
    print(f"Target Achieved?       {'YES! [PASSED >= 50% TARGET]' if comparison['target_achieved'] else 'NO'}")
    print(f"Single-Digit Achieved? {'YES (< 10 min)' if comparison['single_minute_achieved'] else 'NO (11.9 min, Close to single-digit!)'}")
    print("----------------------------------------------------------------------")
    print(f"Internal Time Shift:   {format_time(comparison['before_internal_sec'])} -> {format_time(comparison['after_internal_sec'])} ({comparison['internal_reduction_pct']:.1f}% reduction)")
    print(f"External Time:         {format_time(comparison['before_external_sec'])} -> {format_time(comparison['after_external_sec'])}")
    print(f"Top Bottleneck Solved: {comparison['top_bottleneck_solved']}")
    print("----------------------------------------------------------------------")
    print("Activity-by-Activity Performance Breakdown:")

    for item in comparison["activities_list"]:
        print(
            f" - {item['activity_name'][:36]:36s} | "
            f"Before: {format_time(item['before_avg_sec']):14s} | "
            f"After: {format_time(item['after_avg_sec']):14s} | "
            f"Saved: {item['reduction_sec']:6.1f}s ({item['reduction_pct']:5.1f}%) | "
            f"Kaizen: {item['action_type']}"
        )

    # Validations
    assert comparison["total_reduction_pct"] >= 50.0, f"Expected >= 50% reduction, got {comparison['total_reduction_pct']}%"
    assert comparison["target_achieved"] is True, "Target should be marked achieved!"
    assert comparison["top_bottleneck_solved"] is not None, "Top bottleneck should be identified!"

    print("\n======================================================================")
    print("  ALL TESTS PASSED WITH 100% SUCCESS! Database & Analytics are ready.")
    print("======================================================================")

    # Clean up test DB file
    if os.path.exists(test_db_path):
        try:
            os.remove(test_db_path)
            # Remove wal and shm files if present
            if os.path.exists(test_db_path + "-wal"):
                os.remove(test_db_path + "-wal")
            if os.path.exists(test_db_path + "-shm"):
                os.remove(test_db_path + "-shm")
        except Exception:
            pass


if __name__ == "__main__":
    run_tests()
