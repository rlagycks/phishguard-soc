# PhishGuard SOC

Gmail Pub/Sub webhook 기반 피싱 메일 자동 분석 및 SOC 대시보드입니다.

## 구성

- `backend/`: FastAPI API, Gmail OAuth/Webhook, 분석 파이프라인, dashboard API
- `frontend/`: React SPA 대시보드
- `scripts/`: 모델 학습 및 Gmail watch 운영 스크립트
- `docker-compose.prod.yml`: EC2 운영용 app + Postgres + Caddy 구성
- `Caddyfile`: HTTPS reverse proxy 구성

## 배포 방식

운영 배포는 GHCR 이미지와 EC2 로컬 모델 볼륨을 분리합니다.

- GHCR 이미지: 애플리케이션 코드, React build, Python dependencies
- EC2 직접 업로드: `models/`, `.env`, Postgres volume, Caddy 인증서 데이터

## 로컬 실행

Backend:

```bash
cd backend
./.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

## 검증

```bash
cd frontend
npm run build

cd ../backend
./.venv/bin/python -m pytest tests/test_dashboard_api.py
```

## 절대 커밋하지 않는 파일

- `.env`
- `backend/models/`
- `models/`
- `*.pkl`, `*.bin`, `*.safetensors`
- `*.db`, `*.sqlite`
- `*.csv`
- Google credentials / token files

자세한 AWS 배포 절차는 [docs/AWS_DEPLOYMENT.md](docs/AWS_DEPLOYMENT.md)를 참고하세요.
