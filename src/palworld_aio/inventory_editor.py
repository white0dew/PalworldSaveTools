import os
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QScrollArea, QLabel, QPushButton, QFrame, QDialog, QLineEdit, QListWidget, QListWidgetItem, QSpinBox, QMessageBox, QTabWidget, QSizePolicy, QAbstractItemView, QMenu, QToolTip, QListView, QProgressBar
from PySide6.QtCore import Qt, QSize, Signal, QPoint
from PySide6.QtGui import QPixmap, QIcon, QFont, QCursor, QPainter, QColor, QPen
from i18n import t
try:
    from palworld_aio.inventory_manager import PlayerInventory, ItemData, get_player_inventory, search_items
    from palworld_aio import constants
    from palworld_aio.utils import sav_to_gvasfile, gvasfile_to_sav
    from loading_manager import show_information, show_warning
except ImportError:
    from .inventory_manager import PlayerInventory, ItemData, get_player_inventory, search_items
    from . import constants
    from .utils import sav_to_gvasfile, gvasfile_to_sav
    from ..loading_manager import show_information, show_warning
GRID_COLS = 6
GRID_ROWS = 8
SLOT_SIZE = 56
class ItemSlotWidget(QFrame):
    clicked = Signal(object)
    double_clicked = Signal(object)
    context_menu_requested = Signal(object, QPoint)
    def __init__(self, slot_index: int, container_type: str='main', parent=None):
        super().__init__(parent)
        self.slot_index = slot_index
        self.container_type = container_type
        self.slot_data = None
        self.setFixedSize(SLOT_SIZE, SLOT_SIZE)
        self.setFrameStyle(QFrame.Box | QFrame.Raised)
        self.setLineWidth(1)
        self.setCursor(Qt.PointingHandCursor)
        self._setup_ui()
        self._apply_empty_style()
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(0)
        self.icon_label = QLabel()
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setFixedSize(40, 40)
        layout.addWidget(self.icon_label, alignment=Qt.AlignCenter)
        self.qty_label = QLabel()
        self.qty_label.setAlignment(Qt.AlignRight | Qt.AlignBottom)
        self.qty_label.setStyleSheet('font-size: 10px; font-weight: bold; color: white; background: transparent;')
        layout.addWidget(self.qty_label, alignment=Qt.AlignRight)
    def _apply_empty_style(self):
        self.setStyleSheet('ItemSlotWidget { background-color: rgba(30, 30, 40, 180); border: 1px solid #444; border-radius: 4px; } ItemSlotWidget:hover { background-color: rgba(50, 50, 60, 200); border: 1px solid #666; }')
        self.icon_label.clear()
        self.qty_label.clear()
    def set_item(self, slot_data: dict):
        self.slot_data = slot_data
        if not slot_data:
            self._apply_empty_style()
            return
        icon_path = slot_data.get('icon_path', '')
        if icon_path:
            pixmap = ItemData.get_item_icon(icon_path, QSize(40, 40))
            self.icon_label.setPixmap(pixmap)
        stack_count = slot_data.get('stack_count', 1)
        if stack_count > 1:
            self.qty_label.setText(str(stack_count))
        else:
            self.qty_label.clear()
        category = slot_data.get('category', 'misc')
        self._apply_category_style(category)
    def _apply_category_style(self, category: str):
        category_colors = {'weapon': '#ff6b35', 'armor': '#4ecdc4', 'accessory': '#a855f7', 'food': '#90be6d', 'material': '#f9c74f', 'sphere': '#43b581', 'ammo': '#7289da', 'key_item': '#faa61a', 'tool': '#00bcd4', 'misc': '#888888'}
        color = category_colors.get(category, '#888888')
        self.setStyleSheet(f'ItemSlotWidget {{ background-color: rgba(30, 30, 40, 200); border: 2px solid {color}; border-radius: 4px; }} ItemSlotWidget:hover {{ background-color: rgba(60, 60, 70, 220); border: 2px solid {color}; }}')
    def clear_item(self):
        self.slot_data = None
        self._apply_empty_style()
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.slot_data)
        super().mousePressEvent(event)
    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.double_clicked.emit(self.slot_data)
        super().mouseDoubleClickEvent(event)
    def contextMenuEvent(self, event):
        if self.slot_data:
            self.context_menu_requested.emit(self.slot_data, event.globalPos())
    def enterEvent(self, event):
        if self.slot_data:
            item_name = self.slot_data.get('item_name', 'Unknown')
            qty = self.slot_data.get('stack_count', 1)
            item_id = self.slot_data.get('item_id', '')
            tooltip = f'<b>{item_name}</b><br>Qty: {qty}<br><i>{item_id}</i>'
            QToolTip.showText(QCursor.pos(), tooltip)
        super().enterEvent(event)
