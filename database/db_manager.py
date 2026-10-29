"""
SMED Studio - Database Management Layer (SQLite3)
Thread-safe, offline-first SQLite database interface for SMED engineering projects.

Covers:
- Projects (die changeover studies with target reduction %)
- Standard Activity Master Dictionary (ensuring standardized dropdown across trials)
- Video Trials (Multi-video baseline 'BEFORE' and verification 'AFTER')
- Activity Logs (Micro-activity dual-stopwatch events: start, end, duration, Internal/External)
- Kaizen Solutions (Brainstorming table with action types, targets, and estimated savings)
- Analytical Aggregation Queries (Pareto baseline distribution, Side-by-Side Before vs After comparative metrics)
"""

import os
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union
import pandas as pd


class DatabaseManager:
    """Thread-safe SQLite database manager for SMED Studio."""

    _instance = None
    _singleton_lock = threading.Lock()

    def __init__(self, db_path: str = "smed_local.db"):
        """
        Initialize database manager.
        :param db_path: Path to the SQLite database file or ':memory:'
        """
        self.db_path = os.path.abspath(db_path) if db_path != ":memory:" else ":memory:"
        self._lock = threading.RLock()
        self._init_db()

    @contextmanager
    def get_connection(self):
        """Context manager providing a thread-safe connection with foreign keys and WAL mode."""
        conn = sqlite3.connect(
            self.db_path,
            check_same_thread=False,
            timeout=30.0,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
        )
        conn.row_factory = sqlite3.Row
        with self._lock:
            try:
                # Enable foreign key constraints and WAL journal for concurrency & data integrity
                conn.execute("PRAGMA foreign_keys = ON;")
                if self.db_path != ":memory:":
                    conn.execute("PRAGMA journal_mode = WAL;")
                    conn.execute("PRAGMA synchronous = NORMAL;")
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

    def _init_db(self):
        """Create tables, indexes, and constraints if they do not exist."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 1. Projects Table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    machine_name TEXT,
                    from_die TEXT,
                    to_die TEXT,
                    target_reduction_pct REAL DEFAULT 50.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    notes TEXT
                );
                """
            )

            # 2. Standard Activity Dictionary Table (Master list per project)
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS standard_activities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    activity_name TEXT NOT NULL,
                    default_type TEXT CHECK(default_type IN ('Internal', 'External')) DEFAULT 'Internal',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
                    UNIQUE(project_id, activity_name)
                );
                """
            )

            # 3. Video Trials Table (Before baseline vs After implementation)
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS video_trials (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    phase TEXT CHECK(phase IN ('BEFORE', 'AFTER')) NOT NULL,
                    trial_number INTEGER NOT NULL,
                    video_title TEXT NOT NULL,
                    file_path TEXT,
                    total_smed_duration_sec REAL DEFAULT 0.0,
                    sixth_ok_part_verified BOOLEAN DEFAULT 0,
                    recorded_date TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
                );
                """
            )

            # 4. Activity Logs Table (Micro-activity records per trial)
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS activity_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    video_trial_id INTEGER NOT NULL,
                    standard_activity_id INTEGER NOT NULL,
                    sequence_no INTEGER NOT NULL,
                    activity_type TEXT CHECK(activity_type IN ('Internal', 'External')) NOT NULL,
                    start_time_sec REAL NOT NULL,
                    end_time_sec REAL NOT NULL,
                    duration_sec REAL NOT NULL,
                    remarks TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(video_trial_id) REFERENCES video_trials(id) ON DELETE CASCADE,
                    FOREIGN KEY(standard_activity_id) REFERENCES standard_activities(id) ON DELETE RESTRICT
                );
                """
            )

            # 5. Kaizen Solutions Table (Brainstorming & Action matrix)
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS kaizen_solutions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    standard_activity_id INTEGER NOT NULL,
                    problem_observed TEXT,
                    solution_implemented TEXT,
                    action_type TEXT CHECK(action_type IN ('Eliminate', 'Convert to External', 'Simplify/Streamline', 'Parallelize')),
                    estimated_reduction_sec REAL DEFAULT 0.0,
                    target_type TEXT CHECK(target_type IN ('Internal', 'External')),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
                    FOREIGN KEY(standard_activity_id) REFERENCES standard_activities(id) ON DELETE CASCADE,
                    UNIQUE(project_id, standard_activity_id)
                );
                """
            )

            # Performance Indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_std_act_proj ON standard_activities(project_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trials_proj_phase ON video_trials(project_id, phase);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_trial ON activity_logs(video_trial_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_std_act ON activity_logs(standard_activity_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_kaizen_proj ON kaizen_solutions(project_id);")

    # =========================================================================
    # PROJECT CRUD METHODS
    # =========================================================================

    def create_project(
        self,
        name: str,
        machine_name: Optional[str] = None,
        from_die: Optional[str] = None,
        to_die: Optional[str] = None,
        target_reduction_pct: float = 50.0,
        notes: Optional[str] = None,
    ) -> int:
        """Create a new SMED Project and return its ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO projects (name, machine_name, from_die, to_die, target_reduction_pct, notes)
                VALUES (?, ?, ?, ?, ?, ?);
                """,
                (name.strip(), machine_name, from_die, to_die, target_reduction_pct, notes),
            )
            return cursor.lastrowid

    def get_project(self, project_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve project by ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM projects WHERE id = ?;", (project_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_all_projects(self) -> List[Dict[str, Any]]:
        """Retrieve all SMED projects sorted newest first."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM projects ORDER BY created_at DESC, id DESC;")
            return [dict(row) for row in cursor.fetchall()]

    def update_project(self, project_id: int, **kwargs) -> bool:
        """Update fields of an existing project."""
        allowed_fields = {"name", "machine_name", "from_die", "to_die", "target_reduction_pct", "notes"}
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        if not updates:
            return False

        set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values()) + [project_id]

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE projects SET {set_clause} WHERE id = ?;", values)
            return cursor.rowcount > 0

    def delete_project(self, project_id: int) -> bool:
        """Delete project and cascade delete all associated trials, logs, activities, and solutions."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM projects WHERE id = ?;", (project_id,))
            return cursor.rowcount > 0

    # =========================================================================
    # STANDARD ACTIVITY MASTER DICTIONARY CRUD
    # =========================================================================

    def add_standard_activity(
        self,
        project_id: int,
        activity_name: str,
        default_type: str = "Internal",
    ) -> int:
        """
        Add a standardized activity to the master dictionary of a project.
        Raises sqlite3.IntegrityError if duplicate activity name exists for the project.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO standard_activities (project_id, activity_name, default_type)
                VALUES (?, ?, ?);
                """,
                (project_id, activity_name.strip(), default_type),
            )
            return cursor.lastrowid

    def get_or_create_standard_activity(
        self,
        project_id: int,
        activity_name: str,
        default_type: str = "Internal",
    ) -> Tuple[int, bool]:
        """
        Retrieve existing standard activity ID, or create it if not found.
        Returns: (activity_id, was_created: bool)
        """
        clean_name = activity_name.strip()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id FROM standard_activities
                WHERE project_id = ? AND LOWER(activity_name) = LOWER(?);
                """,
                (project_id, clean_name),
            )
            row = cursor.fetchone()
            if row:
                return row["id"], False

            cursor.execute(
                """
                INSERT INTO standard_activities (project_id, activity_name, default_type)
                VALUES (?, ?, ?);
                """,
                (project_id, clean_name, default_type),
            )
            return cursor.lastrowid, True

    def get_standard_activities(self, project_id: int) -> List[Dict[str, Any]]:
        """
        Retrieve all standardized activities defined for a project.
        Used to populate the video logger dropdown for subsequent trials and AFTER videos.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, project_id, activity_name, default_type, created_at
                FROM standard_activities
                WHERE project_id = ?
                ORDER BY activity_name ASC;
                """,
                (project_id,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def update_standard_activity(
        self,
        activity_id: int,
        activity_name: Optional[str] = None,
        default_type: Optional[str] = None,
    ) -> bool:
        """Update a standard activity's name or default classification."""
        updates = {}
        if activity_name is not None:
            updates["activity_name"] = activity_name.strip()
        if default_type is not None and default_type in ("Internal", "External"):
            updates["default_type"] = default_type
        if not updates:
            return False

        set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values()) + [activity_id]

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE standard_activities SET {set_clause} WHERE id = ?;", values)
            return cursor.rowcount > 0

    def delete_standard_activity(self, activity_id: int) -> bool:
        """Delete standard activity (restricted if already logged in activity_logs)."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM standard_activities WHERE id = ?;", (activity_id,))
            return cursor.rowcount > 0

    # =========================================================================
    # VIDEO TRIALS CRUD (BEFORE & AFTER OBSERVATIONS)
    # =========================================================================

    def create_video_trial(
        self,
        project_id: int,
        phase: str,
        trial_number: int,
        video_title: str,
        file_path: Optional[str] = None,
        total_smed_duration_sec: float = 0.0,
        sixth_ok_part_verified: bool = False,
        recorded_date: Optional[str] = None,
    ) -> int:
        """
        Register a video trial clip (Before Baseline or After Verification).
        :param phase: 'BEFORE' or 'AFTER'
        """
        if phase not in ("BEFORE", "AFTER"):
            raise ValueError("Phase must be either 'BEFORE' or 'AFTER'")

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO video_trials (
                    project_id, phase, trial_number, video_title,
                    file_path, total_smed_duration_sec, sixth_ok_part_verified, recorded_date
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    project_id,
                    phase,
                    trial_number,
                    video_title.strip(),
                    file_path,
                    max(0.0, float(total_smed_duration_sec)),
                    int(sixth_ok_part_verified),
                    recorded_date or datetime.now().strftime("%Y-%m-%d"),
                ),
            )
            return cursor.lastrowid

    def get_video_trial(self, trial_id: int) -> Optional[Dict[str, Any]]:
        """Get video trial by ID with project metadata."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT vt.*, p.name as project_name, p.target_reduction_pct
                FROM video_trials vt
                JOIN projects p ON vt.project_id = p.id
                WHERE vt.id = ?;
                """,
                (trial_id,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_trials_by_project(self, project_id: int, phase: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all video trials for a project, optionally filtered by 'BEFORE' or 'AFTER'."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if phase:
                cursor.execute(
                    """
                    SELECT * FROM video_trials
                    WHERE project_id = ? AND phase = ?
                    ORDER BY trial_number ASC, id ASC;
                    """,
                    (project_id, phase),
                )
            else:
                cursor.execute(
                    """
                    SELECT * FROM video_trials
                    WHERE project_id = ?
                    ORDER BY phase DESC, trial_number ASC, id ASC;
                    """,
                    (project_id,),
                )
            return [dict(row) for row in cursor.fetchall()]

    def update_video_trial(self, trial_id: int, **kwargs) -> bool:
        """Update video trial properties."""
        allowed_fields = {
            "phase", "trial_number", "video_title", "file_path",
            "total_smed_duration_sec", "sixth_ok_part_verified", "recorded_date"
        }
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        if not updates:
            return False

        set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values()) + [trial_id]

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE video_trials SET {set_clause} WHERE id = ?;", values)
            return cursor.rowcount > 0

    def delete_video_trial(self, trial_id: int) -> bool:
        """Delete a video trial and its activity logs."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM video_trials WHERE id = ?;", (trial_id,))
            return cursor.rowcount > 0

    def recalculate_trial_duration(self, trial_id: int) -> float:
        """
        Recalculate and update the trial's total SMED duration based on its activity logs.
        Returns the calculated duration in seconds.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT COALESCE(SUM(duration_sec), 0.0) as total_duration
                FROM activity_logs
                WHERE video_trial_id = ?;
                """,
                (trial_id,),
            )
            row = cursor.fetchone()
            total_duration = float(row["total_duration"]) if row else 0.0

            cursor.execute(
                "UPDATE video_trials SET total_smed_duration_sec = ? WHERE id = ?;",
                (total_duration, trial_id),
            )
            return total_duration

    # =========================================================================
    # ACTIVITY LOGS CRUD (DUAL-STOPWATCH TIMED LOGS)
    # =========================================================================

    def get_next_sequence_no(self, video_trial_id: int) -> int:
        """Get the next sequence number for activity logging in a trial."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COALESCE(MAX(sequence_no), 0) + 1 as next_seq FROM activity_logs WHERE video_trial_id = ?;",
                (video_trial_id,),
            )
            row = cursor.fetchone()
            return int(row["next_seq"]) if row else 1

    def log_activity(
        self,
        video_trial_id: int,
        standard_activity_id: int,
        activity_type: str,
        start_time_sec: float,
        end_time_sec: float,
        duration_sec: Optional[float] = None,
        sequence_no: Optional[int] = None,
        remarks: Optional[str] = None,
        auto_update_trial_duration: bool = True,
    ) -> int:
        """
        Log an observed micro-activity with dual-stopwatch timestamps.
        If duration_sec is None, it is calculated as (end_time_sec - start_time_sec).
        """
        if activity_type not in ("Internal", "External"):
            raise ValueError("activity_type must be 'Internal' or 'External'")

        computed_duration = (
            float(duration_sec)
            if duration_sec is not None
            else max(0.0, float(end_time_sec) - float(start_time_sec))
        )

        with self.get_connection() as conn:
            cursor = conn.cursor()

            if sequence_no is None:
                cursor.execute(
                    "SELECT COALESCE(MAX(sequence_no), 0) + 1 as next_seq FROM activity_logs WHERE video_trial_id = ?;",
                    (video_trial_id,),
                )
                seq = int(cursor.fetchone()["next_seq"])
            else:
                seq = int(sequence_no)

            cursor.execute(
                """
                INSERT INTO activity_logs (
                    video_trial_id, standard_activity_id, sequence_no,
                    activity_type, start_time_sec, end_time_sec, duration_sec, remarks
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    video_trial_id,
                    standard_activity_id,
                    seq,
                    activity_type,
                    round(float(start_time_sec), 2),
                    round(float(end_time_sec), 2),
                    round(computed_duration, 2),
                    remarks,
                ),
            )
            log_id = cursor.lastrowid

            if auto_update_trial_duration:
                cursor.execute(
                    """
                    SELECT COALESCE(SUM(duration_sec), 0.0) as total_duration
                    FROM activity_logs
                    WHERE video_trial_id = ?;
                    """,
                    (video_trial_id,),
                )
                total_duration = float(cursor.fetchone()["total_duration"])
                cursor.execute(
                    "UPDATE video_trials SET total_smed_duration_sec = ? WHERE id = ?;",
                    (total_duration, video_trial_id),
                )

            return log_id

    def bulk_log_activities(self, logs_data: List[Dict[str, Any]]) -> List[int]:
        """Insert multiple activity logs efficiently in a single transaction."""
        inserted_ids = []
        with self.get_connection() as conn:
            cursor = conn.cursor()
            trials_to_update = set()

            for item in logs_data:
                video_trial_id = item["video_trial_id"]
                trials_to_update.add(video_trial_id)
                start_sec = float(item["start_time_sec"])
                end_sec = float(item["end_time_sec"])
                dur = float(item.get("duration_sec", max(0.0, end_sec - start_sec)))
                seq = item.get("sequence_no")

                if seq is None:
                    cursor.execute(
                        "SELECT COALESCE(MAX(sequence_no), 0) + 1 as next_seq FROM activity_logs WHERE video_trial_id = ?;",
                        (video_trial_id,),
                    )
                    seq = int(cursor.fetchone()["next_seq"])

                cursor.execute(
                    """
                    INSERT INTO activity_logs (
                        video_trial_id, standard_activity_id, sequence_no,
                        activity_type, start_time_sec, end_time_sec, duration_sec, remarks
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        video_trial_id,
                        item["standard_activity_id"],
                        seq,
                        item["activity_type"],
                        round(start_sec, 2),
                        round(end_sec, 2),
                        round(dur, 2),
                        item.get("remarks"),
                    ),
                )
                inserted_ids.append(cursor.lastrowid)

            # Update trial durations
            for tid in trials_to_update:
                cursor.execute(
                    "SELECT COALESCE(SUM(duration_sec), 0.0) as total_duration FROM activity_logs WHERE video_trial_id = ?;",
                    (tid,),
                )
                total_dur = float(cursor.fetchone()["total_duration"])
                cursor.execute(
                    "UPDATE video_trials SET total_smed_duration_sec = ? WHERE id = ?;",
                    (total_dur, tid),
                )

        return inserted_ids

    def get_logs_by_trial(self, video_trial_id: int) -> List[Dict[str, Any]]:
        """Retrieve all activity logs for a trial joined with the standard activity name."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT al.*, sa.activity_name, sa.default_type
                FROM activity_logs al
                JOIN standard_activities sa ON al.standard_activity_id = sa.id
                WHERE al.video_trial_id = ?
                ORDER BY al.sequence_no ASC, al.start_time_sec ASC;
                """,
                (video_trial_id,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def update_activity_log(self, log_id: int, **kwargs) -> bool:
        """Update an activity log entry and recalculate trial duration."""
        allowed_fields = {
            "standard_activity_id", "sequence_no", "activity_type",
            "start_time_sec", "end_time_sec", "duration_sec", "remarks"
        }
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        if not updates:
            return False

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT video_trial_id, start_time_sec, end_time_sec FROM activity_logs WHERE id = ?;", (log_id,))
            current = cursor.fetchone()
            if not current:
                return False

            video_trial_id = current["video_trial_id"]

            # If start or end updated and duration not explicitly provided, update duration
            start = updates.get("start_time_sec", current["start_time_sec"])
            end = updates.get("end_time_sec", current["end_time_sec"])
            if "duration_sec" not in updates and ("start_time_sec" in updates or "end_time_sec" in updates):
                updates["duration_sec"] = round(max(0.0, float(end) - float(start)), 2)

            set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
            values = list(updates.values()) + [log_id]
            cursor.execute(f"UPDATE activity_logs SET {set_clause} WHERE id = ?;", values)

            # Recalculate trial total
            cursor.execute(
                "SELECT COALESCE(SUM(duration_sec), 0.0) as total_duration FROM activity_logs WHERE video_trial_id = ?;",
                (video_trial_id,),
            )
            total_dur = float(cursor.fetchone()["total_duration"])
            cursor.execute("UPDATE video_trials SET total_smed_duration_sec = ? WHERE id = ?;", (total_dur, video_trial_id))

            return True

    def delete_activity_log(self, log_id: int) -> bool:
        """Delete an activity log and update trial total duration."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT video_trial_id FROM activity_logs WHERE id = ?;", (log_id,))
            row = cursor.fetchone()
            if not row:
                return False
            video_trial_id = row["video_trial_id"]

            cursor.execute("DELETE FROM activity_logs WHERE id = ?;", (log_id,))

            # Recalculate trial total
            cursor.execute(
                "SELECT COALESCE(SUM(duration_sec), 0.0) as total_duration FROM activity_logs WHERE video_trial_id = ?;",
                (video_trial_id,),
            )
            total_dur = float(cursor.fetchone()["total_duration"])
            cursor.execute("UPDATE video_trials SET total_smed_duration_sec = ? WHERE id = ?;", (total_dur, video_trial_id))

            return True

    # =========================================================================
    # KAIZEN SOLUTIONS CRUD (BRAINSTORMING & ACTION MATRIX)
    # =========================================================================

    def add_or_update_kaizen_solution(
        self,
        project_id: int,
        standard_activity_id: int,
        problem_observed: str,
        solution_implemented: str,
        action_type: str,
        estimated_reduction_sec: float = 0.0,
        target_type: str = "Internal",
    ) -> int:
        """
        Record or update a Kaizen brainstorming idea for a bottleneck activity.
        Action types: 'Eliminate', 'Convert to External', 'Simplify/Streamline', 'Parallelize'
        (Also accepts UI stage descriptions and normalizes them).
        """
        action_map = {
            "Stage 1: Separate Internal -> External": "Convert to External",
            "Stage 2: Convert Internal -> External": "Convert to External",
            "Stage 3: Streamline / Quick Fasteners (One-Turn / Clamps)": "Simplify/Streamline",
            "Eliminate Waste (ECRS)": "Eliminate",
            "Parallelize Operation": "Parallelize",
            "Eliminate": "Eliminate",
            "Convert to External": "Convert to External",
            "Simplify/Streamline": "Simplify/Streamline",
            "Parallelize": "Parallelize",
        }
        canonical_action = action_map.get(action_type, action_type)
        valid_actions = {"Eliminate", "Convert to External", "Simplify/Streamline", "Parallelize"}
        if canonical_action not in valid_actions:
            raise ValueError(f"action_type must be one of {valid_actions} or mapped stages, got: {action_type}")

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO kaizen_solutions (
                    project_id, standard_activity_id, problem_observed,
                    solution_implemented, action_type, estimated_reduction_sec, target_type
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(project_id, standard_activity_id) DO UPDATE SET
                    problem_observed = excluded.problem_observed,
                    solution_implemented = excluded.solution_implemented,
                    action_type = excluded.action_type,
                    estimated_reduction_sec = excluded.estimated_reduction_sec,
                    target_type = excluded.target_type;
                """,
                (
                    project_id,
                    standard_activity_id,
                    problem_observed,
                    solution_implemented,
                    canonical_action,
                    round(float(estimated_reduction_sec), 2),
                    target_type,
                ),
            )
            cursor.execute(
                "SELECT id FROM kaizen_solutions WHERE project_id = ? AND standard_activity_id = ?;",
                (project_id, standard_activity_id),
            )
            return cursor.fetchone()["id"]

    def upsert_kaizen_solution(
        self,
        project_id: int,
        standard_activity_id: int,
        problem_observed: str,
        solution_implemented: str,
        action_type: str,
        estimated_reduction_sec: float = 0.0,
        target_type: str = "Internal",
    ) -> int:
        """Convenience alias for add_or_update_kaizen_solution."""
        return self.add_or_update_kaizen_solution(
            project_id=project_id,
            standard_activity_id=standard_activity_id,
            problem_observed=problem_observed,
            solution_implemented=solution_implemented,
            action_type=action_type,
            estimated_reduction_sec=estimated_reduction_sec,
            target_type=target_type,
        )

    def get_pareto_and_kaizen_data(
        self, project_id: int, category_filter: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Fetch aggregated baseline Pareto data with attached Kaizen brainstorming solutions,
        optionally filtered by 'Internal' or 'External'.
        """
        df = self.get_aggregated_before_activities(project_id)
        if df.empty:
            return df

        if category_filter and category_filter in ("Internal", "External"):
            df = df[df["activity_type"] == category_filter].copy().reset_index(drop=True)
            total_time = df["avg_duration_sec"].sum()
            if total_time > 0:
                df["pct_of_total"] = ((df["avg_duration_sec"] / total_time) * 100.0).round(2)
                df["cumulative_pct"] = df["pct_of_total"].cumsum().round(2)
            else:
                df["pct_of_total"] = 0.0
                df["cumulative_pct"] = 0.0

        return df

    def get_kaizen_solutions_by_project(self, project_id: int) -> List[Dict[str, Any]]:
        """Retrieve all Kaizen solutions for a project joined with standard activity names."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT ks.*, sa.activity_name, sa.default_type as current_activity_type
                FROM kaizen_solutions ks
                JOIN standard_activities sa ON ks.standard_activity_id = sa.id
                WHERE ks.project_id = ?
                ORDER BY ks.estimated_reduction_sec DESC;
                """,
                (project_id,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_kaizen_solution_for_activity(
        self, project_id: int, standard_activity_id: int
    ) -> Optional[Dict[str, Any]]:
        """Retrieve Kaizen solution for a specific activity in a project."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT ks.*, sa.activity_name, sa.default_type
                FROM kaizen_solutions ks
                JOIN standard_activities sa ON ks.standard_activity_id = sa.id
                WHERE ks.project_id = ? AND ks.standard_activity_id = ?;
                """,
                (project_id, standard_activity_id),
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def delete_kaizen_solution(self, solution_id: int) -> bool:
        """Delete a Kaizen solution record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM kaizen_solutions WHERE id = ?;", (solution_id,))
            return cursor.rowcount > 0

    # =========================================================================
    # ANALYTICAL ENGINE (PARETO ANALYSIS & BEFORE VS AFTER DASHBOARD METRICS)
    # =========================================================================

    def get_aggregated_before_activities(self, project_id: int) -> pd.DataFrame:
        """
        Aggregate and average activity durations across all 'BEFORE' video trials of a project.
        Calculates Pareto ranking, cumulative percentages, and attaches Kaizen ideas.

        Engineering Logic:
        - Setup Baseline is calculated from all BEFORE trials.
        - For each standardized activity, its duration per trial is averaged across all BEFORE trials.
        - Sorted descending by baseline average duration (identifying top bottlenecks).
        - Computes cumulative percentage for the 80/20 Pareto rule.
        """
        with self.get_connection() as conn:
            # 1. Count number of BEFORE trials
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) as count FROM video_trials WHERE project_id = ? AND phase = 'BEFORE';",
                (project_id,),
            )
            before_trials_count = cursor.fetchone()["count"]

            if before_trials_count == 0:
                # Return empty formatted DataFrame
                return pd.DataFrame(
                    columns=[
                        "standard_activity_id",
                        "activity_name",
                        "activity_type",
                        "trial_count",
                        "total_duration_sec",
                        "avg_duration_sec",
                        "avg_duration_min",
                        "pct_of_total",
                        "cumulative_pct",
                        "pareto_class",
                        "problem_observed",
                        "solution_implemented",
                        "action_type",
                        "target_type",
                        "estimated_reduction_sec",
                    ]
                )

            # 2. Query aggregated logs across all BEFORE trials
            query = """
                SELECT
                    sa.id as standard_activity_id,
                    sa.activity_name,
                    COALESCE(al.activity_type, sa.default_type) as activity_type,
                    COUNT(DISTINCT al.video_trial_id) as trial_count,
                    COALESCE(SUM(al.duration_sec), 0.0) as total_duration_sec,
                    COALESCE(ks.problem_observed, '') as problem_observed,
                    COALESCE(ks.solution_implemented, '') as solution_implemented,
                    COALESCE(ks.action_type, '') as action_type,
                    COALESCE(ks.target_type, '') as target_type,
                    COALESCE(ks.estimated_reduction_sec, 0.0) as estimated_reduction_sec
                FROM standard_activities sa
                JOIN activity_logs al ON sa.id = al.standard_activity_id
                JOIN video_trials vt ON al.video_trial_id = vt.id
                LEFT JOIN kaizen_solutions ks ON (sa.id = ks.standard_activity_id AND sa.project_id = ks.project_id)
                WHERE sa.project_id = ? AND vt.phase = 'BEFORE'
                GROUP BY sa.id, sa.activity_name, COALESCE(al.activity_type, sa.default_type)
                ORDER BY total_duration_sec DESC;
            """
            df = pd.read_sql_query(query, conn, params=(project_id,))

        if df.empty:
            return pd.DataFrame()

        # Calculate average per baseline trial (total duration across trials / number of before trials)
        df["avg_duration_sec"] = df["total_duration_sec"] / before_trials_count
        df["avg_duration_sec"] = df["avg_duration_sec"].round(2)
        df["avg_duration_min"] = (df["avg_duration_sec"] / 60.0).round(2)

        # Sort strictly descending by average baseline duration
        df = df.sort_values(by="avg_duration_sec", ascending=False).reset_index(drop=True)

        # Calculate Pareto Cumulative Percentages
        total_baseline_time = df["avg_duration_sec"].sum()
        if total_baseline_time > 0:
            df["pct_of_total"] = ((df["avg_duration_sec"] / total_baseline_time) * 100.0).round(2)
            df["cumulative_pct"] = df["pct_of_total"].cumsum().round(2)
        else:
            df["pct_of_total"] = 0.0
            df["cumulative_pct"] = 0.0

        # Pareto Classification (A: <= 80%, B: 80-95%, C: > 95%)
        def assign_pareto_class(cum_pct):
            if cum_pct <= 80.0:
                return "A (Vital Few)"
            elif cum_pct <= 95.0:
                return "B"
            else:
                return "C (Trivial Many)"

        df["pareto_class"] = df["cumulative_pct"].apply(assign_pareto_class)
        return df

    def get_before_vs_after_comparison(self, project_id: int) -> Dict[str, Any]:
        """
        Generate complete Comparative Analytics Dashboard metrics:
        - Total Setup Time Reduction vs 50% target
        - Internal vs External duration and percentage shift
        - Activity-by-activity improvement %, time saved
        - Top bottleneck solved by Kaizen implementations
        - Single-digit minute SMED goal status (< 600 seconds)
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 1. Project details
            cursor.execute("SELECT * FROM projects WHERE id = ?;", (project_id,))
            project = cursor.fetchone()
            if not project:
                raise ValueError(f"Project with ID {project_id} not found.")

            target_pct = float(project["target_reduction_pct"] or 50.0)

            # 2. Count trials
            cursor.execute(
                "SELECT COUNT(*) as count FROM video_trials WHERE project_id = ? AND phase = 'BEFORE';",
                (project_id,),
            )
            before_trials_count = cursor.fetchone()["count"]

            cursor.execute(
                "SELECT COUNT(*) as count FROM video_trials WHERE project_id = ? AND phase = 'AFTER';",
                (project_id,),
            )
            after_trials_count = cursor.fetchone()["count"]

            # If no trials exist
            if before_trials_count == 0:
                return {
                    "project_id": project_id,
                    "project_name": project["name"],
                    "machine_name": project["machine_name"],
                    "target_reduction_pct": target_pct,
                    "before_trials_count": 0,
                    "after_trials_count": after_trials_count,
                    "has_data": False,
                    "message": "No BEFORE baseline video trials recorded yet.",
                }

            # 3. Aggregate Before activity metrics
            before_sql = """
                SELECT
                    sa.id as activity_id,
                    sa.activity_name,
                    al.activity_type,
                    COALESCE(SUM(al.duration_sec), 0.0) as total_duration
                FROM activity_logs al
                JOIN standard_activities sa ON al.standard_activity_id = sa.id
                JOIN video_trials vt ON al.video_trial_id = vt.id
                WHERE sa.project_id = ? AND vt.phase = 'BEFORE'
                GROUP BY sa.id, al.activity_type;
            """
            before_rows = cursor.execute(before_sql, (project_id,)).fetchall()

            # 4. Aggregate After activity metrics
            after_sql = """
                SELECT
                    sa.id as activity_id,
                    sa.activity_name,
                    al.activity_type,
                    COALESCE(SUM(al.duration_sec), 0.0) as total_duration
                FROM activity_logs al
                JOIN standard_activities sa ON al.standard_activity_id = sa.id
                JOIN video_trials vt ON al.video_trial_id = vt.id
                WHERE sa.project_id = ? AND vt.phase = 'AFTER'
                GROUP BY sa.id, al.activity_type;
            """
            after_rows = cursor.execute(after_sql, (project_id,)).fetchall()

            # 5. Get Kaizen solutions
            kaizen_sql = """
                SELECT * FROM kaizen_solutions WHERE project_id = ?;
            """
            kaizen_dict = {
                row["standard_activity_id"]: dict(row)
                for row in cursor.execute(kaizen_sql, (project_id,)).fetchall()
            }

            # 6. Get all standard activities for master reference
            all_act_sql = "SELECT id, activity_name, default_type FROM standard_activities WHERE project_id = ?;"
            all_activities = {row["id"]: dict(row) for row in cursor.execute(all_act_sql, (project_id,)).fetchall()}

        # Map Before durations: activity_id -> {type, avg_sec}
        before_map = {}
        before_total_internal = 0.0
        before_total_external = 0.0
        for r in before_rows:
            aid = r["activity_id"]
            dur = float(r["total_duration"]) / before_trials_count
            act_type = r["activity_type"]
            before_map[aid] = {"type": act_type, "avg_sec": dur}
            if act_type == "Internal":
                before_total_internal += dur
            else:
                before_total_external += dur

        # Map After durations: activity_id -> {type, avg_sec}
        after_map = {}
        after_total_internal = 0.0
        after_total_external = 0.0
        if after_trials_count > 0:
            for r in after_rows:
                aid = r["activity_id"]
                dur = float(r["total_duration"]) / after_trials_count
                act_type = r["activity_type"]
                after_map[aid] = {"type": act_type, "avg_sec": dur}
                if act_type == "Internal":
                    after_total_internal += dur
                else:
                    after_total_external += dur

        # Combine into detailed activity comparison rows
        comparison_rows = []
        all_ids = set(before_map.keys()).union(after_map.keys()).union(all_activities.keys())

        for aid in sorted(all_ids):
            act_info = all_activities.get(aid, {"activity_name": f"Activity #{aid}", "default_type": "Internal"})
            name = act_info["activity_name"]

            b_data = before_map.get(aid, {"type": act_info["default_type"], "avg_sec": 0.0})
            a_data = after_map.get(aid, {"type": b_data["type"], "avg_sec": 0.0})

            b_dur = round(b_data["avg_sec"], 2)
            a_dur = round(a_data["avg_sec"], 2) if after_trials_count > 0 else 0.0
            b_type = b_data["type"]
            a_type = a_data["type"] if after_trials_count > 0 else "Pending"

            reduction_sec = round(b_dur - a_dur, 2)
            reduction_pct = round((reduction_sec / b_dur * 100.0), 2) if b_dur > 0 else 0.0

            # Conversion / Elimination classification
            is_converted = (b_type == "Internal" and a_type == "External")
            is_eliminated = (b_dur > 0 and after_trials_count > 0 and a_dur == 0.0)

            # Kaizen metadata
            ks = kaizen_dict.get(aid, {})
            solution_text = ks.get("solution_implemented", "")
            action_type = ks.get("action_type", "")
            est_reduction = ks.get("estimated_reduction_sec", 0.0)

            comparison_rows.append(
                {
                    "activity_id": aid,
                    "activity_name": name,
                    "before_type": b_type,
                    "after_type": a_type,
                    "before_avg_sec": b_dur,
                    "after_avg_sec": a_dur,
                    "reduction_sec": reduction_sec,
                    "reduction_pct": reduction_pct,
                    "is_converted": is_converted,
                    "is_eliminated": is_eliminated,
                    "action_type": action_type,
                    "solution_implemented": solution_text,
                    "estimated_reduction_sec": est_reduction,
                }
            )

        # Sort rows by biggest reduction (or highest before time)
        comparison_rows.sort(key=lambda x: x["reduction_sec"], reverse=True)
        comparison_df = pd.DataFrame(comparison_rows)

        # Totals and Overall SMED Metrics
        before_total_avg = round(before_total_internal + before_total_external, 2)
        after_total_avg = round(after_total_internal + after_total_external, 2) if after_trials_count > 0 else 0.0

        total_reduction_sec = round(before_total_avg - after_total_avg, 2) if after_trials_count > 0 else 0.0
        total_reduction_pct = (
            round((total_reduction_sec / before_total_avg) * 100.0, 2)
            if before_total_avg > 0 and after_trials_count > 0
            else 0.0
        )

        internal_reduction_sec = round(before_total_internal - after_total_internal, 2) if after_trials_count > 0 else 0.0
        internal_reduction_pct = (
            round((internal_reduction_sec / before_total_internal) * 100.0, 2)
            if before_total_internal > 0 and after_trials_count > 0
            else 0.0
        )

        target_achieved = (total_reduction_pct >= target_pct) if after_trials_count > 0 else False
        single_minute_achieved = (after_total_avg < 600.0) if after_trials_count > 0 else False

        # Identify top bottleneck solved
        top_bottleneck_activity = None
        if comparison_rows and after_trials_count > 0 and comparison_rows[0]["reduction_sec"] > 0:
            top_bottleneck_activity = comparison_rows[0]["activity_name"]

        return {
            "project_id": project_id,
            "project_name": project["name"],
            "machine_name": project["machine_name"],
            "from_die": project["from_die"],
            "to_die": project["to_die"],
            "target_reduction_pct": target_pct,
            "before_trials_count": before_trials_count,
            "after_trials_count": after_trials_count,
            "has_data": True,
            # Setup Durations
            "before_total_avg_sec": before_total_avg,
            "after_total_avg_sec": after_total_avg,
            "total_reduction_sec": total_reduction_sec,
            "total_reduction_pct": total_reduction_pct,
            "target_achieved": target_achieved,
            "single_minute_achieved": single_minute_achieved,
            # Internal vs External Split
            "before_internal_sec": round(before_total_internal, 2),
            "before_external_sec": round(before_total_external, 2),
            "after_internal_sec": round(after_total_internal, 2),
            "after_external_sec": round(after_total_external, 2),
            "internal_reduction_sec": internal_reduction_sec,
            "internal_reduction_pct": internal_reduction_pct,
            "external_shift_sec": round(after_total_external - before_total_external, 2) if after_trials_count > 0 else 0.0,
            # Bottleneck Kaizen highlights
            "top_bottleneck_solved": top_bottleneck_activity,
            "activities_df": comparison_df,
            "activities_list": comparison_rows,
        }

    def get_before_after_comparison_report(self, project_id: int) -> Dict[str, Any]:
        """
        Generate complete Executive Comparative Report data:
        - Baseline rank ordering
        - Est Target vs Actual After comparison with Plan vs Actual status
        - Macro breakdown (Baseline vs Projected vs Actual)
        - 6th OK Part verification check across AFTER trials
        - Raw trials and activity logs for audit reporting
        """
        summary = self.get_before_vs_after_comparison(project_id)
        if not summary.get("has_data"):
            return summary

        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Check 6th OK Part verification on all AFTER trials
            cursor.execute(
                "SELECT sixth_ok_part_verified FROM video_trials WHERE project_id = ? AND phase = 'AFTER';",
                (project_id,),
            )
            after_trials_ok = [bool(row["sixth_ok_part_verified"]) for row in cursor.fetchall()]
            all_sixth_ok_verified = (len(after_trials_ok) > 0 and all(after_trials_ok))

            # Raw trials logs query (for Sheet 3 of Excel export)
            raw_sql = """
                SELECT
                    vt.phase,
                    vt.trial_number,
                    vt.video_title,
                    al.sequence_no,
                    sa.activity_name,
                    al.activity_type,
                    al.start_time_sec,
                    al.end_time_sec,
                    al.duration_sec,
                    COALESCE(al.remarks, '') as remarks,
                    vt.sixth_ok_part_verified
                FROM activity_logs al
                JOIN standard_activities sa ON al.standard_activity_id = sa.id
                JOIN video_trials vt ON al.video_trial_id = vt.id
                WHERE vt.project_id = ?
                ORDER BY vt.phase DESC, vt.trial_number ASC, al.sequence_no ASC;
            """
            raw_rows = [dict(r) for r in cursor.execute(raw_sql, (project_id,)).fetchall()]

        # Process activities: calculate baseline Pareto rank, plan vs actual, contribution %
        activities = summary["activities_list"]

        # Sort by before_avg_sec descending to establish baseline Pareto rank
        sorted_by_baseline = sorted(activities, key=lambda x: x["before_avg_sec"], reverse=True)
        baseline_rank_map = {item["activity_id"]: idx + 1 for idx, item in enumerate(sorted_by_baseline)}

        total_reduction = summary["total_reduction_sec"]
        converted_count = 0

        # Calculate macro projected plan
        projected_internal_sec = 0.0
        projected_external_sec = 0.0

        enhanced_rows = []
        for item in activities:
            aid = item["activity_id"]
            rank = baseline_rank_map.get(aid, 999)
            item["baseline_rank"] = rank

            b_dur = item["before_avg_sec"]
            a_dur = item["after_avg_sec"]
            est_red = float(item.get("estimated_reduction_sec") or 0.0)
            est_target = round(max(0.0, b_dur - est_red), 2)
            item["est_target_sec"] = est_target

            b_type = item["before_type"]
            a_type = item["after_type"]
            if item.get("is_converted"):
                converted_count += 1
                item["category_shift"] = f"{b_type} -> EXTERNAL"
            else:
                item["category_shift"] = f"{b_type} -> {a_type}"

            # Projected Macro time calculation
            tgt_type = item.get("target_type") or ("External" if item.get("is_converted") else b_type)
            if tgt_type == "External":
                projected_external_sec += est_target
            else:
                projected_internal_sec += est_target

            # Share of Total Savings %
            red_sec = item["reduction_sec"]
            if total_reduction > 0 and red_sec > 0:
                item["savings_share_pct"] = round((red_sec / total_reduction) * 100.0, 2)
            else:
                item["savings_share_pct"] = 0.0

            # Plan vs. Actual Status
            if summary["after_trials_count"] > 0:
                if a_dur < est_target:
                    item["plan_vs_actual_status"] = "Beat Estimate"
                elif abs(a_dur - est_target) <= 5.0:
                    item["plan_vs_actual_status"] = "On Target"
                else:
                    item["plan_vs_actual_status"] = "Needs Further Kaizen"
            else:
                item["plan_vs_actual_status"] = "Pending After Trials"

            enhanced_rows.append(item)

        # Sort by baseline rank (Pareto order)
        enhanced_rows.sort(key=lambda x: x["baseline_rank"])

        # Target threshold
        target_pct = summary["target_reduction_pct"]
        before_total = summary["before_total_avg_sec"]
        target_threshold_sec = round(before_total * (1.0 - (target_pct / 100.0)), 2)

        # Macro Breakdown dictionary
        macro_breakdown = {
            "target_threshold_sec": target_threshold_sec,
            # Baseline
            "before_internal_sec": summary["before_internal_sec"],
            "before_external_sec": summary["before_external_sec"],
            "before_total_sec": before_total,
            # Projected (Plan)
            "projected_internal_sec": round(projected_internal_sec, 2),
            "projected_external_sec": round(projected_external_sec, 2),
            "projected_total_sec": round(projected_internal_sec + projected_external_sec, 2),
            # Actual After
            "after_internal_sec": summary["after_internal_sec"],
            "after_external_sec": summary["after_external_sec"],
            "after_total_sec": summary["after_total_avg_sec"],
        }

        # Detailed Spotlight on #1 Bottleneck
        top_activity_name = summary.get("top_bottleneck_solved")
        top_spotlight = None
        if top_activity_name:
            for it in enhanced_rows:
                if it["activity_name"] == top_activity_name:
                    top_spotlight = it
                    break

        summary.update({
            "activities_list": enhanced_rows,
            "activities_df": pd.DataFrame(enhanced_rows),
            "converted_count": converted_count,
            "all_sixth_ok_verified": all_sixth_ok_verified,
            "macro_breakdown": macro_breakdown,
            "top_spotlight": top_spotlight,
            "raw_trials_log": raw_rows,
        })
        return summary

    def backup_database(self, destination_path: str) -> str:
        """
        Create a consistent, thread-safe offline backup of the database.
        Uses SQLite's online backup API (source_conn.backup(dest_conn)),
        ensuring 100% integrity without corruption even during WAL operations.
        :param destination_path: Target path for the backup file (.db)
        :return: Absolute path of created backup file
        """
        dest_abs = os.path.abspath(destination_path)
        os.makedirs(os.path.dirname(dest_abs), exist_ok=True)
        with self._lock:
            with self.get_connection() as src_conn:
                dest_conn = sqlite3.connect(dest_abs)
                try:
                    src_conn.backup(dest_conn)
                finally:
                    dest_conn.close()
        return dest_abs

    def restore_database(self, source_backup_path: str) -> bool:
        """
        Restore database from a backup file.
        Validates SQLite integrity of the backup before applying.
        Uses online backup API to copy from backup to active db,
        preventing file-locking errors on Windows.
        :param source_backup_path: Source backup file path (.db)
        :return: True if restoration succeeded
        """
        src_abs = os.path.abspath(source_backup_path)
        if not os.path.exists(src_abs):
            raise FileNotFoundError(f"Backup file not found: {src_abs}")

        # Quick validation that source is a valid SQLite DB
        test_conn = sqlite3.connect(src_abs)
        try:
            cursor = test_conn.cursor()
            cursor.execute("PRAGMA schema_version;")
            cursor.fetchone()
            # Ensure at least 'projects' table exists or valid sqlite
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [r[0] for r in cursor.fetchall()]
        finally:
            test_conn.close()

        if "projects" not in tables:
            raise ValueError("Invalid SMED database backup: missing required tables.")

        with self._lock:
            # Connect to source and restore into target
            src_conn = sqlite3.connect(src_abs)
            try:
                with self.get_connection() as target_conn:
                    src_conn.backup(target_conn)
            finally:
                src_conn.close()

        return True


# Global singleton helper for standard app lifecycle
_global_db: Optional[DatabaseManager] = None
_global_db_lock = threading.Lock()


def get_db(db_path: str = "smed_local.db") -> DatabaseManager:
    """Get or create singleton DatabaseManager instance."""
    global _global_db
    with _global_db_lock:
        if _global_db is None:
            _global_db = DatabaseManager(db_path)
        return _global_db
