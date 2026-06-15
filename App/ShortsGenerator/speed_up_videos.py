import os
import subprocess
from pathlib import Path


HERE = Path(__file__).resolve().parent  # [web:74]
BASE = HERE.parent.parent               # odpowiednik ../../ względem tego pliku [web:77]


OUTPUT_FOLDER = BASE / "ReadyContent" / "shorts"
SPEED_MULTIPLIER = 1.1  # Bazowa prędkość
MAX_DURATION_SEC = 58   # Maksymalna długość po przyspieszeniu


def get_duration(file_path):
    """Pobiera długość wideo w sekundach używając ffprobe"""
    cmd = [
        'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
        '-of', 'csv=p=0', file_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        return float(result.stdout.strip())
    return None


def speed_up_videos():
    """
    Przyspiesza wszystkie pliki MP4 w folderze shorts.
    Używa SPEED_MULTIPLIER jeśli wynik <=58s, inaczej adaptacyjnie zwiększa.
    Nadpisuje pliki z tą samą nazwą.
    """
    
    if not os.path.exists(OUTPUT_FOLDER):
        print(f"❌ Folder '{OUTPUT_FOLDER}' nie istnieje!")
        return
    
    # Pobierz listę plików MP4
    mp4_files = [f for f in os.listdir(OUTPUT_FOLDER) if f.lower().endswith('.mp4')]
    
    if not mp4_files:
        print(f"❌ Brak plików MP4 w folderze '{OUTPUT_FOLDER}'!")
        return
    
    print(f"⚡ Adaptacyjne przyspieszanie {len(mp4_files)} pliku/ów (bazowa: {SPEED_MULTIPLIER}x, cel: max {MAX_DURATION_SEC}s)...\n")
    
    for filename in mp4_files:
        file_path = os.path.join(OUTPUT_FOLDER, filename)
        temp_path = os.path.join(OUTPUT_FOLDER, f"temp_{filename}")
        
        print(f"📹 Przetwarzanie: {filename}")
        
        # Pobierz oryginalną długość
        duration = get_duration(file_path)
        if duration is None:
            print(f"   ❌ Nie można odczytać długości pliku!\n")
            continue
        
        print(f"   📏 Oryginalna długość: {duration:.1f}s")
        
        # Sprawdź czy SPEED_MULTIPLIER wystarczy
        projected_duration = duration * (1/SPEED_MULTIPLIER)
        if projected_duration <= MAX_DURATION_SEC:
            speed_factor = SPEED_MULTIPLIER
            print(f"   ✅ SPEED_MULTIPLIER OK ({projected_duration:.1f}s <= {MAX_DURATION_SEC}s)")
        else:
            # Adaptacyjnie zwiększ prędkość
            speed_factor = duration / MAX_DURATION_SEC
            print(f"   ⚠️ Za długo po {SPEED_MULTIPLIER}x ({projected_duration:.1f}s)")
        
        speed_factor = max(speed_factor, 1.01)  # min zmiana
        speed_factor = min(speed_factor, 4.0)   # max 4x
        
        # Dopasuj audio tempo
        audio_tempo = min(speed_factor, 2.0)
        
        print(f"   🚀 Prędkość: {speed_factor:.2f}x (audio: {audio_tempo:.2f}x)")
        
        cmd = [
            'ffmpeg', '-i', file_path,
            '-filter:v', f'setpts=PTS/{speed_factor}',
            '-filter:a', f'atempo={audio_tempo}',
            '-y', temp_path
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                # Zastąp oryginalny plik
                os.remove(file_path)
                os.rename(temp_path, file_path)
                
                new_duration = get_duration(file_path)
                size_mb = os.path.getsize(file_path) / (1024*1024)
                print(f"   ✅ Gotowe! ({size_mb:.1f} MB, {new_duration:.1f}s)\n")
            else:
                print(f"   ❌ Błąd: {result.stderr[:200]}\n")
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                
        except FileNotFoundError:
            print(f"   ❌ FFmpeg/ffprobe nie znaleziony!\n")
    
    print("✅ Adaptacyjne przyspieszanie zakończone!")


if __name__ == "__main__":
    print(f"🎬 Bazowa prędkość: {SPEED_MULTIPLIER}x\n")
    speed_up_videos()
