"""
SMED Studio - Project Management Tab
Enables creation, selection, and overview of SMED die changeover optimization projects.
"""

from typing import Optional
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QGridLayout, QBoxLayout, QLabel,
    QLineEdit, QTextEdit, QDoubleSpinBox, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox, QFrame, QAbstractSpinBox,
    QStackedLayout, QSizePolicy
)

from database.db_manager import DatabaseManager, get_db


class ProjectTab(QWidget):
    """
    Project Setup and Master Configuration Tab.
    Emits project_selected(int) when an active project is chosen.
    """
    project_selected = pyqtSignal(int)
    STACK_LAYOUT_WIDTH = 960
    REPOSITORY_HEADER_STACK_WIDTH = 1100

    def __init__(self, db: Optional[DatabaseManager] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.db = db or get_db()
        self.active_project_id: Optional[int] = None
        self._init_ui()
        self.load_projects()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 12, 16, 12)
        main_layout.setSpacing(12)

        self.details_container = QWidget()
        self.details_container.setObjectName("projectDetails")
        self.details_container.setMinimumWidth(0)
        self.details_container.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Maximum
        )
        self.details_layout = QBoxLayout(QBoxLayout.Direction.LeftToRight, self.details_container)
        self.details_layout.setContentsMargins(0, 0, 0, 0)
        self.details_layout.setSpacing(12)

        create_card = QFrame()
        create_card.setObjectName("card")
        create_card.setFrameShape(QFrame.Shape.NoFrame)
        create_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        create_layout = QVBoxLayout(create_card)
        create_layout.setContentsMargins(14, 10, 14, 10)
        create_layout.setSpacing(6)

        create_header = QHBoxLayout()
        create_heading = QLabel("Create a study")
        create_heading.setObjectName("projectSectionTitle")
        create_header.addWidget(create_heading, 1)

        self.btn_create = QPushButton("Create project")
        self.btn_create.setObjectName("primaryBtn")
        self.btn_create.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_create.setMinimumWidth(150)
        self.btn_create.clicked.connect(self._on_create_project)
        create_header.addWidget(self.btn_create)
        create_layout.addLayout(create_header)

        create_description = QLabel("Set machine, tool change and reduction target.")
        create_description.setObjectName("projectSectionDescription")
        create_description.setWordWrap(True)
        create_layout.addWidget(create_description)

        form_layout = QGridLayout()
        form_layout.setContentsMargins(0, 2, 0, 0)
        form_layout.setHorizontalSpacing(12)
        form_layout.setVerticalSpacing(6)
        form_layout.setColumnStretch(0, 1)
        form_layout.setColumnStretch(1, 1)

        self.input_name = QLineEdit()
        self.input_name.setMinimumWidth(120)
        self.input_name.setAccessibleName("Project title, required")
        self.input_name.setPlaceholderText("e.g., Stamping Line 4 - Hood Outer Die Change")
        form_layout.addWidget(
            self._form_field("Title *", self.input_name), 0, 0, 1, 2
        )

        self.input_machine = QLineEdit()
        self.input_machine.setMinimumWidth(120)
        self.input_machine.setAccessibleName("Machine or press")
        self.input_machine.setPlaceholderText("e.g., Komatsu 800-Ton Mechanical Press")
        form_layout.addWidget(
            self._form_field("Machine", self.input_machine), 1, 0
        )

        self.input_target = QDoubleSpinBox()
        self.input_target.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.UpDownArrows)
        self.input_target.setMinimumWidth(100)
        self.input_target.setAccessibleName("Target setup reduction percentage")
        self.input_target.setToolTip(
            "Set the target setup-time reduction. Use the up/down arrows to adjust by 5%."
        )
        self.input_target.setRange(5.0, 95.0)
        self.input_target.setValue(50.0)
        self.input_target.setSingleStep(5.0)
        self.input_target.setSuffix(" %")
        form_layout.addWidget(self._form_field("Target", self.input_target), 1, 1)

        self.input_from_die = QLineEdit()
        self.input_from_die.setMinimumWidth(120)
        self.input_from_die.setAccessibleName("Previous tool or die")
        self.input_from_die.setPlaceholderText("e.g., Hood-Die-402")
        form_layout.addWidget(
            self._form_field("From die", self.input_from_die), 2, 0
        )

        self.input_to_die = QLineEdit()
        self.input_to_die.setMinimumWidth(120)
        self.input_to_die.setAccessibleName("Next tool or die")
        self.input_to_die.setPlaceholderText("e.g., Hood-Die-408")
        form_layout.addWidget(
            self._form_field("To die", self.input_to_die), 2, 1
        )

        self.input_notes = QLineEdit()
        self.input_notes.setMinimumWidth(120)
        self.input_notes.setAccessibleName("Baseline notes")
        self.input_notes.setPlaceholderText(
            "Operational context, line constraints or bottlenecks..."
        )
        form_layout.addWidget(self._form_field("Notes", self.input_notes), 3, 0, 1, 2)

        create_layout.addLayout(form_layout)
        self.details_layout.addWidget(create_card, 3)

        summary_card = QFrame()
        summary_card.setObjectName("card")
        summary_card.setFrameShape(QFrame.Shape.NoFrame)
        summary_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        summary_layout = QVBoxLayout(summary_card)
        summary_layout.setContentsMargins(14, 10, 14, 10)
        summary_layout.setSpacing(5)

        summary_heading = QLabel("Project overview")
        summary_heading.setObjectName("projectSectionTitle")
        summary_layout.addWidget(summary_heading)

        summary_top = QHBoxLayout()
        self.lbl_card_title = QLabel("Select a project")
        self.lbl_card_title.setObjectName("projectName")
        self.lbl_card_title.setWordWrap(True)
        self.lbl_card_title.setMinimumWidth(0)
        summary_top.addWidget(self.lbl_card_title, 1)
        self.lbl_project_status = QLabel("No selection")
        self.lbl_project_status.setObjectName("projectStatusBadge")
        self.lbl_project_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        summary_top.addWidget(self.lbl_project_status, 0, Qt.AlignmentFlag.AlignTop)
        summary_layout.addLayout(summary_top)

        separator = QFrame()
        separator.setObjectName("projectSeparator")
        separator.setFrameShape(QFrame.Shape.NoFrame)
        separator.setFixedHeight(1)
        summary_layout.addWidget(separator)

        details_grid = QGridLayout()
        details_grid.setContentsMargins(0, 0, 0, 0)
        details_grid.setVerticalSpacing(4)
        details_grid.setHorizontalSpacing(10)
        details_grid.setColumnStretch(1, 1)
        self.val_machine = self._add_summary_value(details_grid, 0, "Machine")
        self.val_tool_change = self._add_summary_value(details_grid, 1, "Tool change")
        self.val_target = self._add_summary_value(details_grid, 2, "Reduction")
        summary_layout.addLayout(details_grid)

        counts_layout = QHBoxLayout()
        counts_layout.setSpacing(8)
        self.val_before_count, self.val_after_count, self.val_activities_count = (
            self._add_metric(counts_layout, label)
            for label in ("Baseline", "Verified", "Activities")
        )
        summary_layout.addLayout(counts_layout)

        notes_grid = QGridLayout()
        notes_grid.setContentsMargins(0, 0, 0, 0)
        notes_grid.setHorizontalSpacing(10)
        self.val_notes = self._add_summary_value(notes_grid, 0, "Notes")
        self.val_notes.setMaximumHeight(40)
        summary_layout.addLayout(notes_grid)

        self.btn_set_active = QPushButton("Set as active project")
        self.btn_set_active.setObjectName("primaryBtn")
        self.btn_set_active.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_set_active.setMinimumHeight(38)
        self.btn_set_active.clicked.connect(self._on_set_active_project)
        self.btn_set_active.setEnabled(False)
        summary_layout.addWidget(self.btn_set_active)
        self.details_layout.addWidget(summary_card, 2)
        main_layout.addWidget(self.details_container)

        repository_card = QFrame()
        repository_card.setObjectName("card")
        repository_card.setFrameShape(QFrame.Shape.NoFrame)
        repository_layout = QVBoxLayout(repository_card)
        repository_layout.setContentsMargins(14, 12, 14, 12)
        repository_layout.setSpacing(8)

        self.repository_header = QBoxLayout(
            QBoxLayout.Direction.LeftToRight
        )
        repository_titles = QVBoxLayout()
        repository_titles.setSpacing(2)
        repository_heading = QLabel("Project repository")
        repository_heading.setObjectName("projectSectionTitle")
        repository_titles.addWidget(repository_heading)
        repository_description = QLabel(
            "Select a project to review it; double-click or use the action to open it."
        )
        repository_description.setObjectName("projectSectionDescription")
        repository_description.setWordWrap(True)
        repository_titles.addWidget(repository_description)
        self.repository_header.addLayout(repository_titles, 1)

        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(8)
        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.clicked.connect(self.load_projects)
        btn_bar.addWidget(self.btn_refresh)

        self.btn_demo_videos = QPushButton("Generate demo videos")
        self.btn_demo_videos.setObjectName("accentBtn")
        self.btn_demo_videos.setToolTip(
            "Generate synthetic shop-floor videos and load the sample project."
        )
        self.btn_demo_videos.clicked.connect(self._on_generate_demo_videos)
        btn_bar.addWidget(self.btn_demo_videos)
        btn_bar.addStretch()

        self.btn_delete = QPushButton("Delete project")
        self.btn_delete.setObjectName("dangerBtn")
        self.btn_delete.setEnabled(False)
        self.btn_delete.clicked.connect(self._on_delete_project)
        btn_bar.addWidget(self.btn_delete)
        self.repository_header.addLayout(btn_bar)
        repository_layout.addLayout(self.repository_header)

        self.table_projects = QTableWidget()
        self.table_projects.setObjectName("projectRepositoryTable")
        self.table_projects.setMinimumHeight(74)
        self.table_projects.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Ignored
        )
        self.table_projects.setColumnCount(6)
        self.table_projects.setHorizontalHeaderLabels([
            "ID", "Project title", "Machine", "Tool change", "Target", "Created"
        ])
        self.table_projects.setWordWrap(False)
        self.table_projects.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.table_projects.setHorizontalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)
        self.table_projects.setVerticalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)
        self.table_projects.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_projects.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table_projects.setAlternatingRowColors(True)
        self.table_projects.setShowGrid(False)
        self.table_projects.verticalHeader().setVisible(False)
        self.table_projects.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.table_projects.verticalHeader().setDefaultSectionSize(38)
        self.table_projects.horizontalHeader().setMinimumHeight(38)
        self.table_projects.horizontalHeader().setDefaultAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        for column, width in ((0, 50), (2, 160), (3, 150), (4, 84), (5, 104)):
            self.table_projects.setColumnWidth(column, width)
            self.table_projects.horizontalHeader().setSectionResizeMode(
                column, QHeaderView.ResizeMode.Fixed
            )
        self.table_projects.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self.table_projects.itemSelectionChanged.connect(self._on_table_row_selected)
        self.table_projects.doubleClicked.connect(self._on_set_active_project)

        self.empty_state = QLabel(
            "No projects yet\nCreate a study above to begin organizing changeover work."
        )
        self.empty_state.setObjectName("projectEmptyState")
        self.empty_state.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_state.setWordWrap(True)
        self.empty_state.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.table_stack = QStackedLayout()
        self.table_stack.addWidget(self.table_projects)
        self.table_stack.addWidget(self.empty_state)
        table_container = QWidget()
        table_container.setLayout(self.table_stack)
        repository_layout.addWidget(table_container, 1)

        main_layout.addWidget(repository_card, 1)
        self._update_responsive_layout()

    @staticmethod
    def _form_field(text: str, control: QWidget) -> QWidget:
        field = QWidget()
        field_layout = QHBoxLayout(field)
        field_layout.setContentsMargins(0, 0, 0, 0)
        field_layout.setSpacing(8)
        label = QLabel(text)
        label.setObjectName("projectFieldLabel")
        label.setBuddy(control)
        label.setWordWrap(False)
        label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        label.setFixedWidth(max(58, label.fontMetrics().horizontalAdvance(text) + 4))
        field_layout.addWidget(label)
        field_layout.addWidget(control, 1)
        return field

    @staticmethod
    def _add_summary_value(layout: QGridLayout, row: int, title: str) -> QLabel:
        label = QLabel(title)
        label.setObjectName("projectSummaryLabel")
        label.setMinimumWidth(0)
        label.setMaximumWidth(110)
        label.setWordWrap(False)
        value = QLabel("—")
        value.setObjectName("projectSummaryValue")
        value.setWordWrap(True)
        value.setMinimumWidth(0)
        layout.addWidget(label, row, 0, Qt.AlignmentFlag.AlignTop)
        layout.addWidget(value, row, 1)
        return value

    @staticmethod
    def _add_metric(layout: QHBoxLayout, title: str) -> QLabel:
        metric = QFrame()
        metric.setObjectName("projectMetric")
        metric_layout = QVBoxLayout(metric)
        metric_layout.setContentsMargins(8, 6, 8, 6)
        metric_layout.setSpacing(2)
        label = QLabel(title)
        label.setObjectName("projectMetricLabel")
        value = QLabel("0")
        value.setObjectName("projectMetricValue")
        value.setAccessibleName(title)
        metric_layout.addWidget(label)
        metric_layout.addWidget(value)
        layout.addWidget(metric, 1)
        return value

    def _update_responsive_layout(self):
        """Stack project creation and overview cards when the tab is narrow."""
        stacked = self.width() < self.STACK_LAYOUT_WIDTH
        direction = (
            QBoxLayout.Direction.TopToBottom
            if stacked
            else QBoxLayout.Direction.LeftToRight
        )
        if self.details_layout.direction() != direction:
            self.details_layout.setDirection(direction)
            self.details_layout.invalidate()
            self.details_container.updateGeometry()
        repository_direction = (
            QBoxLayout.Direction.TopToBottom
            if self.width() < self.REPOSITORY_HEADER_STACK_WIDTH
            else QBoxLayout.Direction.LeftToRight
        )
        if self.repository_header.direction() != repository_direction:
            self.repository_header.setDirection(repository_direction)
            self.repository_header.invalidate()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_responsive_layout()

    def load_projects(self):
        """Fetch all projects from SQLite database and populate table."""
        projects = self.db.get_all_projects()
        preferred_project_id = self.active_project_id
        self.table_projects.blockSignals(True)

        try:
            self.table_projects.setRowCount(0)
            for row_idx, project in enumerate(projects):
                self.table_projects.insertRow(row_idx)

                items = (
                    QTableWidgetItem(str(project["id"])),
                    QTableWidgetItem(project["name"]),
                    QTableWidgetItem(project.get("machine_name") or "—"),
                    QTableWidgetItem(
                        f"{project.get('from_die') or 'Old'} → "
                        f"{project.get('to_die') or 'New'}"
                    ),
                    QTableWidgetItem(
                        f"{project.get('target_reduction_pct', 50.0):.1f}%"
                    ),
                    QTableWidgetItem(str(project.get("created_at") or "")[:10]),
                )
                items[1].setData(Qt.ItemDataRole.UserRole, project["id"])
                for column, item in enumerate(items):
                    item.setToolTip(item.text())
                    self.table_projects.setItem(row_idx, column, item)

                for column in (0, 4, 5):
                    items[column].setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        finally:
            self.table_projects.blockSignals(False)

        if not projects:
            self.table_stack.setCurrentWidget(self.empty_state)
            self._clear_project_selection()
            return

        self.table_stack.setCurrentWidget(self.table_projects)
        selected_project_id = next(
            (project["id"] for project in projects if project["id"] == preferred_project_id),
            projects[0]["id"],
        )
        selected_row = next(
            row for row in range(self.table_projects.rowCount())
            if int(self.table_projects.item(row, 0).text()) == selected_project_id
        )
        self.table_projects.blockSignals(True)
        self.table_projects.setCurrentCell(selected_row, 0)
        self.table_projects.selectRow(selected_row)
        self.table_projects.blockSignals(False)
        self._select_project_by_id(selected_project_id)

    def _clear_project_selection(self):
        """Reset the overview and actions when the repository has no projects."""
        self.active_project_id = None
        self.lbl_card_title.setText("No projects yet")
        self.lbl_card_title.setToolTip("")
        self.lbl_project_status.setText("No selection")
        self.val_machine.setText("—")
        self.val_tool_change.setText("—")
        self.val_target.setText("—")
        self.val_before_count.setText("0")
        self.val_after_count.setText("0")
        self.val_activities_count.setText("0")
        self.val_notes.setText("—")
        self.val_before_count.setToolTip("")
        self.val_after_count.setToolTip("")
        self.val_activities_count.setToolTip("")
        self.val_notes.setToolTip("")
        self.btn_set_active.setEnabled(False)
        self.btn_delete.setEnabled(False)

    def _select_project_by_id(self, project_id: int):
        """Update summary pane with selected project details."""
        p = self.db.get_project(project_id)
        if not p:
            return

        self.active_project_id = project_id
        self.lbl_project_status.setText("Selected")
        self.lbl_card_title.setText(p["name"])
        self.lbl_card_title.setToolTip(p["name"])
        self.val_machine.setText(p.get("machine_name") or "N/A")

        from_d = p.get("from_die") or "—"
        to_d = p.get("to_die") or "—"
        self.val_tool_change.setText(f"{from_d} → {to_d}")

        tgt = p.get("target_reduction_pct", 50.0)
        self.val_target.setText(f"≥ {tgt:.1f}%")
        self.val_target.setToolTip(f"{tgt:.1f}% setup reduction target")

        # Query counts
        before_trials = self.db.get_trials_by_project(project_id, phase="BEFORE")
        after_trials = self.db.get_trials_by_project(project_id, phase="AFTER")
        activities = self.db.get_standard_activities(project_id)

        self.val_before_count.setText(str(len(before_trials)))
        self.val_after_count.setText(str(len(after_trials)))
        self.val_activities_count.setText(str(len(activities)))
        notes = p.get("notes") or "No notes provided."
        self.val_notes.setText(
            notes if len(notes) <= 72 else f"{notes[:69].rstrip()}..."
        )

        for value in (
            self.val_machine,
            self.val_tool_change,
            self.val_notes,
        ):
            value.setToolTip(value.text())
        self.val_before_count.setToolTip(
            f"{len(before_trials)} baseline video trial(s)"
        )
        self.val_after_count.setToolTip(
            f"{len(after_trials)} verification video trial(s)"
        )
        self.val_activities_count.setToolTip(
            f"{len(activities)} standardized activities"
        )
        self.val_notes.setToolTip(notes)

        self.btn_set_active.setEnabled(True)
        self.btn_delete.setEnabled(True)

        for row in range(self.table_projects.rowCount()):
            item = self.table_projects.item(row, 0)
            if item and int(item.text()) == project_id and row != self.table_projects.currentRow():
                self.table_projects.blockSignals(True)
                self.table_projects.setCurrentCell(row, 0)
                self.table_projects.selectRow(row)
                self.table_projects.blockSignals(False)
                break

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
