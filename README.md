# NeonVox — Text → MP3

A futuristic, accessible TTS site powered by FastAPI and your original TTS script logic.

## 1) Run the API
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Or via Docker:
```bash
cd backend
docker build -t neonvox-api .
docker run -p 8000:8000 neonvox-api
```

## 2) Open the frontend
Serve `frontend/` with any static server and open `index.html`.
In dev it auto-targets `http://localhost:8000` for the API.

## Notes
- **gTTS path** produces MP3 directly.
- **pyttsx3 path** needs `ffmpeg` + `pydub` for MP3 conversion (Docker includes ffmpeg).
- CSV must contain `filename,script_text` columns (UTF‑8).

## Security & Privacy
- We do not store text; temporary files are deleted after processing.
- You can disable gTTS by setting `NEONVOX_ALLOW_GTTS=false`.
- Adjust `NEONVOX_MAX_CHARS` for limits.

## Accessibility
- Proper labels, focus outlines, sufficient contrast, keyboard‑friendly controls.

## Quick GitHub push
```bash
git init
git add .
git commit -m "NeonVox initial commit"
git branch -M main
git remote add origin <your-repo-url>
git push -u origin main
```
