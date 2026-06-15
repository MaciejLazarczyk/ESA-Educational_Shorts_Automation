#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🎬 SHORTS CONVERTER + COMPILER (FUZZY NUMBER MATCHING)
================================================================================
1. Łączy obraz + dźwięk z shorts_temp jeśli mają TEN SAM CIĄG CYFR w nazwie
2. Np. "moj_short_001.jpg" + "rozne_slowa_001.mp3" → MP4
3. Kompiluje wg numeru w nazwie rosnąco

Struktura:
  shorts_temp/
    ├── dowolna_nazwa_001.jpg + inne_slowa_001.mp3
    ├── text_002.png + audio_002.mp3
    └── ...

  OUTPUT:
    mp4_temp/ + shorts/final_short.mp4
================================================================================
"""

import os
import subprocess
from pathlib import Path
from difflib import SequenceMatcher
from datetime import datetime
import re

# ============================================================================
# KONFIGURACJA
# ============================================================================

SHORTS_TEMP_DIR = "shorts_temp"
MP4_TEMP_DIR = "mp4_temp"
FINALS_DIR = "../../ReadyContent/shorts"
LOGS_DIR = "logs"

VIDEO_BITRATE = "1000k"
AUDIO_BITRATE = "192k"
FPS = 24

# ============================================================================
# SETUP
# ============================================================================

def setup_directories():
    """Tworzy niezbędne foldery"""
    for directory in [MP4_TEMP_DIR, FINALS_DIR, LOGS_DIR]:
        Path(directory).mkdir(exist_ok=True)
    print(f"✅ Foldery utworzone: {MP4_TEMP_DIR}, {FINALS_DIR}, {LOGS_DIR}")
    
    if not Path(SHORTS_TEMP_DIR).exists():
        print(f"❌ BŁĄD: Brak folderu {SHORTS_TEMP_DIR}")
        return False
    return True

def log_to_file(message, log_type="conversion"):
    """Zapisuje do log pliku"""
    log_path = f"{LOGS_DIR}/shorts_converter_log.txt"
    with open(log_path, "a", encoding="utf-8") as f:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"[{timestamp}] {message}\n")

# ============================================================================
# FUZZY NUMBER MATCHING
# ============================================================================

def extract_numbers(filename):
    """Wyodrębnia WSZYSTKIE ciągi cyfr z nazwy pliku"""
    # Znajdź wszystkie sekwencje cyfr (1+ cyfr)
    numbers = re.findall(r'\d+', filename)
    return numbers

def find_number_matches():
    """
    Znajduje pary obraz+dźwięk z IDENTYCZNYMI ciągami cyfr w nazwie
    Np. "rozne_001.mp3" + "image_001.jpg" → match
    """
    temp_path = Path(SHORTS_TEMP_DIR)
    
    # Wszystkie pliki
    all_files = list(temp_path.iterdir())
    images = [f for f in all_files if f.suffix.lower() in ['.jpg', '.jpeg', '.png', '.webp']]
    audios = [f for f in all_files if f.suffix.lower() == '.mp3']
    
    print(f"📁 Znaleziono: {len(images)} obrazów, {len(audios)} audio")
    
    # Mapa: liczba -> lista plików z tą liczbą
    number_to_files = {}
    
    # Grupuj pliki wg ich liczb
    for file in images + audios:
        numbers = extract_numbers(file.stem)
        for num in numbers:
            if num not in number_to_files:
                number_to_files[num] = []
            number_to_files[num].append(file)
    
    # Znajdź pary (image + audio) z IDENTYCZNYMI liczbami
    pairs = []
    used_files = set()
    
    print("\n🔍 Szukanie par z identycznymi liczbami...")
    
    for number, files_with_number in number_to_files.items():
        # Filtruj tylko obrazy i audio z tej listy
        imgs_in_group = [f for f in files_with_number if f.suffix.lower() in ['.jpg', '.jpeg', '.png', '.webp']]
        audios_in_group = [f for f in files_with_number if f.suffix.lower() == '.mp3']
        
        # Znajdź wszystkie możliwe pary
        for img in imgs_in_group:
            for audio in audios_in_group:
                if img not in used_files and audio not in used_files:
                    pairs.append((img, audio, number))
                    used_files.add(img)
                    used_files.add(audio)
                    print(f"   ✅ MATCH: {img.stem} + {audio.stem} [liczba: {number}]")
                    break  # Jeden audio na obraz
    
    print(f"\n✅ Znaleziono {len(pairs)} pasujących par\n")
    return pairs

def extract_sort_number(filename):
    """Wyodrębnia PIERWSZY ciąg cyfr do sortowania"""
    match = re.search(r'\d+', filename)
    return int(match.group()) if match else float('inf')

# ============================================================================
# FFMPEG
# ============================================================================

def create_video_from_pair(image_file, audio_file, number, output_file):
    """Tworzy MP4 z obrazu i audio"""
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5, check=True)
    except:
        print(f"❌ BŁĄD: ffmpeg nie zainstalowany!")
        return False
    
    cmd = [
        "ffmpeg",
        "-loop", "1",
        "-i", str(image_file),
        "-i", str(audio_file),
        "-c:v", "libx264",
        "-c:a", "aac",
        "-b:a", AUDIO_BITRATE,
        "-b:v", VIDEO_BITRATE,
        "-vf", f"fps={FPS},scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black",
        "-shortest",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        "-y",
        str(output_file)
    ]
    
    try:
        subprocess.run(cmd, capture_output=True, timeout=60, check=True)
        return True
    except:
        print(f"   ❌ FFMPEG BŁĄD: {output_file.name}")
        return False

# ============================================================================
# KOMPILACJA
# ============================================================================

def compile_all_mp4s(pairs):
    """Łączy wszystkie MP4 wg numeru sortowania"""
    mp4_files = list(Path(MP4_TEMP_DIR).glob("*.mp4"))
    
    if not mp4_files:
        print("❌ Brak plików MP4 w mp4_temp/")
        return False
    
    # Sortuj wg PIERWSZEGO ciągu cyfr w nazwie
    sorted_files = sorted(mp4_files, key=lambda f: extract_sort_number(f.stem))
    
    print(f"📋 Łączenie {len(sorted_files)} plików (posortowane wg numeru):")
    for i, f in enumerate(sorted_files, 1):
        sort_num = extract_sort_number(f.stem)
        print(f"   {i:2d}. {f.name} [sort: {sort_num}]")
    
    # Lista concat
    concat_list_path = Path(MP4_TEMP_DIR) / "filelist.txt"
    with open(concat_list_path, "w") as f:
        for mp4_file in sorted_files:
            f.write(f"file '{mp4_file.absolute()}'\n")
    
    # Finalny plik
    output_final = Path(FINALS_DIR) / "final_short.mp4"
    cmd = [
        "ffmpeg",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_list_path),
        "-c", "copy",
        "-movflags", "+faststart",
        "-y",
        str(output_final)
    ]
    
    try:
        subprocess.run(cmd, capture_output=True, timeout=300, check=True)
        print(f"\n🎉 GOTOWY: {output_final}")
        log_to_file(f"✅ Finalny plik: {output_final} ({len(sorted_files)} segmentów)")
        return True
    except Exception as e:
        print(f"❌ BŁĄD kompilacji: {str(e)[:100]}")
        return False

# ============================================================================
# GŁÓWNA LOGIKA
# ============================================================================

def process_shorts():
    """Główny proces"""
    print("\n" + "="*80)
    print("🎬 SHORTS CONVERTER (NUMBER FUZZY MATCHING)")
    print("="*80)
    
    if not setup_directories():
        return
    
    # KROK 1: Znajdź pary z identycznymi liczbami
    pairs = find_number_matches()
    if not pairs:
        print("❌ Brak pasujących par z identycznymi liczbami")
        print("\n💡 PRZYKŁADY PASUJĄCYCH PAR:")
        print("   - 'moj_short_001.jpg' + 'audio_001.mp3'")
        print("   - 'image_23.png' + 'rozne_23.mp3'")
        return
    
    # KROK 2: Konwertuj do MP4
    print("\n🔄 KROK 1: Tworzenie MP4...")
    total_converted = 0
    
    for img, audio, number in pairs:
        output_name = f"segment_{number.zfill(3)}.mp4"
        output_mp4 = Path(MP4_TEMP_DIR) / output_name
        
        if output_mp4.exists():
            print(f"   ⏭️ {output_name} już istnieje")
            total_converted += 1
            continue
        
        print(f"   🔄 {img.stem} + {audio.stem} → {output_name}")
        if create_video_from_pair(img, audio, number, output_mp4):
            print(f"     ✅ {output_name}")
            total_converted += 1
        else:
            print(f"     ❌ BŁĄD")
    
    print(f"\n📊 Krok 1: Utworzono {total_converted}/{len(pairs)} MP4")
    
    # KROK 3: Kompilacja
    print("\n🔄 KROK 2: Kompilacja finalnego pliku...")
    compile_all_mp4s(pairs)

# ============================================================================
# CLI
# ============================================================================

def main():
    import sys
    
    print("""
🎬 SHORTS CONVERTER v2.1 - NUMBER FUZZY MATCHING
================================================================================
🔍 Łączy pliki jeśli mają TEN SAM CIĄG CYFR w nazwie!
Np. "tekst_001.jpg" + "audio_001.mp3" → MP4

PRZYKŁADY PASUJĄCYCH PAR:
  • "moj_short_001.jpg" + "rozne_slowa_001.mp3"
  • "image_23.png" + "dźwięk_23.mp3"  
  • "clip_045.webp" + "voice_045.mp3"

Wymagania: FFmpeg
================================================================================
    """)
    
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5, check=True)
        print("✅ FFmpeg OK\n")
    except:
        print("❌ FFmpeg wymagany! https://ffmpeg.org/download.html")
        sys.exit(1)
    
    process_shorts()

if __name__ == "__main__":
    main()
