import os
import json
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, QSpinBox, QComboBox, QTextEdit, QFileDialog, QGroupBox, QFormLayout, QCheckBox, QFrame, QTabWidget, QScrollArea, QWidget, QGridLayout
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QFont
from i18n import t
from loading_manager import show_critical
from palworld_aio import constants
from palworld_aio.utils import sav_to_json, extract_value, get_pal_data, calculate_max_hp, calculate_attack, calculate_defense, format_character_key
DARK_THEME_STYLESHEET = '\n    QDialog {\n        background: qlineargradient(spread:pad, x1:0.0, y1:0.0, x2:1.0, y2:1.0,\n                    stop:0 #07080a, stop:0.5 #08101a, stop:1 #05060a);\n        color: #dfeefc;\n    }\n    QLabel {\n        color: #dfeefc;\n    }\n    QLineEdit {\n        background-color: rgba(255,255,255,0.1);\n        color: #dfeefc;\n        border: 1px solid rgba(255,255,255,0.2);\n        border-radius: 4px;\n        padding: 6px;\n    }\n    QSpinBox {\n        background-color: rgba(255,255,255,0.1);\n        color: #dfeefc;\n        border: 1px solid rgba(255,255,255,0.2);\n        border-radius: 4px;\n        padding: 4px;\n    }\n    QComboBox {\n        background-color: rgba(255,255,255,0.1);\n        color: #dfeefc;\n        border: 1px solid rgba(255,255,255,0.2);\n        border-radius: 4px;\n        padding: 6px;\n    }\n    QComboBox QAbstractItemView {\n        background-color: #2a2a2a;\n        color: #dfeefc;\n        selection-background-color: #3a3a3a;\n    }\n    QCheckBox {\n        color: #dfeefc;\n    }\n    QRadioButton {\n        color: #dfeefc;\n    }\n    QGroupBox {\n        color: #dfeefc;\n        border: 1px solid rgba(255,255,255,0.2);\n        border-radius: 6px;\n        margin-top: 10px;\n        padding-top: 10px;\n    }\n    QGroupBox::title {\n        subcontrol-origin: margin;\n        left: 10px;\n        padding: 0 5px;\n    }\n    QTextEdit {\n        background-color: rgba(255,255,255,0.05);\n        color: #dfeefc;\n        border: 1px solid rgba(255,255,255,0.1);\n        border-radius: 4px;\n    }\n    QPushButton {\n        background-color: #3a3a3a;\n        color: #dfeefc;\n        border: 1px solid #555555;\n        border-radius: 4px;\n        padding: 6px 16px;\n        min-width: 70px;\n    }\n    QPushButton:hover {\n        background-color: #4a4a4a;\n    }\n    QFrame {\n        background-color: rgba(255,255,255,0.03);\n        border: 1px solid rgba(255,255,255,0.08);\n        border-radius: 6px;\n    }\n'
class ThemedDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._apply_theme()
    def _apply_theme(self):
        self.setStyleSheet(DARK_THEME_STYLESHEET)
    def showEvent(self, event):
        super().showEvent(event)
        if not event.spontaneous():
            try:
                from palworld_aio.ui.tools_tab import center_on_parent
                center_on_parent(self)
            except ImportError:
                from ..ui.tools_tab import center_on_parent
                center_on_parent(self)
            self.activateWindow()
            self.raise_()
class InputDialog(ThemedDialog):
    def __init__(self, title, prompt, parent=None, mode='text', initial_text=''):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(400)
        if os.path.exists(constants.ICON_PATH):
            self.setWindowIcon(QIcon(constants.ICON_PATH))
        layout = QVBoxLayout(self)
        label = QLabel(prompt)
        layout.addWidget(label)
        self.input_field = QLineEdit()
        self.input_field.setText(initial_text)
        self.input_field.selectAll()
        layout.addWidget(self.input_field)
        button_layout = QHBoxLayout()
        ok_btn = QPushButton(t('button.ok') if t else 'OK')
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton(t('button.cancel') if t else 'Cancel')
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
        self.result_value = None
    def accept(self):
        self.result_value = self.input_field.text()
        super().accept()
    @staticmethod
    def get_text(title, prompt, parent=None, mode='text', initial_text=''):
        dialog = InputDialog(title, prompt, parent, mode, initial_text)
        if dialog.exec() == QDialog.Accepted:
            return dialog.result_value
        return None
