#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import httpx
import json
import re
import subprocess
import sys
from datetime import datetime
from openai import OpenAI
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parent.parent

ARTICLES_DIR      = BASE / "ReadyContent" / "readyArticles"
DESCRIPTIONS_DIR  = BASE / "ReadyContent" / "readyDescriptions"
PROMPTS_DIR       = BASE / "ReadyContent" / "prompts"
IMAGES_DIR        = BASE / "ReadyContent" / "photosCompress"
POSTS_DIR         = BASE / "ReadyContent" / "readyPosts"
LOG_FILE          = BASE / "ReadyContent" / "log.txt"

# ========== BACKUP ==========
print("\n🛡️  AUTOMATYCZNY BACKUP ISTNIEJĄCYCH PLIKÓW...")
try:
    import backup
    if backup.create_backup():
        print("✅ Backup utworzony")
    else:
        print("⚠️  Błąd backupu - kontynuuję")
except ImportError:
    print("⚠️  backup.py nie znaleziony - pomijam")
except Exception as e:
    print(f"⚠️  Błąd backupu: {e} - kontynuuję")
print("===========================================\n")

# ====================== KONFIGURACJA ======================

NAGA_API_KEY = os.environ["NAGA_API_KEY"]

NUM_CONTENT_SETS = 15

AI_MODELS = {
    "summaries":           "nemotron-3-super-120b-a12b:free",
    "article":             "nemotron-3-super-120b-a12b:free",
    "thumbnail_prompt":    "nemotron-3-super-120b-a12b:free",
    "youtube_description": "nemotron-3-super-120b-a12b:free",
    "community_post":      "nemotron-3-super-120b-a12b:free",
    "image_generation":    "flux-1-schnell:free",
    "topic_selection":     "nemotron-3-super-120b-a12b:free",
    "deduplication":       "nemotron-3-super-120b-a12b:free",
}

GENERATE = {
    "articles":             True,
    "youtube_descriptions": True,
    "thumbnail_prompts":    False,
    "community_posts":      False,
    "thumbnails":           False,
}

for folder in [ARTICLES_DIR, DESCRIPTIONS_DIR, PROMPTS_DIR, IMAGES_DIR, POSTS_DIR]:
    os.makedirs(folder, exist_ok=True)

naga_client = OpenAI(
    base_url="https://api.naga.ac/v1",
    api_key=NAGA_API_KEY,
)

# =========================================================

def sanitize_filename(text: str, max_length: int = 50) -> str:
    filename = re.sub(r'[<>:"/\\|?*]', '', text)
    filename = re.sub(r'\s+', '_', filename).strip('_')
    return filename[:max_length]

def load_log_topics() -> list[str]:
    if not LOG_FILE.exists():
        return []
    try:
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
        topics = []
        for line in content.strip().split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            topic = line.split(' | ', 1)[-1].strip() if ' | ' in line else ''
            if topic:
                topics.append(topic)
        return topics
    except Exception as e:
        print(f"⚠️ Błąd wczytywania log.txt: {e}")
        return []

def save_to_log(topic: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(f"{timestamp} | {topic}\n")
    print(f"📝 Zapisano do log.txt: {topic}")

# ============================================================================
# CORE CALLER — Naga.ac only (all tasks use this single entry point)
# ============================================================================

def call_ai(prompt: str, model: str | None = None) -> str | None:
    """Call Naga.ac via OpenAI-compatible SDK. No Perplexity fallback."""
    model = model or AI_MODELS["youtube_description"]
    print(f"   🤖 Naga [{model}]...", end=" ", flush=True)
    try:
        response = naga_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=2000
        )
        result = response.choices[0].message.content
        if result:
            print("✅")
            return result
        print("⚠️  empty response")
        return None
    except Exception as e:
        print(f"❌ Naga API error: {e}")
        return None


def call_openai_vision(prompt: str, model: str | None = None) -> str | None:
    """
    Image generation — Naga only (no Perplexity fallback for images).
    Falls back gracefully with a clear message.
    """
    try:
        response = naga_client.images.generate(
            model=model or AI_MODELS["image_generation"],
            prompt=prompt,
            n=1,
            size="1024x1024",
            quality="standard"
        )
        return response.data[0].url
    except Exception as e:
        print(f"❌ Naga Image Generation Error: {e}")
        print("   ℹ️  Brak fallbacku dla generowania obrazów — pomijam.")
        return None

