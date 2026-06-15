import os
import sqlite3
import openai
from openai import OpenAI
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from datetime import datetime

# --- KONFIGURACJA ---
NAGA_API_KEY = os.environ["NAGA_API_KEY"]
MAX_VIDEOS = 10
PROMPT_FILE = "instrukcje.txt"
DB_FILE = "processed_comments.db"
SCOPES = ['https://www.googleapis.com/auth/youtube.force-ssl']

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS comments 
                 (comment_id TEXT PRIMARY KEY, author TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    return conn

def is_processed(conn, comment_id):
    c = conn.cursor()
    c.execute("SELECT 1 FROM comments WHERE comment_id = ?", (comment_id,))
    return c.fetchone() is not None

def mark_processed(conn, comment_id, author):
    c = conn.cursor()
    c.execute("INSERT INTO comments (comment_id, author) VALUES (?, ?)", (comment_id, author))
    conn.commit()

def load_prompt(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except FileNotFoundError:
        return "Odpowiadaj krótko i merytorycznie."

def generate_ai_reply(history_context, system_prompt):
    try:
        client = OpenAI(base_url="https://api.naga.ac/v1", api_key=NAGA_API_KEY)
        messages = [{"role": "system", "content": system_prompt}] + history_context
        resp = client.chat.completions.create(
            model="gpt-5-mini-2025-08-07:free",
            messages=messages,
            temperature=0.7,
        )
        return resp.choices[0].message.content
    except Exception as e:
        print(f"Błąd AI: {e}")
        return None

def get_youtube_client():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('client_secret.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return build('youtube', 'v3', credentials=creds)

def get_my_channel_id(youtube):
    res = youtube.channels().list(mine=True, part="id").execute()
    return res['items'][0]['id']

def process_deep_comments():
    db_conn = init_db()
    youtube = get_youtube_client()
    my_id = get_my_channel_id(youtube)
    system_prompt = load_prompt(PROMPT_FILE)
    
    # Pobierz filmy
    channels_res = youtube.channels().list(mine=True, part="contentDetails").execute()
    uploads_id = channels_res['items'][0]['contentDetails']['relatedPlaylists']['uploads']
    videos_res = youtube.playlistItems().list(playlistId=uploads_id, part="snippet", maxResults=MAX_VIDEOS).execute()
    video_ids = [item['snippet']['resourceId']['videoId'] for item in videos_res.get('items', [])]

    for video_id in video_ids:
        print(f"\n--- Wideo: {video_id} ---")
        try:
            threads = youtube.commentThreads().list(
                part="snippet,replies",
                videoId=video_id,
                maxResults=50,
                order="time" # Najnowsze wątki najpierw
            ).execute()

            for thread in threads.get('items', []):
                top_comment = thread['snippet']['topLevelComment']
                top_id = top_comment['id']
                
                # Pobieramy WSZYSTKIE odpowiedzi dla tego wątku (ważne dla długich rozmów)
                # Jeśli jest więcej niż 5 odpowiedzi, poprzedni skrypt mógł ich nie widzieć
                all_comments_in_thread = []
                
                # Dodaj główny komentarz
                all_comments_in_thread.append({
                    'id': top_comment['id'],
                    'text': top_comment['snippet']['textDisplay'],
                    'author_id': top_comment['snippet']['authorChannelId']['value'],
                    'date': top_comment['snippet']['publishedAt']
                })

                # Pobierz odpowiedzi z obiektu replies (jeśli istnieją)
                replies_list = thread.get('replies', {}).get('comments', [])
                for r in replies_list:
                    all_comments_in_thread.append({
                        'id': r['id'],
                        'text': r['snippet']['textDisplay'],
                        'author_id': r['snippet']['authorChannelId']['value'],
                        'date': r['snippet']['publishedAt']
                    })

                # KLUCZOWE: Sortujemy chronologicznie po dacie (od najstarszych do najnowszych)
                all_comments_in_thread.sort(key=lambda x: x['date'])

                # Sprawdzamy ostatni komentarz w posortowanej liście
                last_msg = all_comments_in_thread[-1]
                
                if last_msg['author_id'] == my_id:
                    # Ostatnie słowo należy do nas - pomijamy
                    continue
                
                if is_processed(db_conn, last_msg['id']):
                    continue

                print(f"Nowa wiadomość od widza w wątku {top_id[:5]}...")

                # Budujemy historię dla AI
                history = []
                for msg in all_comments_in_thread:
                    role = "assistant" if msg['author_id'] == my_id else "user"
                    history.append({"role": role, "content": msg['text']})

                ai_reply = generate_ai_reply(history, system_prompt)

                if ai_reply:
                    youtube.comments().insert(
                        part="snippet",
                        body={
                            "snippet": {
                                "parentId": top_id, # Zawsze odpowiadamy do korzenia
                                "textOriginal": ai_reply
                            }
                        }
                    ).execute()

                    mark_processed(db_conn, last_msg['id'], "AI")
                    print("-> Odpowiedziano.")

        except Exception as e:
            print(f"Błąd przetwarzania wątku: {e}")
            continue

    db_conn.close()

if __name__ == "__main__":
    process_deep_comments()