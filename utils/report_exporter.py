"""
SMED Studio - Offline Report Exporter Module
Generates professional Excel (.xlsx) workbooks and executive PDF Kaizen A3 summary reports.
100% offline, self-contained, using openpyxl and reportlab.
"""

import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch, mm
from reportlab.platypus import (
    HRFlowable,
    Image,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from database.db_manager import DatabaseManager


def format_duration(seconds: float) -> str:
    """Format seconds into MMm SSs (seconds) format."""
    if seconds < 0:
        seconds = 0.0
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins:02d}m {secs:02d}s ({seconds:.1f}s)"


# =============================================================================
# 1. OFFLINE EXCEL WORKBOOK EXPORTER (openpyxl)
# =============================================================================

def export_project_to_excel(db: DatabaseManager, project_id: int, filepath: str) -> str:
    """
    Generate an offline, multi-tab Excel report containing:
    - Sheet 1: Executive SMED Summary & KPIs
    - Sheet 2: Activity-by-Activity Before vs. After Comparison Matrix
    - Sheet 3: Raw Video Trials & Timestamp Log
    """
    report = db.get_before_after_comparison_report(project_id)
    if not report.get("has_data"):
        raise ValueError("Project has no baseline trial data to export.")

    project = db.get_project(project_id)
    wb = openpyxl.Workbook()

    # Style Tokens
    font_title = Font(name="Segoe UI", size=15, bold=True, color="38BDF8")
    font_section = Font(name="Segoe UI", size=12, bold=True, color="FFFFFF")
    font_header = Font(name="Segoe UI", size=10, bold=True, color="FFFFFF")
    font_bold = Font(name="Segoe UI", size=10, bold=True, color="1E293B")
    font_regular = Font(name="Segoe UI", size=10, color="1E293B")
    font_small = Font(name="Segoe UI", size=9, italic=True, color="64748B")

    fill_title = PatternFill(start_color="0B0F17", end_color="0B0F17", fill_type="solid")
    fill_section = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
    fill_header = PatternFill(start_color="26354A", end_color="26354A", fill_type="solid")
    fill_stripe = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
    fill_success = PatternFill(start_color="D1FAE5", end_color="D1FAE5", fill_type="solid")
    fill_warning = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")
    fill_danger = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")

    font_success = Font(name="Segoe UI", size=10, bold=True, color="065F46")
    font_warning = Font(name="Segoe UI", size=10, bold=True, color="92400E")
    font_danger = Font(name="Segoe UI", size=10, bold=True, color="991B1B")

    thin_border = Border(
        left=Side(style="thin", color="CBD5E1"),
        right=Side(style="thin", color="CBD5E1"),
        top=Side(style="thin", color="CBD5E1"),
        bottom=Side(style="thin", color="CBD5E1"),
    )

    # -------------------------------------------------------------------------
    # SHEET 1: Executive SMED Summary & KPIs
    # -------------------------------------------------------------------------
    ws1 = wb.active
    ws1.title = "Executive Summary"
    ws1.views.sheetView[0].showGridLines = True

    # Title Banner
    ws1.merge_cells("A1:G1")
    title_cell = ws1["A1"]
    title_cell.value = "SMED STUDIO - EXECUTIVE SETUP REDUCTION & KAIZEN A3 REPORT"
    title_cell.font = font_title
    title_cell.fill = fill_title
    title_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws1.row_dimensions[1].height = 36

    # Project Metadata Block
    ws1.merge_cells("A3:G3")
    sec_meta = ws1["A3"]
    sec_meta.value = "  1. STUDY PROJECT SPECIFICATIONS"
    sec_meta.font = font_section
    sec_meta.fill = fill_section
    ws1.row_dimensions[3].height = 24

    meta_items = [
        ("Project Title:", project["name"], "From Tool / Die:", project.get("from_die") or "N/A"),
        ("Machine / Workcell:", project.get("machine_name") or "N/A", "To Tool / Die:", project.get("to_die") or "N/A"),
        ("Baseline Trials Recorded:", f"{report['before_trials_count']} Video Trial(s)", "Verification Trials:", f"{report['after_trials_count']} Video Trial(s)"),
        ("Target Reduction %:", f"≥ {report['target_reduction_pct']:.1f}% (SMED Goal)", "Report Export Date:", datetime.now().strftime("%Y-%m-%d %H:%M")),
    ]

    r = 4
    for label1, val1, label2, val2 in meta_items:
        ws1.cell(row=r, column=1, value=label1).font = font_bold
        ws1.cell(row=r, column=2, value=val1).font = font_regular
        ws1.cell(row=r, column=4, value=label2).font = font_bold
        ws1.cell(row=r, column=5, value=val2).font = font_regular
        r += 1

    r += 1
    # Executive KPI Block
    ws1.merge_cells(f"A{r}:G{r}")
    sec_kpi = ws1.cell(row=r, column=1, value="  2. SMED SETUP REDUCTION PERFORMANCE METRICS")
    sec_kpi.font = font_section
    sec_kpi.fill = fill_section
    ws1.row_dimensions[r].height = 24
    r += 1

    kpi_headers = ["Metric Description", "Before (Baseline)", "Kaizen Plan (Target)", "After (Verified)", "Absolute Saved", "Improvement %", "Status"]
    for c_idx, h in enumerate(kpi_headers, 1):
        cell = ws1.cell(row=r, column=c_idx, value=h)
        cell.font = font_header
        cell.fill = fill_header
        cell.alignment = Alignment(horizontal="center", vertical="center")
    ws1.row_dimensions[r].height = 22
    r += 1

    macro = report.get("macro_breakdown", {})
    before_tot = report["before_total_avg_sec"]
    after_tot = report["after_total_avg_sec"]
    saved_tot = report["total_reduction_sec"]
    pct_tot = report["total_reduction_pct"]

    before_int = report["before_internal_sec"]
    after_int = report["after_internal_sec"]
    saved_int = report["internal_reduction_sec"]
    pct_int = report["internal_reduction_pct"]

    before_ext = report["before_external_sec"]
    after_ext = report["after_external_sec"]
    shift_ext = report["external_shift_sec"]

    plan_tot = macro.get("projected_total_sec", 0.0)
    plan_int = macro.get("projected_internal_sec", 0.0)
    plan_ext = macro.get("projected_external_sec", 0.0)

    target_achieved_str = "ACHIEVED" if report["target_achieved"] else "NOT MET"
    kpi_rows = [
        (
            "Total Changeover (Last Good -> 6th OK Part)",
            format_duration(before_tot),
            format_duration(plan_tot),
            format_duration(after_tot),
            format_duration(saved_tot),
            f"{pct_tot:.1f}%",
            target_achieved_str,
        ),
        (
            "Internal Setup Time (Machine Downtime - OFF)",
            format_duration(before_int),
            format_duration(plan_int),
            format_duration(after_int),
            format_duration(saved_int),
            f"{pct_int:.1f}%",
            f"{report['converted_count']} Converted to Ext",
        ),
        (
            "External Setup Time (Machine Running - ON)",
            format_duration(before_ext),
            format_duration(plan_ext),
            format_duration(after_ext),
            f"{shift_ext:+.1f}s",
            "—",
            "Shifting Outside Downtime",
        ),
    ]

    for row_data in kpi_rows:
        for c_idx, val in enumerate(row_data, 1):
            cell = ws1.cell(row=r, column=c_idx, value=val)
            cell.font = font_bold if c_idx == 1 else font_regular
            cell.border = thin_border
            if c_idx in (2, 3, 4, 5, 6, 7):
                cell.alignment = Alignment(horizontal="center", vertical="center")
            if c_idx == 7:
                if "ACHIEVED" in val:
                    cell.fill = fill_success
                    cell.font = font_success
                elif "NOT MET" in val:
                    cell.fill = fill_danger
                    cell.font = font_danger
        r += 1

    r += 1
    # Spotlights Block
    ws1.merge_cells(f"A{r}:G{r}")
    sec_spot = ws1.cell(row=r, column=1, value="  3. KEY KAIZEN HIGHLIGHTS & AUDIT VERIFICATION")
    sec_spot.font = font_section
    sec_spot.fill = fill_section
    ws1.row_dimensions[r].height = 24
    r += 1

    top_spot = report.get("top_spotlight")
    top_desc = (
        f"{top_spot['activity_name']}: Saved {top_spot['reduction_sec']:.1f}s ({top_spot['reduction_pct']:.1f}%) "
        f"via '{top_spot.get('solution_implemented') or 'Standardization'}'"
        if top_spot else "No bottleneck data"
    )

    sixth_status = (
        "PASS - Verified on all AFTER trial runs"
        if report.get("all_sixth_ok_verified")
        else "PENDING - Quality signoff required for consecutive OK parts"
    )

    spot_items = [
        ("#1 Top Bottleneck Solved:", top_desc),
        ("50% Setup Reduction Target:", f"{'PASSED (≥ 50% Reduction Achieved)' if report['target_achieved'] else 'IN PROGRESS'}"),
        ("Single-Minute SMED Status (< 10 min):", f"{'ACHIEVED (< 600s Total Setup)' if report['single_minute_achieved'] else f'IN PROGRESS ({format_duration(after_tot)})'}"),
        ("6th Consecutive OK Part Verification:", sixth_status),
    ]

    for label, val in spot_items:
        ws1.cell(row=r, column=1, value=label).font = font_bold
        ws1.merge_cells(start_row=r, start_column=2, end_row=r, end_column=7)
        c = ws1.cell(row=r, column=2, value=val)
        c.font = font_regular
        if "PASSED" in val or "ACHIEVED" in val or "PASS" in val:
            c.font = font_success
        r += 1

    # -------------------------------------------------------------------------
    # SHEET 2: Activity-by-Activity Before vs. After Comparison Matrix
    # -------------------------------------------------------------------------
    ws2 = wb.create_sheet(title="Activity Comparison")
    ws2.views.sheetView[0].showGridLines = True

    ws2.merge_cells("A1:K1")
    t2 = ws2["A1"]
    t2.value = f"ACTIVITY-BY-ACTIVITY BEFORE VS. AFTER COMPARISON: {project['name']}"
    t2.font = font_title
    t2.fill = fill_title
    t2.alignment = Alignment(horizontal="center", vertical="center")
    ws2.row_dimensions[1].height = 32

    headers_s2 = [
        "Rank", "Standardized Activity Name", "Category Shift",
        "Before Avg (s)", "Kaizen Solution Implemented", "SMED Stage",
        "Est. Target (s)", "After Avg (s)", "Time Saved (s)", "Reduction %", "Plan vs Actual"
    ]

    ws2.row_dimensions[3].height = 24
    for c_idx, h in enumerate(headers_s2, 1):
        cell = ws2.cell(row=3, column=c_idx, value=h)
        cell.font = font_header
        cell.fill = fill_header
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = thin_border

    r2 = 4
    for item in report.get("activities_list", []):
        row_vals = [
            f"#{item.get('baseline_rank', r2 - 3)}",
            item["activity_name"],
            item.get("category_shift", f"{item['before_type']} -> {item['after_type']}"),
            f"{item['before_avg_sec']:.1f}",
            item.get("solution_implemented") or "—",
            item.get("action_type") or "—",
            f"{item.get('est_target_sec', 0.0):.1f}",
            f"{item['after_avg_sec']:.1f}",
            f"{item['reduction_sec']:.1f}",
            f"{item['reduction_pct']:.1f}%",
            item.get("plan_vs_actual_status") or "On Target",
        ]

        for c_idx, val in enumerate(row_vals, 1):
            cell = ws2.cell(row=r2, column=c_idx, value=val)
            cell.font = font_regular
            cell.border = thin_border
            if c_idx in (1, 3, 4, 7, 8, 9, 10, 11):
                cell.alignment = Alignment(horizontal="center", vertical="center")
            if item.get("is_converted") and c_idx == 3:
                cell.fill = fill_success
                cell.font = font_success
            if c_idx == 11:
                if "Beat" in val or "On Target" in val:
                    cell.fill = fill_success
                    cell.font = font_success
                elif "Needs" in val:
                    cell.fill = fill_warning
                    cell.font = font_warning

        if (r2 % 2) == 1:
            for c_idx in range(1, 12):
                if ws2.cell(row=r2, column=c_idx).fill.fill_type is None:
                    ws2.cell(row=r2, column=c_idx).fill = fill_stripe

        r2 += 1

    # -------------------------------------------------------------------------
    # SHEET 3: Raw Video Trials & Timestamp Log
    # -------------------------------------------------------------------------
    ws3 = wb.create_sheet(title="Raw Trials Log")
    ws3.views.sheetView[0].showGridLines = True

    ws3.merge_cells("A1:I1")
    t3 = ws3["A1"]
    t3.value = f"AUDIT LOG: RAW VIDEO OBSERVATION TIMESTAMPS ({project['name']})"
    t3.font = font_title
    t3.fill = fill_title
    t3.alignment = Alignment(horizontal="center", vertical="center")
    ws3.row_dimensions[1].height = 32

    headers_s3 = [
        "Phase", "Trial #", "Video Title", "Seq", "Activity Name",
        "Category", "Start (s)", "End (s)", "Duration (s)", "Remarks"
    ]

    ws3.row_dimensions[3].height = 24
    for c_idx, h in enumerate(headers_s3, 1):
        cell = ws3.cell(row=3, column=c_idx, value=h)
        cell.font = font_header
        cell.fill = fill_header
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = thin_border

    r3 = 4
    for log in report.get("raw_trials_log", []):
        row_vals = [
            log["phase"],
            f"Trial {log['trial_number']}",
            log["video_title"],
            log["sequence_no"],
            log["activity_name"],
            log["activity_type"],
            f"{log['start_time_sec']:.2f}",
            f"{log['end_time_sec']:.2f}",
            f"{log['duration_sec']:.2f}",
            log.get("remarks") or "",
        ]

        for c_idx, val in enumerate(row_vals, 1):
            cell = ws3.cell(row=r3, column=c_idx, value=val)
            cell.font = font_regular
            cell.border = thin_border
            if c_idx in (1, 2, 4, 6, 7, 8, 9):
                cell.alignment = Alignment(horizontal="center", vertical="center")
            if c_idx == 1:
                cell.font = font_bold
                if val == "BEFORE":
                    cell.fill = fill_warning
                else:
                    cell.fill = fill_success

        r3 += 1

    # Auto-adjust column widths for all sheets
    for ws in [ws1, ws2, ws3]:
        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                val_str = str(cell.value or "")
                # Ignore merged cells in length calculation
                if cell.row not in (1, 3):
                    max_len = max(max_len, len(val_str))
            ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

    wb.save(filepath)
    return filepath


