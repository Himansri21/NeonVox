# NeonVox API

## Local dev
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

## Docker
```bash
docker build -t neonvox-api ./
docker run -p 8000:8000 --name neonvox neonvox-api
```

## Endpoints
- POST /api/tts — JSON: {text, engine, lang, voice, rate, volume} → MP3
- POST /api/tts-csv — multipart: file=CSV (+engine/lang/voice/rate/volume) → ZIP of MP3s

> If using `pyttsx3`, ensure ffmpeg is present (Dockerfile already includes it).
