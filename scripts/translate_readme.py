"""
README Auto-Translator Script
Translates the main README.md to all supported languages.
Uses deep-translator with Google Translate (free, no API key required).
"""

import re
import os
import time
from pathlib import Path
from typing import List, Tuple, Optional, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

try:
    from deep_translator import GoogleTranslator
except ImportError:
    print("Installing deep-translator...")
    import subprocess

    subprocess.check_call(["pip", "install", "deep-translator"])
    from deep_translator import GoogleTranslator

PROJECT_ROOT = Path(__file__).resolve().parent.parent
README_SOURCE = PROJECT_ROOT / "README.md"
README_DIR = PROJECT_ROOT / "resources" / "readme"

LANGUAGES = {
    "zh_CN": {"name": "Simplified Chinese", "code": "zh-CN"},
    "de_DE": {"name": "German", "code": "de"},
    "es_ES": {"name": "Spanish", "code": "es"},
    "fr_FR": {"name": "French", "code": "fr"},
    "ru_RU": {"name": "Russian", "code": "ru"},
    "ja_JP": {"name": "Japanese", "code": "ja"},
    "ko_KR": {"name": "Korean", "code": "ko"},
}

# Language-specific translations for common terms
TRANSLATIONS = {
    "zh_CN": {
        "title": "Palworld 的综合保存文件编辑工具包",
        "download_text": "从",
        "download_link": "下载独立版本",
        "toc": "目录",
        "features": "特点",
        "installation": "安装",
        "quick_start": "快速入门",
        "tools_overview": "工具概述",
        "guides": "指南",
        "troubleshooting": "故障排除",
        "building": "构建独立可执行文件",
        "contributing": "贡献",
        "license": "许可证",
        "back_to_top": "返回顶部",
        "made_with_love": "用 ❤️ 为 Palworld 社区制作",
    },
    "de_DE": {
        "title": "Ein umfassendes Toolkit zur Bearbeitung gespeicherter Dateien für Palworld",
        "download_text": "Laden Sie die Standalone-Version von",
        "download_link": "herunter",
        "toc": "Inhaltsverzeichnis",
        "features": "Funktionen",
        "installation": "Installation",
        "quick_start": "Schnellstart",
        "tools_overview": "Tools-Übersicht",
        "guides": "Anleitungen",
        "troubleshooting": "Fehlerbehebung",
        "building": "Erstellen einer eigenständigen ausführbaren Datei",
        "contributing": "Mitwirken",
        "license": "Lizenz",
        "back_to_top": "Nach oben",
        "made_with_love": "Hergestellt mit ❤️ für die Palworld-Community",
    },
    "es_ES": {
        "title": "Un kit de herramientas completo para editar archivos de guardado de Palworld",
        "download_text": "Descarga la versión independiente de",
        "download_link": "",
        "toc": "Índice",
        "features": "Características",
        "installation": "Instalación",
        "quick_start": "Inicio rápido",
        "tools_overview": "Descripción de herramientas",
        "guides": "Guías",
        "troubleshooting": "Solución de problemas",
        "building": "Compilar ejecutable independiente",
        "contributing": "Contribuir",
        "license": "Licencia",
        "back_to_top": "Volver arriba",
        "made_with_love": "Hecho con ❤️ para la comunidad de Palworld",
    },
    "fr_FR": {
        "title": "Une boîte à outils complète pour l'édition de fichiers de sauvegarde Palworld",
        "download_text": "Téléchargez la version autonome depuis",
        "download_link": "",
        "toc": "Table des matières",
        "features": "Fonctionnalités",
        "installation": "Installation",
        "quick_start": "Démarrage rapide",
        "tools_overview": "Aperçu des outils",
        "guides": "Guides",
        "troubleshooting": "Dépannage",
        "building": "Compiler l'exécutable autonome",
        "contributing": "Contribuer",
        "license": "Licence",
        "back_to_top": "Retour en haut",
        "made_with_love": "Fait avec ❤️ pour la communauté Palworld",
    },
    "ru_RU": {
        "title": "Комплексный набор инструментов для редактирования файлов сохранений Palworld",
        "download_text": "Скачайте автономную версию с",
        "download_link": "",
        "toc": "Содержание",
        "features": "Возможности",
        "installation": "Установка",
        "quick_start": "Быстрый старт",
        "tools_overview": "Обзор инструментов",
        "guides": "Руководства",
        "troubleshooting": "Устранение неполадок",
        "building": "Сборка автономного исполняемого файла",
        "contributing": "Участие",
        "license": "Лицензия",
        "back_to_top": "Наверх",
        "made_with_love": "Создано с ❤️ для сообщества Palworld",
    },
    "ja_JP": {
        "title": "Palworld 用の包括的なセーブファイル編集ツールキット",
        "download_text": "スタンドアロン バージョンを",
        "download_link": "からダウンロードします",
        "toc": "目次",
        "features": "特徴",
        "installation": "インストール",
        "quick_start": "クイックスタート",
        "tools_overview": "ツールの概要",
        "guides": "ガイド",
        "troubleshooting": "トラブルシューティング",
        "building": "スタンドアロン実行可能ファイルのビルド",
        "contributing": "貢献する",
        "license": "ライセンス",
        "back_to_top": "トップに戻る",
        "made_with_love": "Palworld コミュニティのために ❤️ で作成されました",
    },
    "ko_KR": {
        "title": "Palworld를 위한 포괄적인 저장 파일 편집 툴킷",
        "download_text": "",
        "download_link": "에서 독립형 버전을 다운로드하세요",
        "toc": "목차",
        "features": "기능",
        "installation": "설치",
        "quick_start": "빠른 시작",
        "tools_overview": "도구 개요",
        "guides": "가이드",
        "troubleshooting": "문제 해결",
        "building": "독립형 실행 파일 빌드",
        "contributing": "기여",
        "license": "라이센스",
        "back_to_top": "맨 위로",
        "made_with_love": "Palworld 커뮤니티를 위해 ❤️으로 제작",
    },
}