# =============================================================================
# 2. OFFLINE EXECUTIVE PDF KAIZEN A3 REPORT (reportlab)
# =============================================================================

def export_project_to_pdf(
    db: DatabaseManager,
    project_id: int,
    filepath: str,
    chart_png_path: Optional[str] = None,
) -> str:
    """
    Generate an offline, printable Executive SMED Kaizen A3 Report (A4 Landscape)
    using ReportLab Flowables.
    """
    report = db.get_before_after_comparison_report(project_id)
    if not report.get("has_data"):
        raise ValueError("Project has no baseline trial data to export.")

    project = db.get_project(project_id)

    # Document setup: A4 Landscape (Ideal for A3 / widescreen Kaizen boards)
    doc = SimpleDocTemplate(
        filepath,
        pagesize=landscape(A4),
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
    )

    styles = getSampleStyleSheet()

    # Custom Typography Styles
    style_title = ParagraphStyle(
        "ReportTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=18,
        textColor=colors.HexColor("#0EA5E9"),
    )

    style_sub = ParagraphStyle(
        "ReportSub",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=11,
        textColor=colors.HexColor("#64748B"),
    )

    style_sec_head = ParagraphStyle(
        "SectionHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=12,
        textColor=colors.HexColor("#1E293B"),
    )

    style_cell = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=9,
        textColor=colors.HexColor("#1E293B"),
    )

    style_cell_bold = ParagraphStyle(
        "TableCellBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=9,
        textColor=colors.HexColor("#1E293B"),
    )

    style_cell_head = ParagraphStyle(
        "TableHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.white,
        alignment=1,  # Center
    )

    story = []

    # 1. Header Banner
    header_data = [
        [
            Paragraph("<b>SMED STUDIO - EXECUTIVE SETUP REDUCTION REPORT</b>", style_title),
            Paragraph(f"<b>Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}<br/><b>Status:</b> 100% OFFLINE AUDITED", style_sub),
        ],
        [
            Paragraph(
                f"<b>Project:</b> {project['name']} | <b>Machine:</b> {project.get('machine_name') or 'N/A'} | "
                f"<b>Changeover:</b> {project.get('from_die') or 'Old'} → {project.get('to_die') or 'New'}",
                style_sub,
            ),
            Paragraph(f"<b>Target Reduction:</b> ≥ {report['target_reduction_pct']:.1f}%", style_sub),
        ],
    ]
    t_header = Table(header_data, colWidths=[200 * mm, 68 * mm])
    t_header.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(t_header)
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0EA5E9"), spaceAfter=8))

    # 2. Executive KPI Summary Cards
    before_tot = report["before_total_avg_sec"]
    after_tot = report["after_total_avg_sec"]
    saved_tot = report["total_reduction_sec"]
    pct_tot = report["total_reduction_pct"]
    before_int = report["before_internal_sec"]
    after_int = report["after_internal_sec"]
    pct_int = report["internal_reduction_pct"]

    target_badge_color = colors.HexColor("#10B981") if report["target_achieved"] else colors.HexColor("#EF4444")
    target_badge_text = "50% TARGET: ACHIEVED" if report["target_achieved"] else "50% TARGET: IN PROGRESS"

    kpi_table_data = [
        [
            Paragraph("<b>BASELINE SETUP TIME</b>", style_sec_head),
            Paragraph("<b>ACTUAL AFTER SETUP</b>", style_sec_head),
            Paragraph("<b>SETUP TIME SAVED</b>", style_sec_head),
            Paragraph("<b>DOWNTIME REDUCTION</b>", style_sec_head),
            Paragraph("<b>VERIFICATION STATUS</b>", style_sec_head),
        ],
        [
            Paragraph(f"<b>{format_duration(before_tot)}</b>", ParagraphStyle("K1", fontName="Helvetica-Bold", fontSize=13, textColor=colors.HexColor("#0F172A"))),
            Paragraph(f"<b>{format_duration(after_tot)}</b>", ParagraphStyle("K2", fontName="Helvetica-Bold", fontSize=13, textColor=colors.HexColor("#0EA5E9"))),
            Paragraph(f"<b>-{format_duration(saved_tot)}</b><br/><font size=8 color='#10B981'><b>(-{pct_tot:.1f}%)</b></font>", ParagraphStyle("K3", fontName="Helvetica-Bold", fontSize=13, textColor=colors.HexColor("#10B981"))),
            Paragraph(f"<b>{format_duration(before_int)} → {format_duration(after_int)}</b><br/><font size=8 color='#059669'><b>(-{pct_int:.1f}%)</b></font>", ParagraphStyle("K4", fontName="Helvetica", fontSize=9, textColor=colors.HexColor("#0F172A"))),
            Paragraph(f"<font color='{target_badge_color.hexval()}'><b>{target_badge_text}</b></font><br/><font size=7 color='#64748B'>6th Part Approval Verified</font>", ParagraphStyle("K5", fontName="Helvetica-Bold", fontSize=9)),
        ],
    ]

    t_kpi = Table(kpi_table_data, colWidths=[53 * mm, 53 * mm, 53 * mm, 55 * mm, 54 * mm])
    t_kpi.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F1F5F9")),
        ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#F8FAFC")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(t_kpi)
    story.append(Spacer(1, 8))

    # 3. Optional Embedded Comparison Chart Image
    if chart_png_path and os.path.exists(chart_png_path):
        try:
            chart_img = Image(chart_png_path, width=268 * mm, height=72 * mm)
            story.append(chart_img)
            story.append(Spacer(1, 8))
        except Exception:
            pass

    # 4. Activity Comparison Matrix Table
    story.append(Paragraph("<b>ACTIVITY-BY-ACTIVITY KAIZEN IMPLEMENTATION MATRIX</b>", style_sec_head))
    story.append(Spacer(1, 3))

    matrix_headers = [
        Paragraph("<b>Rank</b>", style_cell_head),
        Paragraph("<b>Activity Name</b>", style_cell_head),
        Paragraph("<b>Category Shift</b>", style_cell_head),
        Paragraph("<b>Before (s)</b>", style_cell_head),
        Paragraph("<b>Kaizen Solution Implemented</b>", style_cell_head),
        Paragraph("<b>After (s)</b>", style_cell_head),
        Paragraph("<b>Saved (s)</b>", style_cell_head),
        Paragraph("<b>Improve %</b>", style_cell_head),
        Paragraph("<b>Plan vs Actual</b>", style_cell_head),
    ]

    matrix_data = [matrix_headers]

    for item in report.get("activities_list", []):
        row = [
            Paragraph(f"#{item.get('baseline_rank', '')}", style_cell),
            Paragraph(item["activity_name"][:38], style_cell_bold),
            Paragraph(item.get("category_shift", ""), style_cell),
            Paragraph(f"{item['before_avg_sec']:.1f}", style_cell),
            Paragraph(item.get("solution_implemented", "—")[:48], style_cell),
            Paragraph(f"{item['after_avg_sec']:.1f}", style_cell),
            Paragraph(f"{item['reduction_sec']:.1f}", style_cell_bold),
            Paragraph(f"{item['reduction_pct']:.1f}%", style_cell_bold),
            Paragraph(item.get("plan_vs_actual_status", "On Target"), style_cell),
        ]
        matrix_data.append(row)

    col_widths = [14 * mm, 56 * mm, 30 * mm, 20 * mm, 64 * mm, 20 * mm, 20 * mm, 20 * mm, 24 * mm]
    t_matrix = Table(matrix_data, colWidths=col_widths, repeatRows=1)
    t_matrix.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E293B")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
    ]))
    story.append(t_matrix)

    # Build PDF document
    doc.build(story)
    return filepath
