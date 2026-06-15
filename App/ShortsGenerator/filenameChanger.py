import os
from pathlib import Path

def main():
    # Pobierz folder od użytkownika
    folder_path = input("Podaj ścieżkę do folderu (lub Enter dla bieżącego): ").strip()
    if not folder_path:
        folder_path = "."
    folder = Path(folder_path)
    
    if not folder.exists():
        print(f"Błąd: Folder '{folder}' nie istnieje!")
        return
    
    # Pobierz teksty do zamiany
    old_text = input("Tekst do zastąpienia (tekstA): ").strip()
    new_text = input("Nowy tekst (tekstB): ").strip()
    
    if not old_text:
        print("Błąd: Podaj tekstA!")
        return
    
    pliki = list(folder.iterdir())
    pliki_do_zmiany = [p for p in pliki if p.is_file() and old_text in p.name]
    
    if not pliki_do_zmiany:
        print(f"Brak plików z '{old_text}' w folderze.")
        return
    
    print(f"\nPodgląd zmian ({len(pliki_do_zmiany)} plików):")
    for p in pliki_do_zmiany:
        new_name = p.name.replace(old_text, new_text)
        print(f"  {p.name} → {new_name}")
    
    potwierdzenie = input("\nWykonać zmiany? (tak/nie): ").strip().lower()
    if potwierdzenie in ['tak', 't', 'y', 'yes']:
        zmieniono = 0
        for p in pliki_do_zmiany:
            new_name = p.name.replace(old_text, new_text)
            new_path = p.parent / new_name
            try:
                p.rename(new_path)
                print(f"✓ {p.name} → {new_name}")
                zmieniono += 1
            except Exception as e:
                print(f"✗ Błąd {p.name}: {e}")
        
        print(f"\nGotowe! Zmieniono {zmieniono} plików.")
    else:
        print("Anulowano.")

if __name__ == "__main__":
    main()
