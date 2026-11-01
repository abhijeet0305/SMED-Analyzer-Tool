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
    QGroupBox, QFrame, QFileDialog, QMessageBox, QAbstractItemView,
    QScrollArea, QSizePolicy
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
        self._dashboard_kpi_cards: List[QFrame] = []
        self._kpi_grid: Optional[QGridLayout] = None
        self._kpi_columns = 0

        self._init_ui()

    def _init_ui(self):
        page_layout = QVBoxLayout(self)
        page_layout.setContentsMargins(0, 0, 0, 0)

        scroll_area = QScrollArea(self)
        scroll_area.setObjectName("dashboardPageScrollArea")
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        page_layout.addWidget(scroll_area)

        page_content = QWidget()
        page_content.setObjectName("dashboardPageContent")
        scroll_area.setWidget(page_content)

        root_layout = QVBoxLayout(page_content)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(10)

        # =====================================================================
        # TOP TOOLBAR: Active Project Title & Export Action Buttons
        # =====================================================================
        top_bar = QFrame()
        top_bar.setObjectName("dashboardToolbar")
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(12, 8, 12, 8)
        top_layout.setSpacing(8)

        project_label = QLabel("ACTIVE PROJECT")
        project_label.setObjectName("dashboardToolbarLabel")
        top_layout.addWidget(project_label)
        self.lbl_project_title = QLabel("No Project Selected")
        self.lbl_project_title.setObjectName("dashboardProjectTitle")
        self.lbl_project_title.setWordWrap(True)
        self.lbl_project_title.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        top_layout.addWidget(self.lbl_project_title, 1)

        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.setToolTip("Refresh the dashboard analytics for the active project.")
        self.btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_refresh.clicked.connect(self.refresh_analytics)
        top_layout.addWidget(self.btn_refresh)

        self.btn_export_excel = QPushButton("Export Excel")
        self.btn_export_excel.setToolTip("Export the full Excel report (.xlsx).")
        self.btn_export_excel.setObjectName("primaryBtn")
        self.btn_export_excel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_export_excel.clicked.connect(self._on_export_excel)
        top_layout.addWidget(self.btn_export_excel)

        self.btn_export_pdf = QPushButton("Export PDF")
        self.btn_export_pdf.setToolTip("Export the executive PDF report (.pdf).")
        self.btn_export_pdf.setObjectName("successBtn")
        self.btn_export_pdf.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_export_pdf.clicked.connect(self._on_export_pdf)
        top_layout.addWidget(self.btn_export_pdf)

        root_layout.addWidget(top_bar)

        # =====================================================================
        # ROW 1: 5 EXECUTIVE KPI CARDS
        # =====================================================================
        kpi_container = QFrame()
        kpi_container.setObjectName("dashboardKpiContainer")
        kpi_grid = QGridLayout(kpi_container)
        kpi_grid.setContentsMargins(0, 0, 0, 0)
        kpi_grid.setHorizontalSpacing(8)
        kpi_grid.setVerticalSpacing(8)
        self._kpi_grid = kpi_grid

        # Card 1: Total SMED Setup Time
        card_total = self._create_kpi_card(kpi_grid, 0, "TOTAL SETUP TIME")
        self.val_kpi_total = QLabel("00m 00s -> 00m 00s")
        self.val_kpi_total.setObjectName("dashboardKpiValue")
        self.val_kpi_total.setProperty("kind", "total")
        self.val_kpi_total.setWordWrap(True)
        card_total.addWidget(self.val_kpi_total)
        self.sub_kpi_total = QLabel("Saved: 00m 00s (0.0% reduction)")
        self.sub_kpi_total.setObjectName("dashboardKpiSubtext")
        self.sub_kpi_total.setWordWrap(True)
        card_total.addWidget(self.sub_kpi_total)

        # Card 2: Internal Machine Downtime
        card_internal = self._create_kpi_card(kpi_grid, 1, "MACHINE DOWNTIME")
        self.val_kpi_internal = QLabel("00m 00s -> 00m 00s")
        self.val_kpi_internal.setObjectName("dashboardKpiValue")
        self.val_kpi_internal.setProperty("kind", "internal")
        self.val_kpi_internal.setWordWrap(True)
        card_internal.addWidget(self.val_kpi_internal)
        self.sub_kpi_internal = QLabel("0.0% machine downtime reduced")
        self.sub_kpi_internal.setObjectName("dashboardKpiSubtext")
        self.sub_kpi_internal.setWordWrap(True)
        card_internal.addWidget(self.sub_kpi_internal)

        # Card 3: External Activity Shift
        card_external = self._create_kpi_card(kpi_grid, 2, "EXTERNAL ACTIVITY SHIFT")
        self.val_kpi_external = QLabel("00m 00s -> 00m 00s")
        self.val_kpi_external.setObjectName("dashboardKpiValue")
        self.val_kpi_external.setProperty("kind", "external")
        self.val_kpi_external.setWordWrap(True)
        card_external.addWidget(self.val_kpi_external)
        self.sub_kpi_external = QLabel("0 activities shifted outside downtime")
        self.sub_kpi_external.setObjectName("dashboardKpiSubtext")
        self.sub_kpi_external.setWordWrap(True)
        card_external.addWidget(self.sub_kpi_external)

        # Card 4: 50% Reduction & Single-Minute Badge
        card_status = self._create_kpi_card(kpi_grid, 3, "SMED GOAL & QUALITY STATUS")
        self.badge_target_status = QLabel("50% TARGET: PENDING")
        self.badge_target_status.setObjectName("dashboardStatusBadge")
        self.badge_target_status.setProperty("status", "pending")
        self.badge_target_status.setWordWrap(True)
        card_status.addWidget(self.badge_target_status)
        self.sub_sixth_part = QLabel("6th OK Approval Part: Pending")
        self.sub_sixth_part.setObjectName("dashboardKpiSubtext")
        self.sub_sixth_part.setProperty("status", "pending")
        self.sub_sixth_part.setWordWrap(True)
        card_status.addWidget(self.sub_sixth_part)

        # Card 5: #1 Bottleneck Solved Spotlight
        card_spotlight = self._create_kpi_card(kpi_grid, 4, "BOTTLENECK SPOTLIGHT")
        self.val_spotlight_name = QLabel("No Bottleneck Solved")
        self.val_spotlight_name.setObjectName("dashboardKpiValue")
        self.val_spotlight_name.setProperty("kind", "spotlight")
        self.val_spotlight_name.setWordWrap(True)
        card_spotlight.addWidget(self.val_spotlight_name)
        self.sub_spotlight_sol = QLabel("Awaiting Kaizen verification trials")
        self.sub_spotlight_sol.setObjectName("dashboardKpiSubtext")
        self.sub_spotlight_sol.setWordWrap(True)
        card_spotlight.addWidget(self.sub_spotlight_sol)

        root_layout.addWidget(kpi_container)

        # ---------------------------------------------------------------------
        # ROW 2: Dual Matplotlib Visual Comparison Canvas
        # ---------------------------------------------------------------------
        charts_box = QGroupBox("Comparative Performance Analytics (Baseline vs. Kaizen Plan vs. Actual Verified)")
        charts_box.setMinimumWidth(0)
        charts_box.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        charts_layout = QVBoxLayout(charts_box)
        charts_layout.setContentsMargins(6, 10, 6, 6)

        self.fig = Figure(facecolor=COLORS["bg_card"], edgecolor=COLORS["border"])
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setMinimumWidth(0)
        self.canvas.setMinimumHeight(360)
        self.canvas.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        charts_layout.addWidget(self.canvas)

        root_layout.addWidget(charts_box)

        # ---------------------------------------------------------------------
        # ROW 3: Comprehensive Activity-by-Activity Comparative Table
        # ---------------------------------------------------------------------
        table_box = QGroupBox("Activity-by-Activity Verification & Plan vs. Actual Performance Matrix")
        table_box.setMinimumWidth(0)
        table_box.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        table_layout = QVBoxLayout(table_box)
        table_layout.setContentsMargins(6, 10, 6, 6)

        self.table_compare = QTableWidget()
        self.table_compare.setObjectName("dashboardComparisonTable")
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
        column_widths = (72, 270, 170, 120, 420, 120, 120, 125, 110, 125, 150)
        for column, width in enumerate(column_widths):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.Interactive)
            self.table_compare.setColumnWidth(column, width)
        header.setMinimumHeight(42)
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table_compare.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_compare.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_compare.setAlternatingRowColors(True)
        self.table_compare.setMinimumWidth(0)
        self.table_compare.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)
        self.table_compare.setWordWrap(True)
        self.table_compare.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.table_compare.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.table_compare.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.table_compare.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.table_compare.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.table_compare.setMinimumHeight(300)
        self.table_compare.setMaximumHeight(430)
        self.table_compare.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.table_compare.verticalHeader().setDefaultSectionSize(44)
        table_layout.addWidget(self.table_compare)

        root_layout.addWidget(table_box)
        root_layout.addStretch(1)
        self._arrange_kpi_cards()

    def _create_kpi_card(self, grid: QGridLayout, column: int, title: str) -> QVBoxLayout:
        card = QFrame()
        card.setObjectName("dashboardKpiCard")
        card.setMinimumHeight(128)
        self._dashboard_kpi_cards.append(card)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(7)
        title_label = QLabel(title)
        title_label.setObjectName("dashboardKpiTitle")
        title_label.setWordWrap(True)
        layout.addWidget(title_label)
        grid.addWidget(card, 0, column)
        return layout

    def _arrange_kpi_cards(self):
        if self._kpi_grid is None or len(self._dashboard_kpi_cards) != 5:
            return

        columns = 5 if self.width() >= 1360 else 3
        if columns == self._kpi_columns:
            return

        for card in self._dashboard_kpi_cards:
            self._kpi_grid.removeWidget(card)

        for column in range(5):
            self._kpi_grid.setColumnStretch(column, 1 if column < columns else 0)

        for index, card in enumerate(self._dashboard_kpi_cards):
            row, column = divmod(index, columns)
            self._kpi_grid.addWidget(card, row, column)
        self._kpi_columns = columns

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._arrange_kpi_cards()

    # =========================================================================
    # PROJECT SETTING & DATA REFRESH
    # =========================================================================

    def set_project(self, project_id: int):
        """Set active project and refresh comparative analytics."""
        self.active_project_id = project_id
        project = self.db.get_project(project_id)
        if project:
            self.lbl_project_title.setText(project["name"])
            self.lbl_project_title.setToolTip(
                f"{project['name']} - {project.get('machine_name') or 'Machine'}"
            )
        else:
            self.lbl_project_title.setText("Unknown Project")
            self.lbl_project_title.setToolTip("Unknown Project")

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
        self._set_dashboard_status(self.badge_target_status, "pending")
        self.sub_sixth_part.setText("6th OK Approval Part: Pending")
        self._set_dashboard_status(self.sub_sixth_part, "pending")
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
                self._set_dashboard_status(self.badge_target_status, "success")
            else:
                self.badge_target_status.setText(f"[TARGET IN PROGRESS] (-{pct_tot:.1f}%)")
                self._set_dashboard_status(self.badge_target_status, "warning")

            sixth_verified = rep.get("all_sixth_ok_verified", False)
            if sixth_verified:
                self.sub_sixth_part.setText("6th OK Part: VERIFIED ON ALL TRIALS")
                self._set_dashboard_status(self.sub_sixth_part, "success")
            else:
                self.sub_sixth_part.setText("6th OK Part: Quality Signoff Pending")
                self._set_dashboard_status(self.sub_sixth_part, "warning")
        else:
            self.badge_target_status.setText("STATUS: AWAITING AFTER TRIALS")
            self._set_dashboard_status(self.badge_target_status, "pending")
            self.sub_sixth_part.setText("6th OK Part: Not Verified Yet")
            self._set_dashboard_status(self.sub_sixth_part, "pending")

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

    @staticmethod
    def _set_dashboard_status(widget: QWidget, status: str):
        widget.setProperty("status", status)
        widget.style().unpolish(widget)
        widget.style().polish(widget)
        widget.update()

    # =========================================================================
    # ROW 2: DUAL MATPLOTLIB VISUAL COMPARISON CANVAS
    # =========================================================================

    def _render_empty_canvas(self, message: str):
        self.fig.clear()
        self.fig.set_facecolor(COLORS["bg_card"])
        ax = self.fig.add_subplot(111)
        ax.set_facecolor(COLORS["bg_card"])
        ax.text(
            0.5, 0.5, message,
            color=COLORS["text_secondary"], fontsize=12, fontweight="bold",
            ha="center", va="center", transform=ax.transAxes
        )
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_color(COLORS["border"])
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
        self.fig.set_facecolor(COLORS["bg_card"])

        # 2 Subplots side-by-side
        ax1 = self.fig.add_subplot(121)
        ax2 = self.fig.add_subplot(122)

        for ax in (ax1, ax2):
            ax.set_facecolor(COLORS["bg_card"])
            for spine in ax.spines.values():
                spine.set_color(COLORS["border"])
            ax.grid(True, linestyle="--", alpha=0.4, color=COLORS["border"])

        # ---------------------------------------------------------------------
        # SUBPLOT 1: Macro Setup Breakdown (Stacked Bar)
        # ---------------------------------------------------------------------
        macro = rep.get("macro_breakdown", {})
        actual_verified = rep.get("after_trials_count", 0) > 0
        categories = [
            "Baseline (Before)",
            "Kaizen Plan",
            "Actual (After)" if actual_verified else "Actual (Pending)",
        ]

        int_times = [
            macro.get("before_internal_sec", 0.0),
            macro.get("projected_internal_sec", 0.0),
            macro.get("after_internal_sec", 0.0) if actual_verified else np.nan,
        ]
        ext_times = [
            macro.get("before_external_sec", 0.0),
            macro.get("projected_external_sec", 0.0),
            macro.get("after_external_sec", 0.0) if actual_verified else np.nan,
        ]

        x_pos = np.arange(len(categories))
        width = 0.52

        # Stacked Bars: Bottom = Internal (Red), Top = External (Green)
        bars_int = ax1.bar(
            x_pos, int_times, width,
            label="Internal (Machine OFF)",
            color=COLORS["internal_red"], edgecolor=COLORS["bg_card"], zorder=3
        )
        bars_ext = ax1.bar(
            x_pos, ext_times, width, bottom=int_times,
            label="External (Machine ON)",
            color=COLORS["external_emerald"], edgecolor=COLORS["bg_card"], zorder=3
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
                    color=COLORS["text_primary"], fontsize=9, fontweight="bold"
                )
        max_total = max((internal + external for internal, external in zip(int_times, ext_times)), default=0.0)
        if max_total > 0:
            ax1.set_ylim(top=max_total * 1.4)

        # 50% Target Threshold line
        target_thresh = macro.get("target_threshold_sec", 0.0)
        if target_thresh > 0:
            ax1.axhline(
                target_thresh,
                color=COLORS["warning_amber"], linestyle="--", linewidth=1.8, zorder=4,
                label=f"50% Target Threshold ({format_duration(target_thresh)})"
            )
        if not actual_verified:
            ax1.text(
                x_pos[2],
                0.5,
                "AFTER TRIALS\nNOT VERIFIED",
                transform=ax1.get_xaxis_transform(),
                ha="center",
                va="center",
                color=COLORS["warning_amber"],
                fontsize=8,
                fontweight="bold",
                bbox={"facecolor": "#FFF4D6", "edgecolor": "#E8C46A", "boxstyle": "round,pad=0.35"},
            )

        ax1.set_title("Macro Setup Duration Breakdown", color=COLORS["deep_navy"], fontsize=11, fontweight="bold")
        ax1.set_ylabel("Duration (Seconds)", color=COLORS["text_primary"], fontsize=9, fontweight="bold")
        ax1.set_xticks(x_pos)
        ax1.set_xticklabels(categories, color=COLORS["text_primary"], fontsize=9, fontweight="bold")
        ax1.tick_params(colors=COLORS["text_secondary"], labelsize=9)

        leg1 = ax1.legend(
            loc="upper right",
            facecolor=COLORS["bg_card_elevated"],
            edgecolor=COLORS["border"],
            fontsize=8,
        )
        for text in leg1.get_texts():
            text.set_color(COLORS["text_primary"])

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
            after_vals = [
                it["after_avg_sec"] if actual_verified else np.nan
                for it in activities
            ]

            y_pos = np.arange(len(act_names))
            h_bar = 0.36

            # Invert so rank #1 is at the top
            act_names.reverse()
            before_vals.reverse()
            after_vals.reverse()

            bars_b = ax2.barh(
                y_pos + h_bar / 2, before_vals, h_bar,
                label="Before Avg", color="#9AAABD", edgecolor=COLORS["bg_card"], zorder=3
            )
            after_label = "After Avg" if actual_verified else "After Avg (Pending)"
            bars_a = ax2.barh(
                y_pos - h_bar / 2, after_vals, h_bar,
                label=after_label, color=COLORS["primary_blue"], edgecolor=COLORS["bg_card"], zorder=3
            )

            # Annotation labels
            for idx, rect in enumerate(bars_a):
                if not actual_verified:
                    continue
                diff = before_vals[idx] - after_vals[idx]
                if diff > 0 and before_vals[idx] > 0:
                    pct = (diff / before_vals[idx]) * 100
                    ax2.annotate(
                        f" -{diff:.0f}s (-{pct:.0f}%)",
                        xy=(rect.get_width(), rect.get_y() + rect.get_height() / 2),
                        xytext=(4, 0), textcoords="offset points",
                        ha="left", va="center",
                        color=COLORS["external_emerald"], fontsize=8, fontweight="bold"
                    )

            ax2.set_title(
                "Top Bottlenecks: Before vs. After\nDuration",
                color=COLORS["deep_navy"],
                fontsize=11,
                fontweight="bold",
            )
            ax2.set_xlabel("Seconds", color=COLORS["text_primary"], fontsize=9, fontweight="bold")
            ax2.set_yticks(y_pos)
            ax2.set_yticklabels(act_names, color=COLORS["text_primary"], fontsize=8)
            ax2.tick_params(colors=COLORS["text_secondary"], labelsize=8)
            if not actual_verified:
                ax2.text(
                    0.98,
                    0.04,
                    "After trials not verified",
                    transform=ax2.transAxes,
                    ha="right",
                    va="bottom",
                    color=COLORS["warning_amber"],
                    fontsize=8,
                    fontweight="bold",
                )

            leg2 = ax2.legend(
                loc="lower right",
                facecolor=COLORS["bg_card_elevated"],
                edgecolor=COLORS["border"],
                fontsize=8,
            )
            for text in leg2.get_texts():
                text.set_color(COLORS["text_primary"])

        self.fig.tight_layout()
        self.canvas.draw()

    # =========================================================================
    # ROW 3: COMPREHENSIVE COMPARATIVE TABLE
    # =========================================================================

    def _populate_comparative_table(self, rep: Dict[str, Any]):
        """Populate activity-by-activity comparative table with badges."""
        self.table_compare.setRowCount(0)
        activities = rep.get("activities_list", [])
        actual_verified = rep.get("after_trials_count", 0) > 0

        for row_idx, item in enumerate(activities):
            self.table_compare.insertRow(row_idx)
            self.table_compare.setRowHeight(row_idx, 48)

            # 1. Rank
            rank_item = QTableWidgetItem(f"#{item.get('baseline_rank', row_idx + 1)}")
            rank_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_compare.setItem(row_idx, 0, rank_item)

            # 2. Activity Name
            name_item = QTableWidgetItem(item["activity_name"])
            name_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            name_item.setToolTip(item["activity_name"])
            self.table_compare.setItem(row_idx, 1, name_item)

            # 3. Category Shift Badge
            category_shift = (
                item.get("category_shift", "")
                if actual_verified
                else f"{item.get('before_type', 'Baseline')} -> Pending"
            )
            shift_label = QLabel(f" {category_shift} ")
            shift_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            if actual_verified and item.get("is_converted"):
                shift_label.setStyleSheet(get_external_badge_style())
            elif "Internal" in category_shift:
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
            sol_item.setToolTip(item.get("solution_implemented") or "No countermeasure recorded.")
            self.table_compare.setItem(row_idx, 4, sol_item)

            # 6. Est. Target (s)
            est_item = QTableWidgetItem(f"{item.get('est_target_sec', 0.0):.1f}")
            est_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            est_item.setForeground(QColor(COLORS["text_muted"]))
            self.table_compare.setItem(row_idx, 5, est_item)

            # 7. Actual After (s)
            a_item = QTableWidgetItem(
                f"{item['after_avg_sec']:.1f}" if actual_verified else "Pending"
            )
            a_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            a_item.setForeground(QColor(
                COLORS["primary_blue_pressed"] if actual_verified else COLORS["text_muted"]
            ))
            a_item.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
            self.table_compare.setItem(row_idx, 6, a_item)

            # 8. Time Saved (s)
            saved_sec = item["reduction_sec"]
            saved_item = QTableWidgetItem(f"{saved_sec:.1f}" if actual_verified else "Pending")
            saved_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            saved_item.setForeground(QColor(
                COLORS["external_emerald"] if actual_verified and saved_sec > 0 else COLORS["text_muted"]
            ))
            saved_item.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
            self.table_compare.setItem(row_idx, 7, saved_item)

            # 9. Improvement %
            pct_item = QTableWidgetItem(
                f"{item['reduction_pct']:.1f}%" if actual_verified else "Pending"
            )
            pct_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            pct_item.setForeground(QColor(
                COLORS["external_emerald"]
                if actual_verified and item["reduction_pct"] > 0
                else COLORS["text_muted"]
            ))
            self.table_compare.setItem(row_idx, 8, pct_item)

            # 10. Share of Total Savings %
            share_item = QTableWidgetItem(
                f"{item.get('savings_share_pct', 0.0):.1f}%" if actual_verified else "Pending"
            )
            share_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table_compare.setItem(row_idx, 9, share_item)

            # 11. Plan vs Actual Status Badge
            status_text = (
                item.get("plan_vs_actual_status") or "On Target"
                if actual_verified
                else "Pending Verification"
            )
            status_label = QLabel(f" {status_text} ")
            status_label.setObjectName("dashboardPlanStatus")
            status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            if "Beat" in status_text:
                status = "success"
            elif "On Target" in status_text:
                status = "onTarget"
            else:
                status = "warning"
            status_label.setProperty("status", status)
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