HEADER_SECTION = """<div align="center">

![PalworldSaveTools Logo](../PalworldSaveTools_Blue.png)

# PalworldSaveTools

**{title}**

[![Downloads](https://img.shields.io/github/downloads/deafdudecomputers/PalworldSaveTools/total)](https://github.com/deafdudecomputers/PalworldTools/releases/latest)
[![License](https://img.shields.io/github/license/deafdudecomputers/PalworldSaveTools)](LICENSE)
[![Discord](https://img.shields.io/badge/Discord-Join_for_support-blue)](https://discord.gg/sYcZwcT4cT)
[![NexusMods](https://img.shields.io/badge/NexusMods-Download-orange)](https://www.nexusmods.com/palworld/mods/3190)

[English](../../README.md) | [简体中文](README.zh_CN.md) | [Deutsch](README.de_DE.md) | [Español](README.es_ES.md) | [Français](README.fr_FR.md) | [Русский](README.ru_RU.md) | [日本語](README.ja_JP.md) | [한국어](README.ko_KR.md)

---

### **{download_text} [GitHub Releases](https://github.com/deafdudecomputers/PalworldSaveTools/releases/latest)** {download_link}

---

</div>
"""

# Section headers that need anchor mapping
SECTION_HEADERS = [
    "Features",
    "Installation", 
    "Quick Start",
    "Tools Overview",
    "Guides",
    "Troubleshooting",
    "Building Standalone Executable",
    "Contributing",
    "License",
]

# Patterns for content protection
CODE_BLOCK_PATTERN = re.compile(r"```[\s\S]*?```", re.MULTILINE)
INLINE_CODE_PATTERN = re.compile(r"`[^`]+`")
URL_PATTERN = re.compile(r'https?://[^\s\)\]>"]+')
# Match markdown links with anchors: [Text](#anchor)
ANCHOR_LINK_PATTERN = re.compile(r'\[([^\]]+)\]\(#[^\)]+\)')
# Match markdown links in general: [Text](url)
MD_LINK_PATTERN = re.compile(r'\[([^\]]+)\]\([^\)]+\)')
# Match images: ![alt](url)
IMAGE_PATTERN = re.compile(r'!\[([^\]]*)\]\([^\)]+\)')
# Match HTML tags that should not be translated
HTML_TAG_PATTERN = re.compile(r'<(?:details|summary|div|align|br|hr|table|tr|td|th|thead|tbody|ul|ol|li|p|a|img|strong|b|em|i|code|pre|span|sub|sup|h[1-6])[^>]*>', re.IGNORECASE)
HTML_CLOSING_TAG_PATTERN = re.compile(r'</(?:details|summary|div|table|tr|td|th|thead|tbody|ul|ol|li|p|a|strong|b|em|i|code|pre|span|sub|sup|h[1-6])>', re.IGNORECASE)


