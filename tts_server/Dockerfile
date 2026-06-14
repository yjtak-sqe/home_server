FROM python:3.10-slim

# MeloTTS 빌드/오디오 라이브러리 의존성
RUN apt-get update && apt-get install -y --no-install-recommends \
        git build-essential libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# MeloTTS (한국어 포함) + 서버 의존성
RUN pip install --no-cache-dir git+https://github.com/myshell-ai/MeloTTS.git \
    && pip install --no-cache-dir fastapi "uvicorn[standard]" soundfile

# 한국어 모델 + nltk 리소스를 빌드 시 미리 받아 캐시 (첫 요청 지연 방지)
RUN python -c "from melo.api import TTS; m=TTS(language='KR', device='cpu'); \
m.tts_to_file('안녕하세요', m.hps.data.spk2id['KR'], '/tmp/warmup.wav')"

WORKDIR /app
COPY app.py /app/app.py

EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