class EquipmentSlotWidget(QFrame):
    item_changed = Signal(str, object)
    def __init__(self, slot_name: str, label: str, parent=None):
        super().__init__(parent)
        self.slot_name = slot_name
        self.current_item = None
        self.setFixedSize(56, 70)
        self.setFrameStyle(QFrame.Box | QFrame.Raised)
        self._setup_ui(label)
        self._apply_style()
    def _setup_ui(self, label: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(1)
        self.label = QLabel(label)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet('font-size: 8px; font-weight: bold; color: #aaa;')
        layout.addWidget(self.label)
        self.icon_label = QLabel()
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setFixedSize(36, 36)
        layout.addWidget(self.icon_label, alignment=Qt.AlignCenter)
        self.name_label = QLabel()
        self.name_label.setAlignment(Qt.AlignCenter)
        self.name_label.setStyleSheet('font-size: 7px; color: #888;')
        self.name_label.setWordWrap(True)
        layout.addWidget(self.name_label)
    def _apply_style(self):
        self.setStyleSheet('EquipmentSlotWidget { background-color: rgba(40, 40, 50, 200); border: 2px solid #555; border-radius: 4px; } EquipmentSlotWidget:hover { background-color: rgba(60, 60, 70, 220); border: 2px solid #777; }')
    def set_item(self, slot_data: dict):
        self.current_item = slot_data
        if not slot_data:
            self.icon_label.clear()
            self.name_label.clear()
            self._apply_style()
            return
        icon_path = slot_data.get('icon_path', '')
        if icon_path:
            pixmap = ItemData.get_item_icon(icon_path, QSize(36, 36))
            self.icon_label.setPixmap(pixmap)
        name = slot_data.get('item_name', '')
        if len(name) > 10:
            name = name[:8] + '..'
        self.name_label.setText(name)
        category = slot_data.get('category', 'misc')
        category_colors = {'weapon': '#ff6b35', 'armor': '#4ecdc4', 'accessory': '#a855f7', 'tool': '#00bcd4', 'food': '#90be6d'}
        color = category_colors.get(category, '#888888')
        self.setStyleSheet(f'EquipmentSlotWidget {{ background-color: rgba(40, 40, 50, 200); border: 2px solid {color}; border-radius: 4px; }} EquipmentSlotWidget:hover {{ background-color: rgba(60, 60, 70, 220); }}')
    def clear_item(self):
        self.current_item = None
        self.icon_label.clear()
        self.name_label.clear()
        self._apply_style()
class StatsPanelWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(120)
        self._setup_ui()
        self._apply_style()
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)
        level_frame = QFrame()
        level_layout = QVBoxLayout(level_frame)
        level_layout.setContentsMargins(0, 0, 0, 0)
        level_layout.setSpacing(2)
        level_header = QHBoxLayout()
        self.level_label = QLabel('Lv. 1')
        self.level_label.setStyleSheet('font-size: 14px; font-weight: bold; color: #fff;')
        level_header.addWidget(self.level_label)
        level_header.addStretch()
        level_layout.addLayout(level_header)
        self.exp_bar = QProgressBar()
        self.exp_bar.setFixedHeight(8)
        self.exp_bar.setRange(0, 100)
        self.exp_bar.setValue(0)
        self.exp_bar.setTextVisible(False)
        self.exp_bar.setStyleSheet('QProgressBar { background-color: #333; border: 1px solid #555; border-radius: 4px; } QProgressBar::chunk { background-color: #43b581; border-radius: 3px; }')
        level_layout.addWidget(self.exp_bar)
        layout.addWidget(level_frame)
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet('background-color: #444;')
        sep.setFixedHeight(1)
        layout.addWidget(sep)
        self.stats = {}
        stat_names = [('hp', 'HP', 100), ('stamina', 'Stamina', 100), ('attack', 'Attack', 10), ('defense', 'Defense', 10), ('work_speed', 'Work Speed', 70), ('weight', 'Weight', '0/500')]
        for key, label, default in stat_names:
            stat_frame = QFrame()
            stat_layout = QHBoxLayout(stat_frame)
            stat_layout.setContentsMargins(0, 0, 0, 0)
            stat_layout.setSpacing(4)
            name_label = QLabel(label)
            name_label.setStyleSheet('font-size: 9px; color: #aaa;')
            stat_layout.addWidget(name_label)
            stat_layout.addStretch()
            value_label = QLabel(str(default))
            value_label.setStyleSheet('font-size: 10px; font-weight: bold; color: #fff;')
            stat_layout.addWidget(value_label)
            self.stats[key] = value_label
            layout.addWidget(stat_frame)
        layout.addStretch()
    def _apply_style(self):
        self.setStyleSheet('StatsPanelWidget { background-color: rgba(30, 30, 40, 200); border: 1px solid #444; border-radius: 8px; }')
    def update_stats(self, stats: dict):
        for key, value in stats.items():
            if key in self.stats:
                self.stats[key].setText(str(value))
    def set_level(self, level: int, exp_percent: int):
        self.level_label.setText(f'Lv. {level}')
        self.exp_bar.setValue(exp_percent)
