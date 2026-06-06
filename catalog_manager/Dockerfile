# 카탈로그 교정 시스템 — 웹 서버 이미지
FROM python:3.12-slim

WORKDIR /app

# 의존성 먼저 설치 (레이어 캐시 활용)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사 (core/, config.py, web/ 등)
COPY . .

# 작업 산출물 저장 위치 (compose에서 볼륨 마운트)
ENV CATALOG_DATA_DIR=/data/jobs \
    PYTHONUNBUFFERED=1
RUN mkdir -p /data/jobs

EXPOSE 8000

# 컨테이너 헬스체크
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health').status==200 else 1)"

CMD ["uvicorn", "web.app:app", "--host", "0.0.0.0", "--port", "8000"]
