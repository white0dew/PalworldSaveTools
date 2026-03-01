from __future__ import annotations
import os, sys, shutil, subprocess, threading, queue, argparse, re, platform, time, json, tempfile, ssl, urllib.request
from pathlib import Path
from typing import Optional, Tuple
STABLE_VERSION_URL = 'https://raw.githubusercontent.com/deafdudecomputers/PalworldSaveTools/main/src/common.py'
RELEASE_DOWNLOAD_URL = 'https://github.com/deafdudecomputers/PalworldSaveTools/releases/download/v{version}/PST_standalone_v{version}.7z'
PROJECT_DIR = Path(__file__).resolve().parent
VENV_DIR = PROJECT_DIR / 'pst_venv'
SENTINEL = VENV_DIR / '.ready'
USE_ANSI = True
if os.name == 'nt':
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 5)
    except Exception:
        pass
def ansi(code: str) -> str:
    return code if USE_ANSI else ''
RESET, BOLD, GREEN, YELLOW, RED, CYAN, DIM = (ansi('\x1b[0m'), ansi('\x1b[1m'), ansi('\x1b[32m'), ansi('\x1b[33m'), ansi('\x1b[31m'), ansi('\x1b[36m'), ansi('\x1b[2m'))
def step_label(n: int, total: int, text: str) -> str:
    return f'[{n}/{total}]{text}'
def print_step_working(label: str):
    sys.stdout.write(f'{BOLD}{label}...{RESET}\r')
    sys.stdout.flush()
def print_ok(label: str):
    sys.stdout.write('\r' + ' ' * 120 + '\r')
    print(f'{BOLD}{label} {GREEN}OK{RESET}')
def print_fail(label: str):
    sys.stdout.write('\r' + ' ' * 120 + '\r')
    print(f'{BOLD}{label} {RED}FAILED{RESET}')
def reader_thread(proc: subprocess.Popen, q: queue.Queue):
    assert proc.stdout is not None
    try:
        for raw in proc.stdout:
            q.put(raw.rstrip('\n'))
    except Exception:
        pass
    finally:
        try:
            proc.stdout.close()
        except Exception:
            pass
        q.put(None)
def progress_bar(pct: int, width: int=30) -> str:
    filled = int(pct / 100.0 * width)
    return '[' + '#' * filled + '-' * (width - filled) + ']'
_SPINNER_FRAMES = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
def run_and_watch(cmd, cwd=None, env=None):
    filter_keys = ('Collecting', 'Downloading', '%', 'Building wheel for', 'Installing collected packages', 'Successfully installed', 'ERROR', 'Failed')
    cmd_list = list(map(str, cmd))
    proc = subprocess.Popen(cmd_list, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, cwd=cwd, env=env)
    q: queue.Queue = queue.Queue()
    threading.Thread(target=reader_thread, args=(proc, q), daemon=True).start()
    progress_pct, last_shown_msg = (None, None)
    try:
        while True:
            try:
                line = q.get(timeout=0.08)
            except queue.Empty:
                line = None
            if line is None:
                if proc.poll() is not None and q.empty():
                    break
                continue
            s = line.rstrip()
            m = re.search('(\\d{1,3})\\s*%+', s)
            pct = int(m.group(1)) if m else None
            if pct is not None:
                progress_pct = max(0, min(100, pct))
            if any((key in s for key in filter_keys)) or progress_pct is not None:
                if s != last_shown_msg:
                    if progress_pct is not None:
                        sys.stdout.write(f'\r{CYAN}{progress_bar(progress_pct, width=28)} {progress_pct:3d}%{RESET}')
                        sys.stdout.flush()
                    else:
                        sys.stdout.write('\r' + ' ' * 120 + '\r')
                        print(f'{CYAN}> {s}{RESET}')
                    last_shown_msg = s
    finally:
        sys.stdout.write('\r' + ' ' * 120 + '\r')
        sys.stdout.flush()
    return proc.wait()
