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
NEW_TRANSLATIONS = {'base_inventory.add_item': 'Add Item', 'base_inventory.select_item': 'Select Item', 'base_inventory.all_items': 'All Items', 'base_inventory.clear_item': 'Clear Item Filter', 'base_inventory.select_container_first': 'Please select a container first', 'base_inventory.container_full': 'Container is full!', 'base_inventory.failed_to_add_item': 'Failed to add item', 'base_inventory.use_context_menu': 'Right-click on an item to remove it', 'base_inventory.edit_quantity': 'Edit Quantity', 'base_inventory.remove_item': 'Remove Item', 'base_inventory.current_count': 'Current count: {count}', 'base_inventory.failed_to_update_quantity': 'Failed to update quantity', 'base_inventory.failed_to_remove_item': 'Failed to remove item', 'base_inventory.auto_save_success': 'Auto-saved changes', 'base_inventory.auto_save_failed': 'Auto-save failed - changes not saved', 'base_inventory.item_not_found': 'Could not find item name for ID: {item_id}', 'base_inventory.modify_container_slots': 'Modify Container Slots', 'base_inventory.current_status': 'Current Status', 'base_inventory.current_slots': 'Current Slots: {count}', 'base_inventory.current_items': 'Current Items: {count}', 'base_inventory.new_slot_count': 'New Slot Count', 'base_inventory.ok': 'OK', 'base_inventory.cancel': 'Cancel', 'base_inventory.warning_cannot_reduce_below_items': 'Warning: Cannot reduce slots below current item count ({item_count})', 'base_inventory.no_change_needed': 'No change needed - slot count is the same', 'base_inventory.container_slots_modified': 'Container slots modified to {new_count}', 'base_inventory.failed_to_modify_slots': 'Failed to modify container slots', 'base_inventory.clear_container': 'Clear Container', 'base_inventory.clear_container_confirm': 'Are you sure you want to clear all items from this container?', 'base_inventory.container_cleared': 'Container cleared successfully', 'base_inventory.failed_to_clear_container': 'Failed to clear container', 'base_inventory.delete_container': 'Delete Container', 'base_inventory.delete_container_confirm': 'Are you sure you want to delete this container and its map object? This action cannot be undone.', 'base_inventory.container_deleted': 'Container deleted successfully', 'base_inventory.failed_to_delete_container': 'Failed to delete container', 'base_inventory.save_failed': 'Failed to save changes', 'base_inventory.save_success': 'Changes saved successfully', 'base_inventory.refresh_all': 'Refresh All', 'base_inventory.slots_count': 'Slots: {count}', 'base_inventory.items': 'Items: {count}', 'base_inventory.empty': 'Empty: {count}', 'base_inventory.container_details': 'Container Details', 'base_inventory.select_guild': 'Select Guild:', 'base_inventory.select_base': 'Select Base:', 'base_inventory.select_container': 'Containers:', 'base_inventory.no_save_loaded': 'No save file loaded', 'base_inventory.load_save_first': 'Load a save file first', 'base_inventory.no_guilds_with_bases': 'No guilds with bases found', 'base_inventory.no_bases_available': 'No bases available', 'base_inventory.no_bases_found': 'No bases found for this guild', 'base_inventory.no_bases_with_item': 'No bases found with this item', 'base_inventory.no_guilds_with_item': 'No guilds found with {item_name}', 'base_inventory.item_picker': 'Item Picker', 'base_inventory.search_items': 'Search items...', 'base_inventory.select_quantity': 'Select Quantity', 'base_inventory.quantity': 'Quantity', 'base_inventory.add': 'Add', 'base_inventory.cancel': 'Cancel'}
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