class InventoryGridWidget(QWidget):
    item_selected = Signal(object)
    item_context_menu = Signal(object, QPoint)
    def __init__(self, container_type: str='main', parent=None):
        super().__init__(parent)
        self.container_type = container_type
        self.slots = {}
        self.current_items = []
        self._setup_ui()
    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(4)
        header = QHBoxLayout()
        self.tab_label = QLabel(t(f'inventory.{self.container_type}', default=self.container_type.title()))
        self.tab_label.setStyleSheet('font-size: 12px; font-weight: bold; color: #fff;')
        header.addWidget(self.tab_label)
        header.addStretch()
        sort_btn = QPushButton(t('inventory.sort', default='Sort'))
        sort_btn.setFixedSize(60, 24)
        sort_btn.clicked.connect(self._sort_items)
        header.addWidget(sort_btn)
        main_layout.addLayout(header)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet('QScrollArea { border: none; background: transparent; }')
        grid_widget = QWidget()
        self.grid_layout = QGridLayout(grid_widget)
        self.grid_layout.setSpacing(4)
        self.grid_layout.setContentsMargins(4, 4, 4, 4)
        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                index = row * GRID_COLS + col
                slot = ItemSlotWidget(index, self.container_type)
                slot.clicked.connect(self._on_slot_clicked)
                slot.double_clicked.connect(self._on_slot_double_clicked)
                slot.context_menu_requested.connect(self._on_slot_context_menu)
                self.grid_layout.addWidget(slot, row, col)
                self.slots[index] = slot
        scroll.setWidget(grid_widget)
        main_layout.addWidget(scroll)
    def load_items(self, items: list):
        self.current_items = items
        for slot in self.slots.values():
            slot.clear_item()
        for item in items:
            slot_index = item.get('slot_index', 0)
            if slot_index in self.slots:
                self.slots[slot_index].set_item(item)
    def _on_slot_clicked(self, slot_data):
        self.item_selected.emit(slot_data)
    def _on_slot_double_clicked(self, slot_data):
        pass
    def _on_slot_context_menu(self, slot_data, pos):
        self.item_context_menu.emit(slot_data, pos)
    def _sort_items(self):
        if not self.current_items:
            return
        sorted_items = sorted(self.current_items, key=lambda x: (x.get('category', 'zzz'), x.get('item_name', '')))
        for i, item in enumerate(sorted_items):
            item['slot_index'] = i
        self.load_items(sorted_items)
