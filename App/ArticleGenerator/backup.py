#!/usr/bin/env python3
"""
BACKUP SKRYPT - Automatyczne przenoszenie plików przed generacją
Wywoływany na początku content_generator.py
Przenosi foldery z datą/godziną do folderu 'copies/' w katalogu BASE (2 poziomy wyżej)
"""

import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

# KATALOG SKRYPTU
SCRIPT_DIR = Path(__file__).resolve().parent

# BASE = odpowiednik ../../ względem tego pliku (czyli katalog projektu)
BASE_DIR = SCRIPT_DIR.parents[1]  # App/ArticleGenerator -> (parents[0]=App) -> (parents[1]=projekt)
BACKUP_ROOT = BASE_DIR / "copies"

# Foldery do backupu (względem SCRIPT_DIR)
SOURCE_FOLDERS = [
    Path("../../ReadyContent/readyArticles"),
    Path("../../ReadyContent/readyDescriptions"),
    Path("../../ReadyContent/photosCompress"),
    Path("../../ReadyContent/readyPosts"),
]

def create_backup():
    """Tworzy backup wszystkich folderów z datą/godziną"""

    print(f"📂 Katalog skryptu: {SCRIPT_DIR}")
    print(f"📦 BASE_DIR: {BASE_DIR}")
    print(f"🗃️  BACKUP_ROOT: {BACKUP_ROOT}")
    print()

    # Rozwiąż źródła do absolutnych ścieżek
    sources = []
    for rel in SOURCE_FOLDERS:
        src = (SCRIPT_DIR / rel).resolve()
        if src.exists() and src.is_dir():
            sources.append(src)
            print(f"✅ Źródło istnieje: {src}")
        else:
            print(f"⚠️  Brak folderu: {src}")

    if not sources:
        print("ℹ️  Brak folderów do backupu - kontynuuję...")
        return True

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_name = f"backup_{timestamp}"
    backup_path = BACKUP_ROOT / backup_name

    print(f"\n📁 Tworzenie backupu: {backup_name}")
    print("=" * 60)

    try:
        backup_path.mkdir(parents=True, exist_ok=True)

        total_files = 0
        total_size = 0

        for source_folder in sources:
            dest_folder = backup_path / source_folder.name

            print(f"🔄 Przenoszę {source_folder} -> {dest_folder} ...")
            shutil.move(str(source_folder), str(dest_folder))

            folder_files = sum(len(files) for _, _, files in os.walk(dest_folder))
            total_files += folder_files

            folder_size = sum(
                os.path.getsize(os.path.join(dirpath, filename))
                for dirpath, _, filenames in os.walk(dest_folder)
                for filename in filenames
            )
            total_size += folder_size

            print(f"✅ {source_folder.name:>18} → {dest_folder}")

        print("\n" + "=" * 60)
        print("📊 PODSUMOWANIE BACKUPU")
        print("=" * 60)
        print(f"📁 Backup zapisany: {backup_path}")
        print(f"📄 Pliki: {total_files:,}")
        print(f"💾 Rozmiar: {total_size / 1024 / 1024:.1f} MB")
        print("✅ Backup utworzony pomyślnie!")
        return True

    except Exception as e:
        print(f"❌ BŁĄD tworzenia backupu: {e}")
        import traceback
        traceback.print_exc()
        return False


def list_backups():
    backups_path = BACKUP_ROOT
    if not backups_path.exists():
        print("ℹ️  Brak folderu backupów")
        return

    backups = sorted(backups_path.iterdir(), key=os.path.getmtime, reverse=True)
    print("\n📋 AKTUALNE BACKUPY (najnowsze pierwsze):")
    print("-" * 50)
    for backup in list(backups)[:10]:
        if backup.is_dir():
            print(f"📁 {backup.name}")


def cleanup_old_backups(days=30):
    import time

    backups_path = BACKUP_ROOT
    if not backups_path.exists():
        print("ℹ️  Brak backupów")
        return

    cutoff = time.time() - (days * 24 * 60 * 60)
    deleted = 0

    for backup_path in backups_path.iterdir():
        if backup_path.is_dir():
            mtime = os.path.getmtime(backup_path)
            if mtime < cutoff:
                shutil.rmtree(backup_path)
                deleted += 1
                print(f"🗑️  Usunięto: {backup_path.name}")

    if deleted == 0:
        print(f"ℹ️  Brak starych backupów (>{days} dni)")
    else:
        print(f"🗑️  Usunięto {deleted} starych backupów")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "list":
            list_backups()
        elif sys.argv[1] == "cleanup":
            days = int(sys.argv[2]) if len(sys.argv) > 2 else 30
            cleanup_old_backups(days)
        else:
            print("Użycie: python backup.py [list|cleanup [dni]]")
            sys.exit(1)
    else:
        success = create_backup()
        sys.exit(0 if success else 1)