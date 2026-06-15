import os
import re
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parent.parent

SOURCE_FOLDER = "mp4_temp"
OUTPUT_FOLDER = BASE / "ReadyContent" / "shorts"
OUTPUT_FILE = "readyShort"
SOURCE_ARTICLE_FOLDER = BASE / "ReadyContent" / "readyArticles"

def extract_number_from_filename(filename):
    match = re.search(r'(\d+)', filename)
    return int(match.group(1)) if match else float('inf')


def create_concat_file(file_list, concat_file_path):
    """Utwórz plik concat.txt z BEZWZGLĘDNYMI ścieżkami"""
    with open(concat_file_path, 'w', encoding='utf-8') as f:
        for file_path in file_list:
            # Konwertuj na ścieżkę bezwzględną
            abs_path = os.path.abspath(file_path)
            # Użyj forward slashes dla FFmpeg
            safe_path = abs_path.replace('\\', '/')
            f.write(f"file '{safe_path}'\n")


def merge_mp4_files():
    if not os.path.exists(SOURCE_FOLDER):
        print(f"❌ Folder '{SOURCE_FOLDER}' nie istnieje!")
        return
    
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    
    mp4_files = [f for f in os.listdir(SOURCE_FOLDER) if f.lower().endswith('.mp4')]
    if not mp4_files:
        print(f"❌ Brak plików MP4 w folderze '{SOURCE_FOLDER}'!")
        return
    
    print(f"✅ Znaleziono {len(mp4_files)} plików MP4")
    sorted_files = sorted(mp4_files, key=extract_number_from_filename)
    
    print(f"\n📋 Posortowana kolejność:")
    for i, f in enumerate(sorted_files, 1):
        num = extract_number_from_filename(f)
        print(f"   {i:2d}. {f} [sort: {num}]")
    
    # ✅ Użyj BEZWZGLĘDNYCH ścieżek
    full_paths = [os.path.join(SOURCE_FOLDER, f) for f in sorted_files]
    
    concat_file = os.path.join(OUTPUT_FOLDER, "filelist.txt")
    create_concat_file(full_paths, concat_file)
    
    # Wyświetl pierwszą ścieżkę do debugowania
    print(f"\n🔍 Debug - przykładowa ścieżka z filelist.txt:")
    with open(concat_file, 'r') as f:
        first_line = f.readline()
        print(f"   {first_line.strip()}")
    article_names = [f for f in os.listdir(SOURCE_ARTICLE_FOLDER)]
    if not article_names:
        print(f"❌ Brak plików MP4 w folderze '{SOURCE_ARTICLE_FOLDER}'!")
        return
    OUTPUT_FILE = f"{article_names[0]}.mp4"
    output_path = os.path.abspath(os.path.join(OUTPUT_FOLDER, OUTPUT_FILE))
    
    # ✅ NOWA KOMENDA - Re-encoding z korektą audio
    cmd = [
        'ffmpeg', '-f', 'concat', '-safe', '0', 
        '-i', concat_file, 
        '-c:v', 'libx264',                    # Re-encode wideo
        '-preset', 'ultrafast',               # Maksymalna szybkość bez straty
        '-crf', '23',                         # Jakość (23 = visually lossless)
        '-c:a', 'aac',                        # Re-encode audio
        '-ar', '48000',                       # Sample rate 48kHz (standard)
        '-b:a', '128k',                       # Bitrate audio
        '-fflags', '+genpts',                 # Generuj nowe timestampy
        '-avoid_negative_ts', 'make_zero',    # Unikaj ujemnych timestampów
        '-y',
        output_path
    ]
    
    print(f"\n⚙️ Uruchamianie FFmpeg z re-encodingiem (audio sync...)...")
    print(f"📊 Komenda: {' '.join(cmd)}\n")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            size_mb = os.path.getsize(output_path) / (1024*1024)
            print(f"\n✅ SUKCES! {output_path}")
            print(f"📊 Rozmiar: {size_mb:.1f} MB")
            print(f"🎵 Audio jest w pełni zsynchronizowane!")
            os.remove(concat_file)
        else:
            print(f"\n❌ BŁĄD FFmpeg (kod: {result.returncode}):")
            print("STDERR:", result.stderr[:500])  # Pierwsze 500 znaków
            
    except FileNotFoundError:
        print("\n❌ FFmpeg nie znaleziony!")
        print("💡 Pobierz FFmpeg: https://ffmpeg.org/download.html")


if __name__ == "__main__":
    merge_mp4_files()