class PlaceholderManager:
    """Manages placeholders to protect content during translation"""
    
    def __init__(self):
        self.placeholders: Dict[str, str] = {}
        self.counter = 0

    def add(self, text: str, prefix: str = "P") -> str:
        """Add text and return a numeric placeholder that won't be translated"""
        # Use purely numeric placeholders to avoid translation
        key = f"__{prefix}{self.counter}__"
        self.placeholders[key] = text
        self.counter += 1
        return key

    def restore(self, text: str) -> str:
        """Restore all placeholders"""
        # Sort by counter value (descending) to restore in reverse creation order
        # This ensures that outer placeholders (created later) are restored first
        # For example, markdown links (L) contain URLs (U), so L must be restored before U
        def get_counter(item):
            key = item[0]
            # Extract the number from the key like "__U34__" or "__L35__"
            match = re.search(r'(\d+)', key)
            return int(match.group(1)) if match else 0
        
        for key, value in sorted(self.placeholders.items(), key=lambda x: -get_counter(x)):
            text = text.replace(key, value)
        return text

    def clear(self):
        """Clear all placeholders"""
        self.placeholders = {}
        self.counter = 0


def protect_code_blocks(text: str, pm: PlaceholderManager) -> str:
    """Protect code blocks from translation"""
    def replace_code(match):
        return pm.add(match.group(0), "C")
    return CODE_BLOCK_PATTERN.sub(replace_code, text)


def protect_inline_code(text: str, pm: PlaceholderManager) -> str:
    """Protect inline code from translation"""
    def replace_inline(match):
        return pm.add(match.group(0), "I")
    return INLINE_CODE_PATTERN.sub(replace_inline, text)


def protect_urls(text: str, pm: PlaceholderManager) -> str:
    """Protect URLs from translation"""
    def replace_url(match):
        return pm.add(match.group(0), "U")
    return URL_PATTERN.sub(replace_url, text)


def protect_images(text: str, pm: PlaceholderManager) -> str:
    """Protect image markdown from translation"""
    def replace_img(match):
        return pm.add(match.group(0), "M")
    return IMAGE_PATTERN.sub(replace_img, text)


def protect_markdown_links(text: str, pm: PlaceholderManager) -> str:
    """Protect markdown links (but not anchor links - those need special handling)"""
    def replace_link(match):
        full = match.group(0)
        # Check if it's an anchor link
        if "](" in full and "(#" in full:
            # This is an anchor link, handle separately
            return full
        return pm.add(full, "L")
    return MD_LINK_PATTERN.sub(replace_link, text)


def protect_anchor_links(text: str, pm: PlaceholderManager) -> str:
    """Protect anchor links like [Text](#section) but NOT in TOC section"""
    # First, extract the TOC section and don't protect its anchor links
    # The TOC will be rebuilt after translation with correct translated anchors
    toc_start = text.find("## Table of Contents")
    if toc_start == -1:
        toc_start = text.find("## 目次")  # Japanese
    
    if toc_start != -1:
        # Find the end of TOC (next ## heading after the list items)
        toc_end_pattern = re.compile(r'\n## ', re.MULTILINE)
        toc_end_match = toc_end_pattern.search(text, toc_start + 10)
        
        if toc_end_match:
            before_toc = text[:toc_start]
            toc_section = text[toc_start:toc_end_match.start()]
            after_toc = text[toc_end_match.start():]
            
            # Protect anchor links only in non-TOC sections
            def replace_anchor(match):
                return pm.add(match.group(0), "A")
            
            before_toc = ANCHOR_LINK_PATTERN.sub(replace_anchor, before_toc)
            after_toc = ANCHOR_LINK_PATTERN.sub(replace_anchor, after_toc)
            # Don't protect TOC anchors - let them be translated
            
            return before_toc + toc_section + after_toc
    
    # No TOC found, protect all anchor links
    def replace_anchor(match):
        return pm.add(match.group(0), "A")
    return ANCHOR_LINK_PATTERN.sub(replace_anchor, text)


