#!/usr/bin/env python3
"""
gen_voice_multilingual.py — Universal Multi-Language Speech Engine.

Supports 80+ languages and 400+ neural voices via Edge-TTS (100% free)
and local Kokoro ONNX neural speech.
Generates word-level subtitle timestamps automatically.
"""
import argparse
import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent

# Popular curated voices mapping
CURATED_VOICES = {
    # English
    "en-US-JennyNeural": {"lang": "English (US)", "gender": "Female", "name": "Jenny (Natural Friendly)"},
    "en-US-GuyNeural": {"lang": "English (US)", "gender": "Male", "name": "Guy (Casual Male)"},
    "en-US-AriaNeural": {"lang": "English (US)", "gender": "Female", "name": "Aria (Expressive Dynamic)"},
    "en-US-ChristopherNeural": {"lang": "English (US)", "gender": "Male", "name": "Christopher (Authoritative)"},
    "en-GB-SoniaNeural": {"lang": "English (UK)", "gender": "Female", "name": "Sonia (British Female)"},
    "en-GB-RyanNeural": {"lang": "English (UK)", "gender": "Male", "name": "Ryan (British Male)"},
    "en-IN-NeerjaNeural": {"lang": "English (India)", "gender": "Female", "name": "Neerja (Indian English)"},
    # Hindi & Indian Languages
    "hi-IN-SwaraNeural": {"lang": "Hindi (India)", "gender": "Female", "name": "Swara (Hindi Female)"},
    "hi-IN-MadhurNeural": {"lang": "Hindi (India)", "gender": "Male", "name": "Madhur (Hindi Male)"},
    "ta-IN-PallaviNeural": {"lang": "Tamil (India)", "gender": "Female", "name": "Pallavi (Tamil)"},
    "te-IN-ShrutiNeural": {"lang": "Telugu (India)", "gender": "Female", "name": "Shruti (Telugu)"},
    # Spanish
    "es-ES-ElviraNeural": {"lang": "Spanish (Spain)", "gender": "Female", "name": "Elvira (Castilian)"},
    "es-ES-AlvaroNeural": {"lang": "Spanish (Spain)", "gender": "Male", "name": "Alvaro (Castilian Male)"},
    "es-MX-DaliaNeural": {"lang": "Spanish (Mexico)", "gender": "Female", "name": "Dalia (Latin America)"},
    # French
    "fr-FR-DeniseNeural": {"lang": "French (France)", "gender": "Female", "name": "Denise (French Female)"},
    "fr-FR-HenriNeural": {"lang": "French (France)", "gender": "Male", "name": "Henri (French Male)"},
    # German
    "de-DE-KatjaNeural": {"lang": "German (Germany)", "gender": "Female", "name": "Katja (German Female)"},
    "de-DE-ConradNeural": {"lang": "German (Germany)", "gender": "Male", "name": "Conrad (German Male)"},
    # Japanese
    "ja-JP-NanamiNeural": {"lang": "Japanese (Japan)", "gender": "Female", "name": "Nanami (Japanese Female)"},
    "ja-JP-KeitaNeural": {"lang": "Japanese (Japan)", "gender": "Male", "name": "Keita (Japanese Male)"},
    # Portuguese
    "pt-BR-FranciscaNeural": {"lang": "Portuguese (Brazil)", "gender": "Female", "name": "Francisca (Brazilian)"},
    "pt-BR-AntonioNeural": {"lang": "Portuguese (Brazil)", "gender": "Male", "name": "Antonio (Brazilian Male)"},
    # Italian
    "it-IT-ElsaNeural": {"lang": "Italian (Italy)", "gender": "Female", "name": "Elsa (Italian Female)"},
    # Korean
    "ko-KR-SunHiNeural": {"lang": "Korean (Korea)", "gender": "Female", "name": "SunHi (Korean Female)"},
    # Arabic
    "ar-SA-ZariyahNeural": {"lang": "Arabic (Saudi)", "gender": "Female", "name": "Zariyah (Arabic Female)"},
    "ar-SA-HamedNeural": {"lang": "Arabic (Saudi)", "gender": "Male", "name": "Hamed (Arabic Male)"},
    # Chinese
    "zh-CN-XiaoxiaoNeural": {"lang": "Chinese (Mandarin)", "gender": "Female", "name": "Xiaoxiao (Mandarin Female)"},
    "zh-CN-YunxiNeural": {"lang": "Chinese (Mandarin)", "gender": "Male", "name": "Yunxi (Mandarin Male)"},
}

