import os
import sys
import re
import ssl
import json
import subprocess
import tempfile
import shutil
import time
import atexit
import urllib.request
from pathlib import Path
from typing import Optional, Callable, Dict, Tuple

try:
    from palworld_aio import constants
except ImportError:
    from . import constants

GIT_REPO_URL = "https://github.com/deafdudecomputers/PalworldSaveTools.git"
STABLE_BRANCH = "main"
BETA_BRANCH = "beta"
STABLE_VERSION_URL = "https://raw.githubusercontent.com/deafdudecomputers/PalworldSaveTools/main/src/common.py"
RELEASE_DOWNLOAD_URL = "https://github.com/deafdudecomputers/PalworldSaveTools/releases/download/v{version}/PST_standalone_v{version}.7z"
RELEASES_PAGE_URL = (
    "https://github.com/deafdudecomputers/PalworldSaveTools/releases/latest"
)
CHANGELOG_URL = "https://raw.githubusercontent.com/deafdudecomputers/PalworldSaveTools/main/CHANGELOG.md"


def get_update_settings() -> Dict:
    """Get update settings from config.json"""
    try:
        from common import get_src_directory, is_standalone

        config_path = os.path.join(
            get_src_directory(), "data", "configs", "config.json"
        )
        standalone = is_standalone()
    except:
        config_path = os.path.join(
            os.path.dirname(__file__), "data", "configs", "config.json"
        )
        standalone = False

    if standalone:
        defaults = {"auto_update": True, "check_updates": True}
    else:
        defaults = {"git_pull": True, "check_updates": True}

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        defaults.update({k: config.get(k, v) for k, v in defaults.items()})
    except:
        pass

    return defaults


def save_update_settings(settings: Dict):
    """Save update settings to config.json"""
    try:
        from common import get_src_directory, is_standalone

        config_path = os.path.join(
            get_src_directory(), "data", "configs", "config.json"
        )
        standalone = is_standalone()
    except:
        config_path = os.path.join(
            os.path.dirname(__file__), "data", "configs", "config.json"
        )
        standalone = False

    config = {}
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
    except:
        pass

    if standalone:
        for key in ["auto_update", "check_updates"]:
            if key in settings:
                config[key] = settings[key]
    else:
        for key in ["git_pull", "check_updates"]:
            if key in settings:
                config[key] = settings[key]

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