def protect_html_tags(text: str, pm: PlaceholderManager) -> str:
    """Protect HTML tags from translation"""
    def replace_tag(match):
        return pm.add(match.group(0), "H")
    result = HTML_TAG_PATTERN.sub(replace_tag, text)
    result = HTML_CLOSING_TAG_PATTERN.sub(replace_tag, result)
    return result


def generate_anchor_id(text: str) -> str:
    """Generate a GitHub-style anchor ID from heading text"""
    # GitHub anchor generation: lowercase, replace spaces with hyphens, remove special chars
    # But keep Unicode letters (for non-English languages)
    anchor = text.lower().strip()
    # Remove punctuation and special chars but keep Unicode letters, numbers, spaces, and hyphens
    anchor = re.sub(r'[^\w\s-]', '', anchor, flags=re.UNICODE)
    # Replace one or more whitespace characters with a single hyphen
    anchor = re.sub(r'\s+', '-', anchor)
    # Collapse multiple hyphens into one
    anchor = re.sub(r'-+', '-', anchor)
    return anchor


def extract_toc_section(content: str) -> Tuple[str, str]:
    """Extract the Table of Contents section from content"""
    toc_pattern = re.compile(r'(## Table of Contents\s*\n(?:-+\s*\n)?)(.*?)(?=\n---\s*\n## )', re.DOTALL)
    match = toc_pattern.search(content)
    
    if match:
        toc_header = match.group(1)
        toc_body = match.group(2)
        remaining = content[:match.start()] + content[match.end():]
        return toc_header, toc_body, remaining
    
    return "", "", content


def build_toc_from_content(content: str, lang_code: str) -> str:
    """Build a new TOC from the translated content's headings"""
    translations = TRANSLATIONS.get(lang_code, {})
    
    # Find all ## headings (section headers)
    heading_pattern = re.compile(r'^## ([^\n]+)', re.MULTILINE)
    headings = heading_pattern.findall(content)
    
    toc_lines = [f"## {translations.get('toc', 'Table of Contents')}", ""]
    
    for heading in headings:
        # Skip the TOC itself
        if heading.lower() in ['table of contents', translations.get('toc', '').lower()]:
            continue
            
        # Generate anchor from heading
        anchor = generate_anchor_id(heading)
        toc_lines.append(f"- [{heading}](#{anchor})")
    
    return "\n".join(toc_lines)


def split_text_for_translation(text: str, max_length: int = 4500) -> List[str]:
    """Split text into chunks for translation API"""
    if len(text) <= max_length:
        return [text]

    chunks = []
    lines = text.split("\n")
    current_chunk = []
    current_length = 0

    for line in lines:
        line_length = len(line) + 1

        if current_length + line_length > max_length and current_chunk:
            chunks.append("\n".join(current_chunk))
            current_chunk = []
            current_length = 0

        current_chunk.append(line)
        current_length += line_length

    if current_chunk:
        chunks.append("\n".join(current_chunk))

    return chunks


def translate_text(text: str, target_lang: str, source_lang: str = "en") -> str:
    """Translate text using Google Translate"""
    try:
        translator = GoogleTranslator(source=source_lang, target=target_lang)

        chunks = split_text_for_translation(text)
        translated_chunks = []

        for i, chunk in enumerate(chunks):
            if chunk.strip():
                if i > 0:
                    time.sleep(0.5)
                translated = translator.translate(chunk)
                translated_chunks.append(translated)
            else:
                translated_chunks.append(chunk)

        return "\n".join(translated_chunks)
    except Exception as e:
        print(f"Translation error: {e}")
        return text


