"""
SMED Studio - Phase 2 GUI Integration & Interaction Verification Script
Simulates user actions across ProjectTab and VideoLoggerTab.
"""

import sys
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt
from main import MainWindow
from database.db_manager import DatabaseManager

# Non-interactive mocks for dialog popups during automated test
QMessageBox.information = lambda *args, **kwargs: QMessageBox.StandardButton.Ok
QMessageBox.warning = lambda *args, **kwargs: QMessageBox.StandardButton.Ok
QMessageBox.question = lambda *args, **kwargs: QMessageBox.StandardButton.Yes


def test_ui():
    app = QApplication.instance() or QApplication(sys.argv)
    print("======================================================================")
    print("  SMED STUDIO - PHASE 2 GUI INTEGRATION TEST")
    print("======================================================================")

    window = MainWindow()
    assert window is not None
    print("[OK] MainWindow instantiated with modern dark QSS.")

    # 1. Verify Tabs
    assert window.tabs.count() == 4
    print("[OK] 4 Main Navigation Tabs confirmed.")

    # 2. Project Tab checks
    ptab = window.tab_projects
    assert ptab.table_projects.rowCount() >= 1, "Expected at least 1 seeded project"
    print(f"[OK] ProjectTab loaded {ptab.table_projects.rowCount()} project(s).")

    # 3. Test New Project Creation
    ptab.input_name.setText("Injection Molding Machine 2 - Mold B3 to B9")
    ptab.input_machine.setText("Engel 500-Ton Victory Press")
    ptab.input_from_die.setText("Mold-B3")
    ptab.input_to_die.setText("Mold-B9")
    ptab.input_target.setValue(55.0)
    ptab.input_notes.setText("Test study for plastic injection tooling.")
    ptab._on_create_project()
    print("[OK] Successfully simulated creating a new project via GUI form.")

    # Verify project was added
    all_proj = ptab.db.get_all_projects()
    latest_id = all_proj[0]["id"]
    ptab._select_project_by_id(latest_id)
    ptab._on_set_active_project()
    assert window.tabs.currentIndex() == 1, "Switching to Video Logger tab failed!"
    print(f"[OK] Set new project (ID: {latest_id}) as active and auto-switched to Video Logger Tab.")

    # 4. Video Logger Tab checks on newly created project
    vtab = window.tab_logger
    assert vtab.active_project_id == latest_id
    print(f"[OK] VideoLoggerTab synchronized with active Project ID {vtab.active_project_id}.")

    # 5. Create a trial manually in new project
    trial_id = vtab.db.create_video_trial(
        project_id=latest_id,
        phase="BEFORE",
        trial_number=1,
        video_title="Baseline Trial 1 - Shift 1",
        total_smed_duration_sec=0.0,
        sixth_ok_part_verified=False,
    )
    vtab._refresh_trials_dropdown()
    assert vtab.active_trial_id == trial_id
    print(f"[OK] VideoLoggerTab loaded trial #{trial_id}.")

    # 6. Test Live Dual-Stopwatch Lap Timing
    # Step 1: Start lap 1
    vtab.combo_activity.setEditText("Purge barrel & clean nozzle tip")
    vtab.radio_internal.setChecked(True)
    vtab._on_lap_triggered()
    assert vtab.lap_running is True, "Lap should be running after first trigger!"
    print("[OK] Lap 1 started (Machine Stopped - Internal).")

    # Advance time simulated
    vtab.master_accumulated_sec = 185.0
    # Step 2: Finish lap 1 & start lap 2
    vtab.input_remarks.setText("Resin purge completed with HDPE compound")
    vtab._on_lap_triggered()
    assert vtab.table_logs.rowCount() == 1, "First activity should be logged in table!"
    print("[OK] Lap 1 successfully logged to database. Zero-gap continuous logging started Lap 2.")

    # Step 3: Finish lap 2 as External
    vtab.combo_activity.setEditText("Transport water cooling manifolds to machine")
    vtab.radio_external.setChecked(True)
    vtab.master_accumulated_sec = 260.0
    vtab._on_lap_triggered()
    assert vtab.table_logs.rowCount() == 2, "Second activity should be logged in table!"
    print("[OK] Lap 2 successfully logged (Machine Running - External).")

    # Step 4: Cancel idle 3rd lap
    vtab._cancel_lap()
    assert vtab.lap_running is False
    print("[OK] Cancelled empty trailing lap.")

    # 7. Check Subtotals
    assert "Internal:" in vtab.lbl_subtotal_internal.text()
    assert "External:" in vtab.lbl_subtotal_external.text()
    assert "2 Micro-Activities Logged" in vtab.lbl_subtotal_count.text()
    print(f"[OK] Live Subtotals confirmed: {vtab.lbl_subtotal_total.text()}")

    # 8. Check 6th Consecutive OK Part Checkbox
    vtab.chk_sixth_part.setChecked(True)
    trial_data = vtab.db.get_video_trial(trial_id)
    assert trial_data["sixth_ok_part_verified"] == 1
    print("[OK] '6th Consecutive OK Part Verified' checkbox synchronized with SQLite.")

    # 9. Verify Standard Activity Auto-Populate
    std_acts = vtab.db.get_standard_activities(latest_id)
    assert len(std_acts) == 2, f"Expected 2 standard activities, found {len(std_acts)}"
    act_names = [a["activity_name"] for a in std_acts]
    assert "Purge barrel & clean nozzle tip" in act_names
    assert "Transport water cooling manifolds to machine" in act_names
    print(f"[OK] Standard Activity Dictionary populated: {act_names}")

    # Switch to AFTER phase and verify standardized dropdown retains the activities
    vtab.combo_phase.setCurrentIndex(1)  # switch to AFTER
    vtab._refresh_standard_activities_dropdown()
    assert vtab.combo_activity.count() == 2
    print("[OK] AFTER Phase dropdown successfully retains standardized activities from BEFORE trials!")

    # Cleanup temporary test project
    ptab.db.delete_project(latest_id)
    print(f"[OK] Cleaned up temporary test project (ID: {latest_id}).")

    print("======================================================================")
    print("  ALL PHASE 2 GUI INTEGRATION TESTS PASSED 100%!")
    print("======================================================================")


if __name__ == "__main__":
    test_ui()
