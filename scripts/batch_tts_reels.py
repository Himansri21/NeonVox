#!/usr/bin/env python3
"""
Batch-generate short reel voiceovers as MP3 files.
- Default engine: gTTS (online, outputs MP3 directly)
- Optional engine: pyttsx3 (offline, outputs WAV; can auto-convert to MP3 if pydub+ffmpeg are available)
"""
import argparse
import csv
import os
import sys
from pathlib import Path

def load_default_scripts():
    return [
        {
            "filename": "Day01_hook-value-cta.mp3",
            "script_text": (
                "Call centers are about to change forever… thanks to Jabras brand-new Engage AI Complete. "
                "This isnt just another AI tool. Engage AI doesnt only hear what customers say — it feels how they say it. Tone, sentiment, emotion — analyzed live, in real time."
                " Agents get instant coaching: adjust your tone, build empathy, connect like never before."
                " AI auto-summaries slash post-call paperwork."
                "Smart dashboards give supervisors live insights to boost team performance."
                "And with Jabras ClearSpeech tech, background noise? Gone."
                "The result?"
                "Happier customers"
                "Motivated agents"
                "Faster, stress-free conversations"
                "Launching globally this June, Engage AI Complete bundles tone AI, speech-to-text, generative AI, and noise cancellation into one powerful package — all for $50 per user per month"
            )
        }
    ]

def load_from_csv(csv_path):
    rows = []
    with open(csv_path, newline='', encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            filename = (r.get("filename") or "").strip()
            text = (r.get("script_text") or "").strip()
            if filename and text:
                rows.append({"filename": filename, "script_text": text})
    if not rows:
        raise SystemExit("CSV appears empty or missing required columns: filename, script_text")
    return rows

def ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)

def save_with_gtts(items, outdir: Path, lang="en"):
    try:
        from gtts import gTTS
    except Exception as e:
        print("gTTS not found. Install with: pip install gTTS", file=sys.stderr)
        raise

    for i, item in enumerate(items, 1):
        fn = item["filename"]
        if not fn.lower().endswith(".mp3"):
            fn += ".mp3"
        outpath = outdir / fn
        print(f"[{i}/{len(items)}] gTTS → {outpath.name}")
        tts = gTTS(item["script_text"], lang=lang)
        tts.save(str(outpath))

def wav_to_mp3_if_possible(wav_path: Path, mp3_path: Path):
    try:
        from pydub import AudioSegment
    except Exception:
        print(f"pydub not installed; keeping WAV only: {wav_path.name}")
        return
    audio = AudioSegment.from_wav(str(wav_path))
    audio.export(str(mp3_path), format="mp3")
    print(f"Converted WAV → MP3: {mp3_path.name}")

def save_with_pyttsx3(items, outdir: Path, voice_pref=None, rate=None, volume=None, mp3_convert=True):
    try:
        import pyttsx3
    except Exception as e:
        print("pyttsx3 not found. Install with: pip install pyttsx3", file=sys.stderr)
        raise

    engine = pyttsx3.init()
    if rate:
        engine.setProperty('rate', int(rate))
    if volume is not None:
        engine.setProperty('volume', float(volume))

    if voice_pref:
        voices = engine.getProperty('voices') or []
        selected_id = None
        pref = voice_pref.lower()
        for v in voices:
            name = (getattr(v, "name", "") or "").lower()
            gender = (getattr(v, "gender", "") or "").lower()
            if pref in name or pref in gender:
                selected_id = v.id
                break
        if selected_id:
            engine.setProperty('voice', selected_id)

    for i, item in enumerate(items, 1):
        base = Path(item["filename"]).stem
        wav_path = outdir / f"{base}.wav"
        mp3_path = outdir / f"{base}.mp3"
        print(f"[{i}/{len(items)}] pyttsx3 → {wav_path.name}")
        engine.save_to_file(item["script_text"], str(wav_path))
        engine.runAndWait()
        if mp3_convert:
            wav_to_mp3_if_possible(wav_path, mp3_path)

def parse_args():
    ap = argparse.ArgumentParser(description="Batch-generate reel voiceovers as audio files.")
    ap.add_argument("--engine", choices=["gtts", "pyttsx3"], default="gtts")
    ap.add_argument("--csv", type=str, default=None)
    ap.add_argument("--out", type=str, default="./reel_audio")
    ap.add_argument("--lang", type=str, default="en")
    ap.add_argument("--voice", type=str, default=None)
    ap.add_argument("--rate", type=int, default=None)
    ap.add_argument("--volume", type=float, default=None)
    ap.add_argument("--no-mp3-convert", action="store_true")
    return ap.parse_args()

def main():
    args = parse_args()
    outdir = Path(args.out)
    ensure_dir(outdir)

    items = load_from_csv(args.csv) if args.csv else load_default_scripts()

    if args.engine == "gtts":
        save_with_gtts(items, outdir, lang=args.lang)
        print(f"Done. MP3 files saved to: {outdir}")
    else:
        save_with_pyttsx3(
            items, outdir,
            voice_pref=args.voice,
            rate=args.rate,
            volume=args.volume,
            mp3_convert=not args.no_mp3_convert
        )
        print(f"Done. WAV files saved to: {outdir}")
        if not args.no_mp3_convert:
            print("If pydub+ffmpeg were available, MP3s were also created.")

if __name__ == "__main__":
    main()
