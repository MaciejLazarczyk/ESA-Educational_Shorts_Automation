#!/usr/bin/env python3
"""
CONTENT GENERATOR - Historia i statystyki generowanych treści
Skrypt do śledzenia historii generowania artykułów, opisów i miniatur
"""

import json
import os
from datetime import datetime
from pathlib import Path

# Konfiguracja
HISTORY_FILE = "generation_history.json"
ARTICLES_DIR = "readyArticles"
DESCRIPTIONS_DIR = "readyDescriptions"
PROMPTS_DIR = "prompts"
IMAGES_DIR = "photosCompress"


def load_history() -> list:
    """Załaduj historię z pliku JSON"""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
    return []


def save_history(history: list):
    """Zapisz historię do pliku JSON"""
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


def add_to_history(summary: str, article_file: str = None, description_file: str = None, 
                   prompt_file: str = None, image_file: str = None):
    """Dodaj nowy zapis do historii"""
    history = load_history()
    
    entry = {
        "timestamp": datetime.now().isoformat(),
        "summary": summary,
        "files": {
            "article": article_file,
            "description": description_file,
            "prompt": prompt_file,
            "image": image_file,
        },
        "status": "completed"
    }
    
    history.append(entry)
    save_history(history)
    print(f"✅ Dodano do historii: {summary[:50]}...")


def view_history():
    """Wyświetl całą historię"""
    history = load_history()
    
    if not history:
        print("📝 Historia jest pusta.")
        return
    
    print("\n" + "="*80)
    print("📋 HISTORIA GENEROWANYCH TREŚCI")
    print("="*80 + "\n")
    
    for i, entry in enumerate(history, 1):
        timestamp = entry.get("timestamp", "Unknown")
        summary = entry.get("summary", "Unknown")
        
        print(f"{i}. [{timestamp}]")
        print(f"   📌 {summary}")
        print(f"   📄 Artykuł: {entry['files'].get('article', 'Brak')}")
        print(f"   📝 Opis: {entry['files'].get('description', 'Brak')}")
        print(f"   🎨 Prompt: {entry['files'].get('prompt', 'Brak')}")
        print(f"   🖼️  Miniatura: {entry['files'].get('image', 'Brak')}")
        print()


def get_stats():
    """Pokaż statystyki"""
    history = load_history()
    
    articles = len([f for f in os.listdir(ARTICLES_DIR) if f.endswith(".txt")]) if os.path.exists(ARTICLES_DIR) else 0
    descriptions = len([f for f in os.listdir(DESCRIPTIONS_DIR) if f.endswith(".md")]) if os.path.exists(DESCRIPTIONS_DIR) else 0
    prompts = len([f for f in os.listdir(PROMPTS_DIR) if f.endswith(".txt")]) if os.path.exists(PROMPTS_DIR) else 0
    images = len([f for f in os.listdir(IMAGES_DIR) if f.endswith((".png", ".webp", ".jpg", ".jpeg"))]) if os.path.exists(IMAGES_DIR) else 0
    
    print("\n" + "="*80)
    print("📊 STATYSTYKI GENEROWANIA")
    print("="*80 + "\n")
    
    print(f"📚 Artykuły: {articles} plików")
    print(f"📝 Opisy YouTube: {descriptions} plików")
    print(f"🎨 Prompty do miniatur: {prompts} plików")
    print(f"🖼️  Miniatury: {images} plików")
    print(f"📋 Historia: {len(history)} wpisów")
    
    total_size = 0
    for folder in [ARTICLES_DIR, DESCRIPTIONS_DIR, PROMPTS_DIR, IMAGES_DIR]:
        if os.path.exists(folder):
            for file in os.listdir(folder):
                filepath = os.path.join(folder, file)
                if os.path.isfile(filepath):
                    total_size += os.path.getsize(filepath)
    
    print(f"💾 Całkowity rozmiar: {total_size/1024/1024:.2f} MB\n")


def cleanup_old_files(days: int = 30):
    """Usuń pliki starsze niż N dni (opcjonalnie)"""
    import time
    
    now = time.time()
    cutoff = now - (days * 24 * 60 * 60)
    
    deleted = 0
    for folder in [ARTICLES_DIR, DESCRIPTIONS_DIR, PROMPTS_DIR, IMAGES_DIR]:
        if os.path.exists(folder):
            for file in os.listdir(folder):
                filepath = os.path.join(folder, file)
                if os.path.isfile(filepath):
                    if os.path.getmtime(filepath) < cutoff:
                        os.remove(filepath)
                        deleted += 1
    
    print(f"🗑️  Usunięto {deleted} starych plików (starszych niż {days} dni)")


def export_history_csv():
    """Eksportuj historię do CSV"""
    import csv
    
    history = load_history()
    
    if not history:
        print("⚠️ Historia jest pusta.")
        return
    
    csv_file = f"history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["timestamp", "summary", "article", "description", "prompt", "image"])
        writer.writeheader()
        
        for entry in history:
            writer.writerow({
                "timestamp": entry["timestamp"],
                "summary": entry["summary"],
                "article": entry["files"].get("article", ""),
                "description": entry["files"].get("description", ""),
                "prompt": entry["files"].get("prompt", ""),
                "image": entry["files"].get("image", ""),
            })
    
    print(f"✅ Historia eksportowana do: {csv_file}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "view":
            view_history()
        elif command == "stats":
            get_stats()
        elif command == "cleanup":
            days = int(sys.argv[2]) if len(sys.argv) > 2 else 30
            cleanup_old_files(days)
        elif command == "export":
            export_history_csv()
        else:
            print("Dostępne polecenia:")
            print("  python history.py view      - Wyświetl historię")
            print("  python history.py stats     - Pokaż statystyki")
            print("  python history.py cleanup [days] - Usuń stare pliki")
            print("  python history.py export    - Eksportuj do CSV")
    else:
        get_stats()