def run_apt_install(packages, label='Installing'):
    total = len(packages)
    cmd = ['sudo', 'apt-get', 'install', '-y', '-qq'] + packages
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    q: queue.Queue = queue.Queue()
    threading.Thread(target=reader_thread, args=(proc, q), daemon=True).start()
    installed_count = 0
    spinner_idx = 0
    current_pct = 0
    error_keywords = ('error', 'failed', 'unable', 'cannot', 'permission denied', 'could not')
    try:
        while True:
            try:
                line = q.get(timeout=0.08)
            except queue.Empty:
                line = None
            if line is None:
                if proc.poll() is not None and q.empty():
                    break
            s = line.rstrip() if line else ''
            if 'Setting up' in s or 'Unpacking' in s:
                installed_count += 1
                current_pct = min(100, int(installed_count / total * 100)) if total > 0 else 100
            if any((err in s.lower() for err in error_keywords)):
                sys.stdout.write('\r' + ' ' * 120 + '\r')
                print(f'{RED}> {s}{RESET}')
            spinner_idx = (spinner_idx + 1) % len(_SPINNER_FRAMES)
            if current_pct > 0:
                sys.stdout.write(f'\r{CYAN}{progress_bar(current_pct, width=28)} {label} ({installed_count}/{total}) {_SPINNER_FRAMES[spinner_idx]}{RESET}')
            else:
                sys.stdout.write(f'\r{CYAN}{label}... {_SPINNER_FRAMES[spinner_idx]}{RESET}')
            sys.stdout.flush()
    finally:
        sys.stdout.write('\r' + ' ' * 120 + '\r')
        sys.stdout.flush()
    return proc.wait()
def nuke_build_artifacts():
    print_step_working('Cleaning environment')
    for item in ['build', 'dist']:
        path = PROJECT_DIR / item
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)
    for p in PROJECT_DIR.rglob('*.egg-info'):
        if p.is_dir():
            shutil.rmtree(p, ignore_errors=True)
    for p in PROJECT_DIR.rglob('__pycache__'):
        if p.is_dir():
            shutil.rmtree(p, ignore_errors=True)
    print_ok('Environment cleaned')
def venv_python_path() -> Path:
    if os.name == 'nt':
        return VENV_DIR / 'Scripts' / 'python.exe'
    return VENV_DIR / 'bin' / 'python'
def ensure_python_venv_installed():
    if os.name != 'posix' or platform.system() != 'Linux':
        return True
    is_debian_based = False
    try:
        result = subprocess.run(['which', 'apt'], capture_output=True, timeout=5)
        is_debian_based = result.returncode == 0
    except Exception:
        pass
    if not is_debian_based:
        return True
    py_version = f'python{sys.version_info.major}.{sys.version_info.minor}'
    print(f'{DIM}Detected Python: {py_version} on Debian/Ubuntu-based system{RESET}')
    test_venv = PROJECT_DIR / '.test_venv'
    if test_venv.exists():
        shutil.rmtree(test_venv, ignore_errors=True)
    try:
        result = subprocess.run([sys.executable, '-m', 'venv', str(test_venv)], capture_output=True, timeout=30)
        if result.returncode == 0:
            shutil.rmtree(test_venv, ignore_errors=True)
            return True
    except Exception:
        pass
    finally:
        if test_venv.exists():
            shutil.rmtree(test_venv, ignore_errors=True)
    packages_to_install = []
    for pkg in [f'{py_version}-venv', f'{py_version}-dev', 'python3-venv', 'python3-pip', 'python3-dev', 'python3-tk']:
        try:
            result = subprocess.run(['dpkg', '-s', pkg], capture_output=True, timeout=5)
            if result.returncode != 0:
                packages_to_install.append(pkg)
        except Exception:
            packages_to_install.append(pkg)
    packages_to_install = list(dict.fromkeys(packages_to_install))
    if not packages_to_install:
        return True
    print(f"{YELLOW}Missing required packages: {', '.join(packages_to_install)}{RESET}")
    print_step_working('Installing system packages')
    try:
        result = run_apt_install(packages_to_install, 'Installing')
        if result == 0:
            print_ok('System packages installed')
            return True
        else:
            print_fail('System package installation failed')
            print(f"{RED}Please run manually: sudo apt install -y {' '.join(packages_to_install)}{RESET}")
            return False
    except Exception as e:
        print_fail(f'System package installation: {e}')
        return False
def nuke_venv():
    if VENV_DIR.exists():
        shutil.rmtree(VENV_DIR, ignore_errors=True)
        if SENTINEL.exists():
            SENTINEL.unlink(missing_ok=True)
