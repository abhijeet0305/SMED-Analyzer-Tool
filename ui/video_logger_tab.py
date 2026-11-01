"""
SMED Studio - Multi-Video Dual-Stopwatch Logger Tab
High-precision video observation and micro-activity timing engine.
Supports offline multi-format video playback (.mp4, .avi, .mkv, .mov) via OpenCV
and continuous zero-gap dual-stopwatch timing with standardized activity dictionary.
"""

import os
import time
import cv2
from typing import Any, Dict, List, Optional
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QTime
from PyQt6.QtGui import QImage, QPixmap, QKeySequence, QShortcut, QColor
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QGridLayout, QLabel,
    QLineEdit, QTextEdit, QComboBox, QCompleter, QRadioButton, QButtonGroup,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QGroupBox, QSlider, QFileDialog, QMessageBox, QFrame,
    QSplitter, QCheckBox, QAbstractItemView
)

from database.db_manager import DatabaseManager, get_db
from ui.styles import (
    COLORS,
    get_internal_badge_style,
    get_external_badge_style,
    get_digital_readout_style
)


def format_seconds(seconds: float) -> str:
    """Format seconds into MM:SS.cc (minutes:seconds.hundredths)."""
    if seconds < 0:
        seconds = 0.0
    mins = int(seconds // 60)
    rem_sec = seconds % 60
    return f"{mins:02d}:{rem_sec:05.2f}"


class VideoCanvas(QLabel):
    """Aspect-ratio preserving video canvas."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(
            "background-color: #080D15; color: #CBD5E1; "
            "border: 1px solid #1E293B; border-radius: 8px;"
        )
        self.setMinimumSize(420, 280)
        self._current_pixmap: Optional[QPixmap] = None

    def set_frame(self, pixmap: QPixmap):
        self._current_pixmap = pixmap
        self.setPixmap(self._current_pixmap.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        ))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._current_pixmap:
            self.setPixmap(self._current_pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            ))


class VideoLoggerTab(QWidget):
    """
    Multi-Video Observation & Dual-Stopwatch SMED Logger Tab.
    Integrates OpenCV video player with Master SMED Stopwatch & Activity Lap Stopwatch.
    """
    data_changed = pyqtSignal()

    def __init__(self, db: Optional[DatabaseManager] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.db = db or get_db()
        self.active_project_id: Optional[int] = None
        self.active_trial_id: Optional[int] = None
        self.active_phase = "BEFORE"

        # OpenCV Video Playback state
        self.cap: Optional[cv2.VideoCapture] = None
        self.video_fps: float = 30.0
        self.total_frames: int = 0
        self.video_duration_sec: float = 0.0
        self.playback_speed: float = 1.0
        self.is_playing: bool = False
        self.video_timer = QTimer(self)
        self.video_timer.timeout.connect(self._on_video_tick)

        # Dual Stopwatch state (Live manual timer fallback when no video)
        self.live_timer = QTimer(self)
        self.live_timer.timeout.connect(self._on_live_tick)
        self.master_running: bool = False
        self.master_accumulated_sec: float = 0.0
        self._last_live_tick_time: Optional[float] = None

        # Activity Lap Timing state
        self.lap_running: bool = False
        self.lap_start_time_sec: float = 0.0

        # Standard Activities Cache for auto-complete & lookup
        self.standard_activities_map: Dict[str, Dict[str, Any]] = {}

        self._init_ui()
        self._setup_shortcuts()

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(10)

        # =====================================================================
        # TOP TOOLBAR: Project Indicator, Phase Toggle, Multi-Video Import
        # =====================================================================
        top_bar = QFrame()
        top_bar.setObjectName("videoToolbar")
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(8, 4, 8, 4)
        top_layout.setSpacing(12)

        # Project Name Badge
        active_project_label = QLabel("<b>Active Project:</b>")
        active_project_label.setObjectName("videoToolbarLabel")
        top_layout.addWidget(active_project_label)
        self.lbl_active_project = QLabel("No Project Selected")
        self.lbl_active_project.setObjectName("videoActiveProject")
        top_layout.addWidget(self.lbl_active_project)

        top_layout.addSpacing(16)

        # Phase Selector
        phase_label = QLabel("<b>Study Phase:</b>")
        phase_label.setObjectName("videoToolbarLabel")
        top_layout.addWidget(phase_label)
        self.combo_phase = QComboBox()
        self.combo_phase.addItems(["BEFORE (Baseline Observation)", "AFTER (Kaizen Verification)"])
        self.combo_phase.currentIndexChanged.connect(self._on_phase_changed)
        top_layout.addWidget(self.combo_phase)

        top_layout.addSpacing(12)

        # Import Multiple Videos Button
        self.btn_import_videos = QPushButton(" Import Video Trials (Batch)...")
        self.btn_import_videos.setObjectName("primaryBtn")
        self.btn_import_videos.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_import_videos.clicked.connect(self._on_import_videos)
        top_layout.addWidget(self.btn_import_videos)

        # Demo SMED Videos Generator Button
        self.btn_demo_videos = QPushButton("🎬 Demo SMED Videos")
        self.btn_demo_videos.setObjectName("accentBtn")
        self.btn_demo_videos.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_demo_videos.setToolTip(
            "Generate accelerated simulation animations for exploring the workflow; "
            "these are not real shop-floor recordings."
        )
        self.btn_demo_videos.clicked.connect(self._on_generate_demo_videos)
        top_layout.addWidget(self.btn_demo_videos)

        # Trial Selector Dropdown
        trial_label = QLabel("<b>Active Trial:</b>")
        trial_label.setObjectName("videoToolbarLabel")
        top_layout.addWidget(trial_label)
        self.combo_trials = QComboBox()
        self.combo_trials.setMinimumWidth(220)
        self.combo_trials.currentIndexChanged.connect(self._on_trial_selected)
        top_layout.addWidget(self.combo_trials)

        # 6th Consecutive OK Part Checkbox
        self.chk_sixth_part = QCheckBox("6th Consecutive OK Part Verified")
        self.chk_sixth_part.setToolTip(
            "SMED Changeover cycle completes when the 6th consecutive part meets quality approval."
        )
        self.chk_sixth_part.stateChanged.connect(self._on_sixth_part_toggled)
        top_layout.addWidget(self.chk_sixth_part)

        top_layout.addStretch()

        # Delete Trial button
        self.btn_delete_trial = QPushButton("Delete Trial")
        self.btn_delete_trial.setObjectName("dangerBtn")
        self.btn_delete_trial.clicked.connect(self._on_delete_active_trial)
        top_layout.addWidget(self.btn_delete_trial)

        root_layout.addWidget(top_bar)

        # =====================================================================
        # MAIN SPLITTER: Left (Video Player) vs Right (Dual Stopwatches & Logger)
        # =====================================================================
        splitter = QSplitter(Qt.Orientation.Horizontal)
        root_layout.addWidget(splitter)

        # ---------------------------------------------------------------------
        # LEFT PANE: OpenCV Video Canvas & Controls
        # ---------------------------------------------------------------------
        left_pane = QWidget()
        left_layout = QVBoxLayout(left_pane)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        self.lbl_video_guidance = QLabel(
            "Laps follow video playback; without a video, starting a lap starts the manual clock. Demo videos are simulated."
        )
        self.lbl_video_guidance.setObjectName("videoGuidance")
        self.lbl_video_guidance.setWordWrap(True)
        left_layout.addWidget(self.lbl_video_guidance)

        # Video Canvas
        self.video_canvas = VideoCanvas()
        self._show_canvas_placeholder(
            "No video loaded\nImport shop-floor footage to review and time activities.\n"
            "Demo videos are accelerated simulations, not real footage."
        )
        left_layout.addWidget(self.video_canvas, stretch=1)

        # Timeline Seek Slider & Timestamp readout
        timeline_layout = QHBoxLayout()
        timeline_layout.setSpacing(10)

        self.lbl_time_display = QLabel("00:00.00 / 00:00.00")
        self.lbl_time_display.setObjectName("videoTimeline")
        timeline_layout.addWidget(self.lbl_time_display)

        self.slider_seek = QSlider(Qt.Orientation.Horizontal)
        self.slider_seek.setRange(0, 1000)
        self.slider_seek.setValue(0)
        self.slider_seek.sliderMoved.connect(self._on_seek_slider_moved)
        timeline_layout.addWidget(self.slider_seek)

        left_layout.addLayout(timeline_layout)

        # Video Playback Controls Bar
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(8)

        self.btn_step_back = QPushButton("◀◀ -1s")
        self.btn_step_back.clicked.connect(lambda: self._seek_relative(-1.0))
        controls_layout.addWidget(self.btn_step_back)

        self.btn_play_pause = QPushButton("▶ Play (Space)")
        self.btn_play_pause.setObjectName("primaryBtn")
        self.btn_play_pause.clicked.connect(self.toggle_play_pause)
        controls_layout.addWidget(self.btn_play_pause)

        self.btn_step_forward = QPushButton("+1s ▶▶")
        self.btn_step_forward.clicked.connect(lambda: self._seek_relative(1.0))
        controls_layout.addWidget(self.btn_step_forward)

        controls_layout.addSpacing(16)

        controls_layout.addWidget(QLabel("Speed:"))
        self.combo_speed = QComboBox()
        self.combo_speed.addItems(["0.5x", "1.0x", "1.5x", "2.0x"])
        self.combo_speed.setCurrentText("1.0x")
        self.combo_speed.currentIndexChanged.connect(self._on_speed_changed)
        controls_layout.addWidget(self.combo_speed)

        controls_layout.addStretch()

        self.lbl_video_info = QLabel("No Video")
        self.lbl_video_info.setObjectName("videoInfo")
        controls_layout.addWidget(self.lbl_video_info)

        left_layout.addLayout(controls_layout)
        splitter.addWidget(left_pane)

        # ---------------------------------------------------------------------
        # RIGHT PANE: Dual-Stopwatch Engine & Rapid Activity Bifurcation
        # ---------------------------------------------------------------------
        right_pane = QWidget()
        right_layout = QVBoxLayout(right_pane)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)

        # Top Group: Dual Stopwatches
        stopwatch_box = QGroupBox("Dual-Stopwatch Observation Engine")
        stopwatch_layout = QGridLayout(stopwatch_box)
        stopwatch_layout.setHorizontalSpacing(16)
        stopwatch_layout.setVerticalSpacing(8)

        # Stopwatch 1: Master SMED Stopwatch
        master_caption = QLabel("<b>MASTER SMED STOPWATCH</b><br><small>Overall changeover elapsed time</small>")
        master_caption.setObjectName("stopwatchCaption")
        stopwatch_layout.addWidget(master_caption, 0, 0)
        self.lbl_master_time = QLabel("00:00.00")
        self.lbl_master_time.setToolTip(
            "Overall trial time. Start Master to run it manually, or sync it to the current video position."
        )
        self.lbl_master_time.setStyleSheet(get_digital_readout_style(font_size_pt=20, text_color="#38BDF8"))
        self.lbl_master_time.setAlignment(Qt.AlignmentFlag.AlignCenter)
        stopwatch_layout.addWidget(self.lbl_master_time, 1, 0)

        master_btn_layout = QHBoxLayout()
        self.btn_master_toggle = QPushButton("Start Master")
        self.btn_master_toggle.setToolTip(
            "Start or pause the overall manual elapsed-time stopwatch. "
            "Starting an activity lap auto-starts it when no video is loaded."
        )
        self.btn_master_toggle.clicked.connect(self._toggle_master_timer)
        master_btn_layout.addWidget(self.btn_master_toggle)

        self.btn_master_sync = QPushButton("Sync to Video")
        self.btn_master_sync.setEnabled(False)
        self.btn_master_sync.setToolTip("Set the master timer to the current video position.")
        self.btn_master_sync.clicked.connect(self._sync_master_to_video)
        master_btn_layout.addWidget(self.btn_master_sync)

        self.btn_master_save = QPushButton("Save to Trial")
        self.btn_master_save.setObjectName("successBtn")
        self.btn_master_save.setToolTip("Record this duration as the official SMED changeover duration for this trial.")
        self.btn_master_save.clicked.connect(self._save_master_duration_to_trial)
        master_btn_layout.addWidget(self.btn_master_save)

        stopwatch_layout.addLayout(master_btn_layout, 2, 0)

        # Stopwatch 2: Activity Lap Stopwatch
        lap_caption = QLabel(
            "<b>ACTIVITY LAP STOPWATCH</b><br><small>One activity interval; uses video or manual time</small>"
        )
        lap_caption.setObjectName("stopwatchCaption")
        stopwatch_layout.addWidget(lap_caption, 0, 1)
        self.lbl_lap_time = QLabel("00:00.00")
        self.lbl_lap_time.setStyleSheet(get_digital_readout_style(font_size_pt=20, text_color="#10B981"))
        self.lbl_lap_time.setAlignment(Qt.AlignmentFlag.AlignCenter)
        stopwatch_layout.addWidget(self.lbl_lap_time, 1, 1)

        lap_info_layout = QHBoxLayout()
        self.lbl_lap_status = QLabel("Status: Idle (Press 'S' to Start)")
        self.lbl_lap_status.setObjectName("lapStatus")
        lap_info_layout.addWidget(self.lbl_lap_status)

        self.btn_cancel_lap = QPushButton("Cancel Lap")
        self.btn_cancel_lap.setEnabled(False)
        self.btn_cancel_lap.clicked.connect(self._cancel_lap)
        lap_info_layout.addWidget(self.btn_cancel_lap)
        stopwatch_layout.addLayout(lap_info_layout, 2, 1)

        right_layout.addWidget(stopwatch_box)

        # Middle Group: Rapid Activity Entry & Classification
        entry_box = QGroupBox("Micro-Activity Logging & SMED Bifurcation")
        entry_layout = QVBoxLayout(entry_box)
        entry_layout.setContentsMargins(12, 14, 12, 12)
        entry_layout.setSpacing(10)

        # Standardized Activity Dropdown with Autocomplete
        act_row = QHBoxLayout()
        act_row.addWidget(QLabel("<b>Activity Name:</b>"))
        self.combo_activity = QComboBox()
        self.combo_activity.setEditable(True)
        self.combo_activity.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.combo_activity.lineEdit().setPlaceholderText("Type or select standard activity name...")
        self.combo_activity.currentIndexChanged.connect(self._on_activity_selected_from_dropdown)
        act_row.addWidget(self.combo_activity, stretch=1)
        entry_layout.addLayout(act_row)

        # Internal vs External Bifurcation Radios
        bifurcation_row = QHBoxLayout()
        bifurcation_row.addWidget(QLabel("<b>Classification:</b>"))

        self.radio_group = QButtonGroup(self)
        self.radio_internal = QRadioButton(" INTERNAL (Machine Stopped) [I]")
        self.radio_internal.setObjectName("internalRadio")
        self.radio_group.addButton(self.radio_internal, 1)
        bifurcation_row.addWidget(self.radio_internal)

        self.radio_external = QRadioButton(" EXTERNAL (Machine Running) [E]")
        self.radio_external.setObjectName("externalRadio")
        self.radio_group.addButton(self.radio_external, 2)
        bifurcation_row.addWidget(self.radio_external)
        self.radio_internal.setChecked(True)

        bifurcation_row.addStretch()
        entry_layout.addLayout(bifurcation_row)

        # Remarks and Big Lap Button
        action_row = QHBoxLayout()
        self.input_remarks = QLineEdit()
        self.input_remarks.setPlaceholderText("Remarks (optional observation, waste observed, etc.)...")
        action_row.addWidget(self.input_remarks, stretch=1)

        self.btn_lap = QPushButton(" Start / Lap Activity (S)")
        self.btn_lap.setObjectName("primaryBtn")
        self.btn_lap.setFixedHeight(38)
        self.btn_lap.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_lap.clicked.connect(self._on_lap_triggered)
        action_row.addWidget(self.btn_lap)

        entry_layout.addLayout(action_row)
        right_layout.addWidget(entry_box)

        # Bottom Table: Activity Logs for current trial
        table_box = QGroupBox("Logged Micro-Activities for Current Trial")
        table_layout = QVBoxLayout(table_box)
        table_layout.setContentsMargins(10, 14, 10, 10)

        self.table_logs = QTableWidget()
        self.table_logs.setColumnCount(8)
        self.table_logs.setHorizontalHeaderLabels([
            "Seq", "Activity Description", "Type", "Start (s)", "End (s)", "Duration", "Remarks", "Action"
        ])
        self.table_logs.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table_logs.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table_logs.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.table_logs.setColumnWidth(2, 136)
        self.table_logs.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table_logs.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table_logs.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.table_logs.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)
        self.table_logs.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_logs.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        table_layout.addWidget(self.table_logs)

        # Subtotal Bar
        subtotal_bar = QFrame()
        subtotal_bar.setObjectName("videoSubtotalBar")
        subtotal_layout = QHBoxLayout(subtotal_bar)
        subtotal_layout.setContentsMargins(4, 2, 4, 2)

        self.lbl_subtotal_internal = QLabel("Internal: 00:00 (0.0s)")
        self.lbl_subtotal_internal.setObjectName("subtotalInternal")
        subtotal_layout.addWidget(self.lbl_subtotal_internal)

        subtotal_layout.addSpacing(16)

        self.lbl_subtotal_external = QLabel("External: 00:00 (0.0s)")
        self.lbl_subtotal_external.setObjectName("subtotalExternal")
        subtotal_layout.addWidget(self.lbl_subtotal_external)

        subtotal_layout.addSpacing(16)

        self.lbl_subtotal_total = QLabel("Total Sum: 00:00 (0.0s)")
        self.lbl_subtotal_total.setObjectName("subtotalTotal")
        subtotal_layout.addWidget(self.lbl_subtotal_total)

        subtotal_layout.addStretch()

        self.lbl_subtotal_count = QLabel("0 Activities Logged")
        self.lbl_subtotal_count.setObjectName("subtotalCount")
        subtotal_layout.addWidget(self.lbl_subtotal_count)

        table_layout.addWidget(subtotal_bar)
        right_layout.addWidget(table_box, stretch=1)

        splitter.addWidget(right_pane)

        # Set ratio 48% : 52%
        splitter.setSizes([540, 580])

    def _setup_shortcuts(self):
        """Configure keyboard hotkeys for rapid operator logging."""
        # Spacebar -> Toggle Video Play / Pause
        self.shortcut_space = QShortcut(QKeySequence(Qt.Key.Key_Space), self)
        self.shortcut_space.activated.connect(self._handle_space_shortcut)

        # 'S' key -> Start / Lap
        self.shortcut_lap = QShortcut(QKeySequence(Qt.Key.Key_S), self)
        self.shortcut_lap.activated.connect(self._handle_lap_shortcut)

        # 'I' key -> Toggle Internal
        self.shortcut_internal = QShortcut(QKeySequence(Qt.Key.Key_I), self)
        self.shortcut_internal.activated.connect(self._handle_internal_shortcut)

        # 'E' key -> Toggle External
        self.shortcut_external = QShortcut(QKeySequence(Qt.Key.Key_E), self)
        self.shortcut_external.activated.connect(self._handle_external_shortcut)

    # =========================================================================
    # SHORTCUT HANDLERS (Context-aware: ignore when user is typing text)
    # =========================================================================

    def _is_text_input_focused(self) -> bool:
        fw = self.focusWidget()
        return isinstance(fw, (QLineEdit, QTextEdit))

    def _handle_space_shortcut(self):
        if not self._is_text_input_focused():
            self.toggle_play_pause()

    def _handle_lap_shortcut(self):
        if not self._is_text_input_focused():
            self._on_lap_triggered()

    def _handle_internal_shortcut(self):
        if not self._is_text_input_focused():
            self.radio_internal.setChecked(True)

    def _handle_external_shortcut(self):
        if not self._is_text_input_focused():
            self.radio_external.setChecked(True)

    # =========================================================================
    # PROJECT & TRIAL LOADING
    # =========================================================================

    def set_project(self, project_id: int):
        """Set active project from external signal or selection."""
        self.active_project_id = project_id
        project = self.db.get_project(project_id)
        if project:
            self.lbl_active_project.setText(f"{project['name']}  ({project.get('machine_name') or 'Machine'})")
        else:
            self.lbl_active_project.setText("Unknown Project")

        self._refresh_standard_activities_dropdown()
        self._refresh_trials_dropdown()

    def _on_phase_changed(self):
        """Handle phase change (BEFORE vs AFTER)."""
        idx = self.combo_phase.currentIndex()
        self.active_phase = "BEFORE" if idx == 0 else "AFTER"
        self._refresh_trials_dropdown()

    def _refresh_standard_activities_dropdown(self):
        """Populate the standardized activity dropdown and completer for the project."""
        if not self.active_project_id:
            return

        activities = self.db.get_standard_activities(self.active_project_id)
        self.standard_activities_map.clear()
        names = []

        for act in activities:
            self.standard_activities_map[act["activity_name"].lower()] = act
            names.append(act["activity_name"])

        # Update QComboBox items without wiping current user typing
        current_text = self.combo_activity.currentText()
        self.combo_activity.blockSignals(True)
        self.combo_activity.clear()
        self.combo_activity.addItems(names)
        self.combo_activity.setCurrentText(current_text)
        self.combo_activity.blockSignals(False)

        # Autocompleter
        completer = QCompleter(names, self)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.combo_activity.setCompleter(completer)

    def _refresh_trials_dropdown(self):
        """Fetch video trials for active project and active phase."""
        if not self.active_project_id:
            self.combo_trials.clear()
            return

        trials = self.db.get_trials_by_project(self.active_project_id, phase=self.active_phase)
        self.combo_trials.blockSignals(True)
        self.combo_trials.clear()

        for t in trials:
            dur_str = format_seconds(t.get("total_smed_duration_sec", 0.0))
            label = f"Trial #{t['trial_number']}: {t['video_title']}  [{dur_str}]"
            self.combo_trials.addItem(label, t["id"])

        self.combo_trials.blockSignals(False)

        if trials:
            self.combo_trials.setCurrentIndex(0)
            self._select_trial(trials[0]["id"])
        else:
            self.active_trial_id = None
            self._reset_timers_for_trial()
            self.master_accumulated_sec = 0.0
            self.lbl_master_time.setText("00:00.00")
            self._close_video()
            self._load_activity_logs()
            self._show_canvas_placeholder(
                f"No {self.active_phase} Trials Recorded Yet.\nClick 'Import Video Trials (Batch)...' to add clips."
            )

    def _on_trial_selected(self, index: int):
        if index < 0:
            return
        trial_id = self.combo_trials.itemData(index)
        if trial_id:
            self._select_trial(trial_id)

    def _select_trial(self, trial_id: int):
        """Load selected trial, open its video if present, and load its activity logs."""
        self._reset_timers_for_trial()
        self.active_trial_id = trial_id
        trial = self.db.get_video_trial(trial_id)
        if not trial:
            return

        # Update 6th OK part checkbox
        self.chk_sixth_part.blockSignals(True)
        self.chk_sixth_part.setChecked(bool(trial.get("sixth_ok_part_verified", 0)))
        self.chk_sixth_part.blockSignals(False)

        # Set master time to saved duration
        saved_duration = float(trial.get("total_smed_duration_sec", 0.0))
        self.master_accumulated_sec = saved_duration
        self.lbl_master_time.setText(format_seconds(saved_duration))
        self.lbl_master_time.setToolTip(
            f"Loaded saved trial duration: {format_seconds(saved_duration)}. "
            "Start Master to continue manually or Sync to Video to set the current playback position."
        )

        # Open video file if exists
        video_path = trial.get("file_path")
        if video_path and os.path.exists(video_path):
            self._load_video_file(video_path)
        else:
            self._close_video()
            self._show_canvas_placeholder(
                f"Manual timing mode\nVideo file '{os.path.basename(video_path or '')}' was not found or is offline.\n"
                "Start Master, then start an activity lap."
            )

        # Load logged activities table
        self._load_activity_logs()

    def _on_sixth_part_toggled(self, state: int):
        """Update 6th consecutive OK part verified flag in database."""
        if not self.active_trial_id:
            return
        is_checked = (state == Qt.CheckState.Checked.value or state == 2)
        self.db.update_video_trial(self.active_trial_id, sixth_ok_part_verified=is_checked)

    def _on_import_videos(self):
        """Batch import 1 to 10+ video files into current project and phase."""
        if not self.active_project_id:
            QMessageBox.warning(self, "No Project", "Please select or create an active SMED project first.")
            return

        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Import SMED Video Observations",
            "",
            "Video Files (*.mp4 *.avi *.mkv *.mov *.wmv *.flv);;All Files (*.*)",
        )
        if not files:
            return

        existing_trials = self.db.get_trials_by_project(self.active_project_id, phase=self.active_phase)
        next_num = len(existing_trials) + 1

        for filepath in files:
            filename = os.path.basename(filepath)
            title = f"{self.active_phase} Trial {next_num} - {os.path.splitext(filename)[0]}"

            # Attempt to extract duration using OpenCV
            dur_sec = 0.0
            try:
                temp_cap = cv2.VideoCapture(filepath)
                if temp_cap.isOpened():
                    fps = temp_cap.get(cv2.CAP_PROP_FPS) or 30.0
                    frames = temp_cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
                    dur_sec = frames / fps if fps > 0 else 0.0
                    temp_cap.release()
            except Exception:
                pass

            self.db.create_video_trial(
                project_id=self.active_project_id,
                phase=self.active_phase,
                trial_number=next_num,
                video_title=title,
                file_path=filepath,
                total_smed_duration_sec=round(dur_sec, 2),
                sixth_ok_part_verified=False,
            )
            next_num += 1

        self._refresh_trials_dropdown()
        self.data_changed.emit()
        QMessageBox.information(
            self, "Import Complete", f"Successfully imported {len(files)} video trial(s) into '{self.active_phase}' phase!"
        )

    def _on_delete_active_trial(self):
        """Delete currently selected video trial."""
        if not self.active_trial_id:
            return

        reply = QMessageBox.question(
            self,
            "Delete Trial",
            "Are you sure you want to delete this video trial and all its logged activities?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.db.delete_video_trial(self.active_trial_id)
            self._refresh_trials_dropdown()
            self.data_changed.emit()

    def _on_generate_demo_videos(self):
        """Generate synthetic shop-floor demo videos and link them to active project."""
        from utils.demo_video_generator import generate_and_seed_demo_project
        try:
            pid = generate_and_seed_demo_project(self.db, "sample_videos")
            self.set_project(pid)
            self.data_changed.emit()
            QMessageBox.information(
                self,
                "Demo SMED Videos Loaded",
                "Successfully generated shop-floor simulation videos in 'sample_videos/'!\n\n"
                "These are accelerated animations for learning the workflow, not real shop-floor footage. "
                "Import an actual recording for a real time study.\n\n"
                "• Baseline Trial #1 (BEFORE): Unoptimized changeover with high manual waste.\n"
                "• Kaizen Trial #1 (AFTER): Standardized quick-clamping & laser alignment.\n\n"
                "Controls:\n"
                "- Space: Play / Pause\n"
                "- Left / Right Arrows: -1s / +1s Scrub\n"
                "- 'S': Start / Lap Activity\n"
                "- 'I': Internal (Machine Stopped)\n"
                "- 'E': External (Machine Running)"
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate demo videos:\n{str(e)}")

    # =========================================================================
    # OPENCV VIDEO PLAYBACK ENGINE
    # =========================================================================

    def _show_canvas_placeholder(self, text: str):
        self.video_canvas.setText(text)
        self.video_canvas.setStyleSheet(
            "background-color: #080D15; color: #CBD5E1; font-size: 14px; font-weight: 600; "
            "border: 1px solid #1E293B; border-radius: 8px;"
        )

    def _load_video_file(self, filepath: str):
        """Open video file using OpenCV."""
        self._close_video()

        self.cap = cv2.VideoCapture(filepath)
        if not self.cap.isOpened():
            self.cap.release()
            self.cap = None
            self._show_canvas_placeholder(
                f"Could not open video\n{os.path.basename(filepath)}\n"
                "Check that the file is a supported video format."
            )
            self.btn_master_sync.setEnabled(False)
            return

        self.btn_master_sync.setEnabled(True)
        self.btn_master_toggle.setToolTip(
            "Run or pause the overall manual elapsed-time stopwatch. "
            "Activity Lap uses video playback position while a video is loaded."
        )
        self.video_fps = self.cap.get(cv2.CAP_PROP_FPS) or 30.0
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        self.video_duration_sec = self.total_frames / self.video_fps if self.video_fps > 0 else 0.0

        filename = os.path.basename(filepath)
        self.lbl_video_info.setText(f"{filename} | {self.video_fps:.1f} FPS | {format_seconds(self.video_duration_sec)}")
        self.lbl_video_info.setToolTip(
            f"Loaded study video: {filepath}\n"
            "Activity start/end times use the video playback position."
        )

        # Read first frame
        self._render_current_frame()
        self._update_time_slider()

    def _close_video(self):
        self.pause()
        if self.cap:
            self.cap.release()
            self.cap = None
        self.total_frames = 0
        self.video_duration_sec = 0.0
        self.lbl_video_info.setText("No Video Loaded")
        self.lbl_video_info.setToolTip(
            "Import shop-floor footage to review it. Without a video, activity timing uses the manual master timer."
        )
        self.btn_master_sync.setEnabled(False)
        self.btn_master_toggle.setToolTip(
            "Start or pause the overall manual elapsed-time stopwatch. "
            "Starting an activity lap auto-starts it when no video is loaded."
        )
        self.lbl_time_display.setText("00:00.00 / 00:00.00")
        self.slider_seek.setValue(0)

    def toggle_play_pause(self):
        if self.is_playing:
            self.pause()
        else:
            self.play()

    def play(self):
        if not self.cap or not self.cap.isOpened():
            return
        self.is_playing = True
        self.btn_play_pause.setText("⏸ Pause (Space)")
        if self.lap_running:
            self.lbl_lap_status.setText("Timing from video playback.")
        interval = max(10, int(1000.0 / (self.video_fps * self.playback_speed)))
        self.video_timer.start(interval)

    def pause(self):
        self.is_playing = False
        self.btn_play_pause.setText("▶ Play (Space)")
        self.video_timer.stop()
        if self.lap_running and self.cap and self.cap.isOpened():
            self.lbl_lap_status.setText("Activity timing paused — play the video to continue.")

    def _on_speed_changed(self):
        speed_text = self.combo_speed.currentText().replace("x", "")
        try:
            self.playback_speed = float(speed_text)
            if self.is_playing:
                interval = max(10, int(1000.0 / (self.video_fps * self.playback_speed)))
                self.video_timer.start(interval)
        except ValueError:
            self.playback_speed = 1.0

    def _on_video_tick(self):
        if not self.cap or not self.cap.isOpened():
            self.pause()
            return

        ret, frame = self.cap.read()
        if ret:
            self._display_cv2_frame(frame)
            self._update_time_slider()
        else:
            # Reached end of video
            self.pause()

    def _render_current_frame(self):
        if not self.cap or not self.cap.isOpened():
            return
        ret, frame = self.cap.read()
        if ret:
            self._display_cv2_frame(frame)

    def _display_cv2_frame(self, frame):
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w
        q_img = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(q_img)
        self.video_canvas.set_frame(pixmap)

    def get_current_time_sec(self) -> float:
        """Get current observation timestamp (either from video playback or live stopwatch)."""
        if self.cap and self.cap.isOpened():
            pos_msec = self.cap.get(cv2.CAP_PROP_POS_MSEC)
            return max(0.0, pos_msec / 1000.0)
        else:
            return self.master_accumulated_sec

    def _seek_relative(self, delta_sec: float):
        if not self.cap or not self.cap.isOpened():
            return
        curr_frame = self.cap.get(cv2.CAP_PROP_POS_FRAMES)
        target_frame = max(0, min(self.total_frames - 1, curr_frame + (delta_sec * self.video_fps)))
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
        self._render_current_frame()
        self._update_time_slider()

    def _on_seek_slider_moved(self, slider_val: int):
        if not self.cap or not self.cap.isOpened() or self.total_frames <= 0:
            return
        target_frame = int((slider_val / 1000.0) * self.total_frames)
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
        self._render_current_frame()
        self._update_time_slider()

    def _update_time_slider(self):
        curr_sec = self.get_current_time_sec()
        self.lbl_time_display.setText(f"{format_seconds(curr_sec)} / {format_seconds(self.video_duration_sec)}")
        if self.video_duration_sec > 0:
            ratio = int((curr_sec / self.video_duration_sec) * 1000)
            self.slider_seek.blockSignals(True)
            self.slider_seek.setValue(min(1000, ratio))
            self.slider_seek.blockSignals(False)

        # If lap is running, update lap display
        if self.lap_running:
            lap_dur = max(0.0, curr_sec - self.lap_start_time_sec)
            self.lbl_lap_time.setText(format_seconds(lap_dur))
        elif not self.cap:
            self.lbl_time_display.setText(f"{format_seconds(curr_sec)} / Live")

    # =========================================================================
    # DUAL STOPWATCH TIMING LOGIC
    # =========================================================================

    def _toggle_master_timer(self):
        """Start or pause the overall manual elapsed-time stopwatch."""
        self._set_master_timer_running(not self.master_running)
        if self.lap_running and not self.cap:
            state = "running" if self.master_running else "paused"
            self.lbl_lap_status.setText(f"Manual activity timing {state} with the master timer.")

    def _set_master_timer_running(self, running: bool):
        self.master_running = running
        if running:
            self._last_live_tick_time = time.monotonic()
            self.btn_master_toggle.setText("Stop Master")
            self.btn_master_toggle.setObjectName("dangerBtn")
            if not self.live_timer.isActive():
                self.live_timer.start(50)
        else:
            self._last_live_tick_time = None
            self.btn_master_toggle.setText("Resume Master" if self.master_accumulated_sec else "Start Master")
            self.btn_master_toggle.setObjectName("primaryBtn")
            self.live_timer.stop()
        self.btn_master_toggle.setStyleSheet("")
        self.btn_master_toggle.style().unpolish(self.btn_master_toggle)
        self.btn_master_toggle.style().polish(self.btn_master_toggle)

    def _reset_timers_for_trial(self):
        self.live_timer.stop()
        self.master_running = False
        self._last_live_tick_time = None
        self.lap_running = False
        self.btn_master_toggle.setText("Start Master")
        self.btn_master_toggle.setObjectName("primaryBtn")
        self.btn_master_toggle.setStyleSheet("")
        self.btn_master_toggle.style().unpolish(self.btn_master_toggle)
        self.btn_master_toggle.style().polish(self.btn_master_toggle)
        self.lbl_lap_time.setText("00:00.00")
        self.lbl_lap_status.setText("Status: Idle (Press 'S' to Start)")
        self.btn_lap.setText(" Start / Lap Activity (S)")
        self.btn_lap.setObjectName("primaryBtn")
        self.btn_lap.setStyleSheet("")
        self.btn_cancel_lap.setEnabled(False)

    def _on_live_tick(self):
        """Update manual stopwatch values using monotonic elapsed time."""
        now = time.monotonic()
        elapsed = now - self._last_live_tick_time if self._last_live_tick_time is not None else 0.0
        self._last_live_tick_time = now

        if self.master_running:
            self.master_accumulated_sec += elapsed
            self.lbl_master_time.setText(format_seconds(self.master_accumulated_sec))

        if not self.cap:
            self.lbl_time_display.setText(f"{format_seconds(self.master_accumulated_sec)} / Live")

        if self.lap_running:
            curr_sec = self.get_current_time_sec()
            lap_dur = max(0.0, curr_sec - self.lap_start_time_sec)
            self.lbl_lap_time.setText(format_seconds(lap_dur))

    def _sync_master_to_video(self):
        """Set Master stopwatch to exact video timestamp."""
        video_sec = self.get_current_time_sec()
        self.master_accumulated_sec = video_sec
        self.lbl_master_time.setText(format_seconds(self.master_accumulated_sec))

    def _save_master_duration_to_trial(self):
        """Save the current Master stopwatch duration to the video_trials table."""
        if not self.active_trial_id:
            return
        dur = round(self.master_accumulated_sec, 2)
        self.db.update_video_trial(self.active_trial_id, total_smed_duration_sec=dur)
        self._refresh_trials_dropdown()
        self.data_changed.emit()
        QMessageBox.information(
            self, "Master Time Saved", f"Total SMED setup duration {format_seconds(dur)} saved to trial!"
        )

    # =========================================================================
    # RAPID ACTIVITY LOGGING & STANDARDIZED DROPDOWN BIFURCATION
    # =========================================================================

    def _on_activity_selected_from_dropdown(self):
        """When an existing activity is chosen from dropdown, auto-select its default type."""
        text = self.combo_activity.currentText().strip().lower()
        if text in self.standard_activities_map:
            act_info = self.standard_activities_map[text]
            def_type = act_info.get("default_type", "Internal")
            if def_type == "External":
                self.radio_external.setChecked(True)
            else:
                self.radio_internal.setChecked(True)

    def _on_lap_triggered(self):
        """
        Operator presses 'S' (or clicks Lap button):
        - If Lap timer is NOT running: Starts timing current activity.
        - If Lap timer IS running: Ends current activity, logs it to database,
          reloads table, and immediately begins timing the next activity (Continuous zero-gap logging).
        """
        if not self.active_trial_id or not self.active_project_id:
            QMessageBox.warning(self, "No Active Trial", "Please select a Project and Trial before logging.")
            return

        curr_time = self.get_current_time_sec()

        if not self.lap_running:
            # START FIRST LAP
            if not self.cap and not self.master_running:
                self._set_master_timer_running(True)
            self.lap_running = True
            self.lap_start_time_sec = curr_time
            self.btn_lap.setText(" Log & Next Lap [S]")
            self.btn_lap.setObjectName("successBtn")
            self.btn_lap.setStyleSheet("")
            self.btn_cancel_lap.setEnabled(True)
            if self.cap:
                status = (
                    "Timing from video playback."
                    if self.is_playing
                    else "Lap started — play the video to advance timing."
                )
            elif curr_time == 0:
                status = "Manual timer started with this activity."
            else:
                status = "Activity timing from manual clock."
            self.lbl_lap_status.setText(f"{status} Start: {format_seconds(curr_time)}")
        else:
            # FINISH CURRENT LAP AND LOG TO DB
            act_name = self.combo_activity.currentText().strip()
            if not act_name:
                act_name = f"Unspecified Step #{self.table_logs.rowCount() + 1}"

            act_type = "Internal" if self.radio_internal.isChecked() else "External"
            end_time = curr_time
            duration = max(0.0, end_time - self.lap_start_time_sec)
            remarks = self.input_remarks.text().strip() or None

            # Get or create standard activity in master dictionary
            std_act_id, was_created = self.db.get_or_create_standard_activity(
                project_id=self.active_project_id,
                activity_name=act_name,
                default_type=act_type,
            )

            # If created on the fly, refresh dropdown so it's standardized for future trials!
            if was_created:
                self._refresh_standard_activities_dropdown()

            # Log activity into SQLite
            self.db.log_activity(
                video_trial_id=self.active_trial_id,
                standard_activity_id=std_act_id,
                activity_type=act_type,
                start_time_sec=self.lap_start_time_sec,
                end_time_sec=end_time,
                duration_sec=duration,
                remarks=remarks,
            )

            # Reset for Next Lap (Zero-gap continuous logging)
            self.lap_start_time_sec = end_time
            self.input_remarks.clear()
            if self.cap:
                status = (
                    "Logged. Next lap is timing from video playback."
                    if self.is_playing
                    else "Logged. Play the video to advance the next lap."
                )
            else:
                status = "Logged. Next manual lap is running."
            self.lbl_lap_status.setText(f"{status} Start: {format_seconds(end_time)}")

            # Reload activity table
            self._load_activity_logs()
            self.data_changed.emit()

    def _cancel_lap(self):
        """Cancel current lap without saving."""
        self.lap_running = False
        self.btn_lap.setText(" Start / Lap Activity (S)")
        self.btn_lap.setObjectName("primaryBtn")
        self.btn_lap.setStyleSheet("")
        self.btn_cancel_lap.setEnabled(False)
        self.lbl_lap_time.setText("00:00.00")
        self.lbl_lap_status.setText(
            "Lap cancelled; master timer continues." if self.master_running else "Status: Lap Cancelled"
        )

    # =========================================================================
    # ACTIVITY LOGS TABLE & SUBTOTAL CALCULATOR
    # =========================================================================

    def _load_activity_logs(self):
        """Load logged activities for the active trial into table."""
        if not self.active_trial_id:
            self.table_logs.setRowCount(0)
            self._update_subtotals(0.0, 0.0, 0)
            return

        logs = self.db.get_logs_by_trial(self.active_trial_id)
        self.table_logs.setRowCount(0)

        total_internal = 0.0
        total_external = 0.0

        for row_idx, item in enumerate(logs):
            self.table_logs.insertRow(row_idx)

            # Seq
            seq_item = QTableWidgetItem(str(item["sequence_no"]))
            seq_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_logs.setItem(row_idx, 0, seq_item)

            # Name
            name_item = QTableWidgetItem(item["activity_name"])
            self.table_logs.setItem(row_idx, 1, name_item)

            # Type Badge
            type_label = QLabel(item["activity_type"])
            type_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            if item["activity_type"] == "Internal":
                type_label.setStyleSheet(get_internal_badge_style())
                total_internal += item["duration_sec"]
            else:
                type_label.setStyleSheet(get_external_badge_style())
                total_external += item["duration_sec"]
            self.table_logs.setCellWidget(row_idx, 2, type_label)

            # Start, End, Duration
            start_item = QTableWidgetItem(f"{item['start_time_sec']:.2f}")
            start_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table_logs.setItem(row_idx, 3, start_item)

            end_item = QTableWidgetItem(f"{item['end_time_sec']:.2f}")
            end_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table_logs.setItem(row_idx, 4, end_item)

            dur_item = QTableWidgetItem(format_seconds(item["duration_sec"]))
            dur_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            dur_item.setForeground(QColor(COLORS["primary_blue"]))
            dur_font = dur_item.font()
            dur_font.setBold(True)
            dur_item.setFont(dur_font)
            self.table_logs.setItem(row_idx, 5, dur_item)

            # Remarks
            rem_item = QTableWidgetItem(item.get("remarks") or "")
            self.table_logs.setItem(row_idx, 6, rem_item)

            # Delete Action Button
            btn_del = QPushButton("✕")
            btn_del.setFixedSize(26, 24)
            btn_del.setObjectName("dangerBtn")
            btn_del.setToolTip("Delete this activity log entry")
            log_id = item["id"]
            btn_del.clicked.connect(lambda checked, lid=log_id: self._delete_activity_log(lid))
            cell_widget = QWidget()
            cw_layout = QHBoxLayout(cell_widget)
            cw_layout.setContentsMargins(0, 0, 0, 0)
            cw_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cw_layout.addWidget(btn_del)
            self.table_logs.setCellWidget(row_idx, 7, cell_widget)

        self._update_subtotals(total_internal, total_external, len(logs))

    def _update_subtotals(self, internal_sec: float, external_sec: float, count: int):
        total_sec = internal_sec + external_sec
        self.lbl_subtotal_internal.setText(f"Internal: {format_seconds(internal_sec)} ({internal_sec:.1f}s)")
        self.lbl_subtotal_external.setText(f"External: {format_seconds(external_sec)} ({external_sec:.1f}s)")
        self.lbl_subtotal_total.setText(f"Total Activity Sum: {format_seconds(total_sec)} ({total_sec:.1f}s)")
        self.lbl_subtotal_count.setText(f"{count} Micro-Activities Logged")

    def _delete_activity_log(self, log_id: int):
        self.db.delete_activity_log(log_id)
        self._load_activity_logs()
        self.data_changed.emit()
