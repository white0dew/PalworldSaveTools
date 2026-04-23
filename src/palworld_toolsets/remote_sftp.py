from __future__ import annotations

import os
import posixpath

from import_libs import *
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QGridLayout, QTreeWidgetItem

from common import open_file_with_default_app
from palworld_toolsets import remote_sftp_core as core


def load_styles(widget):
    user_cfg_path = os.path.join(get_src_directory(), 'data', 'configs', 'user.cfg')
    theme = 'dark'
    if os.path.exists(user_cfg_path):
        try:
            with open(user_cfg_path, 'r', encoding='utf-8') as fh:
                data = json.load(fh)
            theme = data.get('theme', 'dark')
        except Exception:
            pass
    qss_path = os.path.join(get_src_directory(), 'data', 'gui', f'{theme}mode.qss')
    if os.path.exists(qss_path):
        with open(qss_path, 'r', encoding='utf-8') as fh:
            widget.setStyleSheet(fh.read())


class RemoteDirectoryBrowserDialog(QDialog):
    def __init__(self, settings, start_path='.', parent=None):
        super().__init__(parent)
        self.settings = settings
        self.current_path = core.normalize_remote_path(start_path or '.')
        self.selected_path = self.current_path
        self.setWindowTitle(t('remote_sftp.browser.title'))
        self.setModal(True)
        self.resize(560, 460)
        load_styles(self)
        self._setup_ui()
        QTimer.singleShot(0, lambda: self._load_directory(self.current_path))

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        path_row = QHBoxLayout()
        self.path_edit = QLineEdit(self.current_path)
        self.path_edit.setPlaceholderText('.')
        up_btn = QPushButton(t('remote_sftp.browser.up'))
        reload_btn = QPushButton(t('remote_sftp.browser.reload'))
        go_btn = QPushButton(t('remote_sftp.browser.go'))
        up_btn.clicked.connect(self._go_up)
        reload_btn.clicked.connect(lambda: self._load_directory(self.path_edit.text()))
        go_btn.clicked.connect(lambda: self._load_directory(self.path_edit.text()))
        path_row.addWidget(self.path_edit, 1)
        path_row.addWidget(up_btn)
        path_row.addWidget(reload_btn)
        path_row.addWidget(go_btn)
        layout.addLayout(path_row)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels([t('remote_sftp.browser.column')])
        self.tree.header().setStretchLastSection(True)
        self.tree.itemDoubleClicked.connect(self._on_item_activated)
        self.tree.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.tree, 1)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        select_current_btn = QPushButton(t('remote_sftp.browser.select_current'))
        select_btn = QPushButton(t('remote_sftp.browser.select'))
        cancel_btn = QPushButton(t('Cancel'))
        select_current_btn.clicked.connect(self._select_current)
        select_btn.clicked.connect(self._select_selected)
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(select_current_btn)
        buttons.addWidget(select_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)

    def _go_up(self):
        parent_path = core.get_parent_remote_path(self.current_path)
        self._load_directory(parent_path)

    def _load_directory(self, path):
        target_path = core.normalize_remote_path(path)
        self.path_edit.setText(target_path)

        def task():
            return core.list_remote_directories_for_settings(self.settings, target_path)

        def on_done(result):
            self.current_path = result['path']
            self.selected_path = self.current_path
            self.path_edit.setText(self.current_path)
            self.tree.clear()
            for entry in result['directories']:
                item = QTreeWidgetItem([entry['name']])
                item.setData(0, Qt.UserRole, entry['path'])
                self.tree.addTopLevelItem(item)
            if self.tree.topLevelItemCount() > 0:
                self.tree.setCurrentItem(self.tree.topLevelItem(0))

        run_with_loading(on_done, task, parent=self)

    def _on_item_activated(self, item, _column):
        self._load_directory(item.data(0, Qt.UserRole) or self.current_path)

    def _on_selection_changed(self):
        item = self.tree.currentItem()
        if item is not None:
            self.selected_path = item.data(0, Qt.UserRole) or self.current_path

    def _select_current(self):
        self.selected_path = self.current_path
        self.accept()

    def _select_selected(self):
        item = self.tree.currentItem()
        if item is not None:
            self.selected_path = item.data(0, Qt.UserRole) or self.current_path
        else:
            self.selected_path = self.current_path
        self.accept()


class RemoteSftpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t('tool.remote_sftp'))
        self.setModal(True)
        self.resize(760, 620)
        self._autosave_timer = QTimer(self)
        self._autosave_timer.setSingleShot(True)
        self._autosave_timer.timeout.connect(self._autosave_settings)
        load_styles(self)
        self._setup_ui()
        self._load_saved_settings()
        self._update_local_preview()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel(t('remote_sftp.title'))
        title.setFont(QFont('Segoe UI', 14, QFont.Bold))
        layout.addWidget(title)

        subtitle = QLabel(t('remote_sftp.subtitle'))
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        form_frame = QFrame()
        form_frame.setObjectName('glass')
        form_layout = QGridLayout(form_frame)
        form_layout.setContentsMargins(14, 14, 14, 14)
        form_layout.setHorizontalSpacing(12)
        form_layout.setVerticalSpacing(10)

        self.host_edit = QLineEdit()
        self.host_edit.setPlaceholderText('sftp://example.com')
        self.port_edit = QLineEdit('22')
        self.username_edit = QLineEdit()
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.remote_path_edit = QLineEdit('.')
        self.remote_path_edit.setPlaceholderText('pal/Saved/SaveGames/0/World')

        self.host_edit.textChanged.connect(self._update_local_preview)
        self.username_edit.textChanged.connect(self._update_local_preview)
        self.remote_path_edit.textChanged.connect(self._update_local_preview)
        for widget in (self.host_edit, self.port_edit, self.username_edit, self.password_edit, self.remote_path_edit):
            widget.textChanged.connect(self._schedule_autosave)

        fields = [
            (t('remote_sftp.host'), self.host_edit),
            (t('remote_sftp.port'), self.port_edit),
            (t('remote_sftp.username'), self.username_edit),
            (t('remote_sftp.password'), self.password_edit),
            (t('remote_sftp.remote_path'), self.remote_path_edit),
        ]
        for row, (label_text, widget) in enumerate(fields):
            label = QLabel(label_text)
            label.setMinimumWidth(110)
            form_layout.addWidget(label, row, 0)
            form_layout.addWidget(widget, row, 1)

        browse_btn = QPushButton(t('remote_sftp.browse_remote'))
        browse_btn.clicked.connect(self._browse_remote)
        form_layout.addWidget(browse_btn, 4, 2)

        self.local_path_value = QLineEdit()
        self.local_path_value.setReadOnly(True)
        form_layout.addWidget(QLabel(t('remote_sftp.local_cache')), 5, 0)
        form_layout.addWidget(self.local_path_value, 5, 1, 1, 2)

        layout.addWidget(form_frame)

        actions = QHBoxLayout()
        self.test_btn = QPushButton(t('remote_sftp.test'))
        self.download_btn = QPushButton(t('remote_sftp.download'))
        self.open_btn = QPushButton(t('remote_sftp.open_local'))
        self.sync_btn = QPushButton(t('remote_sftp.sync'))
        close_btn = QPushButton(t('Cancel'))
        self.test_btn.clicked.connect(self._test_connection)
        self.download_btn.clicked.connect(self._download_world)
        self.open_btn.clicked.connect(self._open_local_folder)
        self.sync_btn.clicked.connect(self._sync_world)
        close_btn.clicked.connect(self.accept)
        actions.addWidget(self.test_btn)
        actions.addWidget(self.download_btn)
        actions.addWidget(self.open_btn)
        actions.addWidget(self.sync_btn)
        actions.addStretch(1)
        actions.addWidget(close_btn)
        layout.addLayout(actions)

        note = QLabel(t('remote_sftp.note'))
        note.setWordWrap(True)
        layout.addWidget(note)

        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        self.log_edit.setPlaceholderText(t('remote_sftp.log_placeholder'))
        layout.addWidget(self.log_edit, 1)

    def _load_saved_settings(self):
        settings = core.load_settings()
        self.host_edit.setText(settings.get('host', ''))
        self.port_edit.setText(str(settings.get('port', 22)))
        self.username_edit.setText(settings.get('username', ''))
        self.password_edit.setText(settings.get('password', ''))
        self.remote_path_edit.setText(settings.get('remote_path', '.'))

    def _collect_settings(self):
        port_text = self.port_edit.text().strip() or '22'
        try:
            port = int(port_text)
        except ValueError:
            raise core.SftpConfigError(t('remote_sftp.error.invalid_port'))
        return {
            'host': self.host_edit.text().strip(),
            'port': port,
            'username': self.username_edit.text().strip(),
            'password': self.password_edit.text(),
            'remote_path': self.remote_path_edit.text().strip() or '.',
        }

    def _persist_settings(self):
        settings = self._collect_settings()
        core.save_settings(settings)
        return settings

    def _autosave_settings(self):
        port_text = self.port_edit.text().strip() or '22'
        try:
            port = int(port_text)
        except ValueError:
            return
        core.save_settings({
            'host': self.host_edit.text().strip(),
            'port': port,
            'username': self.username_edit.text().strip(),
            'password': self.password_edit.text(),
            'remote_path': self.remote_path_edit.text().strip() or '.',
        })

    def _schedule_autosave(self):
        self._autosave_timer.start(250)

    def _append_log(self, text):
        self.log_edit.append(text)
        cursor = self.log_edit.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.log_edit.setTextCursor(cursor)

    def _update_local_preview(self):
        settings = {
            'host': self.host_edit.text().strip(),
            'username': self.username_edit.text().strip(),
            'remote_path': self.remote_path_edit.text().strip() or '.',
        }
        preview = core.get_savebackup_root() / core.build_cache_slug(settings)
        self.local_path_value.setText(str(preview))

    def _require_settings(self, require_remote_path=True):
        try:
            settings = self._collect_settings()
            if require_remote_path and not settings.get('remote_path'):
                raise core.SftpConfigError(t('remote_sftp.error.remote_path_required'))
            return settings
        except Exception as exc:
            QMessageBox.warning(self, t('Warning'), str(exc))
            return None

    def _browse_remote(self):
        settings = self._require_settings(require_remote_path=False)
        if not settings:
            return
        try:
            core.validate_settings(settings)
        except Exception as exc:
            QMessageBox.warning(self, t('Warning'), str(exc))
            return
        browser = RemoteDirectoryBrowserDialog(settings, self.remote_path_edit.text().strip() or '.', self)
        if browser.exec() == QDialog.Accepted:
            self.remote_path_edit.setText(browser.selected_path)
            self._persist_settings()
            self._append_log(t('remote_sftp.log.selected_remote', path=browser.selected_path))

    def _run_task(self, start_message, task, on_done):
        try:
            self._persist_settings()
        except Exception as exc:
            QMessageBox.warning(self, t('Warning'), str(exc))
            return
        self._append_log(start_message)
        run_with_loading(on_done, task, parent=self)

    def _test_connection(self):
        settings = self._require_settings()
        if not settings:
            return

        def task():
            return core.test_connection(settings)

        def on_done(result):
            dirs = ', '.join(result['sample_directories']) if result['sample_directories'] else '-'
            self._append_log(t('remote_sftp.log.connection_ok', host=result['host'], port=result['port'], path=result['remote_path']))
            self._append_log(t('remote_sftp.log.directory_sample', count=result['directory_count'], names=dirs))
            QMessageBox.information(self, t('Success'), t('remote_sftp.success.connection_tested'))

        self._run_task(t('remote_sftp.log.testing'), task, on_done)

    def _download_world(self):
        settings = self._require_settings()
        if not settings:
            return

        def task():
            return core.download_world(settings)

        def on_done(result):
            self._append_log(t('remote_sftp.log.download_ok', count=result['downloaded_files'], local_dir=result['local_dir']))
            self._append_log(t('remote_sftp.log.backup_ok', archive=result['archive_path']))
            QMessageBox.information(self, t('Success'), t('remote_sftp.success.downloaded'))

        self._run_task(t('remote_sftp.log.downloading'), task, on_done)

    def _sync_world(self):
        settings = self._require_settings()
        if not settings:
            return
        try:
            local_dir = core.resolve_active_world_dir(settings)
        except FileNotFoundError:
            local_dir = core.build_world_cache_dir(settings)
            QMessageBox.warning(self, t('Warning'), t('remote_sftp.error.local_world_missing', path=str(local_dir)))
            return

        def task():
            return core.upload_world(settings)

        def on_done(result):
            self._append_log(t('remote_sftp.log.upload_ok', count=result['uploaded_files'], local_dir=result['local_dir']))
            QMessageBox.information(self, t('Success'), t('remote_sftp.success.synced'))

        self._run_task(t('remote_sftp.log.uploading'), task, on_done)

    def _open_local_folder(self):
        settings = {
            'host': self.host_edit.text().strip(),
            'username': self.username_edit.text().strip(),
            'remote_path': self.remote_path_edit.text().strip() or '.',
        }
        path = core.build_world_cache_dir({
            'host': settings['host'],
            'port': int(self.port_edit.text().strip() or '22') if (self.port_edit.text().strip() or '22').isdigit() else 22,
            'username': settings['username'],
            'password': self.password_edit.text(),
            'remote_path': settings['remote_path'],
        })
        path.mkdir(parents=True, exist_ok=True)
        if open_file_with_default_app(str(path)):
            self._append_log(t('remote_sftp.log.opened_local', path=str(path)))
        else:
            QMessageBox.warning(self, t('Warning'), t('remote_sftp.error.open_local_failed', path=str(path)))

    def closeEvent(self, event):
        try:
            self._persist_settings()
        except Exception:
            pass
        super().closeEvent(event)

    def accept(self):
        try:
            self._persist_settings()
        except Exception:
            pass
        super().accept()

    def reject(self):
        try:
            self._persist_settings()
        except Exception:
            pass
        super().reject()



def remote_sftp_tool():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return RemoteSftpDialog()
