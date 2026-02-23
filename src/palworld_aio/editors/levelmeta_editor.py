import os
import sys
import json
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSpinBox, QLineEdit, QWidget, QApplication, QFormLayout, QGroupBox
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QCursor
from i18n import t
from loading_manager import show_warning, show_critical
def get_src_path():
    env = os.environ.get('src_PATH')
    if env:
        return os.path.abspath(env)
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        src = os.path.join(exe_dir, 'src')
        if os.path.isdir(src):
            return src
    try:
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    except NameError:
        base = os.path.dirname(os.path.abspath(sys.argv[0]))
    if os.path.isdir(base):
        return base
    return os.path.abspath(base)
class LevelMetaEditorDialog(QDialog):
    def __init__(self, json_data, sav_path=None, parent=None):
        super().__init__(parent)
        self.json_data = json_data
        self.sav_path = sav_path
        self.settings = json_data['properties']['SaveData']['value']
        self.parent_window = parent if parent else None
        self.setWindowTitle(t('levelmeta.editor.title') if t else 'LevelMeta Settings Editor')
        self.setModal(True)
        self.setMinimumSize(500, 300)
        self._setup_ui()
        self._load_theme()
    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        form_group = QGroupBox(t('levelmeta.editor.settings_group') if t else 'LevelMeta Settings')
        form_layout = QFormLayout()
        form_group.setLayout(form_layout)
        world_name_label = QLabel(t('levelmeta.editor.world_name') if t else 'World Name:')
        world_name_label.setFont(QFont('Segoe UI', 10, QFont.Bold))
        self.world_name_editor = QLineEdit()
        self.world_name_editor.setText(self.settings.get('WorldName', {}).get('value', ''))
        form_layout.addRow(world_name_label, self.world_name_editor)
        host_name_label = QLabel(t('levelmeta.editor.host_name') if t else 'Host Player Name:')
        host_name_label.setFont(QFont('Segoe UI', 10, QFont.Bold))
        self.host_name_editor = QLineEdit()
        self.host_name_editor.setText(self.settings.get('HostPlayerName', {}).get('value', ''))
        form_layout.addRow(host_name_label, self.host_name_editor)
        host_level_label = QLabel(t('levelmeta.editor.host_level') if t else 'Host Player Level:')
        host_level_label.setFont(QFont('Segoe UI', 10, QFont.Bold))
        self.host_level_editor = QSpinBox()
        self.host_level_editor.setRange(1, 999)
        self.host_level_editor.setValue(self.settings.get('HostPlayerLevel', {}).get('value', 1))
        form_layout.addRow(host_level_label, self.host_level_editor)
        main_layout.addWidget(form_group)
        main_layout.addStretch(1)
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        save_btn = QPushButton(t('levelmeta.editor.save') if t else 'Save Changes')
        save_btn.setObjectName('dialogOption')
        save_btn.setCursor(QCursor(Qt.PointingHandCursor))
        save_btn.clicked.connect(self._save_to_file)
        btn_layout.addWidget(save_btn)
        cancel_btn = QPushButton(t('levelmeta.editor.cancel') if t else 'Cancel')
        cancel_btn.setObjectName('dialogCancel')
        cancel_btn.setCursor(QCursor(Qt.PointingHandCursor))
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        main_layout.addLayout(btn_layout)
    def _save_to_file(self):
        if not self.sav_path:
            show_warning(self, t('error.title') if t else 'Error', t('levelmeta.editor.no_file_path') if t else 'No file path provided. Cannot save.')
            return
        try:
            self.settings['WorldName']['value'] = self.world_name_editor.text()
            self.settings['HostPlayerName']['value'] = self.host_name_editor.text()
            self.settings['HostPlayerLevel']['value'] = self.host_level_editor.value()
            from palworld_aio.utils import json_to_sav
            json_to_sav(self.json_data, self.sav_path)
            self.accept()
        except Exception as e:
            import traceback
            error_details = f"{(t('levelmeta.editor.save_failed') if t else 'Failed to save:')}\n{str(e)}\n\n{traceback.format_exc()}"
            show_critical(self, t('error.title') if t else 'Error', error_details)
    def _load_theme(self):
        is_dark = self.parent_window.is_dark_mode if self.parent_window and hasattr(self.parent_window, 'is_dark_mode') else True
        base_path = get_src_path()
        theme_file = 'darkmode.qss' if is_dark else 'lightmode.qss'
        theme_path = os.path.join(base_path, 'data', 'gui', theme_file)
        if os.path.exists(theme_path):
            try:
                with open(theme_path, 'r', encoding='utf-8') as f:
                    qss_content = f.read()
                    self.setStyleSheet(qss_content)
                return
            except Exception as e:
                print(f'Failed to load theme {theme_file}: {e}')
        self._apply_fallback_styles(is_dark)
    def _apply_fallback_styles(self, is_dark):
        if is_dark:
            bg_gradient = 'qlineargradient(spread:pad,x1:0.0,y1:0.0,x2:1.0,y2:1.0,stop:0 #07080a,stop:0.5 #08101a,stop:1 #05060a)'
            txt_color = '#dfeefc'
        else:
            bg_gradient = 'qlineargradient(spread:pad,x1:0.0,y1:0.0,x2:1.0,y2:1.0,stop:0 #e6ecef,stop:0.5 #bdd5df,stop:1 #a7c9da)'
            txt_color = '#000000'
        self.setStyleSheet(f"\n            QDialog {{\n                background: {bg_gradient};\n                color: {txt_color};\n                font-family: 'Segoe UI', Roboto, Arial;\n            }}\n            QLabel {{\n                color: {txt_color};\n                font-family: 'Segoe UI', Roboto, Arial;\n            }}\n            QGroupBox {{\n                color: {txt_color};\n                font-family: 'Segoe UI', Roboto, Arial;\n                border: 1px solid #256aa0;\n                border-radius: 5px;\n                margin-top: 10px;\n                padding-top: 10px;\n            }}\n            QGroupBox::title {{\n                subcontrol-origin: margin;\n                left: 10px;\n                padding: 0 5px;\n            }}\n            QPushButton {{\n                background: #256aa0;\n                color: white;\n                border: none;\n                padding: 8px 16px;\n                border-radius: 4px;\n                font-family: 'Segoe UI', Roboto, Arial;\n                font-size: 11px;\n            }}\n            QPushButton:hover {{\n                background: #2a7fc0;\n            }}\n            QPushButton:pressed {{\n                background: #1e5a8a;\n            }}\n            QLineEdit {{\n                background: #1a1f2a;\n                color: {txt_color};\n                border: 1px solid #256aa0;\n                border-radius: 3px;\n                padding: 6px;\n            }}\n            QLineEdit:focus {{\n                border: 1px solid #7DD3FC;\n            }}\n            QSpinBox {{\n                background: #1a1f2a;\n                color: {txt_color};\n                border: 1px solid #256aa0;\n                border-radius: 3px;\n                padding: 4px;\n            }}\n        ")
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.reject()
        else:
            super().keyPressEvent(event)
def edit_levelmeta_settings(json_data, sav_path=None, parent=None):
    dialog = LevelMetaEditorDialog(json_data, sav_path, parent)
    result = dialog.exec()
    if result == QDialog.Accepted:
        return True
    return None
if __name__ == '__main__':
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    json_path, _ = QFileDialog.getOpenFileName(None, 'Select LevelMeta.json', '', 'JSON Files (*.json)')
    if not json_path:
        print('No file selected')
        exit(0)
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    result = edit_levelmeta_settings(data, json_path)
    if result:
        print('Settings saved successfully!')