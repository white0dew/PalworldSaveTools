import json
import os
import sys
import concurrent.futures
from pathlib import Path
try:
    from deep_translator import GoogleTranslator
except ImportError:
    print('Installing deep-translator...')
    import subprocess
    subprocess.check_call(['pip', 'install', 'deep-translator'])
    from deep_translator import GoogleTranslator
PROJECT_ROOT = Path(__file__).resolve().parent.parent
LANGUAGES = {'zh_CN': {'name': 'Simplified Chinese', 'code': 'zh-CN'}, 'de_DE': {'name': 'German', 'code': 'de'}, 'es_ES': {'name': 'Spanish', 'code': 'es'}, 'fr_FR': {'name': 'French', 'code': 'fr'}, 'ru_RU': {'name': 'Russian', 'code': 'ru'}, 'ja_JP': {'name': 'Japanese', 'code': 'ja'}, 'ko_KR': {'name': 'Korean', 'code': 'ko'}}
NEW_TRANSLATIONS = {'zone_exclusion.drawing_mode_prompt': 'Zone Drawing Mode: Double-click to set Point A, then double-click Point B to create zone. Right-click to stop.', 'zone_exclusion.drawing_mode_polygon': 'Polygon Mode: Double-click to start, single-click to add points, double-click to close.', 'zone_exclusion.set_point_b_prompt': 'Zone Drawing Mode: Point A set. Double-click to set Point B.', 'zone_exclusion.polygon_adding_points': 'Polygon: {count} points. Single-click to add more, double-click to close.', 'zone_exclusion.rename_prompt': 'Enter new zone name:', 'zone_exclusion.edit_zone_menu': 'Edit Zone', 'zone_exclusion.edit_zones': 'Edit Zones', 'zone_exclusion.create_new_zone': 'Create New Zone', 'zone_exclusion.show_zones': 'Show Zones', 'zone_exclusion.clear_all_zones': 'Clear All Zones', 'zone_exclusion.draw_zones': 'Draw Zones', 'zone_exclusion.stop_drawing': 'Stop Drawing Zones', 'zone_exclusion.import_zones': 'Import Zones', 'zone_exclusion.export_zones': 'Export Zones', 'zone_exclusion.drawing_point_a': 'Zone Drawing: Double-click at Point A', 'zone_exclusion.drawing_point_b': 'Zone Drawing: Click at Point B', 'zone_exclusion.rename_zone': 'Rename Zone', 'zone_exclusion.zone_name': 'Zone Name:', 'zone_exclusion.change_color': 'Change Color', 'zone_exclusion.delete_zone': 'Delete Zone', 'zone_exclusion.confirm_delete': "Are you sure you want to delete zone '{zone_name}'?", 'zone_exclusion.confirm_delete_all': 'Are you sure you want to delete all zones?', 'zone_exclusion.invalid_zone_file': 'Invalid zone file format', 'zone_exclusion.zones_imported': 'Zones imported from {path}', 'zone_exclusion.zones_exported': 'Zones exported to {path}', 'zone_exclusion.zone_added': 'Zone added successfully', 'zone_management.title': 'Protection Zones', 'zone_management.prompt': 'Found {zone_count} protection zone(s) from previous session.\nWhat would you like to do?', 'zone_management.load': 'Load Previous Zones', 'zone_management.clear': 'Clear Zones', 'zone_management.export': 'Export Zones', 'zone_management.export_title': 'Export Protection Zones', 'zone_management.export_success': 'Protection zones exported successfully', 'zone_management.export_failed': 'Failed to export zones', 'zone_management.import': 'Import Zones', 'zone_management.import_title': 'Import Protection Zones', 'zone_management.import_success': 'Protection zones imported successfully', 'zone_management.import_failed': 'Failed to import zones. Invalid file format.', 'map.toggle.zones': 'Zones'}
def add_english_keys():
    lang_file = PROJECT_ROOT / 'resources' / 'i18n' / 'en_US.json'
    with open(lang_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    for key, english_text in NEW_TRANSLATIONS.items():
        if key not in data:
            data[key] = english_text
    with open(lang_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
def translate_text(text: str, target_lang: str) -> str:
    translator = GoogleTranslator(source='en', target=target_lang)
    return translator.translate(text)
def add_keys_to_language(lang_code: str, lang_info: dict) -> bool:
    try:
        lang_file = PROJECT_ROOT / 'resources' / 'i18n' / f'{lang_code}.json'
        with open(lang_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for key, english_text in NEW_TRANSLATIONS.items():
            if key in data:
                continue
            translated = translate_text(english_text, lang_info['code'])
            data[key] = translated
        with open(lang_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f'  [ERROR] Failed: {e}')
        return False
def main():
    print('\n' + '=' * 60)
    print('  ADDING TRANSLATION KEYS')
    print('=' * 60)
    print('\nEnglish (en_US)...')
    add_english_keys()
    print('  [OK] Success')
    print('\nTranslating to other languages (parallel processing)...')
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(LANGUAGES)) as executor:
        future_to_lang = {executor.submit(add_keys_to_language, lang_code, lang_info): lang_code for lang_code, lang_info in LANGUAGES.items()}
        for future in concurrent.futures.as_completed(future_to_lang):
            lang_code = future_to_lang[future]
            lang_info = LANGUAGES[lang_code]
            try:
                success = future.result()
                print(f"  {lang_info['name']} ({lang_code}): {('[OK] Success' if success else '[ERROR] Failed')}")
            except Exception as e:
                print(f"  {lang_info['name']} ({lang_code}): [ERROR] {e}")
    print('\n' + '=' * 60)
    print('  DONE')
    print('=' * 60)
if __name__ == '__main__':
    main()