class ItemPickerDialog(QDialog):
    item_selected = Signal(str, int)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t('inventory.add_item', default='Add Item'))
        self.setMinimumSize(500, 400)
        self.selected_item = None
        self._setup_ui()
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        search_layout = QHBoxLayout()
        search_label = QLabel(t('common.search', default='Search:'))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(t('inventory.search_placeholder', default='Type to search items...'))
        self.search_input.textChanged.connect(self._search)
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)
        self.results_list = QListWidget()
        self.results_list.setViewMode(QListView.IconMode)
        self.results_list.setIconSize(QSize(40, 40))
        self.results_list.setSpacing(4)
        self.results_list.setResizeMode(QListWidget.Adjust)
        self.results_list.setDragEnabled(False)
        self.results_list.setAcceptDrops(False)
        self.results_list.setDragDropMode(QAbstractItemView.NoDragDrop)
        self.results_list.itemClicked.connect(self._on_item_clicked)
        self.results_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.results_list)
        qty_layout = QHBoxLayout()
        qty_label = QLabel(t('inventory.quantity', default='Quantity:'))
        self.qty_spin = QSpinBox()
        self.qty_spin.setRange(1, 999)
        self.qty_spin.setValue(1)
        qty_layout.addWidget(qty_label)
        qty_layout.addWidget(self.qty_spin)
        qty_layout.addStretch()
        layout.addLayout(qty_layout)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        add_btn = QPushButton(t('button.add', default='Add'))
        add_btn.clicked.connect(self._add_item)
        btn_layout.addWidget(add_btn)
        cancel_btn = QPushButton(t('button.cancel', default='Cancel'))
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        self._load_all_items()
    def _load_all_items(self):
        items = ItemData.get_all_items()
        self._display_items(items[:100])
    def _search(self, query: str):
        if not query:
            self._load_all_items()
            return
        results = search_items(query, limit=50)
        self._display_items(results)
    def _display_items(self, items: list):
        self.results_list.clear()
        for item in items:
            list_item = QListWidgetItem(item.get('name', 'Unknown'))
            list_item.setData(Qt.UserRole, item.get('asset', ''))
            icon_path = item.get('icon', '')
            if icon_path:
                pixmap = ItemData.get_item_icon(icon_path, QSize(40, 40))
                list_item.setIcon(QIcon(pixmap))
            item_name = item.get('name', 'Unknown')
            item_id = item.get('asset', '')
            category = item.get('category', 'misc')
            tooltip = f'<b>{item_name}</b><br>ID: {item_id}<br>Category: {category}'
            list_item.setToolTip(tooltip)
            self.results_list.addItem(list_item)
    def _on_item_clicked(self, item: QListWidgetItem):
        self.selected_item = item.data(Qt.UserRole)
    def _on_item_double_clicked(self, item: QListWidgetItem):
        self.selected_item = item.data(Qt.UserRole)
        self._add_item()
    def _add_item(self):
        if self.selected_item:
            self.item_selected.emit(self.selected_item, self.qty_spin.value())
            self.accept()
