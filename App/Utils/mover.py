import os
import random
import shutil

# Ścieżki do folderów - dostosuj do swoich potrzeb
folder1 = "../adsMaterial"  # Źródłowy folder
folder2 = "readyArticles"  # Docelowy folder

# Sprawdź, czy foldery istnieją
if not os.path.exists(folder1):
    print(f"Błąd: Folder '{folder1}' nie istnieje!")
    exit(1)

if not os.path.exists(folder2):
    os.makedirs(folder2)  # Utwórz folder2, jeśli nie istnieje

# Lista plików w folder1 (tylko pliki, bez podfolderów)
pliki = [f for f in os.listdir(folder1) if os.path.isfile(os.path.join(folder1, f))]

if not pliki:
    print(f"Brak plików w folderze '{folder1}'!")
    exit(1)

# Wybierz losowy plik
losowy_plik = random.choice(pliki)
sciezka_zrodlowa = os.path.join(folder1, losowy_plik)
sciezka_docelowa = os.path.join(folder2, losowy_plik)

# Przenieś plik
shutil.move(sciezka_zrodlowa, sciezka_docelowa)
print(f"Przeniesiono: '{losowy_plik}' z '{folder1}' do '{folder2}'")