def ensure_qt_dependencies():
    if os.name != 'posix' or platform.system() != 'Linux':
        return True
    is_debian_based = False
    try:
        result = subprocess.run(['which', 'apt'], capture_output=True, timeout=5)
        is_debian_based = result.returncode == 0
    except Exception:
        pass
    if not is_debian_based:
        return True
    qt_packages = ['libxcb-cursor0', 'libxcb-xinerama0', 'libxcb-xkb1', 'libxcb-icccm4', 'libxcb-image0', 'libxcb-keysyms1', 'libxcb-randr0', 'libxcb-render-util0', 'libxcb-xfixes0', 'libxcb-shape0', 'libxkbcommon-x11-0', 'libfontconfig1', 'libgl1']
    packages_to_install = []
    for pkg in qt_packages:
        try:
            result = subprocess.run(['dpkg', '-s', pkg], capture_output=True, timeout=5)
            if result.returncode != 0:
                packages_to_install.append(pkg)
        except Exception:
            packages_to_install.append(pkg)
    if not packages_to_install:
        return True
    print(f"{YELLOW}Missing Qt dependencies: {', '.join(packages_to_install)}{RESET}")
    print_step_working('Installing Qt dependencies')
    try:
        result = run_apt_install(packages_to_install, 'Installing Qt')
        if result == 0:
            print_ok('Qt dependencies installed')
            return True
        else:
            print_fail('Qt dependency installation failed')
            print(f"{RED}Please run manually: sudo apt install -y {' '.join(packages_to_install)}{RESET}")
            return False
    except Exception as e:
        print_fail(f'Qt dependency installation: {e}')
        return False
def is_standalone_mode():
    cfg_path = PROJECT_DIR / 'src' / 'data' / 'configs' / 'runtime.cfg'
    try:
        import configparser
        cfg = configparser.ConfigParser()
        cfg.read(str(cfg_path))
        return cfg.getboolean('build', 'standalone', fallback=False)
    except:
        return False
def get_auto_update_enabled():
    cfg_path = PROJECT_DIR / 'src' / 'data' / 'configs' / 'config.json'
    try:
        with open(cfg_path, 'r') as f:
            config = json.load(f)
        return config.get('auto_update', False)
    except:
        return False
def git_pull_if_source():
    if is_standalone_mode():
        return
    if not get_auto_update_enabled():
        return
    try:
        result = subprocess.run(['git', 'rev-parse', '--is-inside-work-tree'], capture_output=True, text=True, timeout=5, cwd=str(PROJECT_DIR))
        if result.returncode != 0 or 'true' not in result.stdout.strip().lower():
            return
    except:
        return
    print_step_working('[0/3] Checking for updates')
    try:
        fetch_result = subprocess.run(['git', 'fetch', 'origin'], capture_output=True, text=True, timeout=60, cwd=str(PROJECT_DIR))
        if fetch_result.returncode != 0:
            print_ok('[0/3] Update check skipped (offline)')
            return
        local_result = subprocess.run(['git', 'rev-parse', 'HEAD'], capture_output=True, text=True, timeout=10, cwd=str(PROJECT_DIR))
        remote_result = subprocess.run(['git', 'rev-parse', '@{u}'], capture_output=True, text=True, timeout=10, cwd=str(PROJECT_DIR))
        if local_result.returncode != 0 or remote_result.returncode != 0:
            print_ok('[0/3] Update check skipped')
            return
        local_commit = local_result.stdout.strip()
        remote_commit = remote_result.stdout.strip()
        if local_commit == remote_commit:
            print_ok('[0/3] Already up-to-date')
            return
        print(f'{CYAN}[0/3] Updating...{RESET}')
        pull_result = subprocess.run(['git', 'pull'], capture_output=True, text=True, timeout=120, cwd=str(PROJECT_DIR))
        if pull_result.returncode == 0:
            print_ok('[0/3] Updated successfully')
        else:
            print_fail('[0/3] Update failed')
    except subprocess.TimeoutExpired:
        print_fail('[0/3] Update check timed out')
    except Exception as e:
        print_fail(f'[0/3] Update check error: {e}')
