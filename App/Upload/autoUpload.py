import os
import difflib
import pickle
import re
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# Zakres uprawnień - pełny dostęp do przesyłania filmów
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

def get_authenticated_service():
    """Obsługuje proces logowania i zapamiętuje token dostępu."""
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
            
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('client_secret.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    return build('youtube', 'v3', credentials=creds)

def clean_extracted_title(title_text):
    """Usuwa gwiazdki oraz słowo 'title' (niezależnie od wielkości liter)."""
    # Usuwanie gwiazdek
    title_text = title_text.replace('*', '')
    title_text = title_text.replace(':', '')
    
    # Usuwanie słowa 'title' przy użyciu wyrażeń regularnych (case-insensitive)
    # \b oznacza granice słowa, aby nie usunąć fragmentu innego wyrazu
    title_text = re.sub(r'\btitle\b', '', title_text, flags=re.IGNORECASE)
    
    # Usuwanie zbędnych spacji powstałych po czyszczeniu
    return title_text.strip()

def get_content_and_title(video_filename_stem, desc_dir):
    """
    Znajduje pasujący plik tekstowy (.txt lub .md), wyciąga pierwszą linię jako tytuł,
    czyści go, a resztę ustawia jako opis.
    """
    # Dodana obsługa plików .md
    desc_files = [f for f in os.listdir(desc_dir) if f.endswith(('.txt', '.md'))]
    if not desc_files:
        return clean_extracted_title(video_filename_stem.replace('_', ' ')), "Brak opisu dla tego filmu."

    matches = difflib.get_close_matches(video_filename_stem, desc_files, n=1, cutoff=0.1)
    
    if matches:
        match_path = os.path.join(desc_dir, matches[0])
        with open(match_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        if lines:
            # Pobranie i wyczyszczenie tytułu z pierwszej linii
            raw_title = lines[0].strip()
            extracted_title = clean_extracted_title(raw_title)
            
            # Jeśli po czyszczeniu tytuł jest pusty, użyj nazwy pliku
            if not extracted_title:
                extracted_title = clean_extracted_title(video_filename_stem.replace('_', ' '))

            # Reszta linii staje się opisem
            extracted_desc = "".join(lines[1:]).strip()
            if not extracted_desc:
                extracted_desc = "Zapraszam do oglądania!"
                
            return extracted_title, extracted_desc
    
    return clean_extracted_title(video_filename_stem.replace('_', ' ')), "Nie znaleziono pasującego pliku opisu."

def upload_shorts(youtube, video_path, title, description):
    """Przesyła wideo jako YouTube Shorts."""
    print(f"Rozpoczynanie przesyłania: {title}")
    
    body = {
        'snippet': {
            'title': title[:100], 
            'description': description,
            'categoryId': '22'
        },
        'status': {
            'privacyStatus': 'public',
            'selfDeclaredMadeForKids': False
        }
    }

    media = MediaFileUpload(
        video_path, 
        mimetype='video/mp4', 
        resumable=True, 
        chunksize=1024*1024 
    )

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media
    )

    response = request.execute()
    print(f"Sukces! Film dostępny pod adresem: https://youtu.be/{response.get('id')}")

def main():
    video_dir = "../../ReadyContent/shorts"
    desc_dir = "../../ReadyContent/readyDescriptions"

    if not os.path.exists(video_dir) or not os.path.exists(desc_dir):
        print("Błąd: Jeden z folderów nie istnieje.")
        return

    youtube = get_authenticated_service()

    videos = [f for f in os.listdir(video_dir) if f.endswith('.mp4')]
    
    if not videos:
        print("Nie znaleziono plików .mp4.")
        return

    for video_file in videos:
        video_path = os.path.join(video_dir, video_file)
        file_stem = os.path.splitext(video_file)[0]
        
        final_title, final_description = get_content_and_title(file_stem, desc_dir)
        
        try:
            upload_shorts(youtube, video_path, final_title, final_description)
        except Exception as e:
            print(f"Wystąpił błąd przy {video_file}: {e}")

if __name__ == "__main__":
    main()