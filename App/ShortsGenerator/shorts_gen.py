#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YouTube Video Generator - WERSJA 4 (GOTOWA - FULLY FUNCTIONAL)
Poziome filmy 16:9, automatyczna rotacja API, KONFIGURACJA Z config.txt
"""

import os
import re
import json
from pathlib import Path
from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import requests
from io import BytesIO
import subprocess
import sys
from datetime import datetime
import wave
import shlex
import pathlib
import traceback

# ============================================================================
# LOGOWANIE DO PLIKU I KONSOLI
# ============================================================================

LOG_FILE = Path("generator_log.txt")

def log(message: str, level: str = "INFO"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] [{level}] {message}"
    print(line)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

def log_exception(context: str, e: Exception):
    """Loguje pełny traceback wyjątku"""
    log(f"WYJĄTEK w: {context}", "ERROR")
    log(f"  Typ: {type(e).__name__}", "ERROR")
    log(f"  Treść: {repr(e)}", "ERROR")
    tb = traceback.format_exc()
    log(f"  Traceback:\n{tb}", "ERROR")
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"  Traceback:\n{tb}\n")
    except Exception:
        pass

def simple_log(message: str, level: str = "INFO"):
    log(message, level)

# ============================================================================
# ŁADOWANIE KONFIGURACJI Z PLIKU config.txt
# ============================================================================

def load_config() -> dict:
    config_path = Path(__file__).resolve().parent.parent.parent / "config.txt"
    simple_log(f"Sprawdzam config: {config_path.absolute()}")

    if not config_path.exists():
        simple_log(f"BŁĄD: Plik {config_path.absolute()} nie istnieje!", "ERROR")
        sys.exit(1)

    config = {}
    current_section = None
    line_num = 0

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("[") and line.endswith("]"):
                    current_section = line[1:-1].strip()
                    config[current_section] = {}
                    simple_log(f"Sekcja: {current_section}")
                    continue
                if "=" in line and current_section:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    if value.lower() in ["true", "false"]:
                        config[current_section][key] = value.lower() == "true"
                    elif value.isdigit():
                        config[current_section][key] = int(value)
                    elif re.match(r"^\d+\.\d+$", value):
                        config[current_section][key] = float(value)
                    elif value.startswith("[") and value.endswith("]"):
                        config[current_section][key] = json.loads(value)
                    else:
                        config[current_section][key] = value
                    simple_log(f"  {key} = {str(config[current_section][key])[:50]}...")
    except Exception as e:
        log_exception(f"parsowanie config.txt (linia ~{line_num})", e)
        sys.exit(1)

    required = ["API_KEYS", "API_MODELS", "PROMPTS"]
    for sec in required:
        if sec not in config:
            simple_log(f"BŁĄD: Brak sekcji [{sec}] w config.txt!", "ERROR")
            sys.exit(1)

    simple_log(f"✓ Konfiguracja załadowana ({len(config)} sekcji)")
    return config


CONFIG = load_config()

CONFIG["FOLDERS"]["output_folder"] = str(
    Path(__file__).resolve().parent.parent.parent / CONFIG["FOLDERS"]["output_folder"]
)
CONFIG["FOLDERS"]["input_folder"] = str(
    Path(__file__).resolve().parent.parent.parent / CONFIG["FOLDERS"]["input_folder"]
)

Path(CONFIG["FOLDERS"]["output_folder"]).mkdir(parents=True, exist_ok=True)
Path(CONFIG["FOLDERS"]["temp_folder"]).mkdir(exist_ok=True)

# ============================================================================
# FUNKCJE POMOCNICZE
# ============================================================================

def sanitize_filename(filename: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', "_", filename)

def read_article(file_path: str) -> str:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        log_exception(f"czytanie artykułu: {file_path}", e)
        return ""

def check_ffmpeg_available() -> bool:
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5)
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        log_exception("sprawdzanie FFmpeg", e)
        return False

def get_filename(template: str, article: str, index: int = 0) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return template.format(article=article, index=index, timestamp=timestamp)

def get_client_with_retry(operation_name: str = "operacja"):
    """Create an OpenAI client using NAGA_API_KEY from environment variable."""
    api_key = os.environ["NAGA_API_KEY"]
    try:
        client = OpenAI(base_url=CONFIG["API_MODELS"]["base_url"], api_key=api_key)
        log(f"Używam NAGA_API_KEY (z env) dla: {operation_name}")
        return client
    except Exception as e:
        log_exception(f"tworzenie klienta dla: {operation_name}", e)
        return None

# ============================================================================
# DEBUG: SUROWA ODPOWIEDŹ API OBRAZÓW
# ============================================================================

def debug_image_api_raw(prompt: str) -> str:
    """Zwraca surową odpowiedź z endpointu /images/generations (do logów)"""
    try:
        api_key = os.environ["NAGA_API_KEY"]
        url = CONFIG["API_MODELS"]["base_url"].rstrip("/") + "/images/generations"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": CONFIG["API_MODELS"]["model_image"],
            "prompt": prompt,
            "n": 1,
            "size": "1080x1920", #"size": "1024x1024"
            "response_format": "url",
        }
        r = requests.post(url, headers=headers, json=payload, timeout=120)
        raw = f"STATUS: {r.status_code} | BODY: {r.text[:2000]}"
        log(f"[DEBUG RAW IMAGE API] {raw}", "DEBUG")
        return raw
    except Exception as e:
        log_exception("debug_image_api_raw", e)
        return ""

# ============================================================================
# MODUŁ 1: GENEROWANIE SCENARIUSZA
# ============================================================================

def generate_scenario(article_content: str) -> str:
    pipeline = CONFIG["PIPELINE"]
    if not pipeline.get("step_generate_scenario", True):
        log("Krok generowania scenariusza wyłączony - używam oryginalnego artykułu")
        return article_content

    log("Generowanie scenariusza...")
    prompt = CONFIG["PROMPTS"]["prompt_scenario"].format(article_content=article_content)
    max_retries = CONFIG["API_KEYS"]["max_retries_per_request"]
    model_text = CONFIG["API_MODELS"]["model_text"]
    model_scenario = CONFIG["API_MODELS"]["model_scenario"]

    for attempt in range(max_retries):
        try:
            client = get_client_with_retry("generowanie scenariusza")
            if not client:
                return ""
            resp = client.chat.completions.create(
                model=model_scenario,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            )
            scenario = resp.choices[0].message.content.strip()
            log(f"✓ Scenariusz wygenerowany ({len(scenario)} znaków)")
            return scenario
        except Exception as e:
            log_exception(f"generowanie scenariusza (próba {attempt+1}/{max_retries})", e)
            if attempt == max_retries - 1:
                log("Nie udało się wygenerować scenariusza", "ERROR")
                return ""
    return ""

# ============================================================================
# MODUŁ 2: PODZIAŁ NA ZDANIA
# ============================================================================

def split_into_sentences(text: str) -> list:
    method = CONFIG["TEXT_SPLITTING"]["sentence_split_method"]
    if method == "newline":
        sentences = [line.strip() for line in text.split("\n") if line.strip()]
    elif method == "punctuation":
        sentences = re.split(r"(?<=[.!?,])\s+", text.strip())
        sentences = [s.strip() for s in sentences if s.strip()]
    elif method == "both":
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        sentences = []
        for line in lines:
            parts = re.split(r"(?<=[.!?,])\s+", line)
            sentences.extend([s.strip() for s in parts if s.strip()])
    else:
        log(f"Nieznana metoda podziału: {method}, używam 'newline'", "WARNING")
        sentences = [line.strip() for line in text.split("\n") if line.strip()]
    log(f"Tekst podzielony na {len(sentences)} zdań (metoda: {method})")
    return sentences

# ============================================================================
# MODUŁ 3: TEXT-TO-SPEECH
# ============================================================================

def generate_tts(text: str, article_name: str, sentence_index: int) -> str:
    pipeline = CONFIG["PIPELINE"]
    if not pipeline.get("step_generate_tts", True):
        log(f"Krok TTS wyłączony dla zdania {sentence_index + 1}")
        return ""

    filename = get_filename(CONFIG["FILENAMES"]["filename_audio"], article_name, sentence_index)
    output_path = Path(CONFIG["FOLDERS"]["temp_folder"]) / filename
    log(f"Generowanie TTS dla zdania {sentence_index + 1}...")

    max_retries = CONFIG["API_KEYS"]["max_retries_per_request"]

    for attempt in range(max_retries):
        try:
            client = get_client_with_retry(f"TTS zdanie {sentence_index + 1}")
            if not client:
                return ""
            resp = client.audio.speech.create(
                model=CONFIG["API_MODELS"]["model_tts"],
                voice=CONFIG["API_MODELS"]["voice"],
                input=text,
            )
            resp.stream_to_file(str(output_path))
            log(f"✓ TTS zapisany: {output_path}")
            return str(output_path)
        except Exception as e:
            log_exception(f"TTS zdanie {sentence_index+1} (próba {attempt+1}/{max_retries})", e)
            if attempt == max_retries - 1:
                log(f"Nie udało się wygenerować TTS dla zdania {sentence_index + 1}", "ERROR")
                return ""
    return ""

# ============================================================================
# MODUŁ 4: DŁUGOŚĆ AUDIO
# ============================================================================

def get_audio_duration(audio_path: str) -> float:
    try:
        probe_cmd = [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", audio_path,
        ]
        result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=5)
        if result.returncode == 0 and result.stdout.strip():
            duration = float(result.stdout.strip())
            if duration > 0:
                log(f"Długość audio: {duration:.2f}s")
                return duration
    except Exception as e:
        log_exception("get_audio_duration", e)
    default_duration = CONFIG["AUDIO"]["audio_default_duration"]
    log(f"Używam domyślnej długości: {default_duration}s")
    return default_duration

# ============================================================================
# MODUŁ 5: GENEROWANIE OBRAZU
# ============================================================================

def generate_image_prompt(sentence: str, all_sentences: list, sentence_index: int) -> str:
    context = " ".join(all_sentences[:3])
    prompt = CONFIG["PROMPTS"]["prompt_image"].format(
        context=context, sentence=sentence, sentence_index=sentence_index + 1
    )
    max_retries = CONFIG["API_KEYS"]["max_retries_per_request"]
    for attempt in range(max_retries):
        try:
            client = get_client_with_retry(f"prompt obrazu {sentence_index + 1}")
            if not client:
                return ""
            resp = client.chat.completions.create(
                model=CONFIG["API_MODELS"]["model_text"],
                messages=[{"role": "user", "content": prompt}],
                temperature=0.8,
            )
            image_prompt = resp.choices[0].message.content.strip()
            log(f"✓ Prompt obrazu wygenerowany dla zdania {sentence_index + 1}")
            return image_prompt
        except Exception as e:
            log_exception(f"prompt obrazu {sentence_index+1} (próba {attempt+1}/{max_retries})", e)
            if attempt == max_retries - 1:
                log(f"Nie udało się wygenerować promptu", "ERROR")
                return ""
    return ""


def generate_image(prompt: str, article_name: str, sentence_index: int) -> str:
    pipeline = CONFIG["PIPELINE"]
    if not pipeline.get("step_generate_images", True):
        log(f"Krok generowania obrazów wyłączony dla zdania {sentence_index + 1}")
        return ""

    filename = get_filename(CONFIG["FILENAMES"]["filename_image"], article_name, sentence_index)
    output_path = Path(CONFIG["FOLDERS"]["temp_folder"]) / filename
    log(f"Generowanie obrazu dla zdania {sentence_index + 1}...")

    video_settings = CONFIG["VIDEO_SETTINGS"]
    max_retries = CONFIG["API_KEYS"]["max_retries_per_request"]

    for attempt in range(max_retries):
        try:
            client = get_client_with_retry(f"obraz {sentence_index + 1}")
            if not client:
                return ""

            # Przed każdą próbą loguj surową odpowiedź (tylko przy pierwszej próbie)
            if attempt == 0:
                debug_image_api_raw(prompt)

            resp = client.images.generate(
                model=CONFIG["API_MODELS"]["model_image"],
                prompt=prompt,
                n=1,
                size="1080x1920", #size="1024x1024"
                response_format="url",
            )

            image_url = resp.data[0].url
            log(f"  URL obrazu: {image_url[:100]}...")
            image_response = requests.get(image_url, timeout=60)
            image_response.raise_for_status()
            image = Image.open(BytesIO(image_response.content))
            image = image.resize(
                (video_settings["video_width"], video_settings["video_height"]),
                Image.Resampling.LANCZOS,
            )
            image.save(str(output_path))
            log(f"✓ Obraz zapisany: {output_path}")
            return str(output_path)

        except Exception as e:
            log_exception(f"generowanie obrazu {sentence_index+1} (próba {attempt+1}/{max_retries})", e)
            if attempt == max_retries - 1:
                log(f"Nie udało się wygenerować obrazu dla zdania {sentence_index + 1}", "ERROR")
                return ""
    return ""

# ============================================================================
# MODUŁ 6: NAKŁADKA TEKSTOWA
# ============================================================================

def create_rounded_rectangle(size, radius, color):
    width, height = size
    img = Image.new("RGBA", size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([(0, 0), (width - 1, height - 1)], radius=radius, fill=color)
    return img

def wrap_text(text: str, font, max_width: int) -> list:
    words = text.split()
    lines = []
    current_line = []
    for word in words:
        test_line = " ".join(current_line + [word])
        try:
            bbox = font.getbbox(test_line)
            text_width = bbox[2] - bbox[0]
        except AttributeError:
            text_width = len(test_line) * 12
        if text_width <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(" ".join(current_line))
            lines.append(word)
            current_line = []
    if current_line:
        lines.append(" ".join(current_line))
    return lines

def add_text_to_image(image_path: str, text: str, article_name: str, sentence_index: int) -> str:
    overlay = CONFIG["PIPELINE"].get("step_add_text_overlay", False) and CONFIG["TEXT_OVERLAY"]["text_enabled"]
    if not overlay:
        return image_path

    filename = get_filename(CONFIG["FILENAMES"]["filename_image_text"], article_name, sentence_index)
    output_path = Path(CONFIG["FOLDERS"]["temp_folder"]) / filename
    log(f"Dodawanie tekstu do obrazu dla zdania {sentence_index + 1}...")

    try:
        image = Image.open(image_path).convert("RGBA")
        img_width, img_height = image.size
        try:
            font = ImageFont.truetype(CONFIG["TEXT_OVERLAY"]["text_font_name"], CONFIG["TEXT_OVERLAY"]["text_font_size"])
        except Exception as e:
            log_exception("ładowanie czcionki z config", e)
            try:
                font = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", CONFIG["TEXT_OVERLAY"]["text_font_size"])
            except Exception as e2:
                log_exception("ładowanie arial.ttf", e2)
                font = ImageFont.load_default()

        max_width = img_width - 100
        wrapped_lines = wrap_text(text, font, max_width)
        line_height = CONFIG["TEXT_OVERLAY"]["text_font_size"] + 12
        bg_height = (len(wrapped_lines) * line_height) + (CONFIG["TEXT_OVERLAY"]["text_background_padding"] * 2)
        bg_width = max_width + (CONFIG["TEXT_OVERLAY"]["text_background_padding"] * 2)
        bg_x = (img_width - bg_width) // 2

        if CONFIG["TEXT_OVERLAY"]["text_position"] == "top":
            bg_y = 30
        elif CONFIG["TEXT_OVERLAY"]["text_position"] == "center":
            bg_y = (img_height - bg_height) // 2
        else:
            bg_y = max(img_height - bg_height - 200, 20)

        if CONFIG["TEXT_OVERLAY"]["text_background_type"] == "glassmorphism":
            background_region = image.crop((
                max(0, bg_x), max(0, bg_y),
                min(img_width, bg_x + bg_width), min(img_height, bg_y + bg_height),
            ))
            blurred = background_region.filter(ImageFilter.GaussianBlur(radius=CONFIG["TEXT_OVERLAY"]["text_background_blur"]))
            overlay_bg = Image.new("RGBA", blurred.size, (
                *eval(CONFIG["TEXT_OVERLAY"]["text_background_color"]),
                CONFIG["TEXT_OVERLAY"]["text_background_alpha"],
            ))
            blurred_alpha = blurred.convert("RGBA")
            background = Image.alpha_composite(blurred_alpha, overlay_bg)
            mask = create_rounded_rectangle(background.size, CONFIG["TEXT_OVERLAY"]["text_background_corner_radius"], (255, 255, 255, 255))
            background.putalpha(mask.split()[3])
            image.paste(background, (int(bg_x), int(bg_y)), background)

        draw = ImageDraw.Draw(image)
        text_x = bg_x + CONFIG["TEXT_OVERLAY"]["text_background_padding"]
        text_y = bg_y + CONFIG["TEXT_OVERLAY"]["text_background_padding"]
        text_color = eval(CONFIG["TEXT_OVERLAY"]["text_color"])
        for line in wrapped_lines:
            draw.text((text_x, text_y), line, font=font, fill=(*text_color, 255))
            text_y += line_height

        image = image.convert("RGB")
        image.save(str(output_path))
        log(f"✓ Obraz z tekstem zapisany: {output_path}")
        return str(output_path)

    except Exception as e:
        log_exception(f"add_text_to_image zdanie {sentence_index+1}", e)
        return image_path

# ============================================================================
# PIPELINE GŁÓWNY
# ============================================================================

def process_article(file_path: str):
    log(f"\n{'='*70}")
    log(f"Przetwarzanie: {file_path}")
    log(f"{'='*70}")

    article_name = sanitize_filename(Path(file_path).stem)

    article_content = read_article(file_path)
    if not article_content:
        return

    scenario = generate_scenario(article_content)
    if not scenario:
        return

    sentences = split_into_sentences(scenario)
    if not sentences:
        return

    for idx, sentence in enumerate(sentences):
        log(f"\n--- Zdanie {idx + 1}/{len(sentences)}: '{sentence[:60]}...' ---")
        try:
            audio_path = generate_tts(sentence, article_name, idx)
            if not audio_path:
                continue

            duration = get_audio_duration(audio_path)

            image_prompt = generate_image_prompt(sentence, sentences, idx)
            if not image_prompt:
                continue

            image_path = generate_image(image_prompt, article_name, idx)
            if not image_path:
                continue

            final_image_path = add_text_to_image(image_path, sentence, article_name, idx)
            log(f"✓ Zdanie {idx + 1} OK (audio: {duration:.2f}s)")

        except Exception as e:
            log_exception(f"process_article zdanie {idx+1}", e)
            continue

# ============================================================================
# MAIN
# ============================================================================

def main():
    log(f"{'='*70}")
    log("YouTube Video Generator v4 - START (CONFIG z config.txt)")
    log(f"Log zapisywany do: {LOG_FILE.resolve()}")
    log(f"Format: {CONFIG['VIDEO_SETTINGS']['video_width']}x{CONFIG['VIDEO_SETTINGS']['video_height']}")
    log(f"Podział zdań: {CONFIG['TEXT_SPLITTING']['sentence_split_method']}")
    log(f"Dostępne klucze API: {len(CONFIG['API_KEYS']['api_keys'])}")
    log(f"{'='*70}")

    if not check_ffmpeg_available():
        log("⚠️ FFmpeg niedostępny! Zainstaluj FFmpeg.", "ERROR")
        return

    input_path = Path(CONFIG["FOLDERS"]["input_folder"])
    if not input_path.exists():
        log(f"Folder wejściowy '{input_path}' nie istnieje", "ERROR")
        return

    articles = list(input_path.glob("*.txt")) + list(input_path.glob("*.md"))
    if not articles:
        log("Nie znaleziono artykułów w folderze wejściowym!", "ERROR")
        return

    log(f"Znaleziono {len(articles)} artykułów\n")

    for article_path in articles:
        try:
            process_article(str(article_path))
        except Exception as e:
            log_exception(f"BŁĄD PRZY ARTYKULE {article_path}", e)

    log(f"\n{'='*70}")
    log("Generator - KONIEC - Sprawdź folder: " + CONFIG["FOLDERS"]["output_folder"])
    log(f"{'='*70}")


if __name__ == "__main__":
    main()
