"""
SMED Studio - Desktop Application Main Entry Point
Single-Minute Exchange of Die Video & Kaizen Analyzer (Offline Desktop Edition)

Features:
- Offline SQLite3 Database Storage & Thread-Safe Connection Management
- 4-Stage SMED Engineering Workflow (Projects -> Video Logger -> Pareto Matrix -> Comparative Dashboard)
- Synthetic Shop-Floor Video Simulation Generator (OpenCV)
- Offline Database Backup & Restore Menu
- Multi-Sheet Excel & Executive PDF Report Exporter
"""

import sys
import os
import shutil
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QFont, QKeySequence
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout,
    QHBoxLayout, QLabel, QPushButton, QStatusBar, QMessageBox,
    QDialog, QTextBrowser, QFileDialog
)

from database.db_manager import DatabaseManager, get_db
from database.seed_data import seed_sample_project
from ui.styles import MODERN_DARK_INDUSTRIAL_QSS, COLORS
from ui.project_tab import ProjectTab
from ui.video_logger_tab import VideoLoggerTab
from ui.pareto_kaizen_tab import ParetoKaizenTab
from ui.dashboard_tab import DashboardTab
from utils.demo_video_generator import generate_and_seed_demo_project
from utils.report_exporter import export_project_to_excel, export_project_to_pdf


