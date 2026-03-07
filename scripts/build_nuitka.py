import os
import sys
import subprocess
import shutil
import argparse
from pathlib import Path
def get_project_root():
    return Path(__file__).parent.parent.absolute()
def get_venv_python(project_root: Path) -> Path:
    if os.name == 'nt':
        return project_root / '.venv' / 'Scripts' / 'python.exe'
    return project_root / '.venv' / 'bin' / 'python'
def clean_build_dirs(project_root: Path) -> None:
    dirs_to_clean = ['build', '.build']
    for dir_name in dirs_to_clean:
        dir_path = project_root / dir_name
        if dir_path.exists():
            print(f'Removing {dir_path}...')
            shutil.rmtree(dir_path)
def check_dependencies(python_exe: Path) -> bool:
    print('Checking for Nuitka and zstandard...')
    try:
        result = subprocess.run([str(python_exe), '-c', 'import nuitka; print(nuitka.__version__)'], capture_output=True, text=True, check=True)
        print(f'Nuitka version: {result.stdout.strip()}')
    except subprocess.CalledProcessError:
        print('Nuitka not found, installing...')
        try:
            subprocess.run(['uv', 'pip', 'install', 'nuitka'], check=True)
            print('Nuitka installed successfully')
        except subprocess.CalledProcessError as e:
            print(f'ERROR: Failed to install Nuitka: {e}')
            return False
    try:
        subprocess.run([str(python_exe), '-c', "import zstandard; print('zstandard found')"], capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError:
        print('zstandard not found, installing...')
        try:
            subprocess.run(['uv', 'pip', 'install', 'zstandard'], check=True)
            print('zstandard installed successfully')
        except subprocess.CalledProcessError as e:
            print(f'ERROR: Failed to install zstandard: {e}')
            return False
    return True
def find_ooz_library(python_exe: Path) -> list:
    print('Finding ooz library...')
    try:
        result = subprocess.run([str(python_exe), '-c', 'import ooz; print(ooz.__file__)'], capture_output=True, text=True, check=True)
        ooz_path = Path(result.stdout.strip())
        target_dir = 'src/palworld_save_tools/lib/windows/'
        return [f'--include-data-files={ooz_path}={target_dir}{ooz_path.name}']
    except subprocess.CalledProcessError:
        print('WARNING: ooz library not found')
        return []
def discover_python_packages(project_root: Path) -> list:
    print('Discovering Python packages...')
    src_dir = project_root / 'src'
    packages = []
    for init_file in src_dir.rglob('__init__.py'):
        rel_path = init_file.relative_to(src_dir).parent
        package_name = str(rel_path).replace(os.sep, '.')
        if package_name and package_name != '.':
            packages.append(package_name)
            print(f'  Found package: {package_name}')
    return packages
def discover_data_files(project_root: Path) -> list:
    print('Scanning for data files in src/...')
    src_dir = project_root / 'src'
    data_includes = []
    data_extensions = {'.json', '.yaml', '.yml', '.txt', '.csv', '.md', '.toml', '.ini', '.cfg', '.xml', '.html', '.css', '.png', '.jpg', '.jpeg', '.ico', '.svg', '.ttf', '.otf', '.woff', '.woff2', '.bin', '.dat'}
    excluded_dirs = {'__pycache__', '.git', '.idea', 'venv', '.venv'}
    for file_path in src_dir.rglob('*'):
        if file_path.is_file():
            if file_path.suffix not in data_extensions:
                continue
            if any((excluded in file_path.parts for excluded in excluded_dirs)):
                continue
            if '__pycache__' in str(file_path):
                continue
            rel_path = file_path.relative_to(src_dir)
            target_path = f'src/{rel_path}'
            data_includes.append(f'--include-data-files={file_path}={target_path}')
            print(f'  Found data file: {rel_path}')
    return data_includes
def discover_data_dirs(project_root: Path) -> list:
    print('Scanning for data directories in src/...')
    src_dir = project_root / 'src'
    data_dirs = []
    known_data_dirs = ['data', 'configs', 'assets', 'static', 'templates']
    for dir_name in known_data_dirs:
        dir_path = src_dir / dir_name
        if dir_path.exists() and dir_path.is_dir():
            data_dirs.append(f'--include-data-dir={dir_path}=src/{dir_name}/')
            print(f'  Found data directory: {dir_name}/ (placing under src/)')
    return data_dirs
def build_with_nuitka(project_root: Path, python_exe: Path, main_script: str='src/palworld_aio/main.py', icon_file: str='resources/pal.ico', output_dir: str='.build', debug: bool=False) -> None:
    print(f'Building with Nuitka...')
    print(f'Python: {python_exe}')
    print(f'Main script: {main_script}')
    print(f'Icon: {icon_file}')
    print(f'Output: {output_dir}')
    print(f'Debug mode: {debug}')
    main_script_path = project_root / main_script
    icon_path = project_root / icon_file
    if not main_script_path.exists():
        raise FileNotFoundError(f'Main script not found: {main_script_path}')
    if not icon_path.exists():
        raise FileNotFoundError(f'Icon file not found: {icon_path}')
    nuitka_cmd = ['-m', 'nuitka', '--standalone', '--remove-output', '--assume-yes-for-downloads', '--enable-plugin=pyside6']
    if not debug:
        nuitka_cmd.append('--windows-console-mode=disable')
    nuitka_cmd.extend([f'--include-module=numpy', f'--include-module=pandas', f'--include-module=cityhash', f'--include-module=ooz', f'--include-module=nerdfont', f'--include-module=pydantic', f'--include-module=loguru'])
    packages = discover_python_packages(project_root)
    for package in packages:
        nuitka_cmd.append(f'--include-package={package}')
    data_files = discover_data_files(project_root)
    nuitka_cmd.extend(data_files)
    data_dirs = discover_data_dirs(project_root)
    nuitka_cmd.extend(data_dirs)
    nuitka_cmd.extend([f"--include-data-dir={project_root / 'resources'}=resources/", f"--include-data-files={project_root / 'readme.md'}=readme.md", f"--include-data-files={project_root / 'license'}=license"])
    ooz_files = find_ooz_library(python_exe)
    nuitka_cmd.extend(ooz_files)
    nuitka_cmd.extend(['--output-dir=' + str(project_root / output_dir), '--output-filename=PalworldSaveTools.exe', f'--windows-icon-from-ico={icon_path}', str(main_script_path)])
    print(f"Running: python {' '.join(nuitka_cmd)}")
    env = os.environ.copy()
    env['PYTHONPATH'] = str(project_root / 'src')
    result = subprocess.run([str(python_exe)] + nuitka_cmd, cwd=str(project_root), env=env, check=True)
    dist_dir = project_root / output_dir / 'PalworldSaveTools.dist'
    print(f'\nBuild completed successfully!')
    print(f"Executable location: {dist_dir / 'PalworldSaveTools.exe'}")
def main():
    parser = argparse.ArgumentParser(description='Build PalworldSaveTools with Nuitka')
    parser.add_argument('--use-venv', action='store_true', help='Use .venv instead of current Python interpreter (default: use current Python)')
    parser.add_argument('--no-clean', action='store_true', help='Skip cleaning build directories before building')
    parser.add_argument('--debug', action='store_true', help='Enable console for debugging (default: disabled)')
    parser.add_argument('--main-script', default='src/palworld_aio/main.py', help='Path to the main entry script (default: src/palworld_aio/main.py)')
    parser.add_argument('--icon', default='resources/pal.ico', help='Path to the icon file (default: resources/pal.ico)')
    parser.add_argument('--output-dir', default='.build', help='Output directory for the executable (default: .build)')
    args = parser.parse_args()
    project_root = get_project_root()
    if args.use_venv:
        python_exe = get_venv_python(project_root)
        if not python_exe.exists():
            print(f'ERROR: Virtual environment not found: {python_exe}')
            print('Please ensure .venv exists in the project root')
            sys.exit(1)
    else:
        python_exe = Path(sys.executable)
    if not check_dependencies(python_exe):
        sys.exit(1)
    if not args.no_clean:
        clean_build_dirs(project_root)
    try:
        build_with_nuitka(project_root=project_root, python_exe=python_exe, main_script=args.main_script, icon_file=args.icon, output_dir=args.output_dir, debug=args.debug)
    except Exception as e:
        print(f'ERROR: Build failed: {e}')
        sys.exit(1)
if __name__ == '__main__':
    main()