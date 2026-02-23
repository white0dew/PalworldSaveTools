from import_libs import *
from loading_manager import show_information, show_critical
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, QFileDialog, QApplication, QFrame, QGridLayout
from PySide6.QtGui import QIcon, QFont
from PySide6.QtCore import Qt, QTimer
def sav_to_gvasfile(filepath):
    with open(filepath, 'rb') as f:
        data = f.read()
        raw_gvas, save_type = decompress_sav_to_gvas(data)
    return GvasFile.read(raw_gvas, PALWORLD_TYPE_HINTS, SKP_PALWORLD_CUSTOM_PROPERTIES, allow_nan=True)
def gvasfile_to_sav(gvas_file, output_filepath):
    save_type = 50 if 'PalPalLocalWorldSaveGame' in gvas_file.header.save_game_class_name else 49
    save_type = 50 if 'Pal.PalworldSaveGame' in gvas_file.header.save_game_class_name or 'Pal.PalLocalWorldSaveGame' in gvas_file.header.save_game_class_name else 49
    sav_file = compress_gvas_to_sav(gvas_file.write(SKP_PALWORLD_CUSTOM_PROPERTIES), save_type)
    with open(output_filepath, 'wb') as f:
        f.write(sav_file)
def center_window(win):
    screen = QApplication.primaryScreen().availableGeometry()
    size = win.sizeHint()
    if not size.isValid():
        win.adjustSize()
        size = win.size()
    win.move((screen.width() - size.width()) // 2, (screen.height() - size.height()) // 2)
class SlotNumUpdaterApp(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(t('tool.slot_injector'))
        self.setFixedSize(560, 280)
        self.load_styles()
        try:
            if ICON_PATH and os.path.exists(ICON_PATH):
                self.setWindowIcon(QIcon(ICON_PATH))
        except Exception:
            pass
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(12)
        glass = QFrame()
        glass.setObjectName('glass')
        glass_layout = QVBoxLayout(glass)
        glass_layout.setContentsMargins(12, 12, 12, 12)
        glass_layout.setSpacing(12)
        title = QLabel(t('tool.slot_injector'))
        title.setFont(QFont('Segoe UI', 13, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        glass_layout.addWidget(title)
        input_grid = QGridLayout()
        input_grid.setSpacing(10)
        self.browse_button = QPushButton(t('browse'))
        self.browse_button.setFixedWidth(110)
        self.browse_button.clicked.connect(self.browse_file)
        self.file_label = QLabel(t('slot.select_level_sav'))
        self.file_entry = QLineEdit()
        self.file_entry.setPlaceholderText(t('slot.path_placeholder'))
        input_grid.addWidget(self.browse_button, 0, 0)
        input_grid.addWidget(self.file_label, 0, 1, alignment=Qt.AlignLeft)
        input_grid.addWidget(self.file_entry, 0, 2, 1, 2)
        self.pages_label = QLabel(t('slot.total_pages'))
        self.pages_entry = QLineEdit()
        self.pages_entry.setFixedWidth(90)
        self.pages_entry.setPlaceholderText('e.g.32')
        input_grid.addWidget(self.pages_label, 1, 1, alignment=Qt.AlignLeft)
        input_grid.addWidget(self.pages_entry, 1, 2, alignment=Qt.AlignLeft)
        self.slots_label = QLabel(t('slot.total_slots'))
        self.slots_entry = QLineEdit()
        self.slots_entry.setFixedWidth(90)
        self.slots_entry.setPlaceholderText('e.g.30')
        input_grid.addWidget(self.slots_label, 2, 1, alignment=Qt.AlignLeft)
        input_grid.addWidget(self.slots_entry, 2, 2, alignment=Qt.AlignLeft)
        input_grid.setColumnStretch(3, 1)
        glass_layout.addLayout(input_grid)
        glass_layout.addStretch(1)
        self.apply_button = QPushButton(t('slot.apply'))
        self.apply_button.setObjectName('ApplyButton')
        self.apply_button.clicked.connect(self.apply_slotnum_update)
        glass_layout.addWidget(self.apply_button, alignment=Qt.AlignCenter)
        main_layout.addWidget(glass)
        QTimer.singleShot(0, lambda: center_window(self))
    def showEvent(self, event):
        super().showEvent(event)
        if not event.spontaneous():
            self.activateWindow()
            self.raise_()
    def browse_file(self):
        file, _ = QFileDialog.getOpenFileName(self, t('slot.select_level_sav_title'), '', 'SAV Files(Level.sav)')
        if file:
            self.file_entry.setText(file)
            self.load_selected_save()
    def load_selected_save(self):
        fp = self.file_entry.text()
        if not fp.endswith('Level.sav'):
            show_critical(self, t('error.title'), t('slot.invalid_file'))
            return
        def task():
            return sav_to_gvasfile(fp)
        def on_finished(result):
            self.gvas_file = result
            show_information(self, t('slot.loaded_title'), t('slot.loaded_msg'))
        run_with_loading(on_finished, task)
    def apply_slotnum_update(self):
        filepath = self.file_entry.text()
        if not hasattr(self, 'gvas_file'):
            show_critical(self, t('error.title'), t('slot.load_first'))
            return
        try:
            pages = int(self.pages_entry.text())
            slots = int(self.slots_entry.text())
            if pages < 1 or slots < 1:
                raise ValueError
        except ValueError:
            show_critical(self, t('error.title'), t('slot.invalid_numbers'))
            return
        new_value = pages * slots
        gvas_file = self.gvas_file
        def task():
            container = gvas_file.properties['worldSaveData']['value'].get('CharacterContainerSaveData', {}).get('value', [])
            if not isinstance(container, list):
                raise ValueError(t('slot.invalid_structure'))
            PLAYER_SLOT_THRESHOLD = 960
            editable = [entry for entry in container if entry.get('value', {}).get('SlotNum', {}).get('value', 0) >= PLAYER_SLOT_THRESHOLD]
            total_players = len(editable)
            if total_players == 0:
                return ('no_entries', total_players)
            for entry in editable:
                entry['value']['SlotNum']['value'] = new_value
            backup_whole_directory(os.path.dirname(filepath), 'Backups/Slot Injector')
            gvasfile_to_sav(gvas_file, filepath)
            return ('success', total_players)
        def on_finished(result):
            status, count = result
            if status == 'no_entries':
                show_information(self, t('info.title'), t('slot.no_entries'))
            elif status == 'success':
                show_information(self, t('success.title'), t('slot.success_msg', count=count, new=new_value))
        run_with_loading(on_finished, task)
    def load_styles(self):
        user_cfg_path = os.path.join(get_src_directory(), 'data', 'configs', 'user.cfg')
        theme = 'dark'
        if os.path.exists(user_cfg_path):
            try:
                with open(user_cfg_path, 'r') as f:
                    data = json.load(f)
                theme = data.get('theme', 'dark')
            except:
                pass
        qss_path = os.path.join(get_src_directory(), 'data', 'gui', f'{theme}mode.qss')
        if os.path.exists(qss_path):
            with open(qss_path, 'r') as f:
                self.setStyleSheet(f.read())
def slot_injector():
    return SlotNumUpdaterApp()
if __name__ == '__main__':
    app = QApplication([])
    w = SlotNumUpdaterApp()
    w.show()
    sys.exit(app.exec())