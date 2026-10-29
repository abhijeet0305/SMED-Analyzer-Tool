"""
SMED Studio UI Package
High-contrast Dark Industrial User Interface components for PyQt6.
"""

from .styles import MODERN_DARK_INDUSTRIAL_QSS, COLORS
from .project_tab import ProjectTab
from .video_logger_tab import VideoLoggerTab
from .pareto_kaizen_tab import ParetoKaizenTab
from .dashboard_tab import DashboardTab

__all__ = [
    "MODERN_DARK_INDUSTRIAL_QSS",
    "COLORS",
    "ProjectTab",
    "VideoLoggerTab",
    "ParetoKaizenTab",
    "DashboardTab",
]
