"""
UI Module
"""
from .project_window import ProjectWindow
from .theme import get_stylesheet, COLOR_PALETTE, SPACING, RADIUS

# 旧UIもインポート可能にしておく
try:
    from .main_window_old import MainWindow as MainWindowOld
except ImportError:
    MainWindowOld = None

__all__ = [
    'ProjectWindow',
    'MainWindowOld',
    'get_stylesheet',
    'COLOR_PALETTE',
    'SPACING',
    'RADIUS'
]