class DaysInputDialog(ThemedDialog):
    def __init__(self, title, prompt, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(300)
        if os.path.exists(constants.ICON_PATH):
            self.setWindowIcon(QIcon(constants.ICON_PATH))
        layout = QVBoxLayout(self)
        label = QLabel(prompt)
        layout.addWidget(label)
        self.spin_box = QSpinBox()
        self.spin_box.setMinimum(1)
        self.spin_box.setMaximum(365)
        self.spin_box.setValue(30)
        layout.addWidget(self.spin_box)
        button_layout = QHBoxLayout()
        ok_btn = QPushButton(t('button.ok') if t else 'OK')
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton(t('button.cancel') if t else 'Cancel')
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
        self.result_value = None
    def accept(self):
        self.result_value = self.spin_box.value()
        super().accept()
    @staticmethod
    def get_days(title, prompt, parent=None):
        dialog = DaysInputDialog(title, prompt, parent)
        if dialog.exec() == QDialog.Accepted:
            return dialog.result_value
        return None
class LevelInputDialog(ThemedDialog):
    def __init__(self, title, prompt, current_level, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(300)
        if os.path.exists(constants.ICON_PATH):
            self.setWindowIcon(QIcon(constants.ICON_PATH))
        layout = QVBoxLayout(self)
        label = QLabel(prompt)
        layout.addWidget(label)
        self.spin_box = QSpinBox()
        self.spin_box.setMinimum(1)
        self.spin_box.setMaximum(65)
        self.spin_box.setValue(current_level)
        layout.addWidget(self.spin_box)
        button_layout = QHBoxLayout()
        ok_btn = QPushButton(t('button.ok') if t else 'OK')
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton(t('button.cancel') if t else 'Cancel')
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
        self.result_value = None
    def accept(self):
        self.result_value = self.spin_box.value()
        super().accept()
    @staticmethod
    def get_level(title, prompt, current_level, parent=None):
        dialog = LevelInputDialog(title, prompt, current_level, parent)
        if dialog.exec() == QDialog.Accepted:
            return dialog.result_value
        return None
class KillNearestBaseDialog(ThemedDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t('kill_nearest_base.title') if t else 'Kill Nearest Base Config')
        self.setModal(True)
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        if os.path.exists(constants.ICON_PATH):
            self.setWindowIcon(QIcon(constants.ICON_PATH))
        layout = QVBoxLayout(self)
        form_group = QGroupBox(t('kill_nearest_base.settings') if t else 'Settings')
        form_layout = QFormLayout()
        self.coord_x = QSpinBox()
        self.coord_x.setRange(-999999, 999999)
        self.coord_x.setValue(0)
        form_layout.addRow('X:', self.coord_x)
        self.coord_y = QSpinBox()
        self.coord_y.setRange(-999999, 999999)
        self.coord_y.setValue(0)
        form_layout.addRow('Y:', self.coord_y)
        self.radius = QSpinBox()
        self.radius.setRange(1, 100000)
        self.radius.setValue(5000)
        form_layout.addRow(t('kill_nearest_base.radius') if t else 'Radius:', self.radius)
        self.use_new_coords = QCheckBox(t('kill_nearest_base.use_new_coords') if t else 'Use New Coordinates')
        self.use_new_coords.setChecked(True)
        form_layout.addRow('', self.use_new_coords)
        form_group.setLayout(form_layout)
        layout.addWidget(form_group)
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setFont(QFont('Consolas', 9))
        layout.addWidget(self.output_text)
        button_layout = QHBoxLayout()
        generate_btn = QPushButton(t('kill_nearest_base.generate') if t else 'Generate')
        generate_btn.clicked.connect(self.generate_command)
        copy_btn = QPushButton(t('kill_nearest_base.copy') if t else 'Copy to Clipboard')
        copy_btn.clicked.connect(self.copy_to_clipboard)
        close_btn = QPushButton(t('button.close') if t else 'Close')
        close_btn.clicked.connect(self.reject)
        button_layout.addWidget(generate_btn)
        button_layout.addWidget(copy_btn)
        button_layout.addWidget(close_btn)
        layout.addLayout(button_layout)
    def generate_command(self):
        x = self.coord_x.value()
        y = self.coord_y.value()
        radius = self.radius.value()
        use_new = self.use_new_coords.isChecked()
        import palworld_coord
        if use_new:
            sav_x, sav_y = palworld_coord.map_to_sav(x, y, new=True)
        else:
            sav_x, sav_y = palworld_coord.map_to_sav(x, y, new=False)
        command = f'/KillNearestBase {int(sav_x)} {int(sav_y)} {radius}'
        self.output_text.setPlainText(command)
    def copy_to_clipboard(self):
        from PySide6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(self.output_text.toPlainText())
class ConfirmDialog(ThemedDialog):
    def __init__(self, title, message, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(350)
        if os.path.exists(constants.ICON_PATH):
            self.setWindowIcon(QIcon(constants.ICON_PATH))
        layout = QVBoxLayout(self)
        label = QLabel(message)
        label.setWordWrap(True)
        layout.addWidget(label)
        button_layout = QHBoxLayout()
        yes_btn = QPushButton(t('button.yes') if t else 'Yes')
        yes_btn.clicked.connect(self.accept)
        no_btn = QPushButton(t('button.no') if t else 'No')
        no_btn.clicked.connect(self.reject)
        button_layout.addWidget(yes_btn)
        button_layout.addWidget(no_btn)
        layout.addLayout(button_layout)
    @staticmethod
    def confirm(title, message, parent=None):
        dialog = ConfirmDialog(title, message, parent)
        return dialog.exec() == QDialog.Accepted
class RadiusInputDialog(ThemedDialog):
    DEFAULT_RADIUS = 3500.0
    def __init__(self, title, prompt, current_radius, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(450)
        if os.path.exists(constants.ICON_PATH):
            self.setWindowIcon(QIcon(constants.ICON_PATH))
        self.current_actual_radius = current_radius
        layout = QVBoxLayout(self)
        label = QLabel(prompt)
        layout.addWidget(label)
        input_layout = QHBoxLayout()
        self.spin_box = QSpinBox()
        self.spin_box.setMinimum(50)
        self.spin_box.setMaximum(1000)
        self.spin_box.setSuffix('%')
        current_percent = int(round(current_radius / 35.0))
        self.spin_box.setValue(current_percent)
        input_layout.addWidget(self.spin_box)
        self.actual_value_label = QLabel(f'= {int(current_radius)}')
        self.actual_value_label.setMinimumWidth(80)
        self.actual_value_label.setStyleSheet('color: #a0aec0; font-size: 11px; padding: 4px; background-color: rgba(255,255,255,0.05); border-radius: 4px;')
        input_layout.addWidget(self.actual_value_label)
        layout.addLayout(input_layout)
        warning_label = QLabel(t('base.radius.warning') if t else '⚠ Note: You must load this save in-game for the game to reassign structures within the new radius.')
        warning_label.setWordWrap(True)
        warning_label.setStyleSheet('color: #f59e0b; font-style: italic; padding: 8px; background-color: rgba(245, 158, 11, 0.1); border-radius: 4px;')
        layout.addWidget(warning_label)
        button_layout = QHBoxLayout()
        reset_btn = QPushButton(t('base.radius.reset') if t else 'Reset to Default (100%)')
        reset_btn.clicked.connect(self._reset_to_default)
        ok_btn = QPushButton(t('button.ok') if t else 'OK')
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton(t('button.cancel') if t else 'Cancel')
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(reset_btn)
        button_layout.addStretch()
        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
        self.result_value = None
        self.spin_box.valueChanged.connect(self._update_actual_value)
    def _update_actual_value(self):
        percent = self.spin_box.value()
        actual = int(round(percent * 35.0))
        self.actual_value_label.setText(f'= {actual}')
    def _reset_to_default(self):
        self.spin_box.setValue(100)
    def accept(self):
        percent = self.spin_box.value()
        self.result_value = float(percent * 35.0)
        super().accept()
    @staticmethod
    def get_radius(title, prompt, current_radius, parent=None):
        dialog = RadiusInputDialog(title, prompt, current_radius, parent)
        if dialog.exec() == QDialog.Accepted:
            return dialog.result_value
        return None
class PalDefenderDialog(ThemedDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t('paldefender.title') if t else 'PalDefender - Generate Commands')
        self.setMinimumSize(800, 600)
        if os.path.exists(constants.ICON_PATH):
            self.setWindowIcon(QIcon(constants.ICON_PATH))
        self._setup_ui()
    def _setup_ui(self):
        from PySide6.QtWidgets import QRadioButton, QButtonGroup, QFrame
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        filter_frame = QFrame()
        filter_frame.setFrameShape(QFrame.StyledPanel)
        filter_layout = QVBoxLayout(filter_frame)
        filter_label = QLabel(t('paldefender.filter_type') if t else 'Filter Type:')
        filter_label.setFont(QFont(constants.FONT_FAMILY, constants.FONT_SIZE, QFont.Bold))
        filter_layout.addWidget(filter_label)
        radio_layout = QHBoxLayout()
        self.filter_group = QButtonGroup(self)
        self.radio_inactivity = QRadioButton(t('paldefender.inactivity') if t else 'Inactivity(days)')
        self.radio_maxlevel = QRadioButton(t('paldefender.max_level') if t else 'Max Level')
        self.radio_both = QRadioButton(t('paldefender.both') if t else 'Both')
        self.filter_group.addButton(self.radio_inactivity, 1)
        self.filter_group.addButton(self.radio_maxlevel, 2)
        self.filter_group.addButton(self.radio_both, 3)
        self.radio_inactivity.setChecked(True)
        radio_layout.addWidget(self.radio_inactivity)
        radio_layout.addWidget(self.radio_maxlevel)
        radio_layout.addWidget(self.radio_both)
        radio_layout.addStretch()
        filter_layout.addLayout(radio_layout)
        instructions = QLabel(t('paldefender.instructions') if t else 'Choose filter type:\nInactivity: Select guilds with ALL players inactive for given days.\nMax Level: Select guilds with ALL players below given level.\nBoth: Combine both filters(ALL players must match both criteria).')
        instructions.setStyleSheet(f'color: {constants.MUTED}; padding: 10px;')
        instructions.setWordWrap(True)
        filter_layout.addWidget(instructions)
        layout.addWidget(filter_frame)
        input_layout = QHBoxLayout()
        inactivity_label = QLabel(t('paldefender.inactivity_days') if t else 'Inactivity Days:')
        input_layout.addWidget(inactivity_label)
        self.inactivity_spin = QSpinBox()
        self.inactivity_spin.setMinimum(1)
        self.inactivity_spin.setMaximum(9999)
        self.inactivity_spin.setValue(30)
        self.inactivity_spin.setMinimumWidth(100)
        input_layout.addWidget(self.inactivity_spin)
        input_layout.addSpacing(20)
        maxlevel_label = QLabel(t('paldefender.max_level_label') if t else 'Max Level:')
        input_layout.addWidget(maxlevel_label)
        self.maxlevel_spin = QSpinBox()
        self.maxlevel_spin.setMinimum(1)
        self.maxlevel_spin.setMaximum(100)
        self.maxlevel_spin.setValue(10)
        self.maxlevel_spin.setMinimumWidth(100)
        input_layout.addWidget(self.maxlevel_spin)
        input_layout.addStretch()
        layout.addLayout(input_layout)
        run_btn = QPushButton(t('button.run') if t else 'Generate Commands')
        run_btn.setMinimumHeight(40)
        run_btn.setFont(QFont(constants.FONT_FAMILY, constants.FONT_SIZE, QFont.Bold))
        run_btn.clicked.connect(self._on_generate)
        layout.addWidget(run_btn)
        output_label = QLabel(t('paldefender.output') if t else 'Output (killnearestbase commands):')
        output_label.setFont(QFont(constants.FONT_FAMILY, constants.FONT_SIZE, QFont.Bold))
        layout.addWidget(output_label)
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setFont(QFont('Consolas', 10))
        self.output_text.setStyleSheet(f'background-color: {constants.GLASS}; color: {constants.TEXT};')
        layout.addWidget(self.output_text)
    def _append_output(self, text):
        self.output_text.append(text)
    def _clear_output(self):
        self.output_text.clear()
    def _on_generate(self):
        self._clear_output()
        try:
            if not constants.loaded_level_json:
                self._append_output('No save file loaded.')
                return
            filter_type = self.filter_group.checkedId()
            inactivity_days = self.inactivity_spin.value() if filter_type in (1, 3) else None
            max_level = self.maxlevel_spin.value() if filter_type in (2, 3) else None
            self._generate_commands(inactivity_days=inactivity_days, max_level=max_level)
        except Exception as e:
            show_critical(self, t('error.title') if t else 'Error', str(e))
    def _generate_commands(self, inactivity_days=None, max_level=None):
        from collections import defaultdict
        from .utils import as_uuid, extract_value
        wsd = constants.loaded_level_json['properties']['worldSaveData']['value']
        tick = wsd['GameTimeSaveData']['value']['RealDateTimeTicks']['value']
        player_levels = {}
        char_map = wsd.get('CharacterSaveParameterMap', {}).get('value', [])
        for entry in char_map:
            try:
                sp = entry['value']['RawData']['value']['object']['SaveParameter']
                if sp['struct_type'] != 'PalIndividualCharacterSaveParameter':
                    continue
                sp_val = sp['value']
                if not sp_val.get('IsPlayer', {}).get('value', False):
                    continue
                key = entry.get('key', {})
                uid_obj = key.get('PlayerUId', {})
                uid = str(uid_obj.get('value', '') if isinstance(uid_obj, dict) else uid_obj)
                level = extract_value(sp_val, 'Level', '?')
                if uid:
                    player_levels[uid.replace('-', '').lower()] = level
            except:
                continue
        excluded_guilds = {ex.replace('-', '').lower() for ex in constants.exclusions.get('guilds', [])}
        excluded_bases = {ex.replace('-', '').lower() for ex in constants.exclusions.get('bases', [])}
        matching_guilds = {}
        for g in wsd['GroupSaveDataMap']['value']:
            if g['value']['GroupType']['value']['value'] != 'EPalGroupType::Guild':
                continue
            gid_raw = str(g['key'])
            gid_clean = gid_raw.replace('-', '').lower()
            if gid_clean in excluded_guilds:
                continue
            guild_name = g['value']['RawData']['value'].get('guild_name', 'Unknown')
            players = g['value']['RawData']['value'].get('players', [])
            if not players:
                continue
            matches_inactivity = True
            if inactivity_days is not None:
                for p in players:
                    last_online = p.get('player_info', {}).get('last_online_real_time')
                    if last_online is None:
                        matches_inactivity = False
                        break
                    days_inactive = (tick - last_online) / 10000000.0 / 86400
                    if days_inactive < inactivity_days:
                        matches_inactivity = False
                        break
            if not matches_inactivity:
                continue
            matches_max_level = True
            if max_level is not None:
                for p in players:
                    uid = str(p.get('player_uid', '')).replace('-', '').lower()
                    level = player_levels.get(uid, '?')
                    if level == '?':
                        matches_max_level = False
                        break
                    if isinstance(level, int) and level > max_level:
                        matches_max_level = False
                        break
            if not matches_max_level:
                continue
            matching_guilds[gid_raw] = {'name': guild_name, 'bases': []}
        base_list = wsd.get('BaseCampSaveData', {}).get('value', [])
        for b in base_list:
            gid = as_uuid(b['value']['RawData']['value'].get('group_id_belong_to'))
            base_id = str(b['key'])
            if base_id.replace('-', '').lower() in excluded_bases:
                continue
            gid_str = str(gid)
            if gid_str in matching_guilds:
                raw = b['value']['RawData']['value']
                trans = raw.get('transform', {})
                translation = trans.get('translation', {})
                x = translation.get('x', 0)
                y = translation.get('y', 0)
                z = translation.get('z', 0)
                raw_data = f'RawData: {x},{y},{z}'
                matching_guilds[gid_str]['bases'].append({'id': base_id, 'raw': raw_data})
        kill_commands = []
        for gid, ginfo in matching_guilds.items():
            self._append_output(f"Guild: {ginfo['name']} | ID: {gid}")
            self._append_output(f"Bases: {len(ginfo['bases'])}")
            for base in ginfo['bases']:
                self._append_output(f"  Base {base['id']} | {base['raw']}")
                raw = base['raw'].replace('RawData: ', '')
                coords = raw.split(',')
                if len(coords) >= 3:
                    x, y, z = (coords[0], coords[1], coords[2])
                    kill_commands.append(f'killnearestbase {x} {y} {z}')
            self._append_output('-' * 40)
        self._append_output(f'\nFound {len(matching_guilds)} guild(s) with bases to delete.')
        if kill_commands:
            output_dir = os.path.join(constants.get_base_path(), 'PalDefender')
            os.makedirs(output_dir, exist_ok=True)
            commands_file = os.path.join(output_dir, 'paldefender_bases.log')
            with open(commands_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(kill_commands))
            self._append_output(f'\nWrote {len(kill_commands)} kill commands to:')
            self._append_output(commands_file)
            self._append_output('\n--- Commands ---')
            for cmd in kill_commands:
                self._append_output(cmd)
        else:
            self._append_output('\nNo kill commands generated.')
        if inactivity_days is not None:
            self._append_output(f'\nFilter: Inactivity >= {inactivity_days} days')
        if max_level is not None:
            self._append_output(f'\nFilter: Max Level <= {max_level}')
        self._append_output(f'\nExcluded guilds: {len(excluded_guilds)}')
        self._append_output(f'Excluded bases: {len(excluded_bases)}')
class GuildSelectionDialog(ThemedDialog):
    def __init__(self, guilds_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t('base.import.select_guild') if t else 'Select Guild')
        self.setModal(True)
        self.setMinimumWidth(400)
        if os.path.exists(constants.ICON_PATH):
            self.setWindowIcon(QIcon(constants.ICON_PATH))
        layout = QVBoxLayout(self)
        label = QLabel(t('base.import.select_guild_prompt') if t else 'Select a guild to import the base(s) to:')
        label.setWordWrap(True)
        layout.addWidget(label)
        self.guild_combo = QComboBox()
        self.guild_combo.setMinimumHeight(30)
        self.guild_ids = []
        for guild_id, guild_info in guilds_data.items():
            guild_name = guild_info.get('guild_name', 'Unknown')
            base_count = len(guild_info.get('bases', []))
            display_text = f'{guild_name} ({base_count} bases)'
            self.guild_combo.addItem(display_text, guild_id)
            self.guild_ids.append(guild_id)
        layout.addWidget(self.guild_combo)
        button_layout = QHBoxLayout()
        ok_btn = QPushButton(t('button.ok') if t else 'OK')
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton(t('button.cancel') if t else 'Cancel')
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
        self.selected_guild_id = None
    def accept(self):
        self.selected_guild_id = self.guild_combo.currentData()
        super().accept()
    @staticmethod
    def get_guild(guilds_data, parent=None):
        dialog = GuildSelectionDialog(guilds_data, parent)
        if dialog.exec() == QDialog.Accepted:
            return dialog.selected_guild_id
        return None
from .edit_pals import EditPalsDialog, PalFrame