# ============================================================================

def download_image(url: str, filename: str) -> bool:
    try:
        response = httpx.get(url, timeout=120.0)
        response.raise_for_status()
        with open(filename, "wb") as f:
            f.write(response.content)
        print(f"✅ Pobrano obraz: {filename}")
        return True
    except Exception as e:
        print(f"❌ Błąd pobierania obrazu: {e}")
        return False

def run_photo_compressor():
    script_path = "photoCompressor.py"
    if os.path.exists(script_path):
        try:
            print("\n🔄 Running photoCompressor.py...")
            subprocess.run([sys.executable, script_path], check=True)
            print("✅ Kompresja ukończona!")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ photoCompressor.py error: {e}")
            return False
    else:
        print(f"⚠️ {script_path} nie znaleziony. Pomijam kompresję.")
        return False

# ============================================================================
# ✅ AI SEMANTYCZNA DEDUPLIKACJA
# ============================================================================

def ai_filter_unique_topics(new_topics: list[str], existing_topics: list[str]) -> list[str]:
    if not existing_topics:
        print("ℹ️ Brak historii - wszystkie tematy są unikalne")
        return new_topics

    recent_existing = existing_topics[-40:]
    existing_formatted = "\n".join([f"- {t}" for t in recent_existing])
    new_formatted = "\n".join([f"{i+1}. {t}" for i, t in enumerate(new_topics)])

    dedup_prompt = (
        f"You are a content deduplication expert for a science YouTube channel.\n\n"
        f"EXISTING TOPICS (already covered - DO NOT repeat these or similar):\n"
        f"{existing_formatted}\n\n"
        f"NEW CANDIDATE TOPICS:\n"
        f"{new_formatted}\n\n"
        f"TASK: Identify which NEW topics are truly UNIQUE and NOT covered yet.\n"
        f"Consider topics as DUPLICATES if they:\n"
        f"  - Cover the same scientific concept (even with different wording)\n"
        f"  - Are variations of the same discovery or phenomenon\n"
        f"  - Would result in essentially the same video content\n\n"
        f"Reply ONLY with a JSON object in this exact format:\n"
        f'{{"unique": [1, 3, 7], "duplicates": [2, 4, 5, 6]}}\n'
        f"Where numbers are the indices of NEW topics (1-based). Nothing else."
    )

    print("🤖 AI analizuje semantyczne duplikaty...")
    response = call_ai(dedup_prompt, model=AI_MODELS["deduplication"])

    if not response:
        print("⚠️ AI deduplication nie odpowiedziało - fallback do wszystkich tematów")
        return new_topics

    try:
        json_match = re.search(r'\{.*?\}', response, re.DOTALL)
        if not json_match:
            raise ValueError("Brak JSON w odpowiedzi AI")

        result = json.loads(json_match.group())
        unique_indices = [i - 1 for i in result.get("unique", []) if 1 <= i <= len(new_topics)]
        duplicate_indices = [i - 1 for i in result.get("duplicates", []) if 1 <= i <= len(new_topics)]

        unique_topics = [new_topics[i] for i in unique_indices]

        print(f"✅ AI znalazło {len(unique_topics)} unikalnych tematów")
        print(f"🚫 AI odrzuciło {len(duplicate_indices)} duplikatów:")
        for i in duplicate_indices:
            print(f"   ✗ DUPLIKAT: {new_topics[i]}")

        return unique_topics if unique_topics else new_topics

    except Exception as e:
        print(f"⚠️ Błąd parsowania AI deduplication ({e}) - używam wszystkich tematów")
        return new_topics


