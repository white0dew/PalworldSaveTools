from import_libs import *
from loading_manager import show_information, show_critical
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, QFileDialog, QApplication, QFrame, QGridLayout, QTableWidget, QTableWidgetItem, QHeaderView, QCheckBox, QAbstractItemView, QMessageBox, QSpinBox
from PySide6.QtGui import QIcon, QFont
from PySide6.QtCore import Qt, QTimer
from concurrent.futures import ThreadPoolExecutor
import os
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
def load_player_container_mapping(players_folder, valid_player_uids):
    player_containers = {}
    if not os.path.exists(players_folder):
        return player_containers
    player_files = [f for f in os.listdir(players_folder) if f.endswith('.sav') and '_dps' not in f and (f.replace('.sav', '').lower() in valid_player_uids)]
    if not player_files:
        return player_containers
    def load_player_file(filename):
        try:
            p_gvas = sav_to_gvasfile(os.path.join(players_folder, filename))
            p_prop = p_gvas.properties.get('SaveData', {}).get('value', {})
            p_uid_raw = filename.replace('.sav', '')
            p_uid = p_uid_raw.lower()
            p_box = p_prop.get('PalStorageContainerId', {}).get('value', {}).get('ID', {}).get('value')
            p_party = p_prop.get('OtomoCharacterContainerId', {}).get('value', {}).get('ID', {}).get('value')
            if p_box or p_party:
                return (p_uid, {'party_id': str(p_party).lower() if p_party else None, 'palbox_id': str(p_box).lower() if p_box else None})
        except:
            pass
        return None
    with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
        results = executor.map(load_player_file, player_files)
        for result in results:
            if result:
                player_containers[result[0]] = result[1]
    return player_containers
def get_player_info_from_save(gvas_file, players_folder=None):
    players = {}
    wsd = gvas_file.properties.get('worldSaveData', {}).get('value', {})
    valid_player_uids = set()
    guild_map = wsd.get('GroupSaveDataMap', {}).get('value', [])
    if isinstance(guild_map, list):
        for entry in guild_map:
            value = entry.get('value', {})
            group_type = value.get('GroupType', {}).get('value', {}).get('value', '')
            if group_type == 'EPalGroupType::Guild':
                raw_data = value.get('RawData', {}).get('value', {})
                players_list = raw_data.get('players', [])
                for p in players_list:
                    player_uid = p.get('player_uid', 'N/A')
                    player_uid_str = str(player_uid).replace('-', '').lower() if player_uid else 'N/A'
                    if player_uid_str != 'n/a':
                        valid_player_uids.add(player_uid_str)
    if isinstance(guild_map, list):
        for entry in guild_map:
            value = entry.get('value', {})
            group_type = value.get('GroupType', {}).get('value', {}).get('value', '')
            if group_type == 'EPalGroupType::Guild':
                raw_data = value.get('RawData', {}).get('value', {})
                guild_name = raw_data.get('guild_name', 'Unknown Guild')
                players_list = raw_data.get('players', [])
                for p in players_list:
                    player_uid = p.get('player_uid', 'N/A')
                    player_uid_str = str(player_uid).replace('-', '').lower() if player_uid else 'N/A'
                    player_info = p.get('player_info', {})
                    player_name = player_info.get('player_name', 'Unknown')
                    players[player_uid_str] = {'name': player_name, 'guild': guild_name, 'uid': player_uid_str, 'party_id': None, 'palbox_id': None}
    char_map = wsd.get('CharacterSaveParameterMap', {}).get('value', [])
    if isinstance(char_map, list):
        for entry in char_map:
            key = entry.get('key', {})
            value = entry.get('value', {})
            raw_data = value.get('RawData', {}).get('value', {})
            player_uid = key.get('PlayerUId', {}).get('value', 'N/A')
            player_uid_str = str(player_uid).replace('-', '').lower() if player_uid else 'N/A'
            obj = raw_data.get('object', {})
            sp = obj.get('SaveParameter', {})
            sp_val = sp.get('value', {})
            is_player = sp_val.get('IsPlayer', {}).get('value', False)
            nick_name = sp_val.get('NickName', {}).get('value', '')
            if player_uid_str == '00000000000000000000000000000001':
                continue
            if is_player and player_uid_str not in players:
                players[player_uid_str] = {'name': nick_name if nick_name else 'Unknown', 'guild': 'Unknown Guild', 'uid': player_uid_str, 'party_id': None, 'palbox_id': None}
            elif is_player and nick_name and (players.get(player_uid_str, {}).get('name') == 'Unknown'):
                players[player_uid_str]['name'] = nick_name
    if players_folder and valid_player_uids:
        container_mapping = load_player_container_mapping(players_folder, valid_player_uids)
        for uid, containers in container_mapping.items():
            if uid in players:
                players[uid]['party_id'] = containers.get('party_id')
                players[uid]['palbox_id'] = containers.get('palbox_id')
    return players
