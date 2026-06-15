#!/usr/bin/env python3
"""
BACKUP SKRYPT - Automatyczne przenoszenie plików przed generacją
Wywoływany na początku content_generator.py
Przenosi foldery z datą/godziną do folderu 'copies/' w katalogu skryptu
"""

import os
import shutil
import sys
from datetime import datetime
from pathlib import Path


# KATALOG SKRYPTU - zawsze działa niezależnie od cwd
SCRIPT_DIR = Path(__file__).parent.resolve()
BACKUP_ROOT = "copies"

# Foldery do backupu (w katalogu skryptu)
SOURCE_FOLDERS = [
    "merged_video.mp4",
    "mp4_temp", 
    "shorts",
    "shorts_temp"
]


def create_backup():
    """Tworzy backup wszystkich folderów z datą/godziną"""
    
    print(f"📂 Katalog skryptu: {SCRIPT_DIR.absolute()}")
    print("📂 Zawartość katalogu skryptu:")
    try:
        for item in sorted(SCRIPT_DIR.iterdir()):
            print(f"   {item.name} {'📁' if item.is_dir() else '📄'}")
    except PermissionError:
        print("   ❌ Brak dostępu")
    print()
    
    # Znajdź foldery case-insensitive
    source_folders_exist = []
    all_dirs_lower = {}
    try:
        for p in SCRIPT_DIR.iterdir():
            if p.is_dir():
                all_dirs_lower[p.name.lower()] = p
    except PermissionError:
        print("❌ Błąd dostępu do katalogu")
        return False
    
    for source_name in SOURCE_FOLDERS:
        source_name_lower = source_name.lower()
        if source_name_lower in all_dirs_lower:
            exact_match = all_dirs_lower[source_name_lower]
            source_folders_exist.append(exact_match)
            print(f"✅ Znaleziono: {exact_match.name}")
        else:
            print(f"⚠️  Folder '{source_name}' nie istnieje")
    
    if not source_folders_exist:
        print("ℹ️  Brak folderów do backupu - kontynuuję...")
        return True
    
    # Utwórz backup
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_name = f"backup_{timestamp}"
    backup_path = SCRIPT_DIR / BACKUP_ROOT / backup_name
    
    print(f"\n📁 Tworzenie backupu: {backup_name}")
    print("=" * 60)
    
    try:
        backup_path.mkdir(parents=True, exist_ok=True)
        
        total_files = 0
        total_size = 0
        
        for source_folder in source_folders_exist:
            dest_folder = backup_path / source_folder.name
            
            print(f"🔄 Przenoszę {source_folder.name}...")
            shutil.move(str(source_folder), str(dest_folder))
            
            # Statystyki z docelowego folderu
            folder_files = sum(len(files) for _, _, files in os.walk(dest_folder))
            total_files += folder_files
            
            folder_size = sum(os.path.getsize(os.path.join(dirpath, filename))
                              for dirpath, _, filenames in os.walk(dest_folder)
                              for filename in filenames)
            total_size += folder_size
            
            print(f"✅ {source_folder.name:>18} → {dest_folder.absolute()}")
        
        # Podsumowanie
        print("\n" + "=" * 60)
        print("📊 PODSUMOWANIE BACKUPU")
        print("=" * 60)
        print(f"📁 Backup zapisany: {backup_path.absolute()}")
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
    """Lista wszystkich backupów"""
    backups_path = SCRIPT_DIR / BACKUP_ROOT
    if not backups_path.exists():
        print("ℹ️  Brak folderu backupów")
        return
    
    backups = sorted(backups_path.iterdir(), key=os.path.getmtime, reverse=True)
    print("\n📋 AKTUALNE BACKUPY (najnowsze pierwsze):")
    print("-" * 50)
    for backup in list(backups)[:10]:  # 10 najnowszych
        if backup.is_dir():
            print(f"📁 {backup.name}")


def cleanup_old_backups(days=30):
    """Usuń backupy starsze niż X dni"""
    import time
    backups_path = SCRIPT_DIR / BACKUP_ROOT
    
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
        # Domyślnie: stwórz backup
        success = create_backup()
        sys.exit(0 if success else 1)