class InventoryEditorWindow(QWidget):
    saved = Signal()
    def __init__(self, player_uid: str, player_name: str='Player', parent=None):
        super().__init__(parent)
        self.player_uid = player_uid
        self.player_name = player_name
        self.inventory = None
        self.modified = False
        self.setWindowTitle(t('inventory.title', default=f'Inventory Editor - {player_name}'))
        self.setMinimumSize(950, 650)
        self.resize(1150, 800)
        self._load_styles()
        self._setup_ui()
        self._load_inventory()
    def _load_styles(self):
        user_cfg_path = os.path.join(constants.get_src_path(), 'data', 'configs', 'user.cfg')
        theme = 'dark'
        if os.path.exists(user_cfg_path):
            try:
                import json
                with open(user_cfg_path, 'r') as f:
                    data = json.load(f)
                theme = data.get('theme', 'dark')
            except:
                pass
        qss_path = os.path.join(constants.get_src_path(), 'data', 'gui', f'{theme}mode.qss')
        if os.path.exists(qss_path):
            with open(qss_path, 'r') as f:
                self.setStyleSheet(f.read())
    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)
        header = QHBoxLayout()
        title = QLabel(t('inventory.title', default='Inventory Editor'))
        title.setStyleSheet('font-size: 16px; font-weight: bold; color: #fff;')
        header.addWidget(title)
        player_label = QLabel(f'({self.player_name})')
        player_label.setStyleSheet('font-size: 14px; color: #aaa;')
        header.addWidget(player_label)
        header.addStretch()
        self.modified_label = QLabel()
        self.modified_label.setStyleSheet('color: #ffaa00;')
        header.addWidget(self.modified_label)
        main_layout.addLayout(header)
        content = QHBoxLayout()
        content.setSpacing(12)
        left_panel = QFrame()
        left_panel.setStyleSheet('QFrame { background-color: rgba(20, 20, 30, 200); border-radius: 8px; }')
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(8, 8, 8, 8)
        self.inv_tabs = QTabWidget()
        self.inv_tabs.setStyleSheet('QTabWidget::pane { border: 1px solid #444; background: transparent; } QTabBar::tab { background: #333; padding: 8px 16px; margin-right: 2px; } QTabBar::tab:selected { background: #444; }')
        self.main_grid = InventoryGridWidget('main')
        self.main_grid.item_selected.connect(self._on_item_selected)
        self.main_grid.item_context_menu.connect(self._show_item_context_menu)
        self.inv_tabs.addTab(self.main_grid, t('inventory.main', default='Inventory'))
        self.key_grid = InventoryGridWidget('key')
        self.key_grid.item_selected.connect(self._on_item_selected)
        self.key_grid.item_context_menu.connect(self._show_item_context_menu)
        self.inv_tabs.addTab(self.key_grid, t('inventory.key_items', default='Key Items'))
        left_layout.addWidget(self.inv_tabs)
        content.addWidget(left_panel, 2)
        center_panel = QFrame()
        center_panel.setFixedWidth(200)
        center_panel.setStyleSheet('QFrame { background-color: rgba(20, 20, 30, 200); border-radius: 8px; }')
        center_layout = QVBoxLayout(center_panel)
        center_layout.setContentsMargins(6, 6, 6, 6)
        center_layout.setSpacing(4)
        self.equip_slots = {}
        equip_main_layout = QHBoxLayout()
        equip_main_layout.setSpacing(8)
        left_col = QVBoxLayout()
        left_col.setSpacing(2)
        weapon_header = QLabel('Weapon')
        weapon_header.setStyleSheet('font-size: 9px; font-weight: bold; color: #aaa;')
        left_col.addWidget(weapon_header)
        for i in range(1, 5):
            slot = EquipmentSlotWidget(f'weapon{i}', f'W{i}')
            self.equip_slots[f'weapon{i}'] = slot
            left_col.addWidget(slot)
        acc_header = QLabel('Accessory')
        acc_header.setStyleSheet('font-size: 9px; font-weight: bold; color: #aaa;')
        left_col.addWidget(acc_header)
        acc_grid = QGridLayout()
        acc_grid.setSpacing(2)
        for i, (row, col) in enumerate([(0, 0), (0, 1), (1, 0), (1, 1)]):
            slot = EquipmentSlotWidget(f'accessory{i + 1}', f'A{i + 1}')
            self.equip_slots[f'accessory{i + 1}'] = slot
            acc_grid.addWidget(slot, row, col)
        left_col.addLayout(acc_grid)
        food_header = QLabel('Food')
        food_header.setStyleSheet('font-size: 9px; font-weight: bold; color: #aaa;')
        left_col.addWidget(food_header)
        food_grid = QGridLayout()
        food_grid.setSpacing(2)
        for i in range(4):
            row, col = (i // 2, i % 2)
            slot = EquipmentSlotWidget(f'food{i + 1}', f'F{i + 1}')
            self.equip_slots[f'food{i + 1}'] = slot
            food_grid.addWidget(slot, row, col)
        left_col.addLayout(food_grid)
        equip_main_layout.addLayout(left_col)
        right_col = QVBoxLayout()
        right_col.setSpacing(2)
        head_header = QLabel('Head')
        head_header.setStyleSheet('font-size: 9px; font-weight: bold; color: #aaa;')
        right_col.addWidget(head_header)
        slot = EquipmentSlotWidget('head', 'H1')
        self.equip_slots['head'] = slot
        right_col.addWidget(slot)
        body_header = QLabel('Body')
        body_header.setStyleSheet('font-size: 9px; font-weight: bold; color: #aaa;')
        right_col.addWidget(body_header)
        slot = EquipmentSlotWidget('body', 'B1')
        self.equip_slots['body'] = slot
        right_col.addWidget(slot)
        shield_header = QLabel('Shield')
        shield_header.setStyleSheet('font-size: 9px; font-weight: bold; color: #aaa;')
        right_col.addWidget(shield_header)
        slot = EquipmentSlotWidget('shield', 'S1')
        self.equip_slots['shield'] = slot
        right_col.addWidget(slot)
        glider_header = QLabel('Glider')
        glider_header.setStyleSheet('font-size: 9px; font-weight: bold; color: #aaa;')
        right_col.addWidget(glider_header)
        slot = EquipmentSlotWidget('glider', 'G1')
        self.equip_slots['glider'] = slot
        right_col.addWidget(slot)
        module_header = QLabel('Module')
        module_header.setStyleSheet('font-size: 9px; font-weight: bold; color: #aaa;')
        right_col.addWidget(module_header)
        slot = EquipmentSlotWidget('sphere_mod', 'SM')
        self.equip_slots['sphere_mod'] = slot
        right_col.addWidget(slot)
        right_col.addStretch()
        equip_main_layout.addLayout(right_col)
        center_layout.addLayout(equip_main_layout)
        content.addWidget(center_panel, 1)
        self.stats_panel = StatsPanelWidget()
        content.addWidget(self.stats_panel)
        main_layout.addLayout(content, 1)
        footer = QHBoxLayout()
        footer.setSpacing(8)
        add_btn = QPushButton(t('inventory.add_item', default='Add Item'))
        add_btn.clicked.connect(self._show_add_item_dialog)
        footer.addWidget(add_btn)
        delete_btn = QPushButton(t('inventory.delete_item', default='Delete'))
        delete_btn.clicked.connect(self._delete_selected_item)
        footer.addWidget(delete_btn)
        edit_qty_btn = QPushButton(t('inventory.edit_qty', default='Edit Qty'))
        edit_qty_btn.clicked.connect(self._edit_quantity)
        footer.addWidget(edit_qty_btn)
        footer.addStretch()
        save_btn = QPushButton(t('button.save', default='Save'))
        save_btn.setStyleSheet('background-color: #43b581;')
        save_btn.clicked.connect(self._save_changes)
        footer.addWidget(save_btn)
        cancel_btn = QPushButton(t('button.cancel', default='Cancel'))
        cancel_btn.clicked.connect(self.close)
        footer.addWidget(cancel_btn)
        main_layout.addLayout(footer)
    def _load_inventory(self):
        self.inventory = get_player_inventory(self.player_uid)
        if not self.inventory.is_loaded:
            show_warning(self, t('error.title', default='Error'), t('inventory.load_error', default='Failed to load inventory.'))
            return
        main_container = self.inventory.get_container('main')
        if main_container:
            self.main_grid.load_items(main_container.slots)
        key_container = self.inventory.get_container('key')
        if key_container:
            self.key_grid.load_items(key_container.slots)
        equipment = self.inventory.get_equipment()
        for slot_name, item in equipment.items():
            if slot_name in self.equip_slots:
                self.equip_slots[slot_name].set_item(item)
        self._update_stats()
    def _update_stats(self):
        self.stats_panel.update_stats({'hp': 100, 'stamina': 100, 'attack': 10, 'defense': 10, 'work_speed': 70, 'weight': '0/500'})
        self.stats_panel.set_level(1, 0)
    def _on_item_selected(self, slot_data):
        self.selected_item = slot_data
    def _show_item_context_menu(self, slot_data, pos):
        if not slot_data:
            return
        menu = QMenu(self)
        menu.addAction(t('inventory.edit_qty', default='Edit Quantity')).triggered.connect(lambda: self._edit_quantity_for(slot_data))
        menu.addAction(t('inventory.delete_item', default='Delete')).triggered.connect(lambda: self._delete_item(slot_data))
        menu.exec(pos)
    def _show_add_item_dialog(self):
        dialog = ItemPickerDialog(self)
        dialog.item_selected.connect(self._add_item_to_inventory)
        dialog.exec()
    def _add_item_to_inventory(self, item_id: str, quantity: int):
        if self.inventory.add_item('main', item_id, quantity):
            self._set_modified(True)
            self._load_inventory()
    def _delete_selected_item(self):
        if hasattr(self, 'selected_item') and self.selected_item:
            self._delete_item(self.selected_item)
    def _delete_item(self, slot_data: dict):
        container_type = slot_data.get('container_type', 'main')
        slot_index = slot_data.get('slot_index', 0)
        reply = QMessageBox.question(self, t('inventory.delete_confirm.title', default='Delete Item'), t('inventory.delete_confirm.msg', default=f"Delete {slot_data.get('item_name', 'item')}?"), QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            if self.inventory.remove_item(container_type, slot_index):
                self._set_modified(True)
                self._load_inventory()
    def _edit_quantity(self):
        if hasattr(self, 'selected_item') and self.selected_item:
            self._edit_quantity_for(self.selected_item)
    def _edit_quantity_for(self, slot_data: dict):
        current_qty = slot_data.get('stack_count', 1)
        dialog = QuantityDialog(current_qty, self)
        if dialog.exec() == QDialog.Accepted:
            new_qty = dialog.get_quantity()
            container_type = slot_data.get('container_type', 'main')
            slot_index = slot_data.get('slot_index', 0)
            if self.inventory.update_quantity(container_type, slot_index, new_qty):
                self._set_modified(True)
                self._load_inventory()
    def _set_modified(self, modified: bool):
        self.modified = modified
        if modified:
            self.modified_label.setText(t('inventory.modified', default='* Modified'))
        else:
            self.modified_label.clear()
    def _save_changes(self):
        if self.inventory.save():
            self._set_modified(False)
            show_information(self, t('success.title', default='Success'), t('inventory.save_success', default='Inventory saved successfully!'))
            self.saved.emit()
        else:
            show_warning(self, t('error.title', default='Error'), t('inventory.save_error', default='Failed to save inventory.'))
    def closeEvent(self, event):
        if self.modified:
            reply = QMessageBox.question(self, t('inventory.unsaved.title', default='Unsaved Changes'), t('inventory.unsaved.msg', default='Discard unsaved changes?'), QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.No:
                event.ignore()
                return
        event.accept()
class QuantityDialog(QDialog):
    def __init__(self, current_qty: int=1, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t('inventory.edit_qty', default='Edit Quantity'))
        self.setFixedSize(200, 100)
        layout = QVBoxLayout(self)
        self.spin_box = QSpinBox()
        self.spin_box.setRange(1, 999)
        self.spin_box.setValue(current_qty)
        layout.addWidget(self.spin_box)
        btn_layout = QHBoxLayout()
        ok_btn = QPushButton(t('button.ok', default='OK'))
        ok_btn.clicked.connect(self.accept)
        btn_layout.addWidget(ok_btn)
        cancel_btn = QPushButton(t('button.cancel', default='Cancel'))
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
    def get_quantity(self) -> int:
        return self.spin_box.value()
def open_inventory_editor(player_uid: str, player_name: str='Player', parent=None):
    window = InventoryEditorWindow(player_uid, player_name, parent)
    window.show()
    return window