def get_player_containers(gvas_file, players_folder=None):
    players = get_player_info_from_save(gvas_file, players_folder)
    wsd = gvas_file.properties.get('worldSaveData', {}).get('value', {})
    container = wsd.get('CharacterContainerSaveData', {}).get('value', [])
    container_to_player = {}
    for uid, info in players.items():
        if info.get('party_id'):
            container_to_player[info['party_id']] = {'type': 'Party', **info}
        if info.get('palbox_id'):
            container_to_player[info['palbox_id']] = {'type': 'PalBox', **info}
    player_containers = []
    if isinstance(container, list):
        for i, entry in enumerate(container):
            key = entry.get('key', {})
            value = entry.get('value', {})
            slot_num = value.get('SlotNum', {}).get('value', 0)
            if slot_num >= 960:
                container_id = key.get('ID', {}).get('value', 'N/A')
                container_id_str = str(container_id).lower() if container_id else 'N/A'
                slots = value.get('Slots', {}).get('value', {})
                slots_values = slots.get('values', [])
                player_info = container_to_player.get(container_id_str)
                if player_info:
                    player_name = player_info['name']
                    player_uid = player_info['uid']
                    guild = player_info['guild']
                    container_type = player_info.get('type', 'Unknown')
                else:
                    player_name = 'Unknown Player'
                    player_uid = container_id_str[:8] + '...'
                    guild = 'Unknown Guild'
                    container_type = 'Unknown'
                player_containers.append({'index': i, 'container_id': container_id_str, 'slot_num': slot_num, 'used_slots': len(slots_values), 'max_slots': slot_num, 'player_uid': player_uid, 'player_name': player_name, 'guild': guild, 'container_type': container_type, 'entry': entry})
    return player_containers
