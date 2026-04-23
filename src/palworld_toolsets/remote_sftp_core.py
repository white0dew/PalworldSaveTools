from __future__ import annotations

import json
import os
import posixpath
import re
import shutil
import stat
import tempfile
import zipfile
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from common import get_base_directory

SYNC_FILE_NAMES = ('Level.sav', 'LevelMeta.sav', 'WorldOption.sav')
SETTINGS_KEY = 'remote_sftp'


class SftpDependencyError(RuntimeError):
    pass


class SftpConfigError(ValueError):
    pass


class SftpOperationError(RuntimeError):
    pass


def normalize_host(host: str) -> str:
    value = (host or '').strip()
    if not value:
        return ''
    if '://' in value:
        parsed = urlparse(value)
        value = parsed.hostname or parsed.path or value
    value = value.strip().strip('/')
    if '/' in value:
        value = value.split('/', 1)[0]
    return value


def normalize_remote_path(path: str) -> str:
    value = (path or '').strip().replace('\\', '/')
    if not value or value in ('.', './'):
        return '.'
    if value == '/':
        return '/'
    if value.startswith('/'):
        normalized = posixpath.normpath(value)
        return normalized if normalized else '/'
    normalized = posixpath.normpath(value.lstrip('./'))
    return normalized if normalized not in ('', '.') else '.'


def sanitize_path_segment(value: str) -> str:
    cleaned = re.sub(r'[^A-Za-z0-9._-]+', '_', value or '')
    cleaned = cleaned.strip('._-')
    return cleaned or 'world'


def build_cache_slug(settings: dict[str, Any], require_credentials: bool = False) -> str:
    if require_credentials:
        prepared = validate_settings(settings)
    else:
        prepared = {
            'host': normalize_host(settings.get('host', '')),
            'username': (settings.get('username') or '').strip(),
            'remote_path': normalize_remote_path(settings.get('remote_path') or '.'),
        }
    host = sanitize_path_segment(prepared.get('host', '') or 'host')
    username = sanitize_path_segment(prepared.get('username', '') or 'user')
    remote_name = sanitize_path_segment(posixpath.basename(prepared.get('remote_path', '.').rstrip('/')) or 'world')
    return f'{host}_{username}_{remote_name}'


def get_default_config_path(base_dir: str | os.PathLike[str] | None = None) -> Path:
    root = Path(base_dir or get_base_directory())
    return root / 'src' / 'data' / 'configs' / 'user.cfg'


def load_settings(config_path: str | os.PathLike[str] | None = None) -> dict[str, Any]:
    path = Path(config_path or get_default_config_path())
    if not path.exists():
        return {}
    try:
        with path.open('r', encoding='utf-8') as fh:
            data = json.load(fh)
    except Exception:
        return {}
    settings = data.get(SETTINGS_KEY, {})
    return settings if isinstance(settings, dict) else {}


def save_settings(settings: dict[str, Any], config_path: str | os.PathLike[str] | None = None) -> dict[str, Any]:
    path = Path(config_path or get_default_config_path())
    path.parent.mkdir(parents=True, exist_ok=True)
    data: dict[str, Any] = {}
    if path.exists():
        try:
            with path.open('r', encoding='utf-8') as fh:
                loaded = json.load(fh)
                if isinstance(loaded, dict):
                    data = loaded
        except Exception:
            data = {}
    data[SETTINGS_KEY] = {
        'host': (settings.get('host') or '').strip(),
        'port': int(settings.get('port') or 22),
        'username': (settings.get('username') or '').strip(),
        'password': settings.get('password') or '',
        'remote_path': normalize_remote_path(settings.get('remote_path') or '.'),
    }
    with path.open('w', encoding='utf-8') as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
    return data[SETTINGS_KEY]


