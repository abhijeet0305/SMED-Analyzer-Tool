"""
SMED Studio - Pareto Analysis & Kaizen Brainstorming Matrix Tab
Aggregates multi-video baseline observations, renders embedded Matplotlib 80/20 Pareto chart,
and provides an interactive Kaizen action board with dynamic KPI recalculations.
"""

from typing import Any, Dict, List, Optional
import textwrap
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
    QHeaderView, QGroupBox, QFrame, QDoubleSpinBox,
    QPlainTextEdit, QFileDialog, QMessageBox, QAbstractItemView,
    QScrollArea, QSizePolicy
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
        page_layout = QVBoxLayout(self)
        page_layout.setContentsMargins(0, 0, 0, 0)

        scroll_area = QScrollArea(self)
        scroll_area.setObjectName("paretoPageScrollArea")
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        page_layout.addWidget(scroll_area)
        page_content = QWidget()
        page_content.setObjectName("paretoPageContent")
        scroll_area.setWidget(page_content)

        root_layout = QVBoxLayout(page_content)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(10)

        # =====================================================================
        # TOP TOOLBAR: Project Indicator, Filter, Refresh & Export Buttons
        # =====================================================================
        top_bar = QFrame()
        top_bar.setObjectName("paretoToolbar")
        top_layout = QVBoxLayout(top_bar)
        top_layout.setContentsMargins(8, 6, 8, 6)
        top_layout.setSpacing(8)
        details_layout = QHBoxLayout()
        details_layout.setSpacing(10)

        project_label = QLabel("<b>Active Project:</b>")
        project_label.setObjectName("paretoToolbarLabel")
        details_layout.addWidget(project_label)
        self.lbl_project_name = QLabel("No Project Selected")
        self.lbl_project_name.setObjectName("paretoProjectName")
        self.lbl_project_name.setWordWrap(True)
        self.lbl_project_name.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        details_layout.addWidget(self.lbl_project_name, 1)

        # Category Filter Dropdown
        filter_label = QLabel("<b>View Filter:</b>")
        filter_label.setObjectName("paretoToolbarLabel")
        details_layout.addWidget(filter_label)
        self.combo_filter = QComboBox()
        self.combo_filter.addItems([
            "All Activities (Internal + External)",
            "Internal Activities Only (Machine Stopped)",
            "External Activities Only (Machine Running)",
        ])
        self.combo_filter.currentIndexChanged.connect(self._on_filter_changed)
        self.combo_filter.setMinimumWidth(220)
        details_layout.addWidget(self.combo_filter, 1)
        top_layout.addLayout(details_layout)

        # Action Buttons
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(8)
        self.btn_refresh = QPushButton("Refresh Data")
        self.btn_refresh.setToolTip("Refresh activity data from recorded videos.")
        self.btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_refresh.clicked.connect(self.refresh_data)
        actions_layout.addWidget(self.btn_refresh)

        self.btn_export_chart = QPushButton("Export Chart")
        self.btn_export_chart.setToolTip("Export the Pareto chart as a PNG image.")
        self.btn_export_chart.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_export_chart.clicked.connect(self._export_pareto_chart)
        actions_layout.addWidget(self.btn_export_chart)

        self.btn_save_all = QPushButton("Save All Solutions")
        self.btn_save_all.setToolTip("Save all Kaizen solutions in the matrix.")
        self.btn_save_all.setObjectName("successBtn")
        self.btn_save_all.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save_all.clicked.connect(self._save_all_kaizen_solutions)
        actions_layout.addWidget(self.btn_save_all)
        top_layout.addLayout(actions_layout)

        root_layout.addWidget(top_bar)

        # =====================================================================
        # 4 LIVE KPI CARDS
        # =====================================================================
        kpi_container = QFrame()
        kpi_container.setObjectName("paretoKpiContainer")
        kpi_layout = QGridLayout(kpi_container)
        kpi_layout.setContentsMargins(12, 10, 12, 10)
        kpi_layout.setHorizontalSpacing(18)
        kpi_layout.setVerticalSpacing(4)

        # KPI 1: Current Baseline Setup Time
        baseline_title = QLabel("<b>CURRENT BASELINE SETUP TIME</b>")
        baseline_title.setObjectName("paretoKpiTitle")
        baseline_title.setWordWrap(True)
        kpi_layout.addWidget(baseline_title, 0, 0)
        self.val_kpi_baseline = QLabel("00m 00s (0.0s)")
        self.val_kpi_baseline.setObjectName("paretoKpiBaseline")
        self.val_kpi_baseline.setWordWrap(True)
        kpi_layout.addWidget(self.val_kpi_baseline, 1, 0)
        self.sub_kpi_baseline = QLabel("Averaged across 0 baseline trial(s)")
        self.sub_kpi_baseline.setObjectName("paretoKpiSubtext")
        self.sub_kpi_baseline.setWordWrap(True)
        kpi_layout.addWidget(self.sub_kpi_baseline, 2, 0)

        # KPI 2: 50% SMED Target Time
        target_title = QLabel("<b>50% REDUCTION SMED TARGET</b>")
        target_title.setObjectName("paretoKpiTitle")
        target_title.setWordWrap(True)
        kpi_layout.addWidget(target_title, 0, 1)
        self.val_kpi_target = QLabel("<= 00m 00s (0.0s)")
        self.val_kpi_target.setObjectName("paretoKpiTarget")
        self.val_kpi_target.setWordWrap(True)
        kpi_layout.addWidget(self.val_kpi_target, 1, 1)
        self.sub_kpi_target = QLabel("Target: >= 50.0% setup reduction")
        self.sub_kpi_target.setObjectName("paretoKpiSubtext")
        self.sub_kpi_target.setWordWrap(True)
        kpi_layout.addWidget(self.sub_kpi_target, 2, 1)

        # KPI 3: Total Estimated Savings from Kaizen
        savings_title = QLabel("<b>TOTAL ESTIMATED SAVINGS (KAIZEN)</b>")
        savings_title.setObjectName("paretoKpiTitle")
        savings_title.setWordWrap(True)
        kpi_layout.addWidget(savings_title, 0, 2)
        self.val_kpi_savings = QLabel("00m 00s (0.0s)")
        self.val_kpi_savings.setObjectName("paretoKpiSavings")
        self.val_kpi_savings.setWordWrap(True)
        kpi_layout.addWidget(self.val_kpi_savings, 1, 2)
        self.sub_kpi_savings = QLabel("0.0% setup time reduction estimated")
        self.sub_kpi_savings.setObjectName("paretoKpiSubtext")
        self.sub_kpi_savings.setWordWrap(True)
        kpi_layout.addWidget(self.sub_kpi_savings, 2, 2)

        # KPI 4: Projected New Internal Setup Time & Status Badge
        projected_title = QLabel("<b>PROJECTED MACHINE DOWNTIME</b>")
        projected_title.setObjectName("paretoKpiTitle")
        projected_title.setWordWrap(True)
        kpi_layout.addWidget(projected_title, 0, 3)
        self.val_kpi_projected = QLabel("00m 00s (0.0s)")
        self.val_kpi_projected.setObjectName("paretoKpiProjected")
        self.val_kpi_projected.setWordWrap(True)
        kpi_layout.addWidget(self.val_kpi_projected, 1, 3)
        self.badge_kpi_status = QLabel("STATUS: PENDING BRAINSTORMING")
        self.badge_kpi_status.setObjectName("paretoKpiStatus")
        self.badge_kpi_status.setWordWrap(True)
        kpi_layout.addWidget(self.badge_kpi_status, 2, 3)

        root_layout.addWidget(kpi_container)

        # =====================================================================
        # MAIN CONTENT: Pareto Chart followed by the Kaizen Matrix
        # =====================================================================
        # ---------------------------------------------------------------------
        # UPPER PANE: Embedded Matplotlib Pareto Chart
        # ---------------------------------------------------------------------
        chart_box = QGroupBox("Pareto Analysis: Activity Bottleneck Distribution (80/20 Rule)")
        chart_layout = QVBoxLayout(chart_box)
        chart_layout.setContentsMargins(8, 12, 8, 8)

        # Matplotlib Figure & Canvas
        self.fig = Figure(facecolor=COLORS["bg_card"], edgecolor=COLORS["border"])
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setMinimumHeight(390)
        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        chart_layout.addWidget(self.canvas)

        root_layout.addWidget(chart_box)

        # ---------------------------------------------------------------------
        # LOWER PANE: Interactive Kaizen & ECRS Brainstorming Solution Matrix Table
        # ---------------------------------------------------------------------
        table_box = QGroupBox("Kaizen Action Matrix (Ordered by Top Bottleneck Duration)")
        table_layout = QVBoxLayout(table_box)
        table_layout.setContentsMargins(8, 12, 8, 8)

        self.table_kaizen = QTableWidget()
        self.table_kaizen.setObjectName("kaizenMatrix")
        self.table_kaizen.setColumnCount(10)
        self.table_kaizen.setHorizontalHeaderLabels([
            "Priority",
            "Activity Name",
            "Current Type",
            "Baseline Avg (s)",
            "Problem / Waste",
            "SMED Action Stage",
            "Solution / Countermeasure",
            "Target Type",
            "Est. Reduction (s)",
            "Projected Time",
        ])

        # Explicit widths keep editor controls legible; the matrix scrolls horizontally when needed.
        header = self.table_kaizen.horizontalHeader()
        for column, width in enumerate((150, 320, 150, 180, 360, 440, 380, 150, 180, 160)):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.Interactive)
            self.table_kaizen.setColumnWidth(column, width)
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setMinimumHeight(42)

        self.table_kaizen.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_kaizen.setAlternatingRowColors(True)
        self.table_kaizen.setWordWrap(True)
        self.table_kaizen.setTextElideMode(Qt.TextElideMode.ElideNone)
        self.table_kaizen.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.table_kaizen.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.table_kaizen.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.table_kaizen.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.table_kaizen.setMinimumWidth(0)
        self.table_kaizen.setMinimumHeight(360)
        self.table_kaizen.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.table_kaizen.verticalHeader().setDefaultSectionSize(82)
        matrix_scroll_area = QScrollArea()
        matrix_scroll_area.setObjectName("kaizenMatrixScrollArea")
        matrix_scroll_area.setWidgetResizable(False)
        matrix_scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        matrix_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        matrix_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        matrix_scroll_area.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        matrix_scroll_area.setMinimumWidth(0)
        matrix_scroll_area.setFixedHeight(380)
        self.table_kaizen.setFixedWidth(
            header.length() + self.table_kaizen.verticalHeader().width() + 2 * self.table_kaizen.frameWidth()
        )
        matrix_scroll_area.setWidget(self.table_kaizen)
        table_layout.addWidget(matrix_scroll_area)

        root_layout.addWidget(table_box)
        root_layout.addStretch(1)

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
        ax.set_facecolor(COLORS["bg_card"])
        ax.text(
            0.5, 0.5, message,
            color=COLORS["text_secondary"],
            fontsize=12,
            fontweight="bold",
            ha="center", va="center",
            transform=ax.transAxes
        )
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_color(COLORS["border"])
        self.canvas.draw()

    def _render_pareto_chart(self, df: pd.DataFrame):
        """
        Render dual-axis Pareto Chart:
        - Left Axis: Bar chart of average baseline duration (s), color-coded by Internal (Red) vs External (Green).
        - Right Axis: Cumulative percentage curve (%) in Cyan with 80% cutoff line.
        """
        self.fig.clear()
        ax1 = self.fig.add_subplot(111)
        ax1.set_facecolor(COLORS["bg_card"])

        activities = df["activity_name"].tolist()
        durations = df["avg_duration_sec"].tolist()
        cum_pcts = df["cumulative_pct"].tolist()
        types = df["activity_type"].tolist()

        x_pos = list(range(len(activities)))

        bar_colors = [
            COLORS["internal_red"] if activity_type == "Internal" else COLORS["external_emerald"]
            for activity_type in types
        ]

        bars = ax1.bar(
            x_pos, durations,
            color=bar_colors,
            edgecolor=COLORS["bg_card"],
            width=0.6,
            zorder=3,
        )

        # Primary Y-Axis (Seconds)
        ax1.set_ylabel("Average Duration (seconds)", color=COLORS["text_primary"], fontsize=10, fontweight="bold")
        ax1.tick_params(axis="y", colors=COLORS["text_primary"], labelsize=9)
        ax1.tick_params(axis="x", colors=COLORS["text_primary"], labelsize=8)
        ax1.grid(True, linestyle="--", alpha=0.35, color=COLORS["border"], zorder=0)

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
                color=COLORS["text_primary"], fontsize=8, fontweight="bold",
            )

        labels = [textwrap.fill(str(activity), width=18, break_long_words=False) for activity in activities]
        ax1.set_xticks(x_pos)
        ax1.set_xticklabels(labels, rotation=25, ha="right", fontsize=8, color=COLORS["text_primary"])

        # Secondary Y-Axis (Cumulative %)
        ax2 = ax1.twinx()
        ax2.set_ylabel(
            "Cumulative percentage",
            color=COLORS["primary_blue_pressed"],
            fontsize=10,
            fontweight="bold",
        )
        ax2.plot(
            x_pos, cum_pcts,
            color=COLORS["primary_blue"],
            marker="o",
            markersize=6,
            linewidth=2.5,
            zorder=4,
            label="Cumulative %",
        )
        ax2.set_ylim(0, 105)
        ax2.tick_params(axis="y", colors=COLORS["primary_blue_pressed"], labelsize=9)
        ax2.yaxis.set_major_formatter(ticker.PercentFormatter())

        # 80% Pareto Cutoff Line (Vital Few Threshold)
        ax2.axhline(
            80.0,
            color=COLORS["warning_amber"],
            linestyle="--",
            linewidth=2.0,
            zorder=2,
            label="80% Cutoff (Vital Few)",
        )
        ax2.text(
            len(activities) - 0.5, 82.0,
            "80% Pareto Threshold",
            color=COLORS["warning_amber"],
            fontsize=9,
            fontweight="bold",
            ha="right",
        )

        # Custom Legend
        from matplotlib.patches import Patch
        from matplotlib.lines import Line2D
        legend_elements = [
            Patch(facecolor=COLORS["internal_red"], edgecolor=COLORS["border"], label="Internal (machine stopped)"),
            Patch(facecolor=COLORS["external_emerald"], edgecolor=COLORS["border"], label="External (machine running)"),
            Line2D([0], [0], color=COLORS["primary_blue"], lw=2.5, marker="o", label="Cumulative %"),
            Line2D([0], [0], color=COLORS["warning_amber"], lw=2, linestyle="--", label="80% cutoff"),
        ]
        legend = self.fig.legend(
            handles=legend_elements,
            loc="upper center",
            bbox_to_anchor=(0.5, 0.99),
            ncol=2,
            facecolor=COLORS["bg_card"],
            edgecolor=COLORS["border"],
            fontsize=8,
        )
        for text in legend.get_texts():
            text.set_color(COLORS["text_primary"])

        # Spine styling
        for spine in ax1.spines.values():
            spine.set_color(COLORS["border"])
        for spine in ax2.spines.values():
            spine.set_color(COLORS["border"])

        self.fig.subplots_adjust(left=0.08, right=0.91, bottom=0.34, top=0.82)
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
            self.table_kaizen.setRowHeight(row_idx, 104)
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
                rank_label.setObjectName("paretoVitalFewRank")
            else:
                rank_label.setText(f" #{row_idx + 1} ")
                rank_label.setObjectName("paretoRank")
            rank_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_kaizen.setCellWidget(row_idx, 0, rank_label)

            # 2. Activity Name
            name_item = QTableWidgetItem(act_name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            name_item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            name_item.setToolTip(act_name)
            self.table_kaizen.setItem(row_idx, 1, name_item)

            # 3. Current Category Badge
            type_label = QLabel(curr_type)
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
            time_item.setForeground(QColor(COLORS["primary_blue_pressed"]))
            time_item.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
            self.table_kaizen.setItem(row_idx, 3, time_item)

            # 5. Problem / Waste Observed (Editable multiline field)
            edit_problem = QPlainTextEdit()
            edit_problem.setObjectName("kaizenTextEditor")
            edit_problem.setPlainText(str(row.get("problem_observed") or ""))
            edit_problem.setPlaceholderText("Observed waste, searching, tool friction...")
            edit_problem.setToolTip("Describe the observed problem or waste.")
            self.table_kaizen.setCellWidget(row_idx, 4, edit_problem)

            # 6. SMED Action Stage (Dropdown)
            combo_stage = QComboBox()
            combo_stage.setObjectName("kaizenStageSelector")
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
            combo_stage.setToolTip(combo_stage.currentText())
            combo_stage.currentTextChanged.connect(combo_stage.setToolTip)
            self.table_kaizen.setCellWidget(row_idx, 5, combo_stage)

            # 7. Solution Implementing (Editable multiline field)
            edit_solution = QPlainTextEdit()
            edit_solution.setObjectName("kaizenTextEditor")
            edit_solution.setPlainText(str(row.get("solution_implemented") or ""))
            edit_solution.setPlaceholderText("Kaizen countermeasure, quick fasteners...")
            edit_solution.setToolTip("Describe the proposed or implemented countermeasure.")
            self.table_kaizen.setCellWidget(row_idx, 6, edit_solution)

            # 8. Target Category (Dropdown)
            combo_target = QComboBox()
            combo_target.setObjectName("kaizenTargetSelector")
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
            proj_item.setForeground(QColor(
                COLORS["external_emerald"] if proj_time < base_dur else COLORS["text_secondary"]
            ))
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
            proj_item.setForeground(QColor(COLORS["external_emerald"]))
        else:
            proj_item.setForeground(QColor(COLORS["text_secondary"]))

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
        self.badge_kpi_status.setProperty("status", "pending")
        self._refresh_status_badge_style()

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
            self.badge_kpi_status.setProperty("status", "achieved")
        elif projected_internal <= target_time:
            # 50% target met
            self.badge_kpi_status.setText(f"[50% TARGET HIT] ({savings_pct:.1f}% REDUCTION)")
            self.badge_kpi_status.setProperty("status", "success")
        else:
            # Still exceeds 50% target
            self.badge_kpi_status.setText(f"[GAP] SHAVE {gap_sec:.1f}s MORE TO HIT TARGET")
            self.badge_kpi_status.setProperty("status", "warning")
        self._refresh_status_badge_style()

    def _refresh_status_badge_style(self):
        self.badge_kpi_status.style().unpolish(self.badge_kpi_status)
        self.badge_kpi_status.style().polish(self.badge_kpi_status)

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
                prob = r["edit_problem"].toPlainText().strip()
                stage = r["combo_stage"].currentText()
                sol = r["edit_solution"].toPlainText().strip()
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
