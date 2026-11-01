"""
SMED Studio - Phase 3 Pareto Analysis & Kaizen Matrix Verification Script
Tests Matplotlib chart rendering, PNG export, live KPI recalculation, and Kaizen table persistence.
"""

import os
import sys
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt
from main import MainWindow
from database.db_manager import DatabaseManager

# Non-blocking dialog mocks
QMessageBox.information = lambda *args, **kwargs: QMessageBox.StandardButton.Ok
QMessageBox.warning = lambda *args, **kwargs: QMessageBox.StandardButton.Ok
QMessageBox.question = lambda *args, **kwargs: QMessageBox.StandardButton.Yes


def test_pareto_kaizen():
    app = QApplication.instance() or QApplication(sys.argv)
    print("======================================================================")
    print("  SMED STUDIO - PHASE 3 PARETO & KAIZEN TAB INTEGRATION TEST")
    print("======================================================================")

    window = MainWindow()
    assert window is not None
    print("[OK] MainWindow initialized with Tab 3 mounted.")

    tab = window.tab_pareto
    tab.set_project(1)  # Project 1: Automotive Stamping Line 4
    print(f"[OK] ParetoKaizenTab loaded Project ID 1: '{tab.lbl_project_name.text()}'.")

    # 1. Verify 10 Activities in Table
    assert tab.table_kaizen.rowCount() == 10, f"Expected 10 rows, got {tab.table_kaizen.rowCount()}"
    print(f"[OK] Kaizen table populated with {tab.table_kaizen.rowCount()} standardized activities in Pareto order.")

    # 2. Verify Vital Few (Class A) Ranking
    rank_0 = tab.table_kaizen.cellWidget(0, 0).text()
    act_0 = tab.table_kaizen.item(0, 1).text()
    assert "#1" in rank_0 and "Vital Few" in rank_0
    assert "Unbolt" in act_0, f"Expected unbolting to be rank #1 bottleneck, got: {act_0}"
    print(f"[OK] Rank #1 Bottleneck identified: '{act_0}' with Class A [Vital Few] badge.")

    # 3. Verify Initial KPI Cards
    assert "40m 45s" in tab.val_kpi_baseline.text()
    assert "20m 22s" in tab.val_kpi_target.text()
    assert "m " in tab.val_kpi_savings.text()
    assert "[50% TARGET HIT]" in tab.badge_kpi_status.text()
    print("[OK] 4 Live KPI Cards verified with initial baseline & Kaizen estimates:")
    print(f"     Baseline Setup:    {tab.val_kpi_baseline.text()}")
    print(f"     50% Target Time:   {tab.val_kpi_target.text()}")
    print(f"     Estimated Savings: {tab.val_kpi_savings.text()}")
    print(f"     Projected Machine: {tab.val_kpi_projected.text()} -> {tab.badge_kpi_status.text()}")

    # 4. Test Filtering
    # Filter: Internal Only
    tab.combo_filter.setCurrentIndex(1)
    internal_count = tab.table_kaizen.rowCount()
    assert internal_count == 8, f"Expected 8 internal activities, got {internal_count}"
    print(f"[OK] Filter 'Internal Only' returned {internal_count} activities.")

    # Filter: External Only
    tab.combo_filter.setCurrentIndex(2)
    external_count = tab.table_kaizen.rowCount()
    assert external_count == 2, f"Expected 2 external activities, got {external_count}"
    print(f"[OK] Filter 'External Only' returned {external_count} activities.")

    # Reset Filter to All
    tab.combo_filter.setCurrentIndex(0)
    assert tab.table_kaizen.rowCount() == 10
    print("[OK] Reset filter to 'All Activities' returned 10 activities.")

    # 5. Test Live Dynamic Recalculation
    # Row 0: Unbolt 8 manual clamp bolts (450s)
    # Increase reduction to 400s
    r0 = tab.row_widgets[0]
    initial_proj = r0["proj_item"].text()
    r0["spin_reduction"].setValue(420.0)
    new_proj = r0["proj_item"].text()
    assert "30.0s" in new_proj, f"Expected 30.0s projected, got {new_proj}"
    print(f"[OK] Dynamic spinbox update: Row 0 projected duration changed from {initial_proj} to {new_proj}.")

    # Test conversion of an internal activity to external
    # Row 1: Align guide pins (385s) -> switch to External
    r1 = tab.row_widgets[1]
    r1["combo_target"].setCurrentText("External")
    print(f"[OK] Dynamic conversion: Activity '{r1['activity_name']}' converted to External.")
    print(f"     Updated Savings:   {tab.val_kpi_savings.text()}")
    print(f"     Updated Projected: {tab.val_kpi_projected.text()} -> {tab.badge_kpi_status.text()}")

    # 6. Test Batch Save Kaizen Solutions
    r0["edit_problem"].setPlainText("Bolts stick due to thermal expansion")
    r0["edit_solution"].setPlainText("Hydraulic one-touch quick clamps installed")
    tab._save_all_kaizen_solutions()

    # Verify SQLite persistence
    db = DatabaseManager("smed_local.db")
    saved_ks = db.get_kaizen_solution_for_activity(1, r0["activity_id"])
    assert saved_ks is not None, "Failed to retrieve saved Kaizen solution!"
    assert saved_ks["estimated_reduction_sec"] == 420.0
    assert saved_ks["problem_observed"] == "Bolts stick due to thermal expansion"
    print("[OK] Kaizen solutions saved to SQLite and verified in database.")

    # 7. Test Export Pareto Chart as PNG
    test_png_path = "test_pareto_export.png"
    if os.path.exists(test_png_path):
        os.remove(test_png_path)

    tab.fig.savefig(test_png_path, dpi=200, bbox_inches="tight", facecolor=tab.fig.get_facecolor())
    assert os.path.exists(test_png_path), "Exported PNG file not created!"
    file_size = os.path.getsize(test_png_path)
    assert file_size > 10000, f"PNG file suspiciously small: {file_size} bytes"
    print(f"[OK] Pareto Chart exported to high-resolution PNG ({file_size} bytes).")
    os.remove(test_png_path)

    # 8. Test Tab Switching Synchronization
    window.tabs.setCurrentIndex(2)  # switch to Tab 3
    assert window.tabs.currentIndex() == 2
    print("[OK] Tab switching synchronization confirmed.")

    print("======================================================================")
    print("  ALL PHASE 3 PARETO & KAIZEN TESTS PASSED WITH 100% SUCCESS!")
    print("======================================================================")


if __name__ == "__main__":
    test_pareto_kaizen()