def validate_settings(settings: dict[str, Any]) -> dict[str, Any]:
    host = normalize_host(settings.get('host', ''))
    if not host:
        raise SftpConfigError('SFTP host is required.')
    username = (settings.get('username') or '').strip()
    if not username:
        raise SftpConfigError('SFTP username is required.')
    password = settings.get('password') or ''
    if not password:
        raise SftpConfigError('SFTP password is required.')
    port = int(settings.get('port') or 22)
    remote_path = normalize_remote_path(settings.get('remote_path') or '.')
    return {
        'host': host,
        'port': port,
        'username': username,
        'password': password,
        'remote_path': remote_path,
    }


def get_savebackup_root(base_dir: str | os.PathLike[str] | None = None) -> Path:
    root = Path(base_dir or get_base_directory())
    path = root / 'savebackup'
    path.mkdir(parents=True, exist_ok=True)
    return path


def build_world_cache_dir(settings: dict[str, Any], base_dir: str | os.PathLike[str] | None = None) -> Path:
    validate_settings(settings)
    return get_savebackup_root(base_dir) / build_cache_slug(settings, require_credentials=True)


def iter_sync_relative_paths(local_world_dir: str | os.PathLike[str]) -> list[str]:
    root = Path(local_world_dir)
    paths: list[str] = []
    for file_name in SYNC_FILE_NAMES:
        candidate = root / file_name
        if candidate.is_file():
            paths.append(file_name)
    players_dir = root / 'Players'
    if players_dir.is_dir():
        for path in sorted(players_dir.rglob('*')):
            if path.is_file():
                paths.append(path.relative_to(root).as_posix())
    return paths


def join_remote_path(base_path: str, child_path: str) -> str:
    base = normalize_remote_path(base_path)
    child = (child_path or '').replace('\\', '/').strip('/')
    if not child:
        return base
    if base in ('', '.'):
        return normalize_remote_path(child)
    return normalize_remote_path(posixpath.join(base, child))


def get_parent_remote_path(path: str) -> str:
    current = normalize_remote_path(path)
    if current in ('.', '/'):
        return current
    parent = posixpath.dirname(current)
    if current.startswith('/'):
        return parent or '/'
    return parent if parent not in ('', '.') else '.'