def ai_select_best_topic(unique_topics: list[str]) -> str | None:
    if not unique_topics:
        print("❌ Brak unikalnych tematów do wyboru!")
        return None

    if len(unique_topics) == 1:
        print(f"✅ Tylko 1 unikalny temat: '{unique_topics[0]}'")
        return unique_topics[0]

    topics_formatted = "\n".join([f"{i+1}. {t}" for i, t in enumerate(unique_topics)])

    selection_prompt = (
        f"From the following {len(unique_topics)} unique science topics, "
        f"select EXACTLY ONE that would make the most engaging, viral YouTube Shorts science video.\n\n"
        f"Pick the topic that:\n"
        f"  - Has highest 'wow factor' and surprise element\n"
        f"  - Is accessible to general audience\n"
        f"  - Has strong visual storytelling potential\n"
        f"  - Would make someone stop scrolling\n\n"
        f"Topics:\n{topics_formatted}\n\n"
        f"Reply ONLY with the NUMBER of your best choice (1-{len(unique_topics)}). Nothing else."
    )

    print("🎯 AI wybiera najlepszy temat...")
    response = call_ai(selection_prompt, model=AI_MODELS["topic_selection"])

    if response:
        try:
            number_match = re.search(r'\b(\d+)\b', response.strip())
            if number_match:
                idx = int(number_match.group(1)) - 1
                if 0 <= idx < len(unique_topics):
                    best = unique_topics[idx]
                    print(f"🎉 AI wybrało: #{idx+1} → '{best}'")
                    return best
        except Exception as e:
            print(f"⚠️ Błąd parsowania wyboru: {e}")

    print(f"✅ Fallback: pierwszy unikalny temat: '{unique_topics[0]}'")
    return unique_topics[0]


# ============================================================================
# GŁÓWNA PĘTLA
# ============================================================================

best_topic = None
max_attempts = 5