def extract_content_after_header(content: str) -> str:
    """Extract content after the header section"""
    header_end_pattern = re.compile(r"</div>\s*\n", re.MULTILINE)
    match = header_end_pattern.search(content)

    if match:
        return content[match.end():]
    return content


def fix_section_anchors(content: str) -> str:
    """Fix section anchors to match translated headings"""
    # Find all ## headings and update their anchors
    def fix_heading(match):
        level = match.group(1)
        text = match.group(2).strip()
        # Headings don't have explicit anchors in GitHub markdown
        # The anchor is auto-generated from the text
        return f"{level} {text}"
    
    # Just ensure headings are properly formatted
    return re.sub(r'^(#{2,3})\s+(.+)$', fix_heading, content, flags=re.MULTILINE)


# Thread-safe print lock
_print_lock = threading.Lock()

def safe_print(*args, **kwargs):
    """Thread-safe print function"""
    with _print_lock:
        print(*args, **kwargs)


def translate_readme(target_lang_code: str, target_file_code: str, lang_name: str, quiet: bool = False):
    """Translate README to a specific language
    
    Args:
        target_lang_code: Target language code for translation (e.g., 'zh-CN')
        target_file_code: File code for output (e.g., 'zh_CN')
        lang_name: Display name for the language
        quiet: If True, suppress progress output (for parallel mode)
    """
    if not quiet:
        safe_print(f"\n{'=' * 50}")
        safe_print(f"Translating to {lang_name} ({target_lang_code})...")
        safe_print(f"{'=' * 50}")

    with open(README_SOURCE, "r", encoding="utf-8") as f:
        content = f.read()

    translations = TRANSLATIONS.get(target_file_code, {})
    
    # Build header with translations
    header = HEADER_SECTION.format(
        title=translations.get("title", "A comprehensive save file editing toolkit for Palworld"),
        download_text=translations.get("download_text", "Download the standalone version from"),
        download_link=translations.get("download_link", ""),
    )

    body_content = extract_content_after_header(content)

    pm = PlaceholderManager()

    # Protect various elements (order matters!)
    protected = protect_code_blocks(body_content, pm)
    protected = protect_inline_code(protected, pm)
    protected = protect_images(protected, pm)
    protected = protect_urls(protected, pm)
    protected = protect_markdown_links(protected, pm)
    protected = protect_anchor_links(protected, pm)
    protected = protect_html_tags(protected, pm)

    if not quiet:
        safe_print(f"  Protected {len(pm.placeholders)} elements")
        safe_print(f"  Translating body content...")

    # Translate
    translated = translate_text(protected, target_lang_code)

    # Restore placeholders
    translated = pm.restore(translated)

    # Fix image paths for translated files (resources/ -> ../)
    # Translated READMEs are in resources/readme/, so ../ goes up to resources/
    translated = re.sub(
        r'\!\[([^\]]*)\]\(resources/', r'![\1](../', translated
    )

    # Build new TOC from translated content
    # Get the translated TOC header from our dictionary
    toc_header = translations.get("toc", "Table of Contents")
    
    # Get all level-2 headings from the content
    heading_pattern = re.compile(r'^## ([^\n]+)', re.MULTILINE)
    headings = heading_pattern.findall(translated)
    
    # Build new TOC lines with proper anchors
    new_toc_items = []
    for heading in headings:
        heading_lower = heading.lower().strip()
        # Skip TOC header itself (various translations and common variants)
        toc_variants = ["table of contents", "contents", "目录", "inhaltsverzeichnis", 
                        "índice", "indice", "table des matières", "содержание", 
                        "目次", "목차", "tabla de contenidos"]
        if heading_lower in [v.lower() for v in toc_variants]:
            continue
        
        # Generate anchor from translated heading
        anchor = generate_anchor_id(heading)
        new_toc_items.append(f"- [{heading}](#{anchor})")
    
    new_toc_text = "\n".join(new_toc_items)
    
    # Find and completely replace the TOC section by structure
    # Pattern: ## heading at start of content, followed by list items
    # The TOC is always the first ## heading in the document after the header
    toc_pattern = re.compile(
        r'^## [^\n]+\n+(?:-+\n+)?(?:- \[[^\]]+\]\([^)]+\)\n)+',
        re.MULTILINE
    )
    
    # Build complete new TOC section
    # Add leading newline to ensure blank line after </div>
    new_toc_section = f"\n## {toc_header}\n\n{new_toc_text}\n"
    
    # Replace the old TOC with the new one
    translated = toc_pattern.sub(new_toc_section, translated, count=1)

    # Combine header and translated body
    final_content = header + translated

    # Write output
    output_path = README_DIR / f"README.{target_file_code}.md"

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(final_content)

    if not quiet:
        safe_print(f"  Saved to: {output_path}")
        safe_print(f"  Done!")

    return (target_file_code, True, str(output_path))