def create_zip_backup(world_dir: str | os.PathLike[str], backup_root: str | os.PathLike[str] | None = None) -> Path:
    world_path = Path(world_dir)
    if not world_path.is_dir():
        raise FileNotFoundError(f'World directory not found: {world_path}')
    archives_root = Path(backup_root) if backup_root else world_path.parent / 'archives'
    archives_root.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    archive_path = archives_root / f'{world_path.name}_{timestamp}.zip'
    with zipfile.ZipFile(archive_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(world_path.rglob('*')):
            if path.is_file():
                zf.write(path, path.relative_to(world_path).as_posix())
    return archive_path


def _is_dir_attr(attr: Any) -> bool:
    return stat.S_ISDIR(getattr(attr, 'st_mode', 0))


def download_directory(sftp_client: Any, remote_dir: str, local_dir: str | os.PathLike[str]) -> int:
    local_path = Path(local_dir)
    local_path.mkdir(parents=True, exist_ok=True)
    downloaded = 0
    for entry in sorted(sftp_client.listdir_attr(remote_dir), key=lambda item: item.filename.lower()):
        remote_child = join_remote_path(remote_dir, entry.filename)
        local_child = local_path / entry.filename
        if _is_dir_attr(entry):
            downloaded += download_directory(sftp_client, remote_child, local_child)
        else:
            local_child.parent.mkdir(parents=True, exist_ok=True)
            sftp_client.get(remote_child, str(local_child))
            downloaded += 1
    return downloaded


def ensure_remote_directory(sftp_client: Any, remote_dir: str) -> None:
    path = normalize_remote_path(remote_dir)
    if path in ('.', '/'):
        return
    current = '/' if path.startswith('/') else ''
    for part in [segment for segment in path.strip('/').split('/') if segment]:
        if current in ('', '/'):
            current = f'{current}{part}' if current == '/' else part
        else:
            current = f'{current}/{part}'
        try:
            sftp_client.mkdir(current)
        except Exception:
            pass


def upload_world_targets(sftp_client: Any, local_world_dir: str | os.PathLike[str], remote_world_dir: str) -> int:
    local_root = Path(local_world_dir)
    if not local_root.is_dir():
        raise FileNotFoundError(f'Local world directory not found: {local_root}')
    uploaded = 0
    remote_root = normalize_remote_path(remote_world_dir)
    ensure_remote_directory(sftp_client, remote_root)
    for relative_path in iter_sync_relative_paths(local_root):
        local_file = local_root / relative_path
        remote_file = join_remote_path(remote_root, relative_path.replace('\\', '/'))
        ensure_remote_directory(sftp_client, get_parent_remote_path(remote_file))
        sftp_client.put(str(local_file), remote_file)
        uploaded += 1
    return uploaded


@contextmanager
def sftp_client(settings: dict[str, Any]):
    validated = validate_settings(settings)
    try:
        import paramiko
    except ImportError as exc:
        raise SftpDependencyError('paramiko is required for Remote SFTP support.') from exc
    transport = paramiko.Transport((validated['host'], validated['port']))
    transport.connect(username=validated['username'], password=validated['password'])
    client = paramiko.SFTPClient.from_transport(transport)
    try:
        yield client
    finally:
        try:
            client.close()
        finally:
            transport.close()


def list_remote_directories_for_settings(settings: dict[str, Any], remote_dir: str | None = None) -> dict[str, Any]:
    validated = validate_settings(settings)
    current_path = normalize_remote_path(remote_dir or validated['remote_path'])
    with sftp_client(validated) as client:
        entries = []
        for entry in sorted(client.listdir_attr(current_path), key=lambda item: item.filename.lower()):
            if _is_dir_attr(entry):
                entries.append({
                    'name': entry.filename,
                    'path': join_remote_path(current_path, entry.filename),
                })
    return {'path': current_path, 'directories': entries}


def test_connection(settings: dict[str, Any]) -> dict[str, Any]:
    validated = validate_settings(settings)
    probe_path = normalize_remote_path(validated['remote_path'])
    with sftp_client(validated) as client:
        entries = client.listdir_attr(probe_path)
    dir_names = [entry.filename for entry in entries if _is_dir_attr(entry)]
    return {
        'host': validated['host'],
        'port': validated['port'],
        'remote_path': probe_path,
        'directory_count': len(dir_names),
        'sample_directories': dir_names[:10],
    }


def download_world(settings: dict[str, Any], base_dir: str | os.PathLike[str] | None = None) -> dict[str, Any]:
    validated = validate_settings(settings)
    target_dir = build_world_cache_dir(validated, base_dir=base_dir)
    target_dir.parent.mkdir(parents=True, exist_ok=True)
    temp_dir = Path(tempfile.mkdtemp(prefix=f'{target_dir.name}_', dir=target_dir.parent))
    try:
        with sftp_client(validated) as client:
            downloaded_files = download_directory(client, validated['remote_path'], temp_dir)
        if target_dir.exists():
            shutil.rmtree(target_dir)
        temp_dir.rename(target_dir)
        archive_path = create_zip_backup(target_dir)
        return {
            'local_dir': str(target_dir),
            'archive_path': str(archive_path),
            'downloaded_files': downloaded_files,
        }
    except Exception as exc:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise SftpOperationError(f'Failed to download world directory: {exc}') from exc


def upload_world(settings: dict[str, Any], base_dir: str | os.PathLike[str] | None = None) -> dict[str, Any]:
    validated = validate_settings(settings)
    local_dir = build_world_cache_dir(validated, base_dir=base_dir)
    if not local_dir.is_dir():
        raise FileNotFoundError(f'Local world directory not found: {local_dir}')
    try:
        with sftp_client(validated) as client:
            uploaded_files = upload_world_targets(client, local_dir, validated['remote_path'])
        return {
            'local_dir': str(local_dir),
            'uploaded_files': uploaded_files,
        }
    except Exception as exc:
        raise SftpOperationError(f'Failed to upload world directory: {exc}') from exc
