from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFrame, QGraphicsDropShadowEffect, QMenu, QLabel, QScrollArea, QMenu, QSizePolicy
from PySide6.QtCore import Qt, QPoint, Signal, QTimer, QEvent, QRect
from PySide6.QtGui import QFont, QColor, QCursor, QGuiApplication, QIcon
from i18n import t
try:
    from palworld_aio import constants
except ImportError:
    from .. import constants
class ScrollableContextMenu(QWidget):
    def __init__(self, parent=None, is_dark=True):
        super().__init__(parent)
        self.is_dark = is_dark
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameStyle(QFrame.NoFrame)
        self.content_widget = QWidget()
        self.layout = QVBoxLayout(self.content_widget)
        self.layout.setContentsMargins(8, 8, 8, 8)
        self.layout.setSpacing(0)
        self.content_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.content_widget.setMinimumWidth(200)
        self.scroll_area.setWidget(self.content_widget)
        main_layout.addWidget(self.scroll_area)
        self.setMaximumHeight(600)
        self.setMinimumWidth(220)
        self._update_theme()
    def _update_theme(self):
        if self.is_dark:
            bg = 'rgba(18,20,24,0.95)'
            border = 'rgba(125,211,252,0.2)'
            text_color = '#A6B8C8'
            hover_bg = 'rgba(125,211,252,0.1)'
            hover_color = '#7DD3FC'
        else:
            bg = 'rgba(240,245,255,1.0)'
            border = 'rgba(180,200,220,0.5)'
            text_color = '#000000'
            hover_bg = 'rgba(180,200,220,0.2)'
            hover_color = '#1e3a8a'
        self.setStyleSheet(f'\n            QWidget {{\n                background: {bg};\n                border: 1px solid {border};\n                border-radius: 10px;\n            }}\n            QScrollArea {{\n                border: none;\n                background: transparent;\n            }}\n            QFrame {{\n                background: transparent;\n            }}\n        ')
    def add_action(self, action):
        btn = QPushButton(action.text())
        btn.setFlat(True)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setMinimumHeight(36)
        btn.clicked.connect(action.trigger)
        if self.is_dark:
            btn.setStyleSheet('\n                QPushButton {\n                    background: transparent;\n                    border: none;\n                    padding: 8px 12px;\n                    text-align: left;\n                    color: #A6B8C8;\n                    border-radius: 6px;\n                }\n                QPushButton:hover {\n                    background: rgba(125,211,252,0.1);\n                    color: #7DD3FC;\n                }\n            ')
        else:
            btn.setStyleSheet('\n                QPushButton {\n                    background: transparent;\n                    border: none;\n                    padding: 8px 12px;\n                    text-align: left;\n                    color: #000000;\n                    border-radius: 6px;\n                }\n                QPushButton:hover {\n                    background: rgba(180,200,220,0.2);\n                    color: #1e3a8a;\n                }\n            ')
        self.layout.addWidget(btn)
    def addSeparator(self):
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFrameShadow(QFrame.Sunken)
        sep.setFixedHeight(1)
        if self.is_dark:
            sep.setStyleSheet('border-top: 1px solid rgba(125,211,252,0.2); margin: 4px 0px;')
        else:
            sep.setStyleSheet('border-top: 1px solid rgba(180,200,220,0.5); margin: 4px 0px;')
        self.layout.addWidget(sep)
    def update_theme(self, is_dark):
        self.is_dark = is_dark
        self._update_theme()
    def exec(self, pos):
        self.move(pos)
        self.show()
        self.raise_()
        self.activateWindow()