def get_local_version() -> str:
    common_path = PROJECT_DIR / 'src' / 'common.py'
    try:
        with open(common_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip().startswith('APP_VERSION'):
                    return line.split('=')[1].strip().strip('"').strip("'")
    except:
        pass
    return '0.0.0'
def get_remote_version() -> Optional[str]:
    try:
        context = ssl._create_unverified_context()
        req = urllib.request.Request(STABLE_VERSION_URL)
        req.add_header('Range', 'bytes=0-2048')
        with urllib.request.urlopen(req, timeout=10, context=context) as r:
            content = r.read().decode('utf-8')
        match = re.search('APP_VERSION\\s*=\\s*["\\\']([^"\\\']+)["\\\']', content)
        return match.group(1) if match else None
    except:
        return None
def show_update_popup(local_ver: str, remote_ver: str) -> bool:
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        result = messagebox.askyesno('Update Available', f'A new version is available!\n\nCurrent: v{local_ver}\nLatest:  v{remote_ver}\n\nUpdate now?', icon='question')
        root.destroy()
        return result
    except:
        print(f'{YELLOW}Update available: v{local_ver} -> v{remote_ver}{RESET}')
        try:
            response = input('Update now? (y/n): ').strip().lower()
            return response in ('y', 'yes')
        except:
            return False
def download_update(version: str, progress_callback=None) -> Optional[Path]:
    url = RELEASE_DOWNLOAD_URL.format(version=version)
    temp_dir = Path(tempfile.mkdtemp(prefix='pst_update_'))
    archive_path = temp_dir / f'PST_standalone_v{version}.7z'
    try:
        context = ssl._create_unverified_context()
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=30, context=context) as r:
            total_size = int(r.headers.get('Content-Length', 0))
            downloaded = 0
            chunk_size = 8192
            with open(archive_path, 'wb') as f:
                while True:
                    chunk = r.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback and total_size > 0:
                        pct = int(downloaded / total_size * 100)
                        progress_callback(downloaded, total_size, pct)
        return archive_path
    except Exception as e:
        print_fail(f'[0/3] Download failed: {e}')
        return None
def extract_update(archive_path: Path) -> Optional[Path]:
    try:
        import py7zr
        extract_dir = archive_path.parent / 'extracted'
        extract_dir.mkdir(exist_ok=True)
        with py7zr.SevenZipFile(archive_path, 'r') as z:
            z.extractall(extract_dir)
        return extract_dir
    except ImportError:
        print_fail('[0/3] py7zr not installed, cannot extract')
        return None
    except Exception as e:
        print_fail(f'[0/3] Extraction failed: {e}')
        return None
