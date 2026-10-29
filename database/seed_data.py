"""
SMED Studio - Sample Data Seeder
Populates smed_local.db with a realistic automotive stamping die changeover study:
- Project: Automotive Stamping Line 4 - Hood Outer Panel Die Change
- Machine: Komatsu 800-Ton Mechanical Transfer Press
- Standard Activities: 10 standardized setup micro-steps
- 2 BEFORE Observation Trials (Unoptimized Baseline)
- 5 Kaizen Brainstorming Solutions
- 1 AFTER Observation Trial (Validating >= 50% Setup Reduction)
"""

from database.db_manager import DatabaseManager


def seed_sample_project(db: DatabaseManager) -> int:
    """Seed a sample project with complete Before & After video trials and Kaizen matrix."""
    # 1. Project
    project_id = db.create_project(
        name="Automotive Stamping Line 4 - Hood Outer Panel Die Change",
        machine_name="Komatsu 800-Ton Mechanical Transfer Press",
        from_die="Hood-Die-402 (Sedan Model)",
        to_die="Hood-Die-408 (SUV Model)",
        target_reduction_pct=50.0,
        notes="Target is >= 50% setup time reduction driving toward single-digit minute exchange (SMED).",
    )

    # 2. Standard Activity Dictionary
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

    act_ids = {}
    for name, def_type in activities_def:
        aid, _ = db.get_or_create_standard_activity(project_id, name, def_type)
        act_ids[name] = aid

    # 3. Before Trial 1
    t1_id = db.create_video_trial(
        project_id=project_id,
        phase="BEFORE",
        trial_number=1,
        video_title="Baseline Trial 1 - Shift A Operator (Unoptimized)",
        file_path="videos/before_trial_01.mp4",
        sixth_ok_part_verified=True,
        recorded_date="2026-10-15",
    )
    t1_steps = [
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
    t = 0.0
    for seq, (name, a_type, dur) in enumerate(t1_steps, 1):
        t1_logs.append({
            "video_trial_id": t1_id,
            "standard_activity_id": act_ids[name],
            "sequence_no": seq,
            "activity_type": a_type,
            "start_time_sec": t,
            "end_time_sec": t + dur,
            "duration_sec": dur,
            "remarks": "Observed manual bolt loosening and searching waste",
        })
        t += dur
    db.bulk_log_activities(t1_logs)

    # 4. Before Trial 2
    t2_id = db.create_video_trial(
        project_id=project_id,
        phase="BEFORE",
        trial_number=2,
        video_title="Baseline Trial 2 - Shift B Operator (Unoptimized)",
        file_path="videos/before_trial_02.mp4",
        sixth_ok_part_verified=True,
        recorded_date="2026-10-16",
    )
    t2_steps = [
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
    t = 0.0
    for seq, (name, a_type, dur) in enumerate(t2_steps, 1):
        t2_logs.append({
            "video_trial_id": t2_id,
            "standard_activity_id": act_ids[name],
            "sequence_no": seq,
            "activity_type": a_type,
            "start_time_sec": t,
            "end_time_sec": t + dur,
            "duration_sec": dur,
            "remarks": "Observed bolt thread friction and dial indicator calibration",
        })
        t += dur
    db.bulk_log_activities(t2_logs)

    # 5. Kaizen Solutions
    kaizen_matrix = [
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

    for act_name, prob, sol, a_type, est_red, tgt_type in kaizen_matrix:
        db.add_or_update_kaizen_solution(
            project_id=project_id,
            standard_activity_id=act_ids[act_name],
            problem_observed=prob,
            solution_implemented=sol,
            action_type=a_type,
            estimated_reduction_sec=est_red,
            target_type=tgt_type,
        )

    # 6. After Trial
    t_after_id = db.create_video_trial(
        project_id=project_id,
        phase="AFTER",
        trial_number=1,
        video_title="After Kaizen Verification Trial 1 - Standardized Quick-Clamp Setup",
        file_path="videos/after_trial_01.mp4",
        sixth_ok_part_verified=True,
        recorded_date="2026-10-25",
    )

    after_steps = [
        ("Retrieve new die & transport to press bed", "External", 30.0),
        ("Disconnect hydraulic lines, limit switches & sensors", "Internal", 90.0),
        ("Unbolt 8 manual clamp bolts with breaker bar", "Internal", 55.0),
        ("Crane hoist old die out to transport pallet", "Internal", 175.0),
        ("Crane hoist new die in & roughly position on bed", "Internal", 180.0),
        ("Align guide pins, dial indicator centering & clamp", "Internal", 95.0),
        ("Connect hydraulic lines & sensor harness", "Internal", 60.0),
        ("Trial stamping: parts 1 to 5 (trial & error adjustments)", "Internal", 40.0),
        ("Produce 6th Consecutive OK Approval Part & QC signoff", "Internal", 80.0),
    ]
    after_logs = []
    t = 0.0
    for seq, (name, a_type, dur) in enumerate(after_steps, 1):
        after_logs.append({
            "video_trial_id": t_after_id,
            "standard_activity_id": act_ids[name],
            "sequence_no": seq,
            "activity_type": a_type,
            "start_time_sec": t,
            "end_time_sec": t + dur,
            "duration_sec": dur,
            "remarks": "Kaizen implementations validated with quick-release fixtures",
        })
        t += dur
    db.bulk_log_activities(after_logs)

    return project_id


if __name__ == "__main__":
    db = DatabaseManager("smed_local.db")
    pid = seed_sample_project(db)
    print(f"Successfully seeded sample SMED project (ID: {pid}) into smed_local.db")
