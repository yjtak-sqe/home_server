# 홈 서버 대시보드

Docker Compose로 구성된 홈 서버 컨트롤 패널입니다.

## 포함된 서비스

| 서비스 | 주소 | 역할 |
|--------|------|------|
| **Homarr** | `http://서버IP:7575` | 홈 대시보드 — 서비스 바로가기 모음 |
| **Portainer** | `http://서버IP:9000` | Docker 컨테이너 관리 |
| **Glances** | `http://서버IP:61208` | CPU / RAM / 디스크 실시간 모니터링 |
| **FileBrowser** | `http://서버IP:8080` | 웹 파일 탐색기 |

## 시작하기

### 1. 이 리포지토리를 서버에 클론

```bash
git clone https://github.com/yjtak-sqe/home_server.git ~/home_server
cd ~/home_server
```

### 2. 컨테이너 전체 시작

```bash
docker compose up -d
```

### 3. 첫 설정

- **Portainer**: 처음 접속 시 관리자 계정을 직접 만들어야 합니다.
- **FileBrowser**: 초기 계정은 `admin` / `admin` — **첫 로그인 후 즉시 비밀번호 변경하세요.**
- **Homarr**: 첫 접속 후 UI에서 각 서비스 링크(Portainer, Glances 등)를 추가하면 됩니다.

## 자주 쓰는 명령어

```bash
# 전체 중지
docker compose down

# 특정 서비스만 재시작
docker compose restart portainer

# 로그 확인
docker compose logs -f homarr

# 이미지 최신화 후 재시작
docker compose pull && docker compose up -d
```

## FileBrowser 경로 설명

| 경로 | 서버 경로 | 쓰기 가능 |
|------|-----------|-----------|
| `/srv/host` | 서버 전체 (`/`) | ❌ 읽기 전용 |
| `/srv/data` | `~/data` | ✅ 가능 |

쓰기 가능한 폴더를 추가하려면 `docker-compose.yml`의 `filebrowser` volumes에 추가하면 됩니다.
