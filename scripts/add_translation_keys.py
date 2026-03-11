import json
import os
import sys
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
NEW_TRANSLATIONS = {'oilrig_reset': 'Reset oil rigs', 'oilrig_reset_count': 'Reset {count} oil rigs', 'deletion.menu.reset_oilrig': 'Reset Oil Rigs', 'loading.reset_oilrig': 'Resetting oil rigs...', 'reset_oilrig': 'Reset {count} oil rigs', 'invader_reset': 'Reset invaders', 'invader_reset_count': 'Reset {count} invaders', 'deletion.menu.reset_invader': 'Reset Invaders', 'loading.reset_invader': 'Resetting invaders...', 'reset_invader': 'Reset {count} invaders', 'supply_reset': 'Reset supply', 'supply_reset_count': 'Reset {count} supply drops', 'deletion.menu.reset_supply': 'Reset Supply', 'loading.reset_supply': 'Resetting supply drops...', 'reset_supply': 'Reset {count} supply drops', 'container_selector.title': 'Select Containers for {player_name}', 'container_selector.instruction': 'Browse orphaned containers with items and select which to assign to each slot', 'container_selector.slot_main': 'Main Inventory', 'container_selector.slot_key': 'Key Items', 'container_selector.slot_weapons': 'Weapons', 'container_selector.slot_armor': 'Armor', 'container_selector.slot_food': 'Food Bag', 'container_selector.slot_palbox': 'Pal Box', 'container_selector.slot_party': 'Party', 'container_selector.auto_none': 'Auto (none selected)', 'container_selector.select_as_main': 'Select as Main', 'container_selector.select_as_key': 'Select as Key', 'container_selector.select_as_weapons': 'Select as Weapons', 'container_selector.select_as_armor': 'Select as Armor', 'container_selector.select_as_food': 'Select as Food', 'container_selector.select_as_palbox': 'Select as Pal Box', 'container_selector.select_as_party': 'Select as Party', 'container_selector.update_btn': 'Update Container IDs', 'container_selector.cancel_btn': 'Cancel', 'container_selector.assign_slots': 'Assign Containers to Slots', 'container_selector.select_instruction': "Right-click a container on the left to assign it to a slot below, or click 'Clear' to remove assignment", 'container_selector.clear_slot': 'Clear', 'container_selector.no_containers': 'No orphaned containers with items found', 'container_selector.found_containers': 'Found {count} orphaned containers with items'}
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
        print(f'  ✗ Failed: {e}')
        return False
def main():
    print('\n' + '=' * 60)
    print('  ADDING TRANSLATION KEYS')
    print('=' * 60)
    print('\nEnglish (en_US)...')
    add_english_keys()
    print('  [OK] Success')
    for lang_code, lang_info in LANGUAGES.items():
        print(f"\n{lang_info['name']} ({lang_code})...")
        success = add_keys_to_language(lang_code, lang_info)
        print(f"  {('[OK] Success' if success else '[ERROR] Failed')}")
    print('\n' + '=' * 60)
    print('  DONE')
    print('=' * 60)
if __name__ == '__main__':
    main()