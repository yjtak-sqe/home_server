# 홈 서버

Docker Compose로 구성된 홈 서버 인프라입니다.

## 서비스 목록

| 서비스 | 주소 | 역할 |
|--------|------|------|
| **Homarr** | `http://서버IP:7575` | 홈 대시보드 — 서비스 바로가기 모음 |
| **Portainer** | `http://서버IP:9000` | Docker 컨테이너 관리 |
| **Glances** | `http://서버IP:61208` | CPU / RAM / 디스크 실시간 모니터링 |
| **FileBrowser** | `http://서버IP:8080` | 웹 파일 탐색기 |
| **Vaultwarden** | `https://tak.tail9d038f.ts.net:8181` | 비밀번호 관리자 (Bitwarden 호환, HTTPS) |
| **카탈로그 교정** | `http://서버IP:8090` | 와이프 업무용 웹앱 ([상세](catalog_manager/web/README.md)) |
| **Wetty** | `https://tak.tail9d038f.ts.net:3000` | 브라우저 웹 터미널 (HTTPS) |
| **Home Assistant** | `http://서버IP:8123` | IoT 기기 통합 제어 (삼성 SmartThings 연동) |
| **Uptime Kuma** | `http://서버IP:3001` | 서비스 모니터링 + 이메일 알림 |
| **Immich** | `http://서버IP:2283` | 사진 백업 및 공유 (Google Photos 대체) |

> 서버IP: `100.70.200.35` (Tailscale: `tak.tail9d038f.ts.net`)

## 시작하기

```bash
git clone https://github.com/yjtak-sqe/home_server.git ~/home_server
cd ~/home_server
docker compose up -d
```

카탈로그 교정 앱은 이미지 빌드가 필요합니다:
```bash
docker compose up -d --build catalog-manager
```

## 서비스별 초기 설정

| 서비스 | 초기 계정 | 비고 |
|--------|-----------|------|
| Portainer | 첫 접속 시 직접 생성 | 5분 타임아웃 주의 |
| FileBrowser | `admin` / 랜덤 (로그 확인) | `docker logs filebrowser` |
| Vaultwarden | 첫 접속 시 직접 생성 | HTTPS 필수 |
| Wetty | 서버 `tak` 계정 비밀번호 | SSH 기반 |
| Home Assistant | 첫 접속 시 직접 생성 | SmartThings 통합 연동 |
| Uptime Kuma | 첫 접속 시 직접 생성 | Gmail SMTP 알림 설정 |

## HTTPS 인증서 (Tailscale)

Vaultwarden, Wetty는 Tailscale 인증서를 사용합니다. 인증서는 90일마다 갱신 필요:

```bash
sudo tailscale cert tak.tail9d038f.ts.net
sudo mv tak.tail9d038f.ts.net.* /etc/tailscale-certs/
docker compose restart vaultwarden wetty
```

## 주요 경로

| 경로 | 설명 |
|------|------|
| `docker-compose.yml` | 전체 서비스 정의 |
| `catalog_manager/` | 카탈로그 교정 웹앱 (FastAPI) |
| `/etc/tailscale-certs/` | Tailscale HTTPS 인증서 |
| `/home/tak/immich-app/immich-data` | Immich 사진 데이터 |
| `~/data` | FileBrowser 쓰기 가능 폴더 |

## 자주 쓰는 명령어

```bash
# 전체 재시작
docker compose down && docker compose up -d

# 특정 서비스 재시작
docker compose restart portainer

# 로그 확인
docker compose logs -f catalog-manager

# 이미지 최신화
docker compose pull && docker compose up -d

# 오래된 이미지 정리
docker image prune -f
```

## Claude Code로 작업하기

이 리포지토리에는 `CLAUDE.md` 가 있어 `claude` 실행 시 프로젝트 컨텍스트가 자동 로드됩니다.

```bash
cd ~/home_server
git pull
claude
```