class MainWindow(QMainWindow):
    """Main Application Window for SMED Studio."""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SMED Studio - Single-Minute Exchange of Die Video & Kaizen Analyzer")
        self.resize(1340, 860)
        self.setMinimumSize(1080, 720)

        # Initialize SQLite database
        self.db = get_db("smed_local.db")

        self._init_ui()
        self._init_menu()
        self._check_initial_data()

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(12, 10, 12, 10)
        main_layout.setSpacing(10)

        # Top Header Branding Bar
        header = QWidget()
        header.setStyleSheet("background-color: #0B0F17; border-radius: 8px; padding: 6px 14px;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(8, 6, 8, 6)

        title_layout = QVBoxLayout()
        title_layout.setSpacing(2)
        app_title = QLabel("⚙ SMED STUDIO  <span style='color:#0EA5E9; font-weight:400;'>| Industrial Kaizen Video Analyzer</span>")
        app_title.setStyleSheet("font-size: 17px; font-weight: 800; color: #F8FAFC;")
        title_layout.addWidget(app_title)

        tagline = QLabel("Shigeo Shingo SMED Methodology • Baseline Multi-Video Dual-Stopwatch Observation • Target ≥ 50% Setup Reduction")
        tagline.setStyleSheet("font-size: 11px; color: #64748B; font-weight: 500;")
        title_layout.addWidget(tagline)
        header_layout.addLayout(title_layout)

        header_layout.addStretch()

        # Offline & Target Badges
        offline_badge = QLabel("● 100% OFFLINE LOCAL")
        offline_badge.setStyleSheet(
            "background-color: rgba(16, 185, 129, 0.15); color: #34D399; font-size: 11px; "
            "font-weight: 700; border: 1px solid #059669; border-radius: 4px; padding: 4px 8px;"
        )
        header_layout.addWidget(offline_badge)

        target_badge = QLabel("TARGET: < 10 MIN (SMED)")
        target_badge.setStyleSheet(
            "background-color: rgba(14, 165, 233, 0.15); color: #38BDF8; font-size: 11px; "
            "font-weight: 700; border: 1px solid #0284C7; border-radius: 4px; padding: 4px 8px;"
        )
        header_layout.addWidget(target_badge)

        main_layout.addWidget(header)

        # Tab Navigation Widget
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)

        # Tab 1: Project Setup
        self.tab_projects = ProjectTab(db=self.db)
        self.tabs.addTab(self.tab_projects, "  1. Projects & Repository  ")

        # Tab 2: Multi-Video Dual-Stopwatch Logger
        self.tab_logger = VideoLoggerTab(db=self.db)
        self.tabs.addTab(self.tab_logger, "  2. Multi-Video Dual-Stopwatch Logger  ")

        # Tab 3: Pareto & Kaizen Matrix
        self.tab_pareto = ParetoKaizenTab(db=self.db)
        self.tabs.addTab(self.tab_pareto, "  3. Pareto & Kaizen Matrix  ")

        # Tab 4: Before vs After Dashboard & Report
        self.tab_dashboard = DashboardTab(db=self.db)
        self.tabs.addTab(self.tab_dashboard, "  4. Before vs. After Dashboard & Report  ")

        main_layout.addWidget(self.tabs)

        # Wire Signals across all 4 Tabs
        self.tab_projects.project_selected.connect(self._on_project_activated)

        # When logger data changes, refresh both Pareto and Dashboard
        self.tab_logger.data_changed.connect(self.tab_pareto.refresh_data)
        self.tab_logger.data_changed.connect(self.tab_dashboard.refresh_analytics)

        # When Kaizen solutions are updated, refresh dashboard
        self.tab_pareto.kaizen_updated.connect(self.tab_dashboard.refresh_analytics)
        self.tab_pareto.kaizen_updated.connect(
            lambda: self.status.showMessage("Kaizen matrix countermeasures saved to database.", 4000)
        )

        # When reports are exported
        self.tab_dashboard.report_exported.connect(
            lambda p: self.status.showMessage(f"Report exported: {os.path.basename(p)}", 5000)
        )

        self.tabs.currentChanged.connect(self._on_tab_changed)

        # Status Bar
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("SMED Studio Ready. Database: smed_local.db connected.")

    def _init_menu(self):
        """Initialize comprehensive top Menu Bar for offline database and export operations."""
        menubar = self.menuBar()

        # ---------------------------------------------------------------------
        # File Menu
        # ---------------------------------------------------------------------
        file_menu = menubar.addMenu("&File")

        action_demo = file_menu.addAction("🎬 Generate & Load Sample Project + Demo Videos")
        action_demo.setShortcut("Ctrl+D")
        action_demo.triggered.connect(self._generate_load_demo_videos)

        file_menu.addSeparator()

        action_backup = file_menu.addAction("💾 Backup Local Database (.db)...")
        action_backup.setShortcut("Ctrl+B")
        action_backup.triggered.connect(self._backup_database)

        action_restore = file_menu.addAction("📂 Restore Database from Backup...")
        action_restore.setShortcut("Ctrl+R")
        action_restore.triggered.connect(self._restore_database)

        file_menu.addSeparator()

        action_export_excel = file_menu.addAction("📊 Export Active Project to Excel (.xlsx)")
        action_export_excel.setShortcut("Ctrl+E")
        action_export_excel.triggered.connect(self._export_excel)

        action_export_pdf = file_menu.addAction("📑 Export Active Project to Executive PDF (.pdf)")
        action_export_pdf.setShortcut("Ctrl+P")
        action_export_pdf.triggered.connect(self._export_pdf)

        file_menu.addSeparator()

        action_exit = file_menu.addAction("E&xit")
        action_exit.setShortcut("Ctrl+Q")
        action_exit.triggered.connect(self.close)

        # ---------------------------------------------------------------------
        # Help & Shortcuts Menu
        # ---------------------------------------------------------------------
        help_menu = menubar.addMenu("&Help & Shortcuts")

        action_shortcuts_guide = help_menu.addAction("⌨ Keyboard Shortcuts & SMED Guide")
        action_shortcuts_guide.setShortcut("F1")
        action_shortcuts_guide.triggered.connect(self._show_shortcuts_and_guide)

        help_menu.addSeparator()

        action_about = help_menu.addAction("ℹ About SMED Studio")
        action_about.triggered.connect(self._show_about)

    def _check_initial_data(self):
        """If database has projects, auto-select the first project into Tabs 2, 3, and 4."""
        projects = self.db.get_all_projects()
        if projects:
            first_id = projects[0]["id"]
            self.tab_logger.set_project(first_id)
            self.tab_pareto.set_project(first_id)
            self.tab_dashboard.set_project(first_id)

    def _on_tab_changed(self, index: int):
        """When switching to Tab 3 (Pareto) or Tab 4 (Dashboard), refresh data automatically."""
        if index == 2:
            self.tab_pareto.refresh_data()
        elif index == 3:
            self.tab_dashboard.refresh_analytics()

    def _on_project_activated(self, project_id: int):
        """Switch to Video Logger tab when project is selected and synchronize all tabs."""
        self.tab_logger.set_project(project_id)
        self.tab_pareto.set_project(project_id)
        self.tab_dashboard.set_project(project_id)
        self.tabs.setCurrentIndex(1)  # Switch to Video Logger
        project = self.db.get_project(project_id)
        name = project["name"] if project else f"Project #{project_id}"
        self.status.showMessage(f"Active Project set to: {name}", 5000)

    def _get_active_project_id(self) -> int:
        """Helper to get current active project ID from logger or projects tab."""
        return self.tab_logger.active_project_id or self.tab_projects.active_project_id or 1

    def _generate_load_demo_videos(self):
        """Generate synthetic MP4 shop-floor simulation videos and seed sample project."""
        reply = QMessageBox.question(
            self,
            "Generate & Load Demo SMED Videos",
            "This will synthesize two shop-floor changeover videos (.mp4) in 'sample_videos/' "
            "with realistic industrial HUD overlays, and link them to the sample "
            "'Automotive Stamping Line 4' project.\n\n"
            "• BEFORE Trial: Baseline unoptimized die swap (40m simulated in 30s)\n"
            "• AFTER Trial: Kaizen verified quick-clamp die swap (13m simulated in 30s)\n\n"
            "Proceed with video generation?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.status.showMessage("Generating synthetic SMED demo videos in sample_videos/...", 10000)
                QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
                pid = generate_and_seed_demo_project(self.db, "sample_videos")
                QApplication.restoreOverrideCursor()

                self.tab_projects.load_projects()
                self._on_project_activated(pid)
                self.status.showMessage("Demo SMED videos generated and active in Video Logger!", 6000)

                QMessageBox.information(
                    self,
                    "Demo Simulation Ready",
                    "Demo SMED project & synthetic videos generated successfully!\n\n"
                    "Now active in Tab 2 (Video Logger):\n"
                    "• Press [Space] to Play/Pause video simulation\n"
                    "• Press [Left/Right] to scrub timeline\n"
                    "• Press [S] to start / lap micro-activities\n"
                    "• Switch to Tab 3 for Pareto Kaizen & Tab 4 for Reduction Report."
                )
            except Exception as e:
                QApplication.restoreOverrideCursor()
                QMessageBox.critical(self, "Error", f"Failed to generate demo videos:\n{str(e)}")

    def _backup_database(self, destination_path: str = None) -> str:
        """
        Create a safe offline backup of smed_local.db via shutil.copy2.
        Flushes and checkpoints WAL beforehand to ensure 100% database integrity.
        """
        if not destination_path:
            db_name = os.path.basename(self.db.db_path)
            default_name = f"smed_backup_{db_name}"
            dest_path, _ = QFileDialog.getSaveFileName(
                self,
                "Backup Local Database",
                default_name,
                "SQLite Database (*.db);;All Files (*.*)",
            )
            if not dest_path:
                return None
        else:
            dest_path = destination_path

        try:
            # Checkpoint WAL mode before copying to disk
            with self.db.get_connection() as conn:
                conn.commit()
                try:
                    conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
                except Exception:
                    pass

            # Primary mechanism: shutil.copy2 as specified in Phase 5 requirements
            if os.path.exists(self.db.db_path):
                dest_dir = os.path.dirname(os.path.abspath(dest_path))
                if dest_dir:
                    os.makedirs(dest_dir, exist_ok=True)
                shutil.copy2(self.db.db_path, dest_path)
                bkp_file = os.path.abspath(dest_path)
            else:
                # Fallback to SQLite native online backup API
                bkp_file = self.db.backup_database(dest_path)

            self.status.showMessage(f"Database backed up to: {os.path.basename(bkp_file)}", 5000)
            if not destination_path:
                QMessageBox.information(
                    self,
                    "Backup Successful",
                    f"SQLite database successfully backed up to:\n\n{bkp_file}\n\n"
                    f"File Size: {os.path.getsize(bkp_file):,} bytes"
                )
            return bkp_file
        except Exception as e:
            if not destination_path:
                QMessageBox.critical(self, "Backup Error", f"Failed to backup database:\n{str(e)}")
                return None
            else:
                raise e

    def _restore_database(self, source_path: str = None) -> bool:
        """Restore database from an existing .db backup file."""
        if not source_path:
            src_path, _ = QFileDialog.getOpenFileName(
                self,
                "Restore Database from Backup",
                "",
                "SQLite Database (*.db);;All Files (*.*)",
            )
            if not src_path:
                return False

            reply = QMessageBox.warning(
                self,
                "Confirm Database Restore",
                f"WARNING: Restoring will overwrite all current data in 'smed_local.db' "
                f"with the contents of:\n\n{src_path}\n\n"
                "This action cannot be undone. Are you sure you want to proceed?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return False
        else:
            src_path = source_path

        try:
            self.db.restore_database(src_path)
            self.tab_projects.load_projects()
            self._check_initial_data()
            self.tab_pareto.refresh_data()
            self.tab_dashboard.refresh_analytics()

            self.status.showMessage("Database successfully restored from backup!", 5000)
            if not source_path:
                QMessageBox.information(
                    self,
                    "Restore Successful",
                    "Database has been successfully restored!\nAll projects and trials have been reloaded."
                )
            return True
        except Exception as e:
            if not source_path:
                QMessageBox.critical(self, "Restore Error", f"Failed to restore database:\n{str(e)}")
                return False
            else:
                raise e

    def _export_excel(self, destination_path: str = None) -> str:
        """Export active project to multi-sheet formatted Excel workbook."""
        pid = self._get_active_project_id()
        project = self.db.get_project(pid)
        name = project["name"] if project else f"Project_{pid}"
        clean_name = "".join([c if c.isalnum() else "_" for c in name])[:30]

        if not destination_path:
            dest_path, _ = QFileDialog.getSaveFileName(
                self,
                "Export Project to Excel",
                f"SMED_Report_{clean_name}.xlsx",
                "Excel Workbook (*.xlsx);;All Files (*.*)",
            )
            if not dest_path:
                return None
        else:
            dest_path = destination_path

        try:
            out = export_project_to_excel(self.db, pid, dest_path)
            self.status.showMessage(f"Excel report saved: {os.path.basename(out)}", 5000)
            if not destination_path:
                QMessageBox.information(
                    self,
                    "Excel Export Complete",
                    f"Multi-sheet SMED report exported successfully to:\n\n{out}\n\n"
                    "Includes: Executive Summary, Activity Comparison, and Raw Trials Log."
                )
            return out
        except Exception as e:
            if not destination_path:
                QMessageBox.critical(self, "Export Error", f"Failed to export Excel report:\n{str(e)}")
                return None
            else:
                raise e

    def _export_pdf(self, destination_path: str = None) -> str:
        """Export active project to formatted printable PDF report."""
        pid = self._get_active_project_id()
        project = self.db.get_project(pid)
        name = project["name"] if project else f"Project_{pid}"
        clean_name = "".join([c if c.isalnum() else "_" for c in name])[:30]

        if not destination_path:
            dest_path, _ = QFileDialog.getSaveFileName(
                self,
                "Export Executive PDF Report",
                f"SMED_Executive_Report_{clean_name}.pdf",
                "PDF Document (*.pdf);;All Files (*.*)",
            )
            if not dest_path:
                return None
        else:
            dest_path = destination_path

        try:
            out = export_project_to_pdf(self.db, pid, dest_path)
            self.status.showMessage(f"PDF report saved: {os.path.basename(out)}", 5000)
            if not destination_path:
                QMessageBox.information(
                    self,
                    "PDF Export Complete",
                    f"Printable SMED executive report exported successfully to:\n\n{out}\n\n"
                    "Formatted for shop-floor management and Lean Champions."
                )
            return out
        except Exception as e:
            if not destination_path:
                QMessageBox.critical(self, "Export Error", f"Failed to export PDF report:\n{str(e)}")
                return None
            else:
                raise e

    def _show_shortcuts_and_guide(self):
        """Show unified Hotkeys & SMED 4-Step Methodology Guide Dialog."""
        dlg = QDialog(self)
        dlg.setWindowTitle("SMED Studio - Keyboard Shortcuts & Engineering Guide")
        dlg.resize(740, 560)
        dlg_layout = QVBoxLayout(dlg)
        dlg_layout.setContentsMargins(16, 16, 16, 16)
        dlg_layout.setSpacing(12)

        browser = QTextBrowser()
        browser.setHtml("""
            <div style='font-family: -apple-system, Segoe UI, Arial; color: #F8FAFC;'>
                <h2 style='color: #38BDF8; margin-top:0;'>⚙ Video Logger Keyboard Hotkeys</h2>
                <table style='width: 100%; border-collapse: collapse; margin-bottom: 20px;'>
                    <tr style='background-color: #1E293B;'>
                        <th style='padding: 8px; border: 1px solid #334155; text-align: left; color:#38BDF8;'>Key Shortcut</th>
                        <th style='padding: 8px; border: 1px solid #334155; text-align: left; color:#38BDF8;'>Action & Behavior</th>
                    </tr>
                    <tr>
                        <td style='padding: 8px; border: 1px solid #334155;'><b>Space</b></td>
                        <td style='padding: 8px; border: 1px solid #334155;'>Play / Pause Video Playback</td>
                    </tr>
                    <tr style='background-color: #162032;'>
                        <td style='padding: 8px; border: 1px solid #334155;'><b>Left Arrow (◀)</b></td>
                        <td style='padding: 8px; border: 1px solid #334155;'>Seek Backward -1.0 Second in Video</td>
                    </tr>
                    <tr>
                        <td style='padding: 8px; border: 1px solid #334155;'><b>Right Arrow (▶)</b></td>
                        <td style='padding: 8px; border: 1px solid #334155;'>Seek Forward +1.0 Second in Video</td>
                    </tr>
                    <tr style='background-color: #162032;'>
                        <td style='padding: 8px; border: 1px solid #334155;'><b>S</b></td>
                        <td style='padding: 8px; border: 1px solid #334155;'><b>Start Activity / Lap Activity</b> (Continuous zero-gap micro-activity timing)</td>
                    </tr>
                    <tr>
                        <td style='padding: 8px; border: 1px solid #334155;'><b>I</b></td>
                        <td style='padding: 8px; border: 1px solid #334155;'><span style='color:#F87171;'><b>INTERNAL</b></span> Classification (Machine Stopped / Downtime)</td>
                    </tr>
                    <tr style='background-color: #162032;'>
                        <td style='padding: 8px; border: 1px solid #334155;'><b>E</b></td>
                        <td style='padding: 8px; border: 1px solid #334155;'><span style='color:#34D399;'><b>EXTERNAL</b></span> Classification (Machine Running / Production)</td>
                    </tr>
                    <tr>
                        <td style='padding: 8px; border: 1px solid #334155;'><b>Ctrl+D</b> / <b>Ctrl+B</b> / <b>Ctrl+R</b></td>
                        <td style='padding: 8px; border: 1px solid #334155;'>Generate Demo Videos / Backup Database / Restore Database</td>
                    </tr>
                    <tr style='background-color: #162032;'>
                        <td style='padding: 8px; border: 1px solid #334155;'><b>Ctrl+E</b> / <b>Ctrl+P</b></td>
                        <td style='padding: 8px; border: 1px solid #334155;'>Export to Excel (.xlsx) / Export to Executive PDF (.pdf)</td>
                    </tr>
                </table>

                <h2 style='color: #10B981;'>🏭 The 4-Step SMED Engineering Methodology</h2>
                <p>Formulated by <b>Dr. Shigeo Shingo</b> (Toyota Production System) to systematically reduce machine setup times from hours to under 10 minutes (single-digit minutes).</p>

                <div style='background-color: #1E293B; border-left: 4px solid #F59E0B; padding: 10px; margin-bottom: 12px; border-radius: 4px;'>
                    <b style='color: #F59E0B;'>The Golden SMED Cycle Boundary Rule:</b><br>
                    A changeover cycle strictly begins at the <b>Last Good Part of the Previous Tool</b> and officially finishes only when the <b>6th Consecutive OK Part of the New Tool</b> is stamped and quality-approved. This guarantees all trial-and-error adjustments are captured.
                </div>

                <h3 style='color: #38BDF8; margin-bottom: 4px;'>Step 1: Separate Internal from External Setup</h3>
                <ul>
                    <li><b style='color: #EF4444;'>Internal Setup:</b> Operations that can <i>only</i> be executed while the machine is shut down (e.g., unbolting die, hoisting tooling out).</li>
                    <li><b style='color: #10B981;'>External Setup:</b> Operations that <i>can</i> be performed while the machine is actively running production (e.g., retrieving new die, tool pre-staging, pre-heating).</li>
                </ul>

                <h3 style='color: #38BDF8; margin-bottom: 4px;'>Step 2: Convert Internal Activities to External</h3>
                <p>Move tool preparation, transport, pre-heating, and post-run cleanup outside the machine downtime window.</p>

                <h3 style='color: #38BDF8; margin-bottom: 4px;'>Step 3: Streamline All Remaining Setup (ECRS Kaizen)</h3>
                <p>Apply <b>Eliminate, Combine, Rearrange, and Simplify</b>:
                replace threaded bolts with quarter-turn pneumatic clamps, eliminate trial-and-error adjustments using hardened guide pins, and standardize shut heights.</p>

                <h3 style='color: #10B981; margin-bottom: 4px;'>Target Benchmark</h3>
                <p>Achieve <b>≥ 50% machine downtime reduction</b> driving toward the SMED goal of <b>&lt; 10 minutes</b>.</p>
            </div>
        """)
        dlg_layout.addWidget(browser)

        btn_close = QPushButton("Close")
        btn_close.clicked.connect(dlg.accept)
        dlg_layout.addWidget(btn_close, alignment=Qt.AlignmentFlag.AlignRight)
        dlg.exec()

    def _show_about(self):
        """Show information about SMED Studio desktop software."""
        QMessageBox.about(
            self,
            "About SMED Studio",
            "<h3>⚙ SMED Studio - Desktop Edition</h3>"
            "<p><b>Version 1.0.0 (100% Offline Standalone Edition)</b></p>"
            "<p>Built for Industrial Engineers, Continuous Improvement Leaders, and Lean Champions.</p>"
            "<hr style='border: 1px solid #334155;'>"
            "<p><b>Features:</b></p>"
            "<ul>"
            "<li>Multi-video dual-stopwatch shop-floor video observation</li>"
            "<li>Continuous zero-gap micro-activity logging & standardized dictionary</li>"
            "<li>Automated Pareto 80/20 vital-few bottleneck analysis</li>"
            "<li>ECRS Kaizen Matrix with automated time savings calculations</li>"
            "<li>Side-by-side Before vs. After comparative KPI dashboard</li>"
            "<li>Offline Excel (.xlsx) and printable Executive PDF (.pdf) exports</li>"
            "<li>Built-in synthetic shop-floor simulation video generator</li>"
            "<li>Local SQLite3 backup & restore engine</li>"
            "</ul>"
            "<p style='color:#64748B;'>Engineered with Python 3, PyQt6, SQLite3, OpenCV, Matplotlib, Pandas, and ReportLab.</p>"
        )


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(MODERN_DARK_INDUSTRIAL_QSS)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
