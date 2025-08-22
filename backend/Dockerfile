FROM python:3.11-slim

# ffmpeg for pydub mp3 conversion (pyttsx3 path)
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py ./

ENV NEONVOX_MAX_CHARS=2000     NEONVOX_DEFAULT_ENGINE=gtts     NEONVOX_ALLOW_GTTS=true

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
