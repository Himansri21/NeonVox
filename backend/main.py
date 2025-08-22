import io
import os
import csv
import tempfile
from typing import Optional, List

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator

# --- Dependencies are optional at runtime depending on engine ---
# gTTS for online MP3
try:
    from gtts import gTTS  # type: ignore
except Exception:
    gTTS = None

# pyttsx3 for offline synth (WAV) + pydub/ffmpeg for MP3 convert
try:
    import pyttsx3  # type: ignore
except Exception:
    pyttsx3 = None

try:
    from pydub import AudioSegment  # type: ignore
except Exception:
    AudioSegment = None

app = FastAPI(title="NeonVox TTS API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

MAX_CHARS = int(os.getenv("NEONVOX_MAX_CHARS", "2000"))
DEFAULT_ENGINE = os.getenv("NEONVOX_DEFAULT_ENGINE", "gtts").lower()
ALLOW_GTTS = os.getenv("NEONVOX_ALLOW_GTTS", "true").lower() == "true"

class TTSRequest(BaseModel):
    text: str
    engine: str = DEFAULT_ENGINE  # "gtts" or "pyttsx3"
    lang: str = "en"             # gTTS only
    voice: Optional[str] = None   # pyttsx3 preference ("male", "female", or part of name)
    rate: Optional[int] = None    # pyttsx3 speaking rate
    volume: Optional[float] = None  # 0.0 - 1.0

    @field_validator("engine")
    @classmethod
    def validate_engine(cls, v: str) -> str:
        v = v.lower()
        if v not in {"gtts", "pyttsx3"}:
            raise ValueError("engine must be 'gtts' or 'pyttsx3'")
        return v

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("text is required")
        if len(v) > MAX_CHARS:
            raise ValueError(f"text exceeds limit of {MAX_CHARS} characters")
        return v


def synthesize_gtts(text: str, lang: str) -> bytes:
    if not ALLOW_GTTS:
        raise HTTPException(status_code=403, detail="gTTS is disabled by server policy")
    if gTTS is None:
        raise HTTPException(status_code=500, detail="gTTS not installed. Run: pip install gTTS")
    with tempfile.TemporaryDirectory() as td:
        mp3_path = os.path.join(td, "out.mp3")
        tts = gTTS(text, lang=lang)
        tts.save(mp3_path)
        with open(mp3_path, "rb") as f:
            return f.read()


def _pyttsx3_select_voice(engine, pref: Optional[str]):
    if not pref:
        return
    try:
        voices = engine.getProperty('voices') or []
        pref_low = pref.lower()
        for v in voices:
            name = (getattr(v, "name", "") or "").lower()
            gender = (getattr(v, "gender", "") or "").lower()
            if pref_low in name or pref_low in gender:
                engine.setProperty('voice', v.id)
                return
    except Exception:
        return


def synthesize_pyttsx3_mp3(text: str, voice: Optional[str], rate: Optional[int], volume: Optional[float]) -> bytes:
    if pyttsx3 is None:
        raise HTTPException(status_code=500, detail="pyttsx3 not installed. Run: pip install pyttsx3")
    if AudioSegment is None:
        raise HTTPException(status_code=500, detail="pydub not installed. Run: pip install pydub and install ffmpeg")

    engine = pyttsx3.init()
    if rate:
        engine.setProperty('rate', int(rate))
    if volume is not None:
        engine.setProperty('volume', float(volume))
    _pyttsx3_select_voice(engine, voice)

    with tempfile.TemporaryDirectory() as td:
        wav_path = os.path.join(td, "out.wav")
        engine.save_to_file(text, wav_path)
        engine.runAndWait()

        # Convert WAV -> MP3 via pydub/ffmpeg
        mp3_path = os.path.join(td, "out.mp3")
        try:
            audio = AudioSegment.from_wav(wav_path)
            audio.export(mp3_path, format="mp3")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"ffmpeg missing or conversion failed: {e}")

        with open(mp3_path, "rb") as f:
            return f.read()


@app.get("/health")
async def health():
    return {"ok": True}


@app.post("/api/tts")
async def tts(req: TTSRequest):
    if req.engine == "gtts":
        data = synthesize_gtts(req.text, req.lang)
        filename = "neonvox.mp3"
    else:
        data = synthesize_pyttsx3_mp3(req.text, req.voice, req.rate, req.volume)
        filename = "neonvox.mp3"

    headers = {"Content-Disposition": f"attachment; filename={filename}"}
    return StreamingResponse(io.BytesIO(data), media_type="audio/mpeg", headers=headers)


@app.post("/api/tts-csv")
async def tts_csv(
    file: UploadFile = File(..., description="CSV with columns: filename, script_text"),
    engine: str = Form(DEFAULT_ENGINE),
    lang: str = Form("en"),
    voice: Optional[str] = Form(None),
    rate: Optional[int] = Form(None),
    volume: Optional[float] = Form(None),
):
    engine = (engine or "").lower()
    if engine not in {"gtts", "pyttsx3"}:
        raise HTTPException(status_code=400, detail="engine must be 'gtts' or 'pyttsx3'")

    content = await file.read()
    try:
        text_stream = content.decode("utf-8")
    except Exception:
        raise HTTPException(status_code=400, detail="CSV must be UTF-8 encoded")

    reader = csv.DictReader(text_stream.splitlines())
    rows: List[dict] = []
    for r in reader:
        fn = (r.get("filename") or "").strip()
        txt = (r.get("script_text") or "").strip()
        if not fn or not txt:
            continue
        if len(txt) > MAX_CHARS:
            raise HTTPException(status_code=400, detail=f"Row '{fn}': text exceeds {MAX_CHARS} chars")
        rows.append({"filename": fn, "script_text": txt})

    if not rows:
        raise HTTPException(status_code=400, detail="CSV appears empty or missing required columns: filename, script_text")

    import zipfile
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for i, item in enumerate(rows, 1):
            base = os.path.splitext(item["filename"])[0]
            if engine == "gtts":
                data = synthesize_gtts(item["script_text"], lang)
            else:
                data = synthesize_pyttsx3_mp3(item["script_text"], voice, rate, volume)
            zf.writestr(f"{base}.mp3", data)

    buf.seek(0)
    headers = {"Content-Disposition": "attachment; filename=neonvox_batch.zip"}
    return StreamingResponse(buf, media_type="application/zip", headers=headers)