class SourceUpdater:
    """Git-based updater for source mode"""

    @staticmethod
    def get_project_root() -> Path:
        """Get the project root directory"""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return Path(result.stdout.strip())
        except:
            pass

        return Path(__file__).resolve().parent.parent.parent

    @staticmethod
    def get_current_branch() -> str:
        """Get current git branch name"""
        try:
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=SourceUpdater.get_project_root(),
            )
            if result.returncode == 0:
                branch = result.stdout.strip()
                return branch if branch else "main"
        except:
            pass
        return "main"

    @staticmethod
    def has_uncommitted_changes() -> bool:
        """Check if there are uncommitted changes"""
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=SourceUpdater.get_project_root(),
            )
            return bool(result.stdout.strip())
        except:
            return False

    @staticmethod
    def git_pull(
        branch: str = None, progress_callback: Callable = None
    ) -> Tuple[bool, str]:
        if not branch:
            branch = SourceUpdater.get_current_branch()
        if progress_callback:
            progress_callback("Pulling updates...", 30)
        try:
            result = subprocess.run(
                ["git", "pull", "origin", branch],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=SourceUpdater.get_project_root(),
            )
            if result.returncode != 0:
                return False, result.stderr or "Git pull failed"
            if progress_callback:
                progress_callback("Update complete!", 100)
            return True, "Successfully updated"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def fetch_remote(branch: str = None) -> bool:
        """Fetch from remote"""
        try:
            cmd = ["git", "fetch", "origin"]
            if branch:
                cmd.append(branch)
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
                cwd=SourceUpdater.get_project_root(),
            )
            return result.returncode == 0
        except:
            return False

    @staticmethod
    def get_local_commit(branch: str = None) -> Optional[str]:
        """Get local commit hash"""
        if not branch:
            branch = SourceUpdater.get_current_branch()
        try:
            result = subprocess.run(
                ["git", "rev-parse", branch],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=SourceUpdater.get_project_root(),
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass
        return None

    @staticmethod
    def get_remote_commit(branch: str) -> Optional[str]:
        """Get remote commit hash"""
        try:
            result = subprocess.run(
                ["git", "rev-parse", f"origin/{branch}"],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=SourceUpdater.get_project_root(),
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass
        return None

    @staticmethod
    def check_for_updates(branch: str = None) -> Dict:
        """Check for updates, returns update info"""
        if not branch:
            branch = SourceUpdater.get_current_branch()

        SourceUpdater.fetch_remote(branch)

        local_commit = SourceUpdater.get_local_commit(branch)
        remote_commit = SourceUpdater.get_remote_commit(branch)

        has_update = False
        if local_commit and remote_commit:
            has_update = local_commit != remote_commit

        return {
            "branch": branch,
            "local_commit": local_commit,
            "remote_commit": remote_commit,
            "update_available": has_update,
        }


class StandaloneUpdater:
    """Auto-downloader for standalone mode"""

    def __init__(self):
        self.install_dir = Path(sys.executable).parent
        self.temp_dir = Path(tempfile.mkdtemp(prefix="pst_update_"))
        self.downloaded_file = None
        self.extracted_dir = None
        atexit.register(self.cleanup)

    def check_version(self) -> Dict:
        """Check for updates via HTTP"""
        try:
            context = ssl._create_unverified_context()
            req = urllib.request.Request(STABLE_VERSION_URL)
            req.add_header("Range", "bytes=0-2048")

            with urllib.request.urlopen(req, timeout=10, context=context) as r:
                content = r.read().decode("utf-8")

            match = re.search(r'APP_VERSION\s*=\s*["\']([^"\']+)["\']', content)
            latest = match.group(1) if match else None

            try:
                from common import get_versions

                local, _ = get_versions()
            except:
                local = "0.0.0"

            if not latest:
                return {"local": local, "latest": None, "update_available": False}

            local_tuple = tuple(int(x) for x in local.split("."))
            latest_tuple = tuple(int(x) for x in latest.split("."))

            return {
                "local": local,
                "latest": latest,
                "update_available": latest_tuple > local_tuple,
            }
        except Exception as e:
            return {
                "local": None,
                "latest": None,
                "update_available": False,
                "error": str(e),
            }

    def download(
        self,
        version: str,
        progress_callback: Callable = None,
        cancel_check: Callable = None,
    ) -> Optional[Path]:
        """Download update archive with progress"""
        url = RELEASE_DOWNLOAD_URL.format(version=version)
        archive_path = self.temp_dir / f"PST_standalone_v{version}.7z"

        try:
            context = ssl._create_unverified_context()
            req = urllib.request.Request(url)

            with urllib.request.urlopen(req, timeout=30, context=context) as r:
                total_size = int(r.headers.get("Content-Length", 0))
                downloaded = 0
                chunk_size = 8192

                with open(archive_path, "wb") as f:
                    while True:
                        if cancel_check and cancel_check():
                            return None

                        chunk = r.read(chunk_size)
                        if not chunk:
                            break

                        f.write(chunk)
                        downloaded += len(chunk)

                        if progress_callback and total_size > 0:
                            pct = int((downloaded / total_size) * 100)
                            progress_callback(
                                f"Downloading... {downloaded / (1024 * 1024):.1f} MB",
                                pct,
                            )

            self.downloaded_file = archive_path
            return archive_path

        except Exception as e:
            if progress_callback:
                progress_callback(f"Download failed: {e}", 0)
            return None

    def extract(self, progress_callback: Callable = None) -> Optional[Path]:
        """Extract downloaded archive using py7zr"""
        if not self.downloaded_file or not self.downloaded_file.exists():
            return None

        try:
            import py7zr

            if progress_callback:
                progress_callback("Extracting...", 0)

            extract_dir = self.temp_dir / "extracted"
            extract_dir.mkdir(exist_ok=True)

            with py7zr.SevenZipFile(self.downloaded_file, "r") as z:
                z.extractall(extract_dir)

            if progress_callback:
                progress_callback("Extraction complete!", 100)

            self.extracted_dir = extract_dir
            return extract_dir

        except ImportError:
            if progress_callback:
                progress_callback("py7zr not installed", 0)
            return None
        except Exception as e:
            if progress_callback:
                progress_callback(f"Extraction failed: {e}", 0)
            return None

    def cleanup(self):
        """Clean up temp files"""
        try:
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir, ignore_errors=True)
        except:
            pass

    def create_helper_script(self) -> Path:
        """Create helper script for post-exit file swap"""
        helper_code = f'''import os
import sys
import time
import shutil
import subprocess

PARENT_PID = {os.getpid()}
INSTALL_DIR = r"{self.install_dir}"
TEMP_DIR = r"{self.extracted_dir}"
NEW_EXE = r"{self.extracted_dir / "PalworldSaveTools.exe"}" if os.path.exists(r"{self.extracted_dir / "PalworldSaveTools.exe"}") else None

def wait_for_parent():
    """Wait for parent process to exit"""
    while True:
        try:
            os.kill(PARENT_PID, 0)
            time.sleep(0.5)
        except OSError:
            break
        except Exception:
            break

def copy_files():
    """Copy new files to install directory"""
    if not TEMP_DIR or not os.path.exists(TEMP_DIR):
        return False
    
    for item in os.listdir(TEMP_DIR):
        src = os.path.join(TEMP_DIR, item)
        dst = os.path.join(INSTALL_DIR, item)
        
        try:
            if os.path.isdir(src):
                if os.path.exists(dst):
                    shutil.rmtree(dst, ignore_errors=True)
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)
        except Exception as e:
            print(f"Error copying {{item}}: {{e}}")
    
    return True

def cleanup():
    """Remove temp directory"""
    try:
        parent_temp = os.path.dirname(TEMP_DIR)
        if os.path.exists(parent_temp):
            shutil.rmtree(parent_temp, ignore_errors=True)
    except:
        pass

def launch_new():
    """Launch the new executable"""
    exe_path = NEW_EXE or os.path.join(INSTALL_DIR, 'PalworldSaveTools.exe')
    if os.path.exists(exe_path):
        subprocess.Popen([exe_path], cwd=INSTALL_DIR)

if __name__ == '__main__':
    print("Update helper started...")
    wait_for_parent()
    print("Parent process exited, applying update...")
    time.sleep(1)
    copy_files()
    cleanup()
    print("Update applied, launching...")
    launch_new()
'''

        helper_path = self.temp_dir / "update_helper.py"
        with open(helper_path, "w", encoding="utf-8") as f:
            f.write(helper_code)

        return helper_path

    def apply_and_restart(self) -> bool:
        """Spawn helper process and prepare for exit"""
        if not self.extracted_dir or not self.extracted_dir.exists():
            return False

        try:
            helper_path = self.create_helper_script()

            if os.name == "nt":
                creationflags = (
                    subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
                )
                si = subprocess.STARTUPINFO()
                si.dwFlags = subprocess.STARTF_USESHOWWINDOW
                si.wShowWindow = subprocess.SW_HIDE
            else:
                creationflags = 0
                si = None

            subprocess.Popen(
                [sys.executable, str(helper_path)],
                creationflags=creationflags,
                startupinfo=si,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            return True

        except Exception as e:
            print(f"Failed to spawn update helper: {e}")
            return False


def check_for_updates(branch: str = None) -> Dict:
    """Unified update check - routes to correct updater based on mode"""
    try:
        from common import is_standalone

        if is_standalone():
            updater = StandaloneUpdater()
            return updater.check_version()
        else:
            return SourceUpdater.check_for_updates(branch)
    except:
        updater = StandaloneUpdater()
        return updater.check_version()


def get_version_from_remote(branch: str = None) -> Optional[str]:
    """Get version from remote common.py"""
    try:
        context = ssl._create_unverified_context()
        # Use the correct branch URL
        if branch == "beta":
            version_url = STABLE_VERSION_URL.replace("/main/", "/beta/")
        else:
            version_url = STABLE_VERSION_URL
        
        req = urllib.request.Request(version_url)
        req.add_header("Range", "bytes=0-2048")

        with urllib.request.urlopen(req, timeout=10, context=context) as r:
            content = r.read().decode("utf-8")

        # For beta branch, look for BETA_VERSION, otherwise APP_VERSION
        if branch == "beta":
            match = re.search(r'BETA_VERSION\s*=\s*["\']([^"\']+)["\']', content)
        else:
            match = re.search(r'APP_VERSION\s*=\s*["\']([^"\']+)["\']', content)
        return match.group(1) if match else None
    except:
        return None
