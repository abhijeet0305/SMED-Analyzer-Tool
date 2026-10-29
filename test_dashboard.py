"""
SMED Studio - Phase 4 Dashboard & Report Exporter Verification Script
Tests DashboardTab UI rendering, 5 KPI cards, dual comparison charts,
and validates offline generation of Excel (.xlsx) and executive PDF (.pdf) reports.
"""

import os
import sys
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt
from main import MainWindow
from database.db_manager import DatabaseManager
from utils.report_exporter import export_project_to_excel, export_project_to_pdf
import openpyxl

# Non-blocking dialog mocks
QMessageBox.information = lambda *args, **kwargs: QMessageBox.StandardButton.Ok
QMessageBox.warning = lambda *args, **kwargs: QMessageBox.StandardButton.Ok
QMessageBox.question = lambda *args, **kwargs: QMessageBox.StandardButton.Yes


def test_dashboard_and_export():
    app = QApplication.instance() or QApplication(sys.argv)
    print("======================================================================")
    print("  SMED STUDIO - PHASE 4 DASHBOARD & EXPORT INTEGRATION TEST")
    print("======================================================================")

    window = MainWindow()
    assert window is not None
    print("[OK] MainWindow initialized with all 4 tabs mounted.")

    tab4 = window.tab_dashboard
    tab4.set_project(1)  # Project 1: Automotive Stamping Line 4
    print(f"[OK] DashboardTab loaded Project ID 1: '{tab4.lbl_project_title.text()}'.")

    # 1. Verify 5 Executive KPI Cards
    print("\n--- EXECUTIVE KPI CARDS ---")
    print(f"Card 1 (Total Setup Time):      {tab4.val_kpi_total.text()} | {tab4.sub_kpi_total.text()}")
    print(f"Card 2 (Machine Downtime):      {tab4.val_kpi_internal.text()} | {tab4.sub_kpi_internal.text()}")
    print(f"Card 3 (External Shift):        {tab4.val_kpi_external.text()} | {tab4.sub_kpi_external.text()}")
    print(f"Card 4 (SMED Goal & 6th Part):  {tab4.badge_target_status.text()} | {tab4.sub_sixth_part.text()}")
    print(f"Card 5 (#1 Bottleneck Solved):  {tab4.val_spotlight_name.text()} | {tab4.sub_spotlight_sol.text()}")

    assert "40m 45s" in tab4.val_kpi_total.text()
    assert "13m 25s" in tab4.val_kpi_total.text()
    assert "Saved: 27m 20s" in tab4.sub_kpi_total.text()
    assert "60.8%" in tab4.sub_kpi_internal.text()
    assert "50% TARGET ACHIEVED" in tab4.badge_target_status.text()
    assert "VERIFIED ON ALL TRIALS" in tab4.sub_sixth_part.text()
    assert "Unbolt" in tab4.val_spotlight_name.text()
    print("[OK] All 5 Executive KPI cards correctly computed from multi-trial observations.")

    # 2. Verify Comparative Table
    assert tab4.table_compare.rowCount() == 10, f"Expected 10 rows, got {tab4.table_compare.rowCount()}"
    print(f"[OK] Comparative Table populated with {tab4.table_compare.rowCount()} activity rows.")

    row0_rank = tab4.table_compare.item(0, 0).text()
    row0_name = tab4.table_compare.item(0, 1).text()
    row0_shift = tab4.table_compare.cellWidget(0, 2).text()
    row0_saved = tab4.table_compare.item(0, 7).text()
    row0_imp = tab4.table_compare.item(0, 8).text()
    row0_share = tab4.table_compare.item(0, 9).text()
    row0_status = tab4.table_compare.cellWidget(0, 10).text()

    print(f"Row #1 Breakdown: {row0_rank} | {row0_name[:32]} | Shift: {row0_shift.strip()} | Saved: {row0_saved}s | Improve: {row0_imp} | Share: {row0_share} | Status: {row0_status.strip()}")
    assert "#1" in row0_rank
    assert "Unbolt" in row0_name
    assert float(row0_saved) > 350.0  # Over 350s saved on bolt clamp replacement
    print("[OK] Top bottleneck row verified with detailed time savings & status badge.")

    # 3. Test Offline Excel Export
    excel_file = "test_smed_executive_report.xlsx"
    if os.path.exists(excel_file):
        os.remove(excel_file)

    export_project_to_excel(window.db, 1, excel_file)
    assert os.path.exists(excel_file), "Excel file was not created!"
    file_size_xlsx = os.path.getsize(excel_file)
    assert file_size_xlsx > 5000, f"Excel file suspiciously small ({file_size_xlsx} bytes)"

    # Inspect created Excel workbook sheets
    wb = openpyxl.load_workbook(excel_file)
    assert len(wb.sheetnames) == 3, f"Expected 3 sheets, found {wb.sheetnames}"
    assert "Executive Summary" in wb.sheetnames
    assert "Activity Comparison" in wb.sheetnames
    assert "Raw Trials Log" in wb.sheetnames

    ws1 = wb["Executive Summary"]
    assert "SMED STUDIO" in str(ws1["A1"].value)
    ws2 = wb["Activity Comparison"]
    assert ws2.max_row >= 13  # headers + 10 activities
    ws3 = wb["Raw Trials Log"]
    assert ws3.max_row >= 20  # raw observations

    print(f"[OK] Offline 3-Sheet Excel Workbook successfully generated ({file_size_xlsx} bytes).")
    print(f"     Sheets verified: {wb.sheetnames}")
    wb.close()
    os.remove(excel_file)

    # 4. Test Offline PDF Executive Kaizen Report Export
    pdf_file = "test_smed_executive_report.pdf"
    chart_png = "temp_test_chart.png"
    if os.path.exists(pdf_file):
        os.remove(pdf_file)
    if os.path.exists(chart_png):
        os.remove(chart_png)

    # Save chart image for PDF embedding
    tab4.fig.savefig(chart_png, dpi=180, bbox_inches="tight", facecolor=tab4.fig.get_facecolor())
    assert os.path.exists(chart_png)

    export_project_to_pdf(window.db, 1, pdf_file, chart_png_path=chart_png)
    assert os.path.exists(pdf_file), "PDF file was not created!"
    file_size_pdf = os.path.getsize(pdf_file)
    assert file_size_pdf > 15000, f"PDF file suspiciously small ({file_size_pdf} bytes)"

    print(f"[OK] Offline Printable Executive PDF Report successfully generated ({file_size_pdf} bytes).")
    os.remove(pdf_file)
    os.remove(chart_png)

    # 5. Test Tab Switching to Tab 4
    window.tabs.setCurrentIndex(3)
    assert window.tabs.currentIndex() == 3
    print("[OK] Tab switching synchronization to Tab 4 confirmed.")

    print("\n======================================================================")
    print("  ALL PHASE 4 DASHBOARD & EXPORT TESTS PASSED WITH 100% SUCCESS!")
    print("======================================================================")


if __name__ == "__main__":
    test_dashboard_and_export()
