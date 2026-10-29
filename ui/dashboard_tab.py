"""
SMED Studio - Before vs. After Comparative Analytics Dashboard Tab
Visualizes macro setup shifts, activity-level time savings, 50% target verification,
and drives offline Excel (.xlsx) and executive PDF (.pdf) report generation.
"""

import os
import tempfile
from typing import Any, Dict, List, Optional
import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np
import pandas as pd

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QSplitter, QGroupBox, QFrame, QFileDialog, QMessageBox,
    QAbstractItemView
)

from database.db_manager import DatabaseManager, get_db
from utils.report_exporter import export_project_to_excel, export_project_to_pdf, format_duration
from ui.styles import (
    COLORS,
    get_internal_badge_style,
    get_external_badge_style,
)


class DashboardTab(QWidget):
    """
    Phase 4: Before vs. After Comparative Analytics Dashboard & Offline Report Exporter.
    Side-by-side performance comparison, dual visualization canvas, and report generation.
    """
    report_exported = pyqtSignal(str)

    def __init__(self, db: Optional[DatabaseManager] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.db = db or get_db()
        self.active_project_id: Optional[int] = None
        self.report_data: Optional[Dict[str, Any]] = None

        self._init_ui()

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(10)

        # =====================================================================
        # TOP TOOLBAR: Active Project Title & Export Action Buttons
        # =====================================================================
        top_bar = QFrame()
        top_bar.setStyleSheet("background-color: #1E293B; border-radius: 6px; padding: 6px;")
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(8, 4, 8, 4)
        top_layout.setSpacing(12)

        top_layout.addWidget(QLabel("<b>Active Project:</b>"))
        self.lbl_project_title = QLabel("No Project Selected")
        self.lbl_project_title.setStyleSheet("color: #38BDF8; font-weight: 700; font-size: 14px;")
        top_layout.addWidget(self.lbl_project_title)

        top_layout.addStretch()

        self.btn_refresh = QPushButton(" Refresh Analytics")
        self.btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_refresh.clicked.connect(self.refresh_analytics)
        top_layout.addWidget(self.btn_refresh)

        self.btn_export_excel = QPushButton(" Export Full Excel Report (.xlsx)")
        self.btn_export_excel.setObjectName("primaryBtn")
        self.btn_export_excel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_export_excel.clicked.connect(self._on_export_excel)
        top_layout.addWidget(self.btn_export_excel)

        self.btn_export_pdf = QPushButton(" Export Executive PDF Report (.pdf)")
        self.btn_export_pdf.setObjectName("successBtn")
        self.btn_export_pdf.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_export_pdf.clicked.connect(self._on_export_pdf)
        top_layout.addWidget(self.btn_export_pdf)

        root_layout.addWidget(top_bar)

        # =====================================================================
        # ROW 1: 5 EXECUTIVE KPI CARDS
        # =====================================================================
        kpi_container = QFrame()
        kpi_container.setStyleSheet("background-color: #0F172A; border: 1px solid #1E293B; border-radius: 8px; padding: 6px;")
        kpi_grid = QGridLayout(kpi_container)
        kpi_grid.setContentsMargins(10, 8, 10, 8)
        kpi_grid.setHorizontalSpacing(14)
        kpi_grid.setVerticalSpacing(4)

        # Card 1: Total SMED Setup Time
        kpi_grid.addWidget(QLabel("<b>TOTAL SETUP TIME (BEFORE -> AFTER)</b>"), 0, 0)
        self.val_kpi_total = QLabel("00m 00s -> 00m 00s")
        self.val_kpi_total.setStyleSheet("color: #F8FAFC; font-size: 15px; font-weight: 800; font-family: monospace;")
        kpi_grid.addWidget(self.val_kpi_total, 1, 0)
        self.sub_kpi_total = QLabel("Saved: 00m 00s (0.0% reduction)")
        self.sub_kpi_total.setStyleSheet("color: #10B981; font-weight: 700; font-size: 11px;")
        kpi_grid.addWidget(self.sub_kpi_total, 2, 0)

        # Card 2: Internal Machine Downtime
        kpi_grid.addWidget(QLabel("<b>MACHINE DOWNTIME (INTERNAL TIME)</b>"), 0, 1)
        self.val_kpi_internal = QLabel("00m 00s -> 00m 00s")
        self.val_kpi_internal.setStyleSheet("color: #EF4444; font-size: 15px; font-weight: 800; font-family: monospace;")
        kpi_grid.addWidget(self.val_kpi_internal, 1, 1)
        self.sub_kpi_internal = QLabel("0.0% machine downtime reduced")
        self.sub_kpi_internal.setStyleSheet("color: #94A3B8; font-size: 11px;")
        kpi_grid.addWidget(self.sub_kpi_internal, 2, 1)

        # Card 3: External Activity Shift
        kpi_grid.addWidget(QLabel("<b>EXTERNAL ACTIVITY SHIFT</b>"), 0, 2)
        self.val_kpi_external = QLabel("00m 00s -> 00m 00s")
        self.val_kpi_external.setStyleSheet("color: #34D399; font-size: 15px; font-weight: 800; font-family: monospace;")
        kpi_grid.addWidget(self.val_kpi_external, 1, 2)
        self.sub_kpi_external = QLabel("0 activities shifted outside downtime")
        self.sub_kpi_external.setStyleSheet("color: #94A3B8; font-size: 11px;")
        kpi_grid.addWidget(self.sub_kpi_external, 2, 2)

        # Card 4: 50% Reduction & Single-Minute Badge
        kpi_grid.addWidget(QLabel("<b>SMED GOAL & 6TH OK PART STATUS</b>"), 0, 3)
        self.badge_target_status = QLabel("50% TARGET: PENDING")
        self.badge_target_status.setStyleSheet("background-color: rgba(245, 158, 11, 0.25); color: #FBBF24; font-size: 11px; font-weight: 800; border-radius: 4px; padding: 2px 6px;")
        kpi_grid.addWidget(self.badge_target_status, 1, 3)
        self.sub_sixth_part = QLabel("6th OK Approval Part: Pending")
        self.sub_sixth_part.setStyleSheet("color: #94A3B8; font-size: 11px;")
        kpi_grid.addWidget(self.sub_sixth_part, 2, 3)

        # Card 5: #1 Bottleneck Solved Spotlight
        kpi_grid.addWidget(QLabel("<b>#1 BOTTLENECK SOLVED SPOTLIGHT</b>"), 0, 4)
        self.val_spotlight_name = QLabel("No Bottleneck Solved")
        self.val_spotlight_name.setStyleSheet("color: #38BDF8; font-size: 13px; font-weight: 800;")
        self.val_spotlight_name.setWordWrap(True)
        kpi_grid.addWidget(self.val_spotlight_name, 1, 4)
        self.sub_spotlight_sol = QLabel("Awaiting Kaizen verification trials")
        self.sub_spotlight_sol.setStyleSheet("color: #CBD5E1; font-size: 11px; font-style: italic;")
        self.sub_spotlight_sol.setWordWrap(True)
        kpi_grid.addWidget(self.sub_spotlight_sol, 2, 4)

        root_layout.addWidget(kpi_container)

        # =====================================================================
        # MAIN SPLITTER: Row 2 (Dual Charts) vs Row 3 (Comparative Table)
        # =====================================================================
        splitter = QSplitter(Qt.Orientation.Vertical)
        root_layout.addWidget(splitter, stretch=1)

        # ---------------------------------------------------------------------
        # ROW 2: Dual Matplotlib Visual Comparison Canvas
        # ---------------------------------------------------------------------
        charts_box = QGroupBox("Comparative Performance Analytics (Baseline vs. Kaizen Plan vs. Actual Verified)")
        charts_layout = QVBoxLayout(charts_box)
        charts_layout.setContentsMargins(6, 10, 6, 6)

        self.fig = Figure(facecolor="#1E293B", edgecolor="#334155")
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setMinimumHeight(230)
        charts_layout.addWidget(self.canvas)

        splitter.addWidget(charts_box)

        # ---------------------------------------------------------------------
        # ROW 3: Comprehensive Activity-by-Activity Comparative Table
        # ---------------------------------------------------------------------
        table_box = QGroupBox("Activity-by-Activity Verification & Plan vs. Actual Performance Matrix")
        table_layout = QVBoxLayout(table_box)
        table_layout.setContentsMargins(6, 10, 6, 6)

        self.table_compare = QTableWidget()
        self.table_compare.setColumnCount(11)
        self.table_compare.setHorizontalHeaderLabels([
            "Rank",
            "Standardized Activity",
            "Category Shift",
            "Before Avg (s)",
            "Kaizen Countermeasure Implemented",
            "Est. Target (s)",
            "Actual After (s)",
            "Time Saved (s)",
            "Improve %",
            "Share of Total",
            "Plan vs Actual",
        ])

        header = self.table_compare.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents) # Rank
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents) # Name
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents) # Category Shift
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents) # Before Avg
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)          # Solution
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents) # Est Target
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents) # Actual After
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents) # Time Saved
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.ResizeToContents) # Improve %
        header.setSectionResizeMode(9, QHeaderView.ResizeMode.ResizeToContents) # Share %
        header.setSectionResizeMode(10, QHeaderView.ResizeMode.ResizeToContents) # Status

        self.table_compare.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_compare.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_compare.setAlternatingRowColors(True)
        table_layout.addWidget(self.table_compare)

        splitter.addWidget(table_box)

        # Sizing ratio 45% chart : 55% table
        splitter.setSizes([310, 390])

    # =========================================================================
    # PROJECT SETTING & DATA REFRESH
    # =========================================================================

    def set_project(self, project_id: int):
        """Set active project and refresh comparative analytics."""
        self.active_project_id = project_id
        project = self.db.get_project(project_id)
        if project:
            self.lbl_project_title.setText(
                f"{project['name']}  ({project.get('machine_name') or 'Machine'})"
            )
        else:
            self.lbl_project_title.setText("Unknown Project")

        self.refresh_analytics()

    def refresh_analytics(self):
        """Query complete before/after comparison report and populate UI."""
        if not self.active_project_id:
            self._render_empty_canvas("No Active Project Selected")
            self._reset_kpi_cards()
            self.table_compare.setRowCount(0)
            return

        report = self.db.get_before_after_comparison_report(self.active_project_id)
        self.report_data = report

        if not report.get("has_data") or report.get("before_trials_count", 0) == 0:
            self._render_empty_canvas(
                "No 'BEFORE' Baseline Trials Recorded Yet.\n"
                "Record baseline videos in Tab 2 (Video Logger) to enable analytics."
            )
            self._reset_kpi_cards()
            self.table_compare.setRowCount(0)
            return

        # 1. Update 5 KPI Cards
        self._update_kpi_cards(report)

        # 2. Render Dual Comparison Charts
        self._render_dual_comparison_charts(report)

        # 3. Populate Comparative Table
        self._populate_comparative_table(report)

    def _reset_kpi_cards(self):
        self.val_kpi_total.setText("00m 00s -> 00m 00s")
        self.sub_kpi_total.setText("Saved: 00m 00s (0.0% reduction)")
        self.val_kpi_internal.setText("00m 00s -> 00m 00s")
        self.sub_kpi_internal.setText("0.0% machine downtime reduced")
        self.val_kpi_external.setText("00m 00s -> 00m 00s")
        self.sub_kpi_external.setText("0 activities shifted outside downtime")
        self.badge_target_status.setText("STATUS: NO DATA")
        self.badge_target_status.setStyleSheet("background-color: rgba(148, 163, 184, 0.2); color: #CBD5E1; font-size: 11px; font-weight: 800; border-radius: 4px; padding: 2px 6px;")
        self.sub_sixth_part.setText("6th OK Approval Part: Pending")
        self.val_spotlight_name.setText("No Data")
        self.sub_spotlight_sol.setText("Awaiting trials")

    # =========================================================================
    # ROW 1: KPI CARDS POPULATION
    # =========================================================================

    def _update_kpi_cards(self, rep: Dict[str, Any]):
        before_tot = rep["before_total_avg_sec"]
        after_tot = rep["after_total_avg_sec"]
        saved_tot = rep["total_reduction_sec"]
        pct_tot = rep["total_reduction_pct"]

        before_int = rep["before_internal_sec"]
        after_int = rep["after_internal_sec"]
        pct_int = rep["internal_reduction_pct"]

        before_ext = rep["before_external_sec"]
        after_ext = rep["after_external_sec"]
        converted_cnt = rep.get("converted_count", 0)

        # Card 1: Total Setup Time
        if rep["after_trials_count"] > 0:
            self.val_kpi_total.setText(f"{format_duration(before_tot)} -> {format_duration(after_tot)}")
            self.sub_kpi_total.setText(f"Saved: {format_duration(saved_tot)} (-{pct_tot:.1f}%)")
        else:
            self.val_kpi_total.setText(f"{format_duration(before_tot)} -> Pending")
            self.sub_kpi_total.setText("Awaiting AFTER verification trials")

        # Card 2: Internal Machine Downtime
        if rep["after_trials_count"] > 0:
            self.val_kpi_internal.setText(f"{format_duration(before_int)} -> {format_duration(after_int)}")
            self.sub_kpi_internal.setText(f"-{pct_int:.1f}% Machine Downtime Reduced")
        else:
            self.val_kpi_internal.setText(f"{format_duration(before_int)} (Baseline)")
            self.sub_kpi_internal.setText("Target: Reduce by >= 50%")

        # Card 3: External Time Shift
        if rep["after_trials_count"] > 0:
            self.val_kpi_external.setText(f"{format_duration(before_ext)} -> {format_duration(after_ext)}")
            self.sub_kpi_external.setText(f"{converted_cnt} Activity Converted to External")
        else:
            self.val_kpi_external.setText(f"{format_duration(before_ext)} (Baseline)")
            self.sub_kpi_external.setText("Shift activities outside downtime")

        # Card 4: 50% Reduction & Single-Minute Badge
        if rep["after_trials_count"] > 0:
            if rep["target_achieved"]:
                self.badge_target_status.setText(f"[50% TARGET ACHIEVED] (-{pct_tot:.1f}%)")
                self.badge_target_status.setStyleSheet("background-color: rgba(16, 185, 129, 0.25); color: #34D399; font-size: 11px; font-weight: 800; border: 1px solid #10B981; border-radius: 4px; padding: 2px 6px;")
            else:
                self.badge_target_status.setText(f"[TARGET IN PROGRESS] (-{pct_tot:.1f}%)")
                self.badge_target_status.setStyleSheet("background-color: rgba(245, 158, 11, 0.25); color: #FBBF24; font-size: 11px; font-weight: 800; border: 1px solid #F59E0B; border-radius: 4px; padding: 2px 6px;")

            sixth_verified = rep.get("all_sixth_ok_verified", False)
            if sixth_verified:
                self.sub_sixth_part.setText("6th OK Part: VERIFIED ON ALL TRIALS")
                self.sub_sixth_part.setStyleSheet("color: #34D399; font-weight: 700; font-size: 11px;")
            else:
                self.sub_sixth_part.setText("6th OK Part: Quality Signoff Pending")
                self.sub_sixth_part.setStyleSheet("color: #F87171; font-weight: 700; font-size: 11px;")
        else:
            self.badge_target_status.setText("STATUS: AWAITING AFTER TRIALS")
            self.badge_target_status.setStyleSheet("background-color: rgba(148, 163, 184, 0.2); color: #CBD5E1; font-size: 11px; font-weight: 800; border-radius: 4px; padding: 2px 6px;")
            self.sub_sixth_part.setText("6th OK Part: Not Verified Yet")
            self.sub_sixth_part.setStyleSheet("color: #94A3B8; font-size: 11px;")

        # Card 5: #1 Bottleneck Solved Spotlight
        top_spot = rep.get("top_spotlight")
        if top_spot and rep["after_trials_count"] > 0 and top_spot["reduction_sec"] > 0:
            self.val_spotlight_name.setText(top_spot["activity_name"][:40])
            sol_txt = top_spot.get("solution_implemented") or "Standardization & Quick Clamps"
            self.sub_spotlight_sol.setText(
                f"Saved {top_spot['reduction_sec']:.1f}s (-{top_spot['reduction_pct']:.1f}%) via '{sol_txt[:36]}'"
            )
        else:
            self.val_spotlight_name.setText("Top Bottleneck: Pending Verification")
            self.sub_spotlight_sol.setText("Record After video trials to confirm time savings")

    # =========================================================================
    # ROW 2: DUAL MATPLOTLIB VISUAL COMPARISON CANVAS
    # =========================================================================

    def _render_empty_canvas(self, message: str):
        self.fig.clear()
        ax = self.fig.add_subplot(111)
        ax.set_facecolor("#0F172A")
        ax.text(
            0.5, 0.5, message,
            color="#94A3B8", fontsize=12, fontweight="bold",
            ha="center", va="center", transform=ax.transAxes
        )
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_color("#334155")
        self.canvas.draw()

    def _render_dual_comparison_charts(self, rep: Dict[str, Any]):
        """
        Renders Dual Subplots:
        - Subplot 1 (Left): Stacked macro changeover breakdown (Internal vs External)
          comparing Baseline vs. Kaizen Plan vs. Actual After, with 50% target threshold.
        - Subplot 2 (Right): Horizontal grouped bar chart comparing Before vs. After
          for the top bottleneck activities.
        """
        self.fig.clear()

        # 2 Subplots side-by-side
        ax1 = self.fig.add_subplot(121)
        ax2 = self.fig.add_subplot(122)

        for ax in (ax1, ax2):
            ax.set_facecolor("#0F172A")
            for spine in ax.spines.values():
                spine.set_color("#334155")
            ax.grid(True, linestyle="--", alpha=0.2, color="#475569")

        # ---------------------------------------------------------------------
        # SUBPLOT 1: Macro Setup Breakdown (Stacked Bar)
        # ---------------------------------------------------------------------
        macro = rep.get("macro_breakdown", {})
        categories = ["Baseline (Before)", "Kaizen Plan", "Actual (After)"]

        int_times = [
            macro.get("before_internal_sec", 0.0),
            macro.get("projected_internal_sec", 0.0),
            macro.get("after_internal_sec", 0.0),
        ]
        ext_times = [
            macro.get("before_external_sec", 0.0),
            macro.get("projected_external_sec", 0.0),
            macro.get("after_external_sec", 0.0),
        ]

        x_pos = np.arange(len(categories))
        width = 0.52

        # Stacked Bars: Bottom = Internal (Red), Top = External (Green)
        bars_int = ax1.bar(
            x_pos, int_times, width,
            label="Internal (Machine OFF)",
            color="#EF4444", edgecolor="#334155", zorder=3
        )
        bars_ext = ax1.bar(
            x_pos, ext_times, width, bottom=int_times,
            label="External (Machine ON)",
            color="#10B981", edgecolor="#334155", zorder=3
        )

        # Total duration labels on top
        for i in range(len(categories)):
            tot = int_times[i] + ext_times[i]
            if tot > 0:
                ax1.annotate(
                    format_duration(tot),
                    xy=(x_pos[i], tot),
                    xytext=(0, 4), textcoords="offset points",
                    ha="center", va="bottom",
                    color="#F8FAFC", fontsize=9, fontweight="bold"
                )

        # 50% Target Threshold line
        target_thresh = macro.get("target_threshold_sec", 0.0)
        if target_thresh > 0:
            ax1.axhline(
                target_thresh,
                color="#F59E0B", linestyle="--", linewidth=1.8, zorder=4,
                label=f"50% Target Threshold ({format_duration(target_thresh)})"
            )

        ax1.set_title("Macro Setup Duration Breakdown", color="#38BDF8", fontsize=11, fontweight="bold")
        ax1.set_ylabel("Duration (Seconds)", color="#F8FAFC", fontsize=9, fontweight="bold")
        ax1.set_xticks(x_pos)
        ax1.set_xticklabels(categories, color="#E2E8F0", fontsize=9, fontweight="bold")
        ax1.tick_params(colors="#F8FAFC", labelsize=9)

        leg1 = ax1.legend(loc="upper right", facecolor="#1E293B", edgecolor="#334155", fontsize=8)
        for text in leg1.get_texts():
            text.set_color("#F8FAFC")

        # ---------------------------------------------------------------------
        # SUBPLOT 2: Activity-by-Activity Before vs. After (Top Bottlenecks)
        # ---------------------------------------------------------------------
        activities = rep.get("activities_list", [])[:6]  # Top 6 bottlenecks
        if activities:
            act_names = [
                (it["activity_name"][:20] + "..") if len(it["activity_name"]) > 22 else it["activity_name"]
                for it in activities
            ]
            before_vals = [it["before_avg_sec"] for it in activities]
            after_vals = [it["after_avg_sec"] for it in activities]

            y_pos = np.arange(len(act_names))
            h_bar = 0.36

            # Invert so rank #1 is at the top
            act_names.reverse()
            before_vals.reverse()
            after_vals.reverse()

            bars_b = ax2.barh(
                y_pos + h_bar / 2, before_vals, h_bar,
                label="Before Avg", color="#475569", edgecolor="#334155", zorder=3
            )
            bars_a = ax2.barh(
                y_pos - h_bar / 2, after_vals, h_bar,
                label="After Avg", color="#0EA5E9", edgecolor="#334155", zorder=3
            )

            # Annotation labels
            for idx, rect in enumerate(bars_a):
                diff = before_vals[idx] - after_vals[idx]
                if diff > 0 and before_vals[idx] > 0:
                    pct = (diff / before_vals[idx]) * 100
                    ax2.annotate(
                        f" -{diff:.0f}s (-{pct:.0f}%)",
                        xy=(rect.get_width(), rect.get_y() + rect.get_height() / 2),
                        xytext=(4, 0), textcoords="offset points",
                        ha="left", va="center",
                        color="#10B981", fontsize=8, fontweight="bold"
                    )

            ax2.set_title("Top Bottlenecks: Before vs. After Duration", color="#38BDF8", fontsize=11, fontweight="bold")
            ax2.set_xlabel("Seconds", color="#F8FAFC", fontsize=9, fontweight="bold")
            ax2.set_yticks(y_pos)
            ax2.set_yticklabels(act_names, color="#E2E8F0", fontsize=8)
            ax2.tick_params(colors="#F8FAFC", labelsize=8)

            leg2 = ax2.legend(loc="lower right", facecolor="#1E293B", edgecolor="#334155", fontsize=8)
            for text in leg2.get_texts():
                text.set_color("#F8FAFC")

        self.fig.tight_layout()
        self.canvas.draw()

    # =========================================================================
    # ROW 3: COMPREHENSIVE COMPARATIVE TABLE
    # =========================================================================

    def _populate_comparative_table(self, rep: Dict[str, Any]):
        """Populate activity-by-activity comparative table with badges."""
        self.table_compare.setRowCount(0)
        activities = rep.get("activities_list", [])

        for row_idx, item in enumerate(activities):
            self.table_compare.insertRow(row_idx)

            # 1. Rank
            rank_item = QTableWidgetItem(f"#{item.get('baseline_rank', row_idx + 1)}")
            rank_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_compare.setItem(row_idx, 0, rank_item)

            # 2. Activity Name
            name_item = QTableWidgetItem(item["activity_name"])
            name_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            self.table_compare.setItem(row_idx, 1, name_item)

            # 3. Category Shift Badge
            shift_label = QLabel(f" {item.get('category_shift', '')} ")
            shift_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            if item.get("is_converted"):
                shift_label.setStyleSheet(
                    "background-color: rgba(16, 185, 129, 0.25); color: #34D399; font-weight: 800; "
                    "border: 1px solid #10B981; border-radius: 4px; padding: 2px 6px;"
                )
            elif "Internal" in item.get("category_shift", ""):
                shift_label.setStyleSheet(get_internal_badge_style())
            else:
                shift_label.setStyleSheet(get_external_badge_style())
            self.table_compare.setCellWidget(row_idx, 2, shift_label)

            # 4. Before Avg (s)
            b_item = QTableWidgetItem(f"{item['before_avg_sec']:.1f}")
            b_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table_compare.setItem(row_idx, 3, b_item)

            # 5. Kaizen Solution Implemented
            sol_item = QTableWidgetItem(item.get("solution_implemented") or "—")
            self.table_compare.setItem(row_idx, 4, sol_item)

            # 6. Est. Target (s)
            est_item = QTableWidgetItem(f"{item.get('est_target_sec', 0.0):.1f}")
            est_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            est_item.setForeground(QColor("#94A3B8"))
            self.table_compare.setItem(row_idx, 5, est_item)

            # 7. Actual After (s)
            a_item = QTableWidgetItem(f"{item['after_avg_sec']:.1f}")
            a_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            a_item.setForeground(QColor("#38BDF8"))
            a_item.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
            self.table_compare.setItem(row_idx, 6, a_item)

            # 8. Time Saved (s)
            saved_sec = item["reduction_sec"]
            saved_item = QTableWidgetItem(f"{saved_sec:.1f}")
            saved_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            saved_item.setForeground(QColor("#10B981" if saved_sec > 0 else "#94A3B8"))
            saved_item.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
            self.table_compare.setItem(row_idx, 7, saved_item)

            # 9. Improvement %
            pct_item = QTableWidgetItem(f"{item['reduction_pct']:.1f}%")
            pct_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            pct_item.setForeground(QColor("#10B981" if item["reduction_pct"] > 0 else "#94A3B8"))
            self.table_compare.setItem(row_idx, 8, pct_item)

            # 10. Share of Total Savings %
            share_item = QTableWidgetItem(f"{item.get('savings_share_pct', 0.0):.1f}%")
            share_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table_compare.setItem(row_idx, 9, share_item)

            # 11. Plan vs Actual Status Badge
            status_text = item.get("plan_vs_actual_status") or "On Target"
            status_label = QLabel(f" {status_text} ")
            status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            if "Beat" in status_text:
                status_label.setStyleSheet("background-color: rgba(16, 185, 129, 0.2); color: #34D399; font-weight: 700; border-radius: 4px; padding: 2px 4px;")
            elif "On Target" in status_text:
                status_label.setStyleSheet("background-color: rgba(14, 165, 233, 0.2); color: #38BDF8; font-weight: 700; border-radius: 4px; padding: 2px 4px;")
            else:
                status_label.setStyleSheet("background-color: rgba(245, 158, 11, 0.2); color: #FBBF24; font-weight: 700; border-radius: 4px; padding: 2px 4px;")
            self.table_compare.setCellWidget(row_idx, 10, status_label)

    # =========================================================================
    # EXPORT ACTION HANDLERS
    # =========================================================================

    def _on_export_excel(self):
        """Prompt file location and export 3-sheet Excel report."""
        if not self.active_project_id or not self.report_data or not self.report_data.get("has_data"):
            QMessageBox.warning(self, "No Data", "No project analytics data available to export.")
            return

        proj_name = self.report_data.get("project_name", "SMED_Project").replace(" ", "_")
        default_filename = f"{proj_name}_Executive_SMED_Report.xlsx"

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Full Excel Report",
            default_filename,
            "Excel Workbook (*.xlsx);;All Files (*.*)",
        )
        if file_path:
            try:
                export_project_to_excel(self.db, self.active_project_id, file_path)
                self.report_exported.emit(file_path)
                QMessageBox.information(
                    self,
                    "Excel Export Complete",
                    f"Full 3-sheet SMED Executive Report exported successfully to:\n\n{file_path}"
                )
            except Exception as e:
                QMessageBox.critical(self, "Export Failed", f"Failed to export Excel report:\n{str(e)}")

    def _on_export_pdf(self):
        """Render temporary comparison chart image and export executive PDF."""
        if not self.active_project_id or not self.report_data or not self.report_data.get("has_data"):
            QMessageBox.warning(self, "No Data", "No project analytics data available to export.")
            return

        proj_name = self.report_data.get("project_name", "SMED_Project").replace(" ", "_")
        default_filename = f"{proj_name}_Executive_Kaizen_A3_Report.pdf"

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Executive PDF Report",
            default_filename,
            "PDF Document (*.pdf);;All Files (*.*)",
        )
        if file_path:
            temp_png = None
            try:
                # Save high-res chart image for embedding into PDF
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tf:
                    temp_png = tf.name

                self.fig.savefig(temp_png, dpi=200, bbox_inches="tight", facecolor=self.fig.get_facecolor())

                export_project_to_pdf(
                    db=self.db,
                    project_id=self.active_project_id,
                    filepath=file_path,
                    chart_png_path=temp_png,
                )
                self.report_exported.emit(file_path)
                QMessageBox.information(
                    self,
                    "PDF Export Complete",
                    f"Printable Executive SMED Kaizen A3 Report exported successfully to:\n\n{file_path}"
                )
            except Exception as e:
                QMessageBox.critical(self, "Export Failed", f"Failed to export PDF report:\n{str(e)}")
            finally:
                if temp_png and os.path.exists(temp_png):
                    try:
                        os.remove(temp_png)
                    except Exception:
                        pass