def words_to_vo_beats(words, chunk_size=5):
    """Groups word timings into punchy subtitle chunks for video captions."""
    if not words:
        return []
    beats = []
    current_chunk = []
    for w in words:
        current_chunk.append(w)
        word_text = w.get("word", "")
        # Break on punctuation or after chunk_size words
        if len(current_chunk) >= chunk_size or (word_text and word_text[-1] in ".?!,:;"):
            start = current_chunk[0]["start"]
            end = current_chunk[-1]["end"]
            text = " ".join(item["word"] for item in current_chunk)
            beats.append({"text": text, "start": round(start, 2), "end": round(end, 2)})
            current_chunk = []
    if current_chunk:
        start = current_chunk[0]["start"]
        end = current_chunk[-1]["end"]
        text = " ".join(item["word"] for item in current_chunk)
        beats.append({"text": text, "start": round(start, 2), "end": round(end, 2)})
    return beats

async def generate_edge_tts(text, voice, out_audio_path, out_timings_path=None, speed=1.0):
    import edge_tts

    rate_str = f"+{int((speed - 1.0) * 100)}%" if speed >= 1.0 else f"{int((speed - 1.0) * 100)}%"
    communicate = edge_tts.Communicate(text, voice, rate=rate_str)
    
    words = []
    sentences = []
    out_audio_path.parent.mkdir(parents=True, exist_ok=True)
    is_wav = out_audio_path.suffix.lower() == ".wav"
    raw_mp3_path = out_audio_path.with_suffix(".tmp.mp3") if is_wav else out_audio_path
    
    with open(raw_mp3_path, "wb") as f_out:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f_out.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                words.append({
                    "word": chunk.get("text", ""),
                    "start": chunk["offset"] / 10_000_000,
                    "duration": chunk["duration"] / 10_000_000,
                    "end": (chunk["offset"] + chunk["duration"]) / 10_000_000
                })
            elif chunk["type"] == "SentenceBoundary":
                sentences.append({
                    "text": chunk.get("text", ""),
                    "start": chunk["offset"] / 10_000_000,
                    "duration": chunk["duration"] / 10_000_000,
                    "end": (chunk["offset"] + chunk["duration"]) / 10_000_000
                })

    # If WordBoundary wasn't emitted by the engine, interpolate words from SentenceBoundary
    if not words and sentences:
        for s in sentences:
            s_text = s["text"].strip()
            s_words = s_text.split()
            if s_words:
                w_dur = s["duration"] / len(s_words)
                for i, w in enumerate(s_words):
                    w_start = s["start"] + i * w_dur
                    w_end = w_start + w_dur
                    words.append({
                        "word": w,
                        "start": round(w_start, 3),
                        "duration": round(w_dur, 3),
                        "end": round(w_end, 3)
                    })
                
    if is_wav:
        # Convert MP3 to standard 24kHz 16-bit mono PCM WAV via FFmpeg
        cmd_conv = [
            "ffmpeg", "-y",
            "-i", str(raw_mp3_path),
            "-ar", "24000",
            "-ac", "1",
            str(out_audio_path)
        ]
        res = subprocess.run(cmd_conv, capture_output=True, text=True)
        if raw_mp3_path.exists():
            try:
                raw_mp3_path.unlink()
            except Exception:
                pass
        if res.returncode != 0:
            print(f"[FFmpeg WAV conversion error] {res.stderr}")
            return False

    if out_timings_path and words:
        with open(out_timings_path, "w", encoding="utf-8") as f_json:
            json.dump(words, f_json, indent=2, ensure_ascii=False)
            
    print(f"✓ Multi-language voice saved: {out_audio_path}")
    print(f"✓ Word timestamps captured: {len(words)} words")
    return True

def get_curated_voices():
    return CURATED_VOICES

def main():
    parser = argparse.ArgumentParser(description="Multi-Language Neural Voice Generator")
    parser.add_argument("--text", required=True, help="Text to speak")
    parser.add_argument("--voice", default="en-US-JennyNeural", help="Edge-TTS voice name")
    parser.add_argument("--out", default="output/voice.mp3", help="Output audio file path")
    parser.add_argument("--timings", default="output/timings.json", help="Output timings file path")
    parser.add_argument("--speed", type=float, default=1.0, help="Speech rate multiplier")
    parser.add_argument("--list-voices", action="store_true", help="List curated voices")
    args = parser.parse_args()

    if args.list_voices:
        print(json.dumps(CURATED_VOICES, indent=2))
        return

    out_audio = Path(args.out).resolve()
    out_timings = Path(args.timings).resolve() if args.timings else None
    
    asyncio.run(generate_edge_tts(args.text, args.voice, out_audio, out_timings, args.speed))

if __name__ == "__main__":
    main()