for attempt in range(1, max_attempts + 1):
    print(f"\n{'='*80}")
    print(f"🔄 PRÓBA {attempt}/{max_attempts}")
    print(f"{'='*80}")

    existing_topics = load_log_topics()
    print(f"📊 Historia: {len(existing_topics)} tematów z log.txt")
    if existing_topics:
        print(f"   Ostatnie 3: {existing_topics[-3:]}")

    print(f"\n🚀 ETAP 1: Generowanie {NUM_CONTENT_SETS} kandydatów")
    summaries_prompt = (
        f"Generate {NUM_CONTENT_SETS} different catchy headlines for a popular science YouTube Shorts video. "
        f"Each must cover a DIFFERENT topic about cosmos. "
        f"Topics must be interesting for general audience (max 15 words each). "
        f"Separate each with /// exactly. NO NUMBERS, NO HEADERS, NO OTHER TEXT."
    )

    # ETAP 1 uses call_ai — all tasks go through the unified Naga caller
    summaries_raw = call_ai(summaries_prompt, model=AI_MODELS["summaries"])
    if not summaries_raw:
        print("❌ Błąd generowania kandydatów. Ponawiam...")
        continue

    all_candidates = [s.strip() for s in re.split(r"\s*///\s*", summaries_raw.strip()) if s.strip()][:NUM_CONTENT_SETS]
    print(f"✅ Wygenerowano {len(all_candidates)} kandydatów:")
    for i, s in enumerate(all_candidates, 1):
        print(f"   {i}. {s}")

    print(f"\n🔍 ETAP 2: AI semantyczna deduplikacja")
    unique_candidates = ai_filter_unique_topics(all_candidates, existing_topics)
    print(f"   Unikalnych po filtracji: {len(unique_candidates)}/{len(all_candidates)}")

    if not unique_candidates:
        print("❌ Wszystkie tematy to duplikaty! Generuję nowe kandydatury...")
        continue

    print(f"\n🎯 ETAP 3: Wybór najlepszego tematu")
    best_topic = ai_select_best_topic(unique_candidates)

    if not best_topic:
        print("❌ Nie udało się wybrać tematu. Ponawiam...")
        continue

    print(f"\n{'='*80}")
    print(f"✅ WYBRANY TEMAT: '{best_topic}'")
    print(f"{'='*80}")

    safe_filename = sanitize_filename(best_topic)
    article_text = None
    success = True

    save_to_log(best_topic)

    # ---- ARTYKUŁ ----
    if GENERATE["articles"]:
        print(f"\n📄 [1/2] Generowanie artykułu: {best_topic}")
        article_prompt = (
            f"Write a maximally detailed, engaging popular science article in English (2000-2500 words) "
            f"about: '{best_topic}'. Accessible to general audience but scientifically accurate. "
            f"Include explanations of complex concepts, real-world examples, recent research findings, "
            f"and why this discovery matters. Structure with clear headings, engaging storytelling style "
            f"for YouTube science video. End with implications for future research."
        )
        article_text = call_ai(article_prompt, model=AI_MODELS["article"])
        if article_text:
            path = ARTICLES_DIR / f"{safe_filename}_science.txt"
            path.write_text(article_text, encoding='utf-8')
            print(f"✅ Artykuł zapisany: {path.name} ({len(article_text)} znaków)")
        else:
            print("❌ Błąd generowania artykułu")
            success = False

    # ---- OPIS YOUTUBE ----
    if GENERATE["youtube_descriptions"] and article_text:
        print(f"\n🎬 [2/2] Generowanie opisu YouTube")
        desc_prompt = (
            f"Based on the science article, create an English YouTube video description.\n"
            f"Include:\n"
            f"1. Title with #shorts (under 100 chars, first line only)\n"
            f"2. Compelling hook (2-3 lines)\n"
            f"3. Timestamps for key sections\n"
            f"4. 'Keywords' section with 15-20 SEO hashtags\n"
            f"5. 'Sources' section with links from article\n"
            f"6. Call-to-action (subscribe, like, comment)\n"
            f"7. AI-generated content disclaimer\n\n"
            f"Headline: '{best_topic}'\n\n"
            f"ARTICLE:\n{article_text[:3000]}...\n\n"
            f"Use emojis. NO META LABELS like 'Title:' — only the requested text."
        )
        desc_text = call_ai(desc_prompt, model=AI_MODELS["youtube_description"])
        if desc_text:
            path = DESCRIPTIONS_DIR / f"{safe_filename}_science.md"
            path.write_text(desc_text, encoding='utf-8')
            print(f"✅ Opis zapisany: {path.name}")
        else:
            print("❌ Błąd generowania opisu")
            success = False

    # ---- THUMBNAIL PROMPT ----
    if GENERATE["thumbnail_prompts"]:
        print(f"\n🎨 [3/3] Generowanie promptu do thumbnailki")
        thumb_prompt = (
            f"Generate a detailed English prompt for a YouTube science thumbnail (16:9) "
            f"about: '{best_topic}'. Dramatic, high-contrast, bold visuals, "
            f"space/lab elements. Include 3-5 words of big white text. "
            f"Clickbait-style but credible for science audience."
        )
        thumb_text = call_ai(thumb_prompt, model=AI_MODELS["thumbnail_prompt"])
        if thumb_text:
            path = PROMPTS_DIR / f"{safe_filename}_thumb.txt"
            path.write_text(thumb_text, encoding='utf-8')
            print(f"✅ Prompt zapisany: {path.name}")

    print(f"\n{'✅' if success else '❌'} Przetwarzanie '{best_topic}' | Sukces: {success}")

    if success:
        print("\n🎉 GENEROWANIE ZAKOŃCZONE SUKCESEM!")
        break
    else:
        print("\n⚠️ Częściowy błąd - ponawiam...")

else:
    print("\n❌ Wyczerpano próby - sprawdź klucze API i limity")

# ── KOMPRESJA ZDJĘĆ ──────────────────────────────────────────────────────────
print("\n" + "="*80)
print("🖼️ ETAP 4: Kompresja zdjęć")
print("="*80)
run_photo_compressor()

# ── PODSUMOWANIE ─────────────────────────────────────────────────────────────
if best_topic:
    print("\n" + "="*90)
    print("🎬 TREŚĆ GOTOWA!")
    print("="*90)
    print(f"📁 Pliki dla '{best_topic}':")
    print(f"   📄 Artykuł:   {ARTICLES_DIR}/")
    print(f"   📝 Opis:      {DESCRIPTIONS_DIR}/")
    print(f"   🎨 Thumbnail: {PROMPTS_DIR}/")
    print(f"   📋 Historia:  {LOG_FILE}")
    print(f"\n🚀 Uruchom ponownie po następny unikalny temat!")
