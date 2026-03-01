# Changelog

All notable changes to PalworldSaveTools will be documented in this file.

## [Unreleased]

### Added
- `scripts/translate_readme.py` - Auto-translate README.md to all supported languages using Google Translate

### Changed
- **README.md improvements:**
  - Fixed Python version requirement (3.10 → 3.11)
  - Rewrote "From Source" section to use `start_win.cmd` / `start_linux.sh` (auto-venv setup)
  - Added "Branches" section with stable and beta clone URLs
  - Updated "Building Standalone Executable" section (Windows-only, uses `scripts\build.cmd`)
  - Fixed Quick Start menu instructions to reflect actual UI
  - Removed non-existent tools from Additional Tools table
  - Added working hyperlinks to Table of Contents
  - Fixed Map Unlock guide path (`resources\` instead of `src\resources\`)
- **Language switcher links:**
  - Root README.md: English links to itself, other languages link to `resources/readme/`
  - Non-English READMEs: English links to `../../README.md` (root), other languages link within same directory
- Fixed corrupted badge links in all non-English README files

## [1.1.72] - 2026-02-23

### Added
- **Player Inventory Editor** - Full-featured inventory management system
  - New `src/palworld_aio/ui/inventory_tab.py` - Main inventory tab widget
  - New `src/palworld_aio/inventory_manager.py` - Inventory data management and parsing
  - Equipment slots display: Weapons (4), Accessories (4), Armor (Head/Body/Shield/Glider/Module), Food (4)
  - Inventory grid with dynamic slot count based on key items owned (42-54 slots)
  - Key items tab for special items
  - Stats panel with editable HP, Stamina, Attack, Defense, Work Speed, Weight
  - Level editor with +/- buttons and EXP bar visualization
  - Auto-save on all edits (stats, level, item quantities)
  - Context menus for adding/editing/deleting items
  - Player search and selection dropdown
  - Translation support with `inventory.*` i18n keys
- `scripts/update_inventory_i18n.py` - Script to update inventory-related translation keys
- Translation keys for inventory added to `resources/i18n/en_US.json`

### Changed
- Slot Injector: Now has player name / player uid / slots for easier management.

### Fixed
- Edit Pal. It wasn't saving on x button, at close window - causing the incomplete edit/save situation.

## [1.1.71] - 2026-02-22

### Added
- Built-in update system with auto-update support
- Source mode: Git-based updates with stable/beta branch switching
- Standalone mode: Auto-download and install updates
- Update settings dialog with auto-update toggle
- `runtime.cfg` for runtime mode detection
- Source mode update settings now show "Allow git pull updates" option
- Standalone mode update settings show "Auto-update when available" option

### Changed
- Build script now sets standalone mode during build process
- Version check now reads correct version based on branch (APP_VERSION for stable, BETA_VERSION for beta)
- Update settings now context-aware based on runtime mode

### Fixed
- Player .sav file paths now use uppercase GUIDs to match Palworld's filename convention on Linux
  - Fixes `FileNotFoundError` when migrating host saves on case-sensitive filesystems (Linux/macOS)
  - Affected files: `fix_host_save.py`, `player_manager.py`, `func_manager.py`, `main_window.py`
- ImportError: `STABLE_BRANCH` and `BETA_BRANCH` now properly exported from `updater.py`
- Duplicate `_remove_invalid_passives` method removed from `main_window.py`
- `urllib.request` import moved to top of `updater.py` for proper initialization
- Temp directory cleanup now guaranteed via `atexit` handler in `StandaloneUpdater`
