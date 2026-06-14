"""한국어 TTS 서버 (MeloTTS 래퍼).

게임(hangul_car)에서 POST /tts {"text": "..."} 로 호출하면 WAV 오디오를 반환한다.
MeloTTS 한국어 모델은 컨테이너 시작 시 한 번 로드된다.
"""
import io

import soundfile as sf
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from melo.api import TTS
from pydantic import BaseModel

app = FastAPI(title="Korean TTS (MeloTTS)")

# 게임이 다른 포트에서 호출하므로 CORS 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 모델 1회 로드 (CPU)
_model = TTS(language="KR", device="cpu")
_speaker_id = _model.hps.data.spk2id["KR"]
_sr = _model.hps.data.sampling_rate


class TTSRequest(BaseModel):
    text: str
    speed: float = 1.0


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/tts")
def tts(req: TTSRequest):
    audio = _model.tts_to_file(req.text, _speaker_id, None, speed=req.speed)
    buf = io.BytesIO()
    sf.write(buf, audio, _sr, format="WAV")
    buf.seek(0)
    return Response(content=buf.read(), media_type="audio/wav")