def translate_all():
    """Translate README to all supported languages in parallel"""
    print("\n" + "=" * 60)
    print("  README AUTO-TRANSLATOR (PARALLEL)")
    print("  Translating README.md to all supported languages")
    print("=" * 60)

    if not README_SOURCE.exists():
        print(f"\nError: Source README not found at {README_SOURCE}")
        return False

    README_DIR.mkdir(parents=True, exist_ok=True)

    # Print languages being translated
    print(f"\n  Translating {len(LANGUAGES)} languages in parallel...")
    for lang_code, lang_info in LANGUAGES.items():
        print(f"    - {lang_info['name']} ({lang_info['code']})")
    print()

    start_time = time.time()
    results = []

    # Use ThreadPoolExecutor for parallel translation
    with ThreadPoolExecutor(max_workers=len(LANGUAGES)) as executor:
        # Submit all translation jobs
        future_to_lang = {
            executor.submit(
                translate_readme, 
                lang_info["code"], 
                lang_code, 
                lang_info["name"],
                quiet=True  # Suppress individual progress for cleaner output
            ): (lang_code, lang_info["name"])
            for lang_code, lang_info in LANGUAGES.items()
        }

        # Collect results as they complete
        for future in as_completed(future_to_lang):
            lang_code, lang_name = future_to_lang[future]
            try:
                result = future.result()
                results.append(result)
                safe_print(f"  ✓ {lang_name} ({lang_code}) completed")
            except Exception as e:
                safe_print(f"  ✗ {lang_name} ({lang_code}) failed: {e}")
                results.append((lang_code, False, str(e)))

    elapsed_time = time.time() - start_time

    print("\n" + "=" * 60)
    print("  TRANSLATION SUMMARY")
    print("=" * 60)

    # Sort results by language code for consistent output
    results.sort(key=lambda x: list(LANGUAGES.keys()).index(x[0]) if x[0] in LANGUAGES else 999)

    for lang_code, success, info in results:
        status = "SUCCESS" if success else "FAILED"
        print(f"  {lang_code}: {status}")

    success_count = sum(1 for _, s, _ in results if s)
    print(f"\n  Total: {success_count}/{len(results)} successful")
    print(f"  Time: {elapsed_time:.1f} seconds")

    return all(s for _, s, _ in results)


def translate_single(lang_code: str):
    """Translate README to a single language"""
    if lang_code not in LANGUAGES:
        print(f"Error: Unknown language code '{lang_code}'")
        print(f"Available: {', '.join(LANGUAGES.keys())}")
        return False

    lang_info = LANGUAGES[lang_code]
    return translate_readme(lang_info["code"], lang_code, lang_info["name"])


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Translate README.md to supported languages"
    )
    parser.add_argument(
        "language",
        nargs="?",
        default="all",
        help="Language code to translate (e.g., zh_CN, de_DE). Use 'all' for all languages.",
    )
    parser.add_argument(
        "--list", "-l", action="store_true", help="List available languages"
    )

    args = parser.parse_args()

    if args.list:
        print("\nAvailable languages:")
        for code, info in LANGUAGES.items():
            print(f"  {code}: {info['name']}")
        exit(0)

    if args.language == "all":
        success = translate_all()
    else:
        success = translate_single(args.language)

    exit(0 if success else 1)