def apply_update_and_restart(extract_dir: Path):
    install_dir = Path(sys.executable).parent if getattr(sys, 'frozen', False) else PROJECT_DIR
    new_exe = extract_dir / 'PalworldSaveTools.exe'
    helper_code = f'import os, sys, time, shutil, subprocess\nPARENT_PID = {os.getpid()}\nINSTALL_DIR = r"{install_dir}"\nTEMP_DIR = r"{extract_dir}"\nNEW_EXE = r"{new_exe}" if os.path.exists(r"{new_exe}") else None\ndef wait_for_parent():\n    while True:\n        try:\n            os.kill(PARENT_PID, 0)\n            time.sleep(0.5)\n        except OSError:\n            break\n        except Exception:\n            break\ndef copy_files():\n    if not TEMP_DIR or not os.path.exists(TEMP_DIR):\n        return False\n    for item in os.listdir(TEMP_DIR):\n        src = os.path.join(TEMP_DIR, item)\n        dst = os.path.join(INSTALL_DIR, item)\n        try:\n            if os.path.isdir(src):\n                if os.path.exists(dst):\n                    shutil.rmtree(dst, ignore_errors=True)\n                shutil.copytree(src, dst)\n            else:\n                shutil.copy2(src, dst)\n        except Exception as e:\n            print(f"Error copying {{item}}: {{e}}")\n    return True\ndef cleanup():\n    try:\n        parent_temp = os.path.dirname(TEMP_DIR)\n        if os.path.exists(parent_temp):\n            shutil.rmtree(parent_temp, ignore_errors=True)\n    except:\n        pass\ndef launch_new():\n    exe_path = NEW_EXE or os.path.join(INSTALL_DIR, "PalworldSaveTools.exe")\n    if os.path.exists(exe_path):\n        subprocess.Popen([exe_path], cwd=INSTALL_DIR)\nif __name__ == "__main__":\n    print("Update helper started...")\n    wait_for_parent()\n    print("Parent process exited, applying update...")\n    time.sleep(1)\n    copy_files()\n    cleanup()\n    print("Update applied, launching...")\n    launch_new()\n'
    helper_path = extract_dir.parent / 'update_helper.py'
    with open(helper_path, 'w', encoding='utf-8') as f:
        f.write(helper_code)
    if os.name == 'nt':
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
        si = subprocess.STARTUPINFO()
        si.dwFlags = subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = subprocess.SW_HIDE
    else:
        creationflags = 0
        si = None
    subprocess.Popen([sys.executable, str(helper_path)], creationflags=creationflags, startupinfo=si, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print_ok('[0/3] Update applied, restarting...')
    time.sleep(1)
    sys.exit(0)
def standalone_update_check():
    if not is_standalone_mode():
        return
    if not get_auto_update_enabled():
        return
    print_step_working('[0/3] Checking for updates')
    local_ver = get_local_version()
    remote_ver = get_remote_version()
    if not remote_ver:
        print_ok('[0/3] Update check skipped (offline)')
        return
    try:
        local_tuple = tuple((int(x) for x in local_ver.split('.')))
        remote_tuple = tuple((int(x) for x in remote_ver.split('.')))
        if remote_tuple <= local_tuple:
            print_ok('[0/3] Already up-to-date')
            return
    except:
        print_ok('[0/3] Version check skipped')
        return
    print(f'{CYAN}[0/3] Update available: v{local_ver} -> v{remote_ver}{RESET}')
    if not show_update_popup(local_ver, remote_ver):
        print(f'{DIM}[0/3] Update skipped by user{RESET}')
        return
    print(f'{BOLD}[0/3] Downloading v{remote_ver}...{RESET}')
    def progress_cb(downloaded, total, pct):
        sys.stdout.write(f'\r{CYAN}{progress_bar(pct, width=28)} {downloaded // (1024 * 1024)}MB/{total // (1024 * 1024)}MB{RESET}')
        sys.stdout.flush()
    archive_path = download_update(remote_ver, progress_cb)
    if not archive_path:
        return
    print()
    print_step_working('[0/3] Extracting update')
    extract_dir = extract_update(archive_path)
    if not extract_dir:
        return
    print_ok('[0/3] Extraction complete')
    apply_update_and_restart(extract_dir)
def main():
    msg = "\n  ___      _                _    _ ___              _____         _    \n | _ \\__ _| |_ __ _____ _ _| |__| / __| __ ___ ____|_   _|__  ___| |___\n |  _/ _` | \\ V  V / _ \\ '_| / _` \\__ \\/ _` \\ V / -_)| |/ _ \\/ _ \\(_-<\n |_| \\__,_|_|\\_/\\_/\\___/_| |_\\__,_|___/\\__,_|\\_/\\___||_|\\___/\\___/_/__/\n    "
    print(msg)
    git_pull_if_source()
    standalone_update_check()
    if not SENTINEL.exists():
        nuke_build_artifacts()
        if not VENV_DIR.exists():
            if not ensure_python_venv_installed():
                print_fail(step_label(1, 3, 'python3-venv setup failed'))
                return
            print_step_working(step_label(1, 3, 'Creating Virtual Environment'))
            venv_result = subprocess.run([sys.executable, '-m', 'venv', str(VENV_DIR)])
            if venv_result.returncode != 0:
                print_fail(step_label(1, 3, 'Venv creation failed'))
                nuke_venv()
                return
            print_ok(step_label(1, 3, 'Venv created'))
        vpy = venv_python_path()
        print_step_working(step_label(2, 3, 'Updating Dependencies'))
        ret = run_and_watch([str(vpy), '-m', 'pip', 'install', 'pip==24.3.1', 'setuptools==75.6.0', 'wheel', 'numpy==2.1.3', 'PySide6-Essentials', 'shiboken6', 'packaging'])
        if ret == 0:
            SENTINEL.touch()
            print_ok(step_label(2, 3, 'Dependencies updated'))
        else:
            print_fail(step_label(2, 3, 'Dependency update failed'))
            nuke_venv()
            return
    vpy = venv_python_path()
    start_py = PROJECT_DIR / 'start.py'
    if start_py.exists():
        if SENTINEL.exists():
            print(f"{DIM}{step_label(3, 3, 'Environment ready,bypassing checks')}{RESET}")
        if not ensure_qt_dependencies():
            print_fail(step_label(3, 3, 'Qt dependencies check failed'))
            return
        print(f"{BOLD}{step_label(3, 3, 'Launching Application')}{RESET}")
        subprocess.call([str(vpy), str(start_py)])
if __name__ == '__main__':
    main()