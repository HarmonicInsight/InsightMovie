"""
UI Module
"""
from .project_window import ProjectWindow

# 旧UIもインポート可能にしておく
try:
    from .main_window_old import MainWindow as MainWindowOld
except ImportError:
    MainWindowOld = None

__all__ = ['ProjectWindow', 'MainWindowOld']
