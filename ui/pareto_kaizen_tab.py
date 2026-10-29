"""
SMED Studio - Pareto Analysis & Kaizen Brainstorming Matrix Tab
Aggregates multi-video baseline observations, renders embedded Matplotlib 80/20 Pareto chart,
and provides an interactive Kaizen action board with dynamic KPI recalculations.
"""

from typing import Any, Dict, List, Optional
import os
import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.ticker as ticker
import pandas as pd

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QSplitter, QGroupBox, QFrame, QDoubleSpinBox,
    QLineEdit, QFileDialog, QMessageBox, QAbstractItemView
)

from database.db_manager import DatabaseManager, get_db
from ui.styles import (
    COLORS,
    get_internal_badge_style,
    get_external_badge_style
)


def format_seconds_min(seconds: float) -> str:
    """Format seconds into MMm SSs (seconds) format."""
    if seconds < 0:
        seconds = 0.0
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins:02d}m {secs:02d}s ({seconds:.1f}s)"


class ParetoKaizenTab(QWidget):
    """
    Phase 3: Pareto Analysis & Kaizen Brainstorming Matrix Tab.
    Provides automated multi-video aggregation, 80/20 bottleneck visualization,
    and an interactive ECRS / SMED stage action table with live savings calculations.
    """
    kaizen_updated = pyqtSignal()

    SMED_ACTION_STAGES = [
        "Stage 2: Convert Internal -> External",
        "Stage 3: Streamline / Quick Fasteners (One-Turn / Clamps)",
        "Eliminate Waste (ECRS)",
        "Parallelize Operation",
        "Stage 1: Separate Internal -> External",
    ]

    def __init__(self, db: Optional[DatabaseManager] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.db = db or get_db()
        self.active_project_id: Optional[int] = None
        self.category_filter: Optional[str] = None
        self.current_df: Optional[pd.DataFrame] = None

        # Tracking row widgets for dynamic recalculation & batch save
        # row_idx -> dict of widgets and metadata
        self.row_widgets: Dict[int, Dict[str, Any]] = {}

        self._init_ui()

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(10)

        # =====================================================================
        # TOP TOOLBAR: Project Indicator, Filter, Refresh & Export Buttons
        # =====================================================================
        top_bar = QFrame()
        top_bar.setStyleSheet("background-color: #1E293B; border-radius: 6px; padding: 6px;")
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(8, 4, 8, 4)
        top_layout.setSpacing(12)

        top_layout.addWidget(QLabel("<b>Active Project:</b>"))
        self.lbl_project_name = QLabel("No Project Selected")
        self.lbl_project_name.setStyleSheet("color: #38BDF8; font-weight: 700; font-size: 14px;")
        top_layout.addWidget(self.lbl_project_name)

        top_layout.addSpacing(16)

        # Category Filter Dropdown
        top_layout.addWidget(QLabel("<b>View Filter:</b>"))
        self.combo_filter = QComboBox()
        self.combo_filter.addItems([
            "All Activities (Internal + External)",
            "Internal Activities Only (Machine Stopped)",
            "External Activities Only (Machine Running)",
        ])
        self.combo_filter.currentIndexChanged.connect(self._on_filter_changed)
        top_layout.addWidget(self.combo_filter)

        top_layout.addStretch()

        # Action Buttons
        self.btn_refresh = QPushButton(" Refresh Data from Videos")
        self.btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_refresh.clicked.connect(self.refresh_data)
        top_layout.addWidget(self.btn_refresh)

        self.btn_export_chart = QPushButton(" Export Pareto Chart (PNG)")
        self.btn_export_chart.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_export_chart.clicked.connect(self._export_pareto_chart)
        top_layout.addWidget(self.btn_export_chart)

        self.btn_save_all = QPushButton(" Save All Kaizen Solutions")
        self.btn_save_all.setObjectName("successBtn")
        self.btn_save_all.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save_all.clicked.connect(self._save_all_kaizen_solutions)
        top_layout.addWidget(self.btn_save_all)

        root_layout.addWidget(top_bar)

        # =====================================================================
        # 4 LIVE KPI CARDS
        # =====================================================================
        kpi_container = QFrame()
        kpi_container.setStyleSheet("background-color: #0F172A; border: 1px solid #1E293B; border-radius: 8px; padding: 6px;")
        kpi_layout = QGridLayout(kpi_container)
        kpi_layout.setContentsMargins(12, 10, 12, 10)
        kpi_layout.setHorizontalSpacing(18)
        kpi_layout.setVerticalSpacing(4)

        # KPI 1: Current Baseline Setup Time
        kpi_layout.addWidget(QLabel("<b>CURRENT BASELINE SETUP TIME</b>"), 0, 0)
        self.val_kpi_baseline = QLabel("00m 00s (0.0s)")
        self.val_kpi_baseline.setStyleSheet("color: #F8FAFC; font-size: 19px; font-weight: 800; font-family: monospace;")
        kpi_layout.addWidget(self.val_kpi_baseline, 1, 0)
        self.sub_kpi_baseline = QLabel("Averaged across 0 baseline trial(s)")
        self.sub_kpi_baseline.setStyleSheet("color: #94A3B8; font-size: 11px;")
        kpi_layout.addWidget(self.sub_kpi_baseline, 2, 0)

        # KPI 2: 50% SMED Target Time
        kpi_layout.addWidget(QLabel("<b>50% REDUCTION SMED TARGET</b>"), 0, 1)
        self.val_kpi_target = QLabel("<= 00m 00s (0.0s)")
        self.val_kpi_target.setStyleSheet("color: #38BDF8; font-size: 19px; font-weight: 800; font-family: monospace;")
        kpi_layout.addWidget(self.val_kpi_target, 1, 1)
        self.sub_kpi_target = QLabel("Target: >= 50.0% setup reduction")
        self.sub_kpi_target.setStyleSheet("color: #94A3B8; font-size: 11px;")
        kpi_layout.addWidget(self.sub_kpi_target, 2, 1)

        # KPI 3: Total Estimated Savings from Kaizen
        kpi_layout.addWidget(QLabel("<b>TOTAL ESTIMATED SAVINGS (KAIZEN)</b>"), 0, 2)
        self.val_kpi_savings = QLabel("00m 00s (0.0s)")
        self.val_kpi_savings.setStyleSheet("color: #10B981; font-size: 19px; font-weight: 800; font-family: monospace;")
        kpi_layout.addWidget(self.val_kpi_savings, 1, 2)
        self.sub_kpi_savings = QLabel("0.0% setup time reduction estimated")
        self.sub_kpi_savings.setStyleSheet("color: #94A3B8; font-size: 11px;")
        kpi_layout.addWidget(self.sub_kpi_savings, 2, 2)

        # KPI 4: Projected New Internal Setup Time & Status Badge
        kpi_layout.addWidget(QLabel("<b>PROJECTED MACHINE DOWNTIME</b>"), 0, 3)
        self.val_kpi_projected = QLabel("00m 00s (0.0s)")
        self.val_kpi_projected.setStyleSheet("color: #F59E0B; font-size: 19px; font-weight: 800; font-family: monospace;")
        kpi_layout.addWidget(self.val_kpi_projected, 1, 3)
        self.badge_kpi_status = QLabel("STATUS: PENDING BRAINSTORMING")
        self.badge_kpi_status.setStyleSheet(
            "background-color: rgba(148, 163, 184, 0.2); color: #CBD5E1; font-size: 11px; "
            "font-weight: 700; border-radius: 4px; padding: 2px 6px;"
        )
        kpi_layout.addWidget(self.badge_kpi_status, 2, 3)

        root_layout.addWidget(kpi_container)

        # =====================================================================
        # MAIN SPLITTER: Upper (Matplotlib Pareto Chart) vs Lower (Kaizen Table)
        # =====================================================================
        splitter = QSplitter(Qt.Orientation.Vertical)
        root_layout.addWidget(splitter, stretch=1)

        # ---------------------------------------------------------------------
        # UPPER PANE: Embedded Matplotlib Pareto Chart
        # ---------------------------------------------------------------------
        chart_box = QGroupBox("Pareto Analysis: Activity Bottleneck Distribution (80/20 Rule)")
        chart_layout = QVBoxLayout(chart_box)
        chart_layout.setContentsMargins(8, 12, 8, 8)

        # Matplotlib Figure & Canvas
        self.fig = Figure(facecolor="#1E293B", edgecolor="#334155")
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setMinimumHeight(240)
        chart_layout.addWidget(self.canvas)

        splitter.addWidget(chart_box)

        # ---------------------------------------------------------------------
        # LOWER PANE: Interactive Kaizen & ECRS Brainstorming Solution Matrix Table
        # ---------------------------------------------------------------------
        table_box = QGroupBox("Kaizen Action Matrix (Ordered by Top Bottleneck Duration)")
        table_layout = QVBoxLayout(table_box)
        table_layout.setContentsMargins(8, 12, 8, 8)

        self.table_kaizen = QTableWidget()
        self.table_kaizen.setColumnCount(10)
        self.table_kaizen.setHorizontalHeaderLabels([
            "Rank",
            "Activity Name",
            "Current Type",
            "Baseline Avg (s)",
            "Problem / Waste Observed",
            "SMED Action Stage",
            "Solution Implementing",
            "Target Type",
            "Est. Reduction (s)",
            "Projected Time",
        ])

        # Column sizing policies
        header = self.table_kaizen.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents) # Rank
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents) # Name
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents) # Current Type
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents) # Baseline Avg
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)          # Problem
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents) # Action Stage
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)          # Solution
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents) # Target Type
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.ResizeToContents) # Est Reduction
        header.setSectionResizeMode(9, QHeaderView.ResizeMode.ResizeToContents) # Projected Time

        self.table_kaizen.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_kaizen.setAlternatingRowColors(True)
        table_layout.addWidget(self.table_kaizen)

        splitter.addWidget(table_box)

        # Sizing ratio 38% chart : 62% table
        splitter.setSizes([320, 520])

    # =========================================================================
    # PROJECT SELECTION & DATA LOADING
    # =========================================================================

    def set_project(self, project_id: int):
        """Set active project from external signal and load its Pareto data."""
        self.active_project_id = project_id
        project = self.db.get_project(project_id)
        if project:
            self.lbl_project_name.setText(
                f"{project['name']}  ({project.get('machine_name') or 'Machine'})"
            )
        else:
            self.lbl_project_name.setText("Unknown Project")

        self.refresh_data()

    def _on_filter_changed(self):
        """Handle category filter switch."""
        idx = self.combo_filter.currentIndex()
        if idx == 1:
            self.category_filter = "Internal"
        elif idx == 2:
            self.category_filter = "External"
        else:
            self.category_filter = None

        self.refresh_data()

    def refresh_data(self):
        """Query SQLite for aggregated baseline data and refresh chart and table."""
        if not self.active_project_id:
            self._render_empty_chart("No Active Project Selected")
            self.table_kaizen.setRowCount(0)
            self._update_kpi_cards_empty()
            return

        df = self.db.get_pareto_and_kaizen_data(self.active_project_id, self.category_filter)
        self.current_df = df

        if df.empty:
            self._render_empty_chart(
                f"No 'BEFORE' Video Trials Recorded Yet for {self.category_filter or 'All'} Activities.\n"
                "Please record baseline trials in Tab 2 (Video Logger)."
            )
            self.table_kaizen.setRowCount(0)
            self._update_kpi_cards_empty()
            return

        # Render Chart & Populate Table
        self._render_pareto_chart(df)
        self._populate_kaizen_table(df)
        self._recalculate_kpi_cards()

    # =========================================================================
    # EMBEDDED MATPLOTLIB PARETO CHART ENGINE
    # =========================================================================

    def _render_empty_chart(self, message: str):
        self.fig.clear()
        ax = self.fig.add_subplot(111)
        ax.set_facecolor("#0F172A")
        ax.text(
            0.5, 0.5, message,
            color="#94A3B8",
            fontsize=12,
            fontweight="bold",
            ha="center", va="center",
            transform=ax.transAxes
        )
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_color("#334155")
        self.canvas.draw()

    def _render_pareto_chart(self, df: pd.DataFrame):
        """
        Render dual-axis Pareto Chart:
        - Left Axis: Bar chart of average baseline duration (s), color-coded by Internal (Red) vs External (Green).
        - Right Axis: Cumulative percentage curve (%) in Cyan with 80% cutoff line.
        """
        self.fig.clear()
        ax1 = self.fig.add_subplot(111)
        ax1.set_facecolor("#0F172A")

        activities = df["activity_name"].tolist()
        durations = df["avg_duration_sec"].tolist()
        cum_pcts = df["cumulative_pct"].tolist()
        types = df["activity_type"].tolist()

        x_pos = list(range(len(activities)))

        # Color-code bars: Red (#EF4444) for Internal, Green (#10B981) for External
        bar_colors = ["#EF4444" if t == "Internal" else "#10B981" for t in types]

        bars = ax1.bar(
            x_pos, durations,
            color=bar_colors,
            edgecolor="#334155",
            width=0.6,
            zorder=3,
        )

        # Primary Y-Axis (Seconds)
        ax1.set_ylabel("Average Duration (Seconds)", color="#F8FAFC", fontsize=11, fontweight="bold")
        ax1.tick_params(axis="y", colors="#F8FAFC", labelsize=10)
        ax1.tick_params(axis="x", colors="#F8FAFC", labelsize=9)
        ax1.grid(True, linestyle="--", alpha=0.25, color="#475569", zorder=0)

        # Bar value annotations
        max_dur = max(durations) if durations else 1.0
        for bar in bars:
            h = bar.get_height()
            mins = int(h // 60)
            secs = int(h % 60)
            label = f"{mins}m{secs}s" if mins > 0 else f"{secs}s"
            ax1.annotate(
                label,
                xy=(bar.get_x() + bar.get_width() / 2, h),
                xytext=(0, 4),
                textcoords="offset points",
                ha="center", va="bottom",
                color="#F8FAFC", fontsize=9, fontweight="bold",
            )

        # Truncate long activity names for clean X-axis readability
        short_labels = [
            (act[:22] + "...") if len(act) > 25 else act
            for act in activities
        ]
        ax1.set_xticks(x_pos)
        ax1.set_xticklabels(short_labels, rotation=28, ha="right", fontsize=9, color="#E2E8F0")

        # Secondary Y-Axis (Cumulative %)
        ax2 = ax1.twinx()
        ax2.set_ylabel("Cumulative Percentage (%)", color="#38BDF8", fontsize=11, fontweight="bold")
        ax2.plot(
            x_pos, cum_pcts,
            color="#38BDF8",
            marker="o",
            markersize=6,
            linewidth=2.5,
            zorder=4,
            label="Cumulative %",
        )
        ax2.set_ylim(0, 105)
        ax2.tick_params(axis="y", colors="#38BDF8", labelsize=10)
        ax2.yaxis.set_major_formatter(ticker.PercentFormatter())

        # 80% Pareto Cutoff Line (Vital Few Threshold)
        ax2.axhline(
            80.0,
            color="#F59E0B",
            linestyle="--",
            linewidth=2.0,
            zorder=2,
            label="80% Cutoff (Vital Few)",
        )
        ax2.text(
            len(activities) - 0.5, 82.0,
            "80% Pareto Threshold",
            color="#F59E0B",
            fontsize=9,
            fontweight="bold",
            ha="right",
        )

        # Custom Legend
        from matplotlib.patches import Patch
        from matplotlib.lines import Line2D
        legend_elements = [
            Patch(facecolor="#EF4444", edgecolor="#334155", label="Internal Setup (Machine OFF)"),
            Patch(facecolor="#10B981", edgecolor="#334155", label="External Setup (Machine ON)"),
            Line2D([0], [0], color="#38BDF8", lw=2.5, marker="o", label="Cumulative %"),
            Line2D([0], [0], color="#F59E0B", lw=2, linestyle="--", label="80% Cutoff (Vital Few)"),
        ]
        leg = ax1.legend(
            handles=legend_elements,
            loc="upper right",
            facecolor="#1E293B",
            edgecolor="#334155",
            fontsize=9,
        )
        for text in leg.get_texts():
            text.set_color("#F8FAFC")

        # Spine styling
        for spine in ax1.spines.values():
            spine.set_color("#334155")
        for spine in ax2.spines.values():
            spine.set_color("#334155")

        self.fig.tight_layout()
        self.canvas.draw()

    def _export_pareto_chart(self):
        """Export high-resolution Pareto Chart as PNG or PDF."""
        if not self.active_project_id or self.current_df is None or self.current_df.empty:
            QMessageBox.warning(self, "No Chart", "No active Pareto chart data to export.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Pareto Chart",
            "SMED_Pareto_Analysis.png",
            "PNG Image (*.png);;PDF Document (*.pdf);;All Files (*.*)",
        )
        if file_path:
            try:
                self.fig.savefig(
                    file_path,
                    dpi=300,
                    bbox_inches="tight",
                    facecolor=self.fig.get_facecolor(),
                )
                QMessageBox.information(
                    self, "Chart Exported", f"Pareto chart exported successfully to:\n{file_path}"
                )
            except Exception as e:
                QMessageBox.critical(self, "Export Failed", f"Failed to export chart:\n{str(e)}")

    # =========================================================================
    # KAIZEN ACTION MATRIX TABLE & DYNAMIC AUTO-CALCULATION
    # =========================================================================

    def _populate_kaizen_table(self, df: pd.DataFrame):
        """Populate Kaizen brainstorming table with editable inputs and widgets."""
        self.table_kaizen.setRowCount(0)
        self.row_widgets.clear()

        # Map canonical action types to UI dropdown strings
        canonical_to_ui = {
            "Convert to External": "Stage 2: Convert Internal -> External",
            "Simplify/Streamline": "Stage 3: Streamline / Quick Fasteners (One-Turn / Clamps)",
            "Eliminate": "Eliminate Waste (ECRS)",
            "Parallelize": "Parallelize Operation",
        }

        for row_idx, row in df.iterrows():
            self.table_kaizen.insertRow(row_idx)
            act_id = row["standard_activity_id"]
            act_name = row["activity_name"]
            curr_type = row["activity_type"]
            base_dur = float(row["avg_duration_sec"])
            pct_share = float(row["pct_of_total"])
            cum_pct = float(row["cumulative_pct"])

            # 1. Rank & Class A Badge
            rank_label = QLabel()
            is_class_a = (cum_pct <= 80.0) or (row_idx == 0)
            if is_class_a:
                rank_label.setText(f" #{row_idx + 1}  [Vital Few] ")
                rank_label.setStyleSheet("background-color: rgba(245, 158, 11, 0.2); color: #F59E0B; font-weight: 800; border-radius: 4px; padding: 2px 4px;")
            else:
                rank_label.setText(f" #{row_idx + 1} ")
                rank_label.setStyleSheet("color: #94A3B8; font-weight: 600; padding: 2px 4px;")
            rank_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_kaizen.setCellWidget(row_idx, 0, rank_label)

            # 2. Activity Name
            name_item = QTableWidgetItem(act_name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            name_item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            self.table_kaizen.setItem(row_idx, 1, name_item)

            # 3. Current Category Badge
            type_label = QLabel(f" {curr_type} ")
            type_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            if curr_type == "Internal":
                type_label.setStyleSheet(get_internal_badge_style())
            else:
                type_label.setStyleSheet(get_external_badge_style())
            self.table_kaizen.setCellWidget(row_idx, 2, type_label)

            # 4. Baseline Avg Time & % Share
            time_item = QTableWidgetItem(f"{base_dur:.1f}s ({pct_share:.1f}%)")
            time_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            time_item.setFlags(time_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            time_item.setForeground(QColor("#38BDF8"))
            time_item.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
            self.table_kaizen.setItem(row_idx, 3, time_item)

            # 5. Problem / Waste Observed (Editable QLineEdit)
            edit_problem = QLineEdit()
            edit_problem.setText(str(row.get("problem_observed") or ""))
            edit_problem.setPlaceholderText("Observed waste, searching, tool friction...")
            self.table_kaizen.setCellWidget(row_idx, 4, edit_problem)

            # 6. SMED Action Stage (Dropdown)
            combo_stage = QComboBox()
            combo_stage.addItems(self.SMED_ACTION_STAGES)
            saved_action = str(row.get("action_type") or "")
            mapped_ui_stage = canonical_to_ui.get(saved_action, saved_action)
            if mapped_ui_stage in self.SMED_ACTION_STAGES:
                combo_stage.setCurrentText(mapped_ui_stage)
            else:
                # Default selection based on current category
                if curr_type == "Internal":
                    combo_stage.setCurrentText("Stage 2: Convert Internal -> External")
                else:
                    combo_stage.setCurrentText("Eliminate Waste (ECRS)")
            self.table_kaizen.setCellWidget(row_idx, 5, combo_stage)

            # 7. Solution Implementing (Editable QLineEdit)
            edit_solution = QLineEdit()
            edit_solution.setText(str(row.get("solution_implemented") or ""))
            edit_solution.setPlaceholderText("Kaizen countermeasure, quick fasteners...")
            self.table_kaizen.setCellWidget(row_idx, 6, edit_solution)

            # 8. Target Category (Dropdown)
            combo_target = QComboBox()
            combo_target.addItems(["Internal", "External"])
            saved_target = str(row.get("target_type") or "")
            if saved_target in ("Internal", "External"):
                combo_target.setCurrentText(saved_target)
            else:
                combo_target.setCurrentText(curr_type)
            self.table_kaizen.setCellWidget(row_idx, 7, combo_target)

            # 9. Estimated Time Reduction (s) SpinBox
            spin_reduction = QDoubleSpinBox()
            spin_reduction.setRange(0.0, max(base_dur, 9999.0))
            spin_reduction.setSingleStep(5.0)
            spin_reduction.setDecimals(1)
            spin_reduction.setSuffix(" s")
            saved_red = float(row.get("estimated_reduction_sec") or 0.0)
            spin_reduction.setValue(min(base_dur, saved_red))
            self.table_kaizen.setCellWidget(row_idx, 8, spin_reduction)

            # 10. Projected Time (s) (Read-only Item)
            proj_time = max(0.0, base_dur - spin_reduction.value())
            proj_item = QTableWidgetItem(f"{proj_time:.1f}s")
            proj_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            proj_item.setFlags(proj_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            proj_item.setForeground(QColor("#10B981" if proj_time < base_dur else "#94A3B8"))
            proj_item.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
            self.table_kaizen.setItem(row_idx, 9, proj_item)

            # Track widgets for dynamic recalculation
            row_data = {
                "activity_id": act_id,
                "activity_name": act_name,
                "current_type": curr_type,
                "baseline_dur": base_dur,
                "edit_problem": edit_problem,
                "combo_stage": combo_stage,
                "edit_solution": edit_solution,
                "combo_target": combo_target,
                "spin_reduction": spin_reduction,
                "proj_item": proj_item,
            }
            self.row_widgets[row_idx] = row_data

            # Connect dynamic listeners for real-time calculation
            spin_reduction.valueChanged.connect(
                lambda val, r=row_idx: self._on_row_value_changed(r)
            )
            combo_target.currentIndexChanged.connect(
                lambda idx, r=row_idx: self._on_row_value_changed(r)
            )

    def _on_row_value_changed(self, row_idx: int):
        """Update projected duration cell and recalculate KPI cards in real time."""
        if row_idx not in self.row_widgets:
            return

        r = self.row_widgets[row_idx]
        base_dur = r["baseline_dur"]
        red = r["spin_reduction"].value()
        proj_time = max(0.0, base_dur - red)

        proj_item = r["proj_item"]
        proj_item.setText(f"{proj_time:.1f}s")
        if proj_time < base_dur:
            proj_item.setForeground(QColor("#10B981"))
        else:
            proj_item.setForeground(QColor("#94A3B8"))

        self._recalculate_kpi_cards()

    # =========================================================================
    # KPI CARDS DYNAMIC RECALCULATION
    # =========================================================================

    def _update_kpi_cards_empty(self):
        self.val_kpi_baseline.setText("00m 00s (0.0s)")
        self.sub_kpi_baseline.setText("No baseline trials recorded")
        self.val_kpi_target.setText("<= 00m 00s (0.0s)")
        self.sub_kpi_target.setText("Target: >= 50.0% reduction")
        self.val_kpi_savings.setText("00m 00s (0.0s)")
        self.sub_kpi_savings.setText("0.0% reduction")
        self.val_kpi_projected.setText("00m 00s (0.0s)")
        self.badge_kpi_status.setText("STATUS: NO DATA")
        self.badge_kpi_status.setStyleSheet("background-color: rgba(148, 163, 184, 0.2); color: #CBD5E1; font-size: 11px; font-weight: 700; border-radius: 4px; padding: 2px 6px;")

    def _recalculate_kpi_cards(self):
        """
        Dynamically calculate and update the 4 live KPI cards:
        - Baseline internal & external totals
        - 50% target threshold
        - Sum of estimated savings & internal->external converted time
        - Projected machine downtime and achievement status badge
        """
        if not self.row_widgets:
            return

        project = self.db.get_project(self.active_project_id) if self.active_project_id else None
        target_pct = float(project["target_reduction_pct"]) if project else 50.0

        total_baseline = 0.0
        baseline_internal = 0.0
        baseline_external = 0.0

        total_savings = 0.0
        projected_internal = 0.0

        for r in self.row_widgets.values():
            base_dur = r["baseline_dur"]
            curr_type = r["current_type"]
            target_type = r["combo_target"].currentText()
            red_sec = r["spin_reduction"].value()

            total_baseline += base_dur
            if curr_type == "Internal":
                baseline_internal += base_dur
            else:
                baseline_external += base_dur

            # Savings & Machine Downtime Logic:
            if curr_type == "Internal":
                if target_type == "External":
                    # Activity converted to External! Entire baseline duration removed from downtime!
                    total_savings += base_dur
                else:
                    # Stays internal: duration reduced by estimated reduction
                    total_savings += red_sec
                    projected_internal += max(0.0, base_dur - red_sec)
            else:
                # Was external already
                total_savings += red_sec

        # 1. KPI 1: Baseline
        self.val_kpi_baseline.setText(format_seconds_min(total_baseline))
        self.sub_kpi_baseline.setText(
            f"Internal: {format_seconds_min(baseline_internal)} | External: {format_seconds_min(baseline_external)}"
        )

        # 2. KPI 2: Target
        target_time = round(total_baseline * (1.0 - (target_pct / 100.0)), 2)
        self.val_kpi_target.setText(f"<= {format_seconds_min(target_time)}")
        self.sub_kpi_target.setText(f"Target: >= {target_pct:.1f}% Reduction (SMED Goal)")

        # 3. KPI 3: Savings
        savings_pct = (total_savings / total_baseline * 100.0) if total_baseline > 0 else 0.0
        self.val_kpi_savings.setText(format_seconds_min(total_savings))
        self.sub_kpi_savings.setText(f"{savings_pct:.1f}% of Baseline Eliminated / Converted")

        # 4. KPI 4: Projected Internal Downtime & Status
        self.val_kpi_projected.setText(format_seconds_min(projected_internal))

        gap_sec = projected_internal - target_time
        if projected_internal < 600.0 and projected_internal <= target_time:
            # Single-digit minute SMED achieved!
            self.badge_kpi_status.setText(f"[SMED ACHIEVED] ({format_seconds_min(projected_internal)})")
            self.badge_kpi_status.setStyleSheet("background-color: rgba(14, 165, 233, 0.25); color: #38BDF8; font-size: 11px; font-weight: 800; border: 1px solid #0EA5E9; border-radius: 4px; padding: 2px 8px;")
        elif projected_internal <= target_time:
            # 50% target met
            self.badge_kpi_status.setText(f"[50% TARGET HIT] ({savings_pct:.1f}% REDUCTION)")
            self.badge_kpi_status.setStyleSheet("background-color: rgba(16, 185, 129, 0.25); color: #34D399; font-size: 11px; font-weight: 800; border: 1px solid #10B981; border-radius: 4px; padding: 2px 8px;")
        else:
            # Still exceeds 50% target
            self.badge_kpi_status.setText(f"[GAP] SHAVE {gap_sec:.1f}s MORE TO HIT TARGET")
            self.badge_kpi_status.setStyleSheet("background-color: rgba(245, 158, 11, 0.25); color: #FBBF24; font-size: 11px; font-weight: 800; border: 1px solid #F59E0B; border-radius: 4px; padding: 2px 8px;")

    # =========================================================================
    # BATCH SAVE KAIZEN SOLUTIONS
    # =========================================================================

    def _save_all_kaizen_solutions(self):
        """Save all rows from the Kaizen matrix into SQLite database."""
        if not self.active_project_id:
            return

        saved_count = 0
        try:
            for r in self.row_widgets.values():
                act_id = r["activity_id"]
                prob = r["edit_problem"].text().strip()
                stage = r["combo_stage"].currentText()
                sol = r["edit_solution"].text().strip()
                tgt_type = r["combo_target"].currentText()
                est_red = float(r["spin_reduction"].value())

                # Upsert into kaizen_solutions
                self.db.upsert_kaizen_solution(
                    project_id=self.active_project_id,
                    standard_activity_id=act_id,
                    problem_observed=prob,
                    solution_implemented=sol,
                    action_type=stage,
                    estimated_reduction_sec=est_red,
                    target_type=tgt_type,
                )
                saved_count += 1

            self.kaizen_updated.emit()
            QMessageBox.information(
                self,
                "Kaizen Matrix Saved",
                f"Successfully saved {saved_count} Kaizen countermeasure(s) to the project database!"
            )
        except Exception as e:
            QMessageBox.critical(self, "Save Failed", f"Failed to save Kaizen solutions:\n{str(e)}")
