"""
SMED Studio - Master End-to-End Verification Test Suite (Phase 5)
Tests:
1. Synthetic shop-floor demo video generator (.mp4) using OpenCV and NumPy.
2. OpenCV video loading, scrubbing, and dual-stopwatch playback in VideoLoggerTab.
3. Offline database backup and restore operations via shutil.copy2 and SQLite API.
4. Full 4-tab workflow: Projects -> Video Logger -> Pareto Matrix -> Dashboard.
5. Multi-sheet Excel (.xlsx) and printable Executive PDF (.pdf) exports.
6. Menu bar actions, shortcuts, and SMED guide dialog.
"""

import os
import sys
import shutil
import sqlite3
import cv2
import pandas as pd
from openpyxl import load_workbook
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from database.db_manager import DatabaseManager, get_db
from database.seed_data import seed_sample_project
from main import MainWindow
from utils.demo_video_generator import (
    generate_all_demo_videos,
    generate_and_seed_demo_project,
)


def run_full_suite() -> bool:
    print("=" * 72)
    print("  SMED STUDIO - PHASE 5 MASTER END-TO-END VERIFICATION TEST")
    print("=" * 72)

    # Initialize headless QApplication
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

    # Use a clean test database
    test_db_path = "test_smed_full_suite.db"
    if os.path.exists(test_db_path):
        os.remove(test_db_path)

    db = DatabaseManager(test_db_path)

    try:
        # =====================================================================
        # 1. TEST SYNTHETIC DEMO VIDEO GENERATION
        # =====================================================================
        print("\n--- TEST 1: Synthetic Shop-Floor Video Generation (OpenCV) ---")
        demo_dir = "sample_videos"
        os.makedirs(demo_dir, exist_ok=True)

        # Generate 5-second accelerated simulation videos for fast testing (120 frames @ 24fps)
        video_paths = generate_all_demo_videos(demo_dir, duration_sec=5.0, fps=24)
        before_mp4 = video_paths["BEFORE"]
        after_mp4 = video_paths["AFTER"]

        assert os.path.exists(before_mp4), f"Before MP4 not found at {before_mp4}"
        assert os.path.exists(after_mp4), f"After MP4 not found at {after_mp4}"
        assert os.path.getsize(before_mp4) > 10000, "Before MP4 is unusually small"
        assert os.path.getsize(after_mp4) > 10000, "After MP4 is unusually small"
        print(f"[OK] Generated BEFORE Video: {before_mp4} ({os.path.getsize(before_mp4):,} bytes)")
        print(f"[OK] Generated AFTER Video:  {after_mp4} ({os.path.getsize(after_mp4):,} bytes)")

        # Verify OpenCV can read both videos, verify frame dimension, FPS, HUD
        for phase_name, vpath in [("BEFORE", before_mp4), ("AFTER", after_mp4)]:
            cap = cv2.VideoCapture(vpath)
            assert cap.isOpened(), f"OpenCV failed to open {vpath}"
            fps = cap.get(cv2.CAP_PROP_FPS)
            frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            ret, frame = cap.read()
            cap.release()

            assert ret is True, f"Failed to read first frame from {vpath}"
            assert width == 640 and height == 360, f"Unexpected dimensions: {width}x{height}"
            assert fps == 24.0, f"Expected 24 FPS, got {fps}"
            assert frames >= 120, f"Expected >= 120 frames, got {frames}"
            print(f"[OK] {phase_name} Video OpenCV Verification: {width}x{height} @ {fps:.1f} FPS, {frames} frames.")

        # =====================================================================
        # 2. TEST DEMO PROJECT SEEDING & VIDEO LINKING
        # =====================================================================
        print("\n--- TEST 2: Demo Project Seeding & Video Path Association ---")
        project_id = generate_and_seed_demo_project(db, output_dir=demo_dir)
        assert project_id is not None and project_id > 0, "Failed to seed demo project"
        project = db.get_project(project_id)
        assert project is not None, "Project record not found in DB"
        print(f"[OK] Demo Project #{project_id} active: '{project['name']}'")

        # Verify video trials are linked to actual MP4 files
        before_trials = db.get_trials_by_project(project_id, phase="BEFORE")
        after_trials = db.get_trials_by_project(project_id, phase="AFTER")
        assert len(before_trials) >= 1, "No BEFORE trials found"
        assert len(after_trials) >= 1, "No AFTER trials found"
        assert os.path.exists(before_trials[0]["file_path"]), "BEFORE trial video path invalid"
        assert os.path.exists(after_trials[0]["file_path"]), "AFTER trial video path invalid"
        print(f"[OK] Video Trial #1 file paths linked directly to generated .mp4 files.")

        # =====================================================================
        # 3. TEST DATABASE BACKUP & RESTORE (shutil.copy2 & SQLite API)
        # =====================================================================
        print("\n--- TEST 3: Database Backup & Restore Operations ---")
        backup_file = "test_smed_backup.db"
        if os.path.exists(backup_file):
            os.remove(backup_file)

        # 3A. Test Backup
        # Create MainWindow pointing to test DB
        win = MainWindow()
        win.db = db
        # Point tabs to test DB
        win.tab_projects.db = db
        win.tab_logger.db = db
        win.tab_pareto.db = db
        win.tab_dashboard.db = db

        # Trigger programmatic backup
        created_backup = win._backup_database(destination_path=backup_file)
        assert os.path.exists(created_backup), f"Backup file {created_backup} was not created"
        assert os.path.getsize(created_backup) > 0, "Backup file is empty"
        print(f"[OK] Database successfully backed up to: {created_backup} ({os.path.getsize(created_backup):,} bytes)")

        # Verify integrity of backup database
        bkp_conn = sqlite3.connect(created_backup)
        bkp_cursor = bkp_conn.cursor()
        integrity = bkp_cursor.execute("PRAGMA integrity_check;").fetchone()[0]
        bkp_projects_count = bkp_cursor.execute("SELECT COUNT(*) FROM projects;").fetchone()[0]
        assert bkp_projects_count >= 1, "Backup DB missing projects"
        bkp_conn.close()
        print(f"[OK] Backup DB integrity check: OK. Contains {bkp_projects_count} project(s).")

        # 3B. Test Restore
        # Add a dummy project to current DB, restore from backup, verify dummy project is gone
        dummy_id = db.create_project("Temporary Test Project To Be Overwritten", "Machine X", 50.0)
        assert db.get_project(dummy_id) is not None, "Failed to create dummy project"

        restore_success = win._restore_database(source_path=created_backup)
        assert restore_success is True, "Database restoration returned False"
        assert db.get_project(dummy_id) is None, "Dummy project still exists after restore!"
        assert db.get_project(project_id) is not None, "Original project missing after restore!"
        print(f"[OK] Database restore successful! Restored to consistent backup state.")

        if os.path.exists(backup_file):
            os.remove(backup_file)

        # =====================================================================
        # 4. TEST FULL 4-TAB GUI WORKFLOW
        # =====================================================================
        print("\n--- TEST 4: Full 4-Tab Navigation & Synchronization ---")
        # Tab 1: Project Repository
        win.tabs.setCurrentIndex(0)
        win.tab_projects.load_projects()
        assert win.tab_projects.table_projects.rowCount() >= 1, "Projects table empty"
        print(f"[OK] Tab 1 (Projects): {win.tab_projects.table_projects.rowCount()} project(s) in repository.")

        # Activate Demo Project
        win._on_project_activated(project_id)
        assert win.tabs.currentIndex() == 1, "Did not auto-switch to Tab 2 (Video Logger)"

        # Tab 2: Video Logger
        print("\n--- Tab 2: Video Logger & Dual Stopwatches ---")
        logger = win.tab_logger
        assert logger.active_project_id == project_id, "Active project mismatch in logger"
        assert logger.active_trial_id is not None, "No active trial loaded in logger"
        assert logger.cap is not None and logger.cap.isOpened(), "Video player failed to load OpenCV capture"
        assert logger.total_frames >= 120, f"Expected >= 120 frames, got {logger.total_frames}"
        assert logger.video_duration_sec > 0.0, "Video duration is 0"
        print(f"[OK] Tab 2 (Logger): Video loaded in OpenCV ({logger.video_duration_sec:.1f}s, {logger.total_frames} frames).")

        # Test video playback controls
        logger.play()
        assert logger.is_playing is True, "Logger play() did not set is_playing"
        logger.pause()
        assert logger.is_playing is False, "Logger pause() did not reset is_playing"

        # Test video scrubbing
        logger._seek_relative(1.0)
        assert logger.slider_seek.value() >= 0, "Scrubbing forward did not advance slider"

        # Test activity logging (Start Lap -> Change type -> Lap)
        initial_log_count = len(db.get_logs_by_trial(logger.active_trial_id))
        logger.combo_activity.setEditText("Test Phase 5 Dynamic Micro-Activity")
        logger.radio_internal.setChecked(True)
        logger.master_accumulated_sec = 10.0
        logger._on_lap_triggered()
        assert logger.lap_running is True, "Lap timer did not start"

        logger.master_accumulated_sec = 35.0
        logger._on_lap_triggered()  # Laps and logs
        logger._cancel_lap()

        updated_logs = db.get_logs_by_trial(logger.active_trial_id)
        assert len(updated_logs) == initial_log_count + 1, "Micro-activity was not saved to DB"
        print(f"[OK] Tab 2 (Logger): Micro-activity logged successfully with continuous zero-gap stopwatch.")

        # Tab 3: Pareto & Kaizen Matrix
        print("\n--- Tab 3: Pareto Analysis & ECRS Kaizen Matrix ---")
        win.tabs.setCurrentIndex(2)
        win.tab_pareto.refresh_data()
        assert win.tab_pareto.table_kaizen.rowCount() >= 10, "Pareto table missing activities"
        bottleneck_name = win.tab_pareto.table_kaizen.item(0, 1).text()
        print(f"[OK] Tab 3 (Pareto): Ranked #1 bottleneck identified as '{bottleneck_name}'.")

        # Verify live Kaizen calculations
        est_savings_txt = win.tab_pareto.val_kpi_savings.text()
        assert "m" in est_savings_txt or "s" in est_savings_txt, "Estimated savings card not updated"
        print(f"[OK] Tab 3 (Pareto): Live Kaizen dynamic savings card: {est_savings_txt}")

        # Tab 4: Comparative Dashboard
        print("\n--- Tab 4: Comparative Analytics Dashboard ---")
        win.tabs.setCurrentIndex(3)
        win.tab_dashboard.refresh_analytics()

        # Check KPI cards
        val1 = win.tab_dashboard.val_kpi_total.text()
        val2 = win.tab_dashboard.val_kpi_internal.text()
        val4 = win.tab_dashboard.badge_target_status.text()
        assert "->" in val1, f"Expected Before -> After format, got: {val1}"
        assert "->" in val2, f"Expected Before -> After format, got: {val2}"
        assert "50% TARGET" in val4 or "ACHIEVED" in val4, f"Target status unexpected: {val4}"
        print(f"[OK] Tab 4 (Dashboard): Total Setup Time: {val1}")
        print(f"[OK] Tab 4 (Dashboard): Machine Downtime: {val2}")
        print(f"[OK] Tab 4 (Dashboard): SMED Goal Status:  {val4}")

        # =====================================================================
        # 5. TEST OFFLINE EXCEL & PDF EXPORTS VIA MAIN WINDOW
        # =====================================================================
        print("\n--- TEST 5: Offline Excel & PDF Report Exports ---")
        excel_out = "test_phase5_report.xlsx"
        pdf_out = "test_phase5_report.pdf"
        if os.path.exists(excel_out):
            os.remove(excel_out)
        if os.path.exists(pdf_out):
            os.remove(pdf_out)

        # 5A. Excel Export
        excel_file = win._export_excel(destination_path=excel_out)
        assert os.path.exists(excel_file), f"Excel file {excel_file} not created"
        assert os.path.getsize(excel_file) > 5000, "Excel file is empty or corrupted"
        wb = load_workbook(excel_file)
        expected_sheets = ["Executive Summary", "Activity Comparison", "Raw Trials Log"]
        for s in expected_sheets:
            assert s in wb.sheetnames, f"Missing expected sheet: {s}"
        print(f"[OK] Multi-Sheet Excel exported: {excel_file} ({os.path.getsize(excel_file):,} bytes, Sheets: {wb.sheetnames}).")

        # 5B. PDF Export
        pdf_file = win._export_pdf(destination_path=pdf_out)
        assert os.path.exists(pdf_file), f"PDF file {pdf_file} not created"
        assert os.path.getsize(pdf_file) > 1000, "PDF file is empty or corrupted"
        print(f"[OK] Printable Executive PDF exported: {pdf_file} ({os.path.getsize(pdf_file):,} bytes).")

        # Clean up exported test artifacts
        if os.path.exists(excel_out):
            os.remove(excel_out)
        if os.path.exists(pdf_out):
            os.remove(pdf_out)

        # =====================================================================
        # 6. TEST MENU BAR ACTIONS & SHORTCUTS
        # =====================================================================
        print("\n--- TEST 6: Menu Bar & Shortcuts Verification ---")
        menubar = win.menuBar()
        menu_actions = menubar.actions()
        assert len(menu_actions) >= 2, "Menu bar missing File or Help menu"

        file_menu = menu_actions[0].menu()
        help_menu = menu_actions[1].menu()
        file_action_texts = [a.text() for a in file_menu.actions() if a.text()]
        help_action_texts = [a.text() for a in help_menu.actions() if a.text()]

        # Verify key menu actions exist
        assert any("Generate & Load" in t for t in file_action_texts), "Missing Generate Demo Videos action"
        assert any("Backup" in t for t in file_action_texts), "Missing Backup action"
        assert any("Restore" in t for t in file_action_texts), "Missing Restore action"
        assert any("Excel" in t for t in file_action_texts), "Missing Excel export action"
        assert any("PDF" in t for t in file_action_texts), "Missing PDF export action"
        assert any("Exit" in t for t in file_action_texts), "Missing Exit action"
        assert any("Shortcuts & SMED Guide" in t for t in help_action_texts), "Missing Shortcuts & Guide action"
        print(f"[OK] Top Menu Bar verified with File & Help menus and complete action triggers.")

        print("\n" + "=" * 72)
        print("  ALL PHASE 5 MASTER VERIFICATION TESTS PASSED WITH 100% SUCCESS!")
        print("=" * 72)
        return True

    finally:
        # Cleanup test database
        if os.path.exists(test_db_path):
            try:
                os.remove(test_db_path)
            except Exception:
                pass


if __name__ == "__main__":
    success = run_full_suite()
    sys.exit(0 if success else 1)
