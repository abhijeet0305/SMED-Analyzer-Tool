"""
SMED Studio - Project Management Tab
Enables creation, selection, and overview of SMED die changeover optimization projects.
"""

from typing import Optional
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QGridLayout, QLabel,
    QLineEdit, QTextEdit, QDoubleSpinBox, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QGroupBox, QMessageBox, QFrame,
    QSplitter
)

from database.db_manager import DatabaseManager, get_db
from ui.styles import COLORS


class ProjectTab(QWidget):
    """
    Project Setup and Master Configuration Tab.
    Emits project_selected(int) when an active project is chosen.
    """
    project_selected = pyqtSignal(int)

    def __init__(self, db: Optional[DatabaseManager] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.db = db or get_db()
        self.active_project_id: Optional[int] = None
        self._init_ui()
        self.load_projects()

    def _init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)

        # =====================================================================
        # LEFT PANE: Create Project Form & Projects Directory Table
        # =====================================================================
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(16)

        # 1. Project Creation Card
        create_box = QGroupBox("Create New SMED Study Project")
        form_layout = QGridLayout(create_box)
        form_layout.setHorizontalSpacing(14)
        form_layout.setVerticalSpacing(10)

        # Name
        form_layout.addWidget(QLabel("Project Title: *"), 0, 0)
        self.input_name = QLineEdit()
        self.input_name.setPlaceholderText("e.g., Stamping Line 4 - Hood Outer Die Change")
        form_layout.addWidget(self.input_name, 0, 1, 1, 3)

        # Machine
        form_layout.addWidget(QLabel("Machine / Press:"), 1, 0)
        self.input_machine = QLineEdit()
        self.input_machine.setPlaceholderText("e.g., Komatsu 800-Ton Mechanical Press")
        form_layout.addWidget(self.input_machine, 1, 1)

        # Target Reduction %
        form_layout.addWidget(QLabel("Target Reduction %:"), 1, 2)
        self.input_target = QDoubleSpinBox()
        self.input_target.setRange(5.0, 95.0)
        self.input_target.setValue(50.0)
        self.input_target.setSingleStep(5.0)
        self.input_target.setSuffix(" %")
        form_layout.addWidget(self.input_target, 1, 3)

        # From Die & To Die
        form_layout.addWidget(QLabel("Previous Tool (From):"), 2, 0)
        self.input_from_die = QLineEdit()
        self.input_from_die.setPlaceholderText("e.g., Hood-Die-402 (Sedan)")
        form_layout.addWidget(self.input_from_die, 2, 1)

        form_layout.addWidget(QLabel("Next Tool (To):"), 2, 2)
        self.input_to_die = QLineEdit()
        self.input_to_die.setPlaceholderText("e.g., Hood-Die-408 (SUV)")
        form_layout.addWidget(self.input_to_die, 2, 3)

        # Notes
        form_layout.addWidget(QLabel("Baseline Notes:"), 3, 0)
        self.input_notes = QLineEdit()
        self.input_notes.setPlaceholderText("Operational context, target single-digit goal, or line bottlenecks...")
        form_layout.addWidget(self.input_notes, 3, 1, 1, 2)

        # Submit button
        self.btn_create = QPushButton(" Create SMED Project")
        self.btn_create.setObjectName("primaryBtn")
        self.btn_create.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_create.clicked.connect(self._on_create_project)
        form_layout.addWidget(self.btn_create, 3, 3)

        left_layout.addWidget(create_box)

        # 2. Existing Projects Table
        table_box = QGroupBox("SMED Project Repository")
        table_layout = QVBoxLayout(table_box)
        table_layout.setContentsMargins(12, 16, 12, 12)

        self.table_projects = QTableWidget()
        self.table_projects.setColumnCount(6)
        self.table_projects.setHorizontalHeaderLabels([
            "ID", "Project Title", "Machine", "Changeover (From -> To)", "Target %", "Created"
        ])
        self.table_projects.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table_projects.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table_projects.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table_projects.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table_projects.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_projects.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table_projects.setAlternatingRowColors(True)
        self.table_projects.itemSelectionChanged.connect(self._on_table_row_selected)
        self.table_projects.doubleClicked.connect(self._on_set_active_project)

        table_layout.addWidget(self.table_projects)

        # Refresh / Delete / Demo button bar
        btn_bar = QHBoxLayout()
        self.btn_refresh = QPushButton("Refresh List")
        self.btn_refresh.clicked.connect(self.load_projects)
        btn_bar.addWidget(self.btn_refresh)

        self.btn_demo_videos = QPushButton("🎬 Generate & Load Demo SMED Videos")
        self.btn_demo_videos.setObjectName("accentBtn")
        self.btn_demo_videos.setToolTip("Generate synthetic shop-floor simulation videos and load sample project.")
        self.btn_demo_videos.clicked.connect(self._on_generate_demo_videos)
        btn_bar.addWidget(self.btn_demo_videos)

        btn_bar.addStretch()

        self.btn_delete = QPushButton("Delete Project")
        self.btn_delete.setObjectName("dangerBtn")
        self.btn_delete.clicked.connect(self._on_delete_project)
        btn_bar.addWidget(self.btn_delete)

        table_layout.addLayout(btn_bar)
        left_layout.addWidget(table_box)

        splitter.addWidget(left_widget)

        # =====================================================================
        # RIGHT PANE: Active Project Summary Card & Direct Navigation
        # =====================================================================
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        summary_box = QGroupBox("Active Study Project Overview")
        summary_layout = QVBoxLayout(summary_box)
        summary_layout.setContentsMargins(20, 24, 20, 20)
        summary_layout.setSpacing(16)

        # Title Banner
        self.lbl_card_title = QLabel("Select a Project from the Repository")
        self.lbl_card_title.setStyleSheet("font-size: 18px; font-weight: 700; color: #38BDF8;")
        self.lbl_card_title.setWordWrap(True)
        summary_layout.addWidget(self.lbl_card_title)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("color: #334155;")
        summary_layout.addWidget(separator)

        # Grid Details
        details_grid = QGridLayout()
        details_grid.setVerticalSpacing(12)
        details_grid.setHorizontalSpacing(16)

        details_grid.addWidget(QLabel("<b>Machine:</b>"), 0, 0)
        self.val_machine = QLabel("—")
        self.val_machine.setStyleSheet("color: #F8FAFC;")
        details_grid.addWidget(self.val_machine, 0, 1)

        details_grid.addWidget(QLabel("<b>Tool Change:</b>"), 1, 0)
        self.val_tool_change = QLabel("—")
        self.val_tool_change.setStyleSheet("color: #F8FAFC;")
        details_grid.addWidget(self.val_tool_change, 1, 1)

        details_grid.addWidget(QLabel("<b>Setup Reduction Target:</b>"), 2, 0)
        self.val_target = QLabel("—")
        self.val_target.setStyleSheet("color: #10B981; font-weight: 700;")
        details_grid.addWidget(self.val_target, 2, 1)

        details_grid.addWidget(QLabel("<b>Before Trials Recorded:</b>"), 3, 0)
        self.val_before_count = QLabel("0 Baseline Video(s)")
        self.val_before_count.setStyleSheet("color: #F59E0B; font-weight: 600;")
        details_grid.addWidget(self.val_before_count, 3, 1)

        details_grid.addWidget(QLabel("<b>After Trials Recorded:</b>"), 4, 0)
        self.val_after_count = QLabel("0 Verification Video(s)")
        self.val_after_count.setStyleSheet("color: #10B981; font-weight: 600;")
        details_grid.addWidget(self.val_after_count, 4, 1)

        details_grid.addWidget(QLabel("<b>Standard Activities Mastered:</b>"), 5, 0)
        self.val_activities_count = QLabel("0 Activities in Dictionary")
        details_grid.addWidget(self.val_activities_count, 5, 1)

        details_grid.addWidget(QLabel("<b>Notes:</b>"), 6, 0)
        self.val_notes = QLabel("—")
        self.val_notes.setWordWrap(True)
        self.val_notes.setStyleSheet("color: #94A3B8; font-style: italic;")
        details_grid.addWidget(self.val_notes, 6, 1)

        summary_layout.addLayout(details_grid)
        summary_layout.addStretch()

        # Prominent CTA Button
        self.btn_set_active = QPushButton(" Set as Active Project & Open Video Logger  ")
        self.btn_set_active.setObjectName("primaryBtn")
        self.btn_set_active.setFixedHeight(46)
        self.btn_set_active.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_set_active.clicked.connect(self._on_set_active_project)
        self.btn_set_active.setEnabled(False)
        summary_layout.addWidget(self.btn_set_active)

        right_layout.addWidget(summary_box)
        splitter.addWidget(right_widget)

        # Splitter sizing ratio 60% : 40%
        splitter.setSizes([650, 450])

    def load_projects(self):
        """Fetch all projects from SQLite database and populate table."""
        projects = self.db.get_all_projects()
        self.table_projects.setRowCount(0)

        for row_idx, p in enumerate(projects):
            self.table_projects.insertRow(row_idx)

            id_item = QTableWidgetItem(str(p["id"]))
            id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_projects.setItem(row_idx, 0, id_item)

            name_item = QTableWidgetItem(p["name"])
            name_item.setData(Qt.ItemDataRole.UserRole, p["id"])
            self.table_projects.setItem(row_idx, 1, name_item)

            mach_item = QTableWidgetItem(p.get("machine_name") or "—")
            self.table_projects.setItem(row_idx, 2, mach_item)

            from_to = f"{p.get('from_die') or 'Old'} → {p.get('to_die') or 'New'}"
            change_item = QTableWidgetItem(from_to)
            self.table_projects.setItem(row_idx, 3, change_item)

            tgt_item = QTableWidgetItem(f"{p.get('target_reduction_pct', 50.0):.1f}%")
            tgt_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_projects.setItem(row_idx, 4, tgt_item)

            created_str = str(p.get("created_at") or "")[:10]
            date_item = QTableWidgetItem(created_str)
            date_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_projects.setItem(row_idx, 5, date_item)

        # Select first row if available and none selected
        if projects and self.active_project_id is None:
            self.table_projects.selectRow(0)
            self._select_project_by_id(projects[0]["id"])
        elif self.active_project_id is not None:
            self._select_project_by_id(self.active_project_id)

    def _select_project_by_id(self, project_id: int):
        """Update summary pane with selected project details."""
        p = self.db.get_project(project_id)
        if not p:
            return

        self.active_project_id = project_id
        self.lbl_card_title.setText(p["name"])
        self.val_machine.setText(p.get("machine_name") or "N/A")

        from_d = p.get("from_die") or "—"
        to_d = p.get("to_die") or "—"
        self.val_tool_change.setText(f"{from_d}  ➔  {to_d}")

        tgt = p.get("target_reduction_pct", 50.0)
        self.val_target.setText(f"≥ {tgt:.1f}% Reduction (SMED Goal)")

        # Query counts
        before_trials = self.db.get_trials_by_project(project_id, phase="BEFORE")
        after_trials = self.db.get_trials_by_project(project_id, phase="AFTER")
        activities = self.db.get_standard_activities(project_id)

        self.val_before_count.setText(f"{len(before_trials)} Baseline Video Trial(s)")
        self.val_after_count.setText(f"{len(after_trials)} Verification Video Trial(s)")
        self.val_activities_count.setText(f"{len(activities)} Standardized Activities")
        self.val_notes.setText(p.get("notes") or "No notes provided.")

        self.btn_set_active.setEnabled(True)

    def _on_table_row_selected(self):
        """Handle row selection change in projects table."""
        selected_rows = self.table_projects.selectedItems()
        if not selected_rows:
            return
        row = self.table_projects.currentRow()
        id_item = self.table_projects.item(row, 0)
        if id_item:
            try:
                pid = int(id_item.text())
                self._select_project_by_id(pid)
            except ValueError:
                pass

    def _on_create_project(self):
        """Create new project from input fields."""
        name = self.input_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation Error", "Please provide a Project Title.")
            self.input_name.setFocus()
            return

        mach = self.input_machine.text().strip() or None
        from_d = self.input_from_die.text().strip() or None
        to_d = self.input_to_die.text().strip() or None
        target = float(self.input_target.value())
        notes = self.input_notes.text().strip() or None

        try:
            new_id = self.db.create_project(
                name=name,
                machine_name=mach,
                from_die=from_d,
                to_die=to_d,
                target_reduction_pct=target,
                notes=notes,
            )

            # Clear inputs
            self.input_name.clear()
            self.input_machine.clear()
            self.input_from_die.clear()
            self.input_to_die.clear()
            self.input_notes.clear()

            self.load_projects()
            self._select_project_by_id(new_id)

            QMessageBox.information(
                self, "Project Created", f"Project '{name}' was created successfully!\nID: {new_id}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Failed to create project:\n{str(e)}")

    def _on_set_active_project(self):
        """Emit signal to switch active project across application tabs."""
        if self.active_project_id is not None:
            self.project_selected.emit(self.active_project_id)

    def _on_delete_project(self):
        """Prompt confirmation and delete selected project."""
        if self.active_project_id is None:
            return

        p = self.db.get_project(self.active_project_id)
        if not p:
            return

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete project:\n\n'{p['name']}' (ID: {self.active_project_id})?\n\n"
            "This will permanently delete all associated trials, activity logs, and Kaizen records.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.db.delete_project(self.active_project_id)
            self.active_project_id = None
            self.load_projects()

    def _on_generate_demo_videos(self):
        """Generate synthetic shop-floor videos and seed/activate demo project."""
        from utils.demo_video_generator import generate_and_seed_demo_project
        try:
            pid = generate_and_seed_demo_project(self.db, "sample_videos")
            self.load_projects()
            self._select_project_by_id(pid)
            self.project_selected.emit(pid)
            QMessageBox.information(
                self,
                "Demo Project & Videos Ready",
                "Successfully generated shop-floor simulation videos in 'sample_videos/'!\n\n"
                "• Baseline Trial #1 (BEFORE): Unoptimized 40m setup with manual waste.\n"
                "• Kaizen Trial #1 (AFTER): Standardized quick-clamping & laser alignment (13m).\n\n"
                "Switched to Video Logger. Press Space to play video and 'S' to lap activities."
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate demo project & videos:\n{str(e)}")
