# PhishGuard SOC

Gmail Pub/Sub webhook 기반 피싱 메일 자동 분석 및 SOC 대시보드.  
수신 이메일을 실시간으로 분석해 피싱 여부를 판단하고, 웹 대시보드에서 결과를 확인할 수 있습니다.

## 시스템 구조

```
Gmail → Pub/Sub → PhishGuard Backend (FastAPI)
                        │
              ┌─────────┼─────────┐
           NLP 모델   URL 모델   규칙 엔진
          (BERT)    (XGBoost)
                        │
              앙상블 스코어 (0.0 ~ 1.0)
                        │
           normal / suspicious / dangerous
                        │
                 React 대시보드
```

### 앙상블 스코어 계산

```
final = 0.45 × NLP점수 + 0.45 × max(URL점수들) + 0.10 × 규칙점수
```

| 구간 | 판정 |
|------|------|
| 0.00 ~ 0.39 | normal |
| 0.40 ~ 0.69 | suspicious |
| 0.70 ~ 1.00 | dangerous |

### 디렉터리 구성

```
backend/          FastAPI 서버, 분석 파이프라인, Gmail OAuth/Webhook
frontend/         React SPA 대시보드
scripts/          모델 학습, Gmail watch 운영 스크립트
docs/             배포 가이드, 디버깅 기록
docker-compose.prod.yml  EC2 운영용 구성
```

---

## 로컬 설치 및 실행

### 사전 요구사항

- Python 3.9+
- Node.js 18+
- Google Cloud 프로젝트 (Gmail API, Pub/Sub 활성화)

### 1. 저장소 클론

```bash
git clone <repo-url>
cd phishguard
```

### 2. 백엔드 설정

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. 환경변수 설정

`backend/.env` 파일 생성:

```env
# Google OAuth 2.0 (Google Cloud Console에서 발급)
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/callback

# 감시할 Gmail 계정
GMAIL_ACCOUNT=your-email@gmail.com

# Google Cloud Pub/Sub 토픽 (projects/{project}/topics/{topic} 형식)
PUBSUB_TOPIC=projects/your-project/topics/gmail-phishguard

# Webhook 검증 토큰 (임의 문자열)
WEBHOOK_TOKEN=your-secret-token

# JWT 인증
JWT_SECRET_KEY=your-jwt-secret-key-at-least-32-chars

# 대시보드 URL
FRONTEND_URL=http://localhost:5173

# AI 모델 경로 (BERT 모델 디렉터리 사용 시)
NLP_MODEL_PATH=../models/bert
URL_MODEL_PATH=../models/url_model.pkl
```

> Google OAuth credentials는 Google Cloud Console → API 및 서비스 → 사용자 인증 정보에서 발급.  
> Gmail API와 Cloud Pub/Sub API가 활성화되어 있어야 합니다.

### 4. 모델 파일 배치

```bash
# BERT NLP 모델 (로컬 학습 또는 Hugging Face에서 fine-tuning 후 저장)
backend/models/bert/              ← 모델 디렉터리

# XGBoost URL 모델
backend/models/url_model.pkl      ← 학습된 모델 파일
```

URL 모델을 직접 학습하려면:

```bash
cd backend
python ../scripts/train_url_model.py
```

### 5. 백엔드 실행

```bash
cd backend
./.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

서버 시작 후 확인:
```bash
curl http://localhost:8000/health
# {"status":"ok"}
```

### 6. 프론트엔드 실행

```bash
cd frontend
npm install
npm run dev
# http://localhost:5173 접속
```

---

## Gmail 연동 설정

### 1. Gmail OAuth 로그인

브라우저에서 `http://localhost:8000/auth/login` 접속 → Google 계정 인증.

### 2. Gmail Watch 등록

```bash
curl -X POST http://localhost:8000/api/admin/watch/setup \
  -H "Authorization: Bearer <JWT_TOKEN>"
```

또는 대시보드 → 시스템 상태 → Watch 설정 버튼 클릭.

### 3. 시스템 상태 확인

```bash
curl http://localhost:8000/api/dashboard/system-health
```

```json
{
  "gmail_watch": { "status": "active" },
  "pubsub": { "status": "connected" },
  "nlp_model": { "status": "loaded" },
  "url_model": { "status": "loaded" }
}
```

---

## API 테스트

### 헬스체크

```bash
curl http://localhost:8000/health
```

### 대시보드 최근 이메일 조회

```bash
curl http://localhost:8000/api/dashboard/emails/recent \
  -H "Authorization: Bearer <JWT_TOKEN>"
```
```

---

## 유닛 테스트

```bash
cd backend
./.venv/bin/python -m pytest tests/ -v
```

주요 테스트 파일:

| 파일 | 검증 내용 |
|------|---------|
| `test_url_extractor.py` | URL 피처 추출 정확성, at_symbol netloc 검사 |
| `test_url_model.py` | XGBoost 모델 로드, 정상/피싱 URL 분류 |
| `test_ensemble.py` | 앙상블 가중치, 임계값 판정 |
| `test_email_parser.py` | 이메일 파싱, URL 추출 |
| `test_dashboard_api.py` | REST API 엔드포인트 |

---

## 운영 배포 (EC2)

자세한 절차는 [docs/AWS_DEPLOYMENT.md](docs/AWS_DEPLOYMENT.md) 참고.

**빠른 요약:**

```bash
# EC2 접속
ssh -i ~/.ssh/your-key.pem ec2-user@<EC2_IP>

# 서비스 상태 확인
sudo systemctl status phishguard

# 로그 확인
sudo journalctl -u phishguard -f

# 서비스 재시작
sudo systemctl restart phishguard
```

### 모델 업데이트 절차

```bash
# 1. EC2에서 새 모델 학습
python scripts/train_url_model.py

# 2. 기존 모델 백업
cp backend/models/url_model.pkl backend/models/url_model_backup_$(date +%Y%m%d).pkl

# 3. 새 모델 교체
cp backend/models/url_model_v3.pkl backend/models/url_model.pkl

# 4. 서비스 재시작
sudo systemctl restart phishguard

# 5. 헬스체크
curl http://localhost:8000/health
```

---

## 트러블슈팅

### 정상 URL이 높은 점수를 받는 경우

→ [docs/URL_MODEL_DEBUGGING.md](docs/URL_MODEL_DEBUGGING.md) 참고.  
주요 원인: 훈련 데이터 URL 형식 불일치(`is_https` 피처), `at_symbol` 피처 버그.

### Gmail Watch가 만료되는 경우

Gmail Watch는 최대 7일 유효. 서버는 23시간마다 자동 갱신하지만 수동으로도 가능:

```bash
curl -X POST http://localhost:8000/api/admin/watch/setup \
  -H "Authorization: Bearer <JWT_TOKEN>"
```

### Pub/Sub 메시지가 수신되지 않는 경우

1. Google Cloud Console → Pub/Sub → 구독 확인
2. Webhook URL이 외부에서 접근 가능한지 확인 (로컬은 ngrok 필요)
3. `WEBHOOK_TOKEN` 이 서버와 Pub/Sub 구독 설정에서 일치하는지 확인

---

## 커밋하지 않는 파일

```
.env
backend/models/*.pkl
backend/models/bert/
*.db, *.sqlite
*.csv
backend/credentials/
```

---

## 관련 문서

- [docs/AWS_DEPLOYMENT.md](docs/AWS_DEPLOYMENT.md) — EC2 배포 전체 절차
- [docs/URL_MODEL_DEBUGGING.md](docs/URL_MODEL_DEBUGGING.md) — URL 모델 오탐 디버깅 기록