class SlotNumUpdaterApp(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(t('tool.slot_injector'))
        self.setMinimumSize(900, 500)
        self.resize(1000, 600)
        self.gvas_file = None
        self.player_containers = []
        self.save_folder = None
        self.load_styles()
        try:
            if ICON_PATH and os.path.exists(ICON_PATH):
                self.setWindowIcon(QIcon(ICON_PATH))
        except Exception:
            pass
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(12)
        file_frame = QFrame()
        file_frame.setObjectName('glass')
        file_layout = QHBoxLayout(file_frame)
        file_layout.setContentsMargins(12, 8, 12, 8)
        self.browse_button = QPushButton(t('browse'))
        self.browse_button.setFixedWidth(100)
        self.browse_button.clicked.connect(self.browse_file)
        self.file_entry = QLineEdit()
        self.file_entry.setPlaceholderText(t('slot.path_placeholder'))
        self.file_entry.setReadOnly(True)
        file_layout.addWidget(self.browse_button)
        file_layout.addWidget(self.file_entry)
        main_layout.addWidget(file_frame)
        self.table_label = QLabel(t('slotinjector.table_title'))
        self.table_label.setFont(QFont('Segoe UI', 11, QFont.Bold))
        main_layout.addWidget(self.table_label)
        search_frame = QFrame()
        search_frame.setObjectName('glass')
        search_layout = QHBoxLayout(search_frame)
        search_layout.setContentsMargins(12, 8, 12, 8)
        search_icon_label = QLabel('🔍')
        search_icon_label.setFont(QFont('Segoe UI', 12))
        self.search_entry = QLineEdit()
        self.search_entry.setPlaceholderText(t('slotinjector.search_placeholder'))
        self.search_entry.textChanged.connect(self.filter_table)
        self.clear_search_btn = QPushButton('×')
        self.clear_search_btn.setFixedSize(24, 24)
        self.clear_search_btn.clicked.connect(self.clear_search)
        search_layout.addWidget(search_icon_label)
        search_layout.addWidget(self.search_entry)
        search_layout.addWidget(self.clear_search_btn)
        main_layout.addWidget(search_frame)
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([t('slotinjector.col_select'), t('slotinjector.col_player'), t('slotinjector.col_uid'), t('slotinjector.col_guild'), t('slotinjector.col_current'), t('slotinjector.col_used'), t('slotinjector.col_new_value')])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setColumnWidth(0, 50)
        self.table.setColumnWidth(1, 150)
        self.table.setColumnWidth(2, 280)
        self.table.setColumnWidth(3, 150)
        main_layout.addWidget(self.table)
        select_layout = QHBoxLayout()
        self.select_all_btn = QPushButton(t('slotinjector.select_all'))
        self.select_all_btn.clicked.connect(self.select_all)
        self.select_none_btn = QPushButton(t('slotinjector.select_none'))
        self.select_none_btn.clicked.connect(self.select_none)
        select_layout.addWidget(self.select_all_btn)
        select_layout.addWidget(self.select_none_btn)
        select_layout.addStretch()
        main_layout.addLayout(select_layout)
        input_frame = QFrame()
        input_frame.setObjectName('glass')
        input_layout = QHBoxLayout(input_frame)
        input_layout.setContentsMargins(12, 12, 12, 12)
        self.new_slots_label = QLabel(t('slotinjector.new_slots_label'))
        self.new_slots_label.setFont(QFont('Segoe UI', 10, QFont.Bold))
        self.new_slots_entry = QSpinBox()
        self.new_slots_entry.setRange(1, 99999)
        self.new_slots_entry.setValue(960)
        self.new_slots_entry.setFixedWidth(100)
        input_layout.addWidget(self.new_slots_label)
        input_layout.addWidget(self.new_slots_entry)
        input_layout.addStretch()
        main_layout.addWidget(input_frame)
        button_layout = QHBoxLayout()
        self.apply_selected_btn = QPushButton(t('slotinjector.apply_selected'))
        self.apply_selected_btn.setObjectName('ApplyButton')
        self.apply_selected_btn.clicked.connect(self.apply_selected)
        self.apply_all_btn = QPushButton(t('slotinjector.apply_all'))
        self.apply_all_btn.setObjectName('ApplyButton')
        self.apply_all_btn.clicked.connect(self.apply_all)
        self.save_changes_btn = QPushButton(t('menu.file.save_changes'))
        self.save_changes_btn.setObjectName('ApplyButton')
        self.save_changes_btn.clicked.connect(self.save_changes)
        button_layout.addStretch()
        button_layout.addWidget(self.apply_selected_btn)
        button_layout.addWidget(self.apply_all_btn)
        button_layout.addWidget(self.save_changes_btn)
        button_layout.addStretch()
        main_layout.addLayout(button_layout)
        self.has_changes = False
        self.pending_new_value = None
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
            self.save_folder = os.path.dirname(file)
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
            players_folder = os.path.join(self.save_folder, 'Players') if self.save_folder else None
            self.player_containers = get_player_containers(self.gvas_file, players_folder)
            self.populate_table()
            show_information(self, t('slot.loaded_title'), t('slotinjector.loaded_msg', count=len(self.player_containers)))
        run_with_loading(on_finished, task)
    def populate_table(self):
        self.table.setRowCount(len(self.player_containers))
        for row, container in enumerate(self.player_containers):
            checkbox = QCheckBox()
            checkbox.setChecked(True)
            checkbox_widget = QWidget()
            checkbox_layout = QHBoxLayout(checkbox_widget)
            checkbox_layout.addWidget(checkbox)
            checkbox_layout.setAlignment(Qt.AlignCenter)
            checkbox_layout.setContentsMargins(0, 0, 0, 0)
            self.table.setCellWidget(row, 0, checkbox_widget)
            name_item = QTableWidgetItem(container['player_name'])
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 1, name_item)
            uid_item = QTableWidgetItem(str(container['player_uid']))
            uid_item.setFlags(uid_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 2, uid_item)
            guild_item = QTableWidgetItem(container['guild'])
            guild_item.setFlags(guild_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 3, guild_item)
            current_item = QTableWidgetItem(str(container['slot_num']))
            current_item.setFlags(current_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 4, current_item)
            used_item = QTableWidgetItem(f"{container['used_slots']}/{container['max_slots']}")
            used_item.setFlags(used_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 5, used_item)
            new_item = QTableWidgetItem('-')
            new_item.setFlags(new_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 6, new_item)
    def filter_table(self, text):
        search_text = text.lower().strip()
        for row in range(self.table.rowCount()):
            if not search_text:
                self.table.setRowHidden(row, False)
                continue
            player_name = self.table.item(row, 1).text().lower() if self.table.item(row, 1) else ''
            player_uid = self.table.item(row, 2).text().lower() if self.table.item(row, 2) else ''
            guild = self.table.item(row, 3).text().lower() if self.table.item(row, 3) else ''
            if search_text in player_name or search_text in player_uid or search_text in guild:
                self.table.setRowHidden(row, False)
            else:
                self.table.setRowHidden(row, True)
    def clear_search(self):
        self.search_entry.clear()
    def select_all(self):
        for row in range(self.table.rowCount()):
            if not self.table.isRowHidden(row):
                checkbox_widget = self.table.cellWidget(row, 0)
                if checkbox_widget:
                    checkbox = checkbox_widget.findChild(QCheckBox)
                    if checkbox:
                        checkbox.setChecked(True)
    def select_none(self):
        for row in range(self.table.rowCount()):
            checkbox_widget = self.table.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox:
                    checkbox.setChecked(False)
    def get_selected_containers(self):
        selected = []
        for row in range(self.table.rowCount()):
            checkbox_widget = self.table.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox and checkbox.isChecked():
                    selected.append(self.player_containers[row])
        return selected
    def apply_selected(self):
        selected = self.get_selected_containers()
        if not selected:
            show_information(self, t('info.title'), t('slotinjector.no_selection'))
            return
        self._apply_to_containers(selected)
    def apply_all(self):
        if not self.player_containers:
            show_information(self, t('info.title'), t('slot.no_entries'))
            return
        self._apply_to_containers(self.player_containers)
    def _apply_to_containers(self, containers):
        if not hasattr(self, 'gvas_file'):
            show_critical(self, t('error.title'), t('slot.load_first'))
            return
        new_value = self.new_slots_entry.value()
        reply = QMessageBox.question(self, t('slot.confirm_title'), t('slotinjector.confirm_msg', count=len(containers), new=new_value), QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        for container in containers:
            container['entry']['value']['SlotNum']['value'] = new_value
        self.has_changes = True
        self.pending_new_value = new_value
        for row, container in enumerate(self.player_containers):
            new_item = QTableWidgetItem(str(new_value))
            new_item.setFlags(new_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 6, new_item)
            current_item = QTableWidgetItem(str(new_value))
            current_item.setFlags(current_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 4, current_item)
            used_item = QTableWidgetItem(f"{container['used_slots']}/{new_value}")
            used_item.setFlags(used_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 5, used_item)
        for container in self.player_containers:
            container['slot_num'] = new_value
            container['max_slots'] = new_value
        show_information(self, t('success.title'), t('slotinjector.applied_in_memory', count=len(containers), new=new_value))
    def save_changes(self):
        if not hasattr(self, 'gvas_file'):
            show_critical(self, t('error.title'), t('slot.load_first'))
            return
        if not self.has_changes:
            show_information(self, t('info.title'), t('slotinjector.no_changes'))
            return
        filepath = self.file_entry.text()
        gvas_file = self.gvas_file
        def task():
            backup_whole_directory(os.path.dirname(filepath), 'Backups/Slot Injector')
            gvasfile_to_sav(gvas_file, filepath)
            return True
        def on_finished(result):
            show_information(self, t('success.title'), t('slotinjector.saved_success'))
            self.accept()
        run_with_loading(on_finished, task)
    def closeEvent(self, event):
        if self.has_changes:
            reply = QMessageBox.question(self, t('warning.title'), t('slotinjector.unsaved_changes'), QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.No:
                event.ignore()
                return
        event.accept()
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