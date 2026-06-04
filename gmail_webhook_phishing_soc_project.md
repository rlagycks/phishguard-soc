# Gmail API Webhook 기반 피싱 메일·악성 URL 자동 분석 및 격리 시스템 기획서

## 1. 프로젝트 개요

### 프로젝트 주제명

**Gmail API Webhook과 Ensemble AI를 활용한 피싱 메일 자동 분석·격리 시스템**

### 한 줄 설명

Gmail로 인입되는 이메일을 Google Cloud Pub/Sub Webhook 이벤트로 자동 감지하고, 이메일 본문 NLP 모델과 URL 정형 특성 기반 ML 모델을 결합해 피싱 위험도를 산출한 뒤 SOC 대시보드에 기록하고 격리하는 보안 자동화 시스템이다.

### 프로젝트 방향

본 프로젝트는 단순히 사용자가 이메일이나 URL을 직접 입력해 검사하는 도구가 아니라, **메일 수신 이벤트를 트리거로 보안관제 업무를 자동화하는 서버 중심 Security Automation 프로젝트**이다.

보안관제센터에서는 피싱 의심 메일을 사람이 열람하고, 본문을 확인하고, URL을 별도 분석 도구에 넣어 판단하는 과정을 반복한다. 이 프로젝트는 해당 수작업 triage 과정을 다음과 같이 자동화한다.

```text
메일 수신
→ Gmail API Push Notification 발생
→ Pub/Sub가 FastAPI Webhook 호출
→ Gmail API로 실제 메일 조회
→ 본문·헤더·URL 추출
→ 이메일 NLP 모델 + URL ML 모델 분석
→ Ensemble Risk Score 산출
→ 자동 격리/검토 큐 등록
→ SOC Dashboard 실시간 표시
```

---

## 2. 핵심 연구 질문

### 메인 연구 질문

> 이메일의 자연어 문맥 정보와 포함된 URL의 정형적 특성을 앙상블 AI 엔진으로 융합 분석했을 때, 피싱 의심 메일을 사람의 개입 없이 얼마나 정확하고 신속하게 탐지·분류·격리할 수 있는가?

### 세부 연구 질문

| 구분 | 연구 질문 |
|---|---|
| 탐지 성능 | 이메일 본문 모델 단독, URL 모델 단독, 앙상블 모델의 성능 차이는 얼마나 나는가? |
| 자동화 성능 | 메일 수신부터 위험도 판단 및 격리까지 평균 몇 초 이내에 처리할 수 있는가? |
| 보안 운영성 | 수동 분석 대비 자동 triage가 처리 시간을 얼마나 줄일 수 있는가? |
| 설명 가능성 | 모델이 피싱으로 판단한 근거를 SOC 분석가에게 설명할 수 있는가? |
| 일반화 성능 | 학습 데이터에 없는 새로운 피싱 문구나 새로운 URL 패턴에도 탐지 성능을 유지할 수 있는가? |

---

## 3. Gmail API Webhook 기반 이벤트 파이프라인

### 3.1 왜 Gmail API Webhook인가?

기존 `imaplib` 방식은 일정 주기로 메일함을 확인하는 polling 방식이다. 구현은 쉽지만 진정한 이벤트 기반 구조는 아니다.

반면 Gmail API의 Push Notification 구조는 Gmail 메일함 변경 사항을 Google Cloud Pub/Sub로 전달하고, Pub/Sub가 서버의 Webhook endpoint를 호출하는 구조다. 따라서 메일이 도착했을 때 분석 파이프라인을 자동 실행하는 **event-driven security automation**을 설계할 수 있다.

### 3.2 전체 이벤트 흐름

```text
[1] 사용자가 Gmail 수신함으로 메일 전송
        ↓
[2] Gmail mailbox에 변경 발생
        ↓
[3] Gmail API watch 설정에 따라 Pub/Sub Topic으로 알림 발행
        ↓
[4] Pub/Sub Push Subscription이 FastAPI Webhook 호출
        ↓
[5] Webhook 서버가 payload의 emailAddress, historyId 확인
        ↓
[6] Gmail API history.list 또는 messages.get으로 실제 신규 메일 조회
        ↓
[7] Email Parser가 제목, 발신자, 본문, URL, 첨부 메타데이터 추출
        ↓
[8] AI 분석 엔진이 본문 위험도와 URL 위험도 계산
        ↓
[9] Ensemble Risk Scoring Engine이 최종 위험도 산출
        ↓
[10] 임계값에 따라 정상/의심/위험으로 분류
        ↓
[11] 위험 메일은 Quarantine label로 이동
        ↓
[12] SOC Dashboard에 탐지 내역 기록
```

### 3.3 Gmail API + Pub/Sub 구성 요소

| 구성 요소 | 역할 |
|---|---|
| Gmail API `users.watch` | 특정 Gmail mailbox의 변경 사항을 Pub/Sub Topic으로 전달하도록 설정 |
| Google Cloud Pub/Sub Topic | Gmail이 mailbox 변경 알림을 발행하는 메시지 채널 |
| Pub/Sub Push Subscription | Pub/Sub 메시지를 FastAPI Webhook URL로 HTTP POST 전송 |
| FastAPI Webhook Endpoint | Pub/Sub 알림을 수신하고 분석 파이프라인을 시작 |
| Gmail API `users.history.list` | 알림의 `historyId` 이후 실제 변경된 메일을 조회 |
| Gmail API `users.messages.get` | 신규 메일의 제목, 본문, 헤더, URL 등을 가져옴 |
| Gmail API `users.messages.modify` | 위험 메일에 Quarantine label 부여 또는 INBOX 제거 |
| Scheduler / Cron | Gmail watch 만료 전 자동 갱신 |

### 3.4 중요한 Gmail API 특성

- Gmail API Push Notification은 polling 없이 mailbox 변경을 감지하기 위한 기능이다.
- Pub/Sub Push Subscription은 공개적으로 접근 가능한 HTTPS endpoint로 메시지를 POST한다.
- Gmail `watch` 요청은 영구적이지 않으므로 주기적으로 갱신해야 한다.
- Gmail 알림 payload 자체에는 이메일 본문이 포함되지 않는다. 알림은 `emailAddress`, `historyId` 중심이므로 실제 메일 내용은 Gmail API로 다시 조회해야 한다.
- 운영 안정성을 위해 마지막으로 처리한 `historyId`를 DB에 저장해야 한다.

---

## 4. 서버 중심 시스템 아키텍처

### 4.1 전체 구조

```text
┌──────────────────────────┐
│ Gmail Mailbox            │
│ phishing-report@gmail... │
└─────────────┬────────────┘
              │ Gmail mailbox change
              ▼
┌──────────────────────────┐
│ Gmail API users.watch    │
└─────────────┬────────────┘
              │ publish
              ▼
┌──────────────────────────┐
│ Google Cloud Pub/Sub     │
│ Topic: gmail-alert-topic │
└─────────────┬────────────┘
              │ push HTTP POST
              ▼
┌──────────────────────────┐
│ FastAPI Webhook Server   │
│ /webhook/gmail           │
└─────────────┬────────────┘
              │
              ▼
┌──────────────────────────┐
│ Email Fetcher            │
│ Gmail history/messages   │
└─────────────┬────────────┘
              │
              ▼
┌──────────────────────────┐
│ Email Parser             │
│ Header / Body / URL      │
└──────┬─────────────┬─────┘
       │             │
       ▼             ▼
┌──────────────┐ ┌──────────────┐
│ NLP Model    │ │ URL ML Model │
│ BERT/RoBERTa │ │ XGBoost/RF   │
└──────┬───────┘ └──────┬───────┘
       │                │
       └──────┬─────────┘
              ▼
┌──────────────────────────┐
│ Ensemble Risk Engine     │
└─────────────┬────────────┘
              │
              ▼
┌──────────────────────────┐
│ Auto Response Module     │
│ Quarantine / Review / OK │
└─────────────┬────────────┘
              │
              ▼
┌──────────────────────────┐
│ SOC Dashboard            │
│ Logs / Alerts / Metrics  │
└──────────────────────────┘
```

### 4.2 주요 백엔드 컴포넌트

| 컴포넌트 | 설명 |
|---|---|
| Webhook Receiver | Pub/Sub의 POST 요청을 수신하고 메시지 중복 여부를 확인 |
| Gmail Client | OAuth 인증 후 Gmail API로 신규 메일 원문 조회 |
| Email Parser | MIME 구조를 파싱해 제목, 본문, URL, 첨부파일 메타데이터 추출 |
| URL Feature Extractor | URL 문자열과 도메인 정보를 정형 feature vector로 변환 |
| NLP Inference Module | 이메일 본문을 BERT/RoBERTa 모델로 분석해 피싱 확률 산출 |
| URL Inference Module | RandomForest/XGBoost/LightGBM으로 악성 URL 확률 산출 |
| Ensemble Engine | 본문 점수, URL 점수, 룰 점수를 결합해 최종 위험도 산출 |
| Action Engine | 위험도에 따라 정상 처리, 검토 큐 등록, 격리 label 적용 |
| Dashboard API | SOC Dashboard에 탐지 로그와 통계를 제공 |
| Watch Renewal Job | Gmail watch가 만료되기 전에 자동 재등록 |

---

## 5. AI 모델 설계

### 5.1 이메일 본문 분석 모델

#### 입력 데이터

- 제목
- 본문 텍스트
- 발신자 표시명
- 일부 헤더 정보
- 링크 주변 문맥

#### 탐지 대상 문맥

| 문맥 유형 | 예시 |
|---|---|
| 긴급성 | 즉시 확인, 24시간 내 처리, 계정 정지 예정 |
| 금융 유도 | 송금, 결제 오류, 환불, 세금, 청구서 |
| 계정 탈취 유도 | 비밀번호 재설정, 로그인 인증, 계정 확인 |
| 사칭 | 은행, 학교, 배송사, 클라우드, 포털 서비스 |
| 링크 클릭 유도 | 아래 링크 확인, 보안 페이지 접속 |
| 협박성 표현 | 미조치 시 차단, 서비스 중단, 법적 조치 |

#### 후보 모델

| 모델 | 난이도 | 장점 | 프로젝트 추천도 |
|---|---:|---|---:|
| TF-IDF + Logistic Regression | 하 | 빠르고 베이스라인으로 좋음 | 높음 |
| TF-IDF + SVM | 하~중 | 소량 데이터에서 성능 좋음 | 높음 |
| BERT / RoBERTa Fine-tuning | 중상 | 문맥 이해 가능, 발표 임팩트 큼 | 매우 높음 |
| KoBERT / KcBERT | 중상 | 한국어 피싱 메일 확장 가능 | 선택 |
| LLM 기반 설명 생성 | 중 | 결과 요약과 설명에 유리 | 보조 기능 추천 |

#### 추천 구성

```text
Baseline: TF-IDF + SVM
Main Model: BERT 또는 RoBERTa Fine-tuning
Optional: LLM 기반 관리자용 분석 요약 생성
```

---

### 5.2 URL 정형 특성 분석 모델

#### 입력 데이터

이메일 본문에서 추출한 모든 URL을 대상으로 feature vector를 만든다.

#### URL Feature 예시

| Feature 그룹 | 예시 |
|---|---|
| 문자열 기반 | URL 길이, 도메인 길이, path 길이, 숫자 비율 |
| 특수문자 기반 | `@`, `-`, `_`, `%`, `=`, `?`, `&` 개수 |
| 도메인 기반 | 서브도메인 개수, IP 직접 사용 여부, 의심 TLD |
| 보안 기반 | HTTPS 여부, SSL 인증서 여부 |
| 평판 기반 | 도메인 나이, WHOIS 정보, 검색 인덱스 여부 |
| 키워드 기반 | login, verify, update, secure, account, reset 포함 여부 |
| 우회 패턴 | URL shortener 여부, punycode 여부, 과도한 redirect 의심 |

#### 후보 모델

| 모델 | 장점 | 추천도 |
|---|---|---:|
| RandomForest | 구현 쉬움, 성능 안정적, feature importance 가능 | 매우 높음 |
| XGBoost | 성능 우수, tabular data에 강함 | 매우 높음 |
| LightGBM | 빠르고 대용량 데이터에 적합 | 높음 |
| Logistic Regression | 베이스라인으로 적합 | 중간 |

#### 추천 구성

```text
Baseline: Logistic Regression
Main Model: RandomForest 또는 XGBoost
Explainability: SHAP feature importance
```

---

## 6. Ensemble Risk Scoring 설계

### 6.1 단순 가중합 방식

초기 구현에서는 단순 가중합 방식이 가장 현실적이다.

```text
Final Risk Score =
0.45 × Email_Text_Risk
+ 0.45 × URL_Risk
+ 0.10 × Rule_Based_Risk
```

### 6.2 위험도 구간

| 최종 점수 | 판단 | 자동 조치 |
|---:|---|---|
| 0.00 ~ 0.39 | 정상 | 기록 후 통과 |
| 0.40 ~ 0.69 | 의심 | SOC 검토 큐 등록 |
| 0.70 ~ 1.00 | 위험 | Quarantine label 적용, INBOX 제거, 대시보드 경고 |

### 6.3 Stacking Ensemble 확장안

시간이 남으면 다음과 같은 메타 분류기를 추가할 수 있다.

```text
Email_Text_Risk
URL_Risk_Max
URL_Risk_Avg
Header_Rule_Risk
Attachment_Rule_Risk
        ↓
Meta Classifier: Logistic Regression 또는 XGBoost
        ↓
Final Risk Score
```

이 방식은 단순 가중합보다 실험적으로 더 높은 성능을 낼 수 있으며, 프로젝트의 연구성을 강화한다.

---

## 7. 자동 대응 정책

### 7.1 메일 처리 정책

| 위험도 | 정책 | Gmail 처리 방식 |
|---|---|---|
| 정상 | 별도 조치 없음 | INBOX 유지 |
| 의심 | 관리자 검토 필요 | `Needs-Review` label 부여 |
| 위험 | 자동 격리 | `Quarantine` label 부여 + INBOX label 제거 |

### 7.2 삭제가 아니라 격리해야 하는 이유

발표와 보고서에서는 “자동 삭제”보다 **자동 격리**를 강조하는 것이 좋다.

- 오탐 발생 시 복구 가능
- 사후 포렌식 분석 가능
- SOC 관점에서 감사 로그 보존 가능
- 사용자 피해 방지와 운영 안정성 균형 확보

### 7.3 안전한 프로젝트 범위

본 프로젝트는 다음 범위까지만 수행한다.

- 메일 본문과 URL의 정적 분석
- URL 문자열 및 도메인 메타데이터 분석
- 위험도 점수화
- 격리 label 적용
- 대시보드 시각화

다음 기능은 제외한다.

- 악성 URL에 실제 접속하여 행위 분석
- 첨부파일 실행 또는 동적 분석
- 피싱 페이지 생성
- 공격 절차 재현
- 우회 기법 연구

---

## 8. 데이터셋 계획

### 8.1 이메일 데이터셋

| 데이터셋 | 용도 | 비고 |
|---|---|---|
| Enron Email Dataset | 정상 업무 메일 학습 | 정상 메일 문맥 학습에 적합 |
| SpamAssassin Public Corpus | 스팸/정상 분류 | 베이스라인 실험 가능 |
| Nazario Phishing Corpus | 피싱 이메일 학습 | 피싱 본문 문맥 학습에 적합 |
| Kaggle Phishing Email Dataset | 피싱/정상 이메일 분류 | 빠른 실험에 적합 |
| 직접 제작한 테스트 메일 | 데모 및 통합 테스트 | 개인정보 없는 샘플만 사용 |

### 8.2 URL 데이터셋

| 데이터셋 | 용도 | 비고 |
|---|---|---|
| PhiUSIIL Phishing URL Dataset | 피싱/정상 URL 분류 | URL feature 기반 ML에 적합 |
| UCI Phishing Websites Dataset | 베이스라인 | 고전적 URL feature 포함 |
| PhishTank URL Feed | 최신 피싱 URL 평가 | 실시간성 강조 가능 |
| 정상 URL 샘플 | benign class 구성 | Alexa/Tranco 등 공개 정상 도메인 활용 가능 |

### 8.3 데이터 병합 전략

이메일 데이터와 URL 데이터는 출처와 라벨 체계가 다르므로 억지로 하나의 데이터셋으로 합치기보다, 다음과 같이 독립 학습 후 앙상블하는 것이 적절하다.

```text
이메일 본문 데이터셋
→ NLP 모델 학습

URL 데이터셋
→ URL ML 모델 학습

직접 제작한 통합 테스트 메일
→ 전체 파이프라인 평가
```

---

## 9. 실험 설계

### 실험 1. 이메일 본문 모델 성능 비교

| 항목 | 내용 |
|---|---|
| 입력 | 제목 + 본문 |
| 모델 | TF-IDF + SVM, BERT/RoBERTa |
| 출력 | 피싱 확률 |
| 지표 | Accuracy, Precision, Recall, F1, ROC-AUC |

### 실험 2. URL 모델 성능 비교

| 항목 | 내용 |
|---|---|
| 입력 | URL feature vector |
| 모델 | Logistic Regression, RandomForest, XGBoost, LightGBM |
| 출력 | 악성 URL 확률 |
| 지표 | Accuracy, Precision, Recall, F1, ROC-AUC |

### 실험 3. 앙상블 성능 비교

| 모델 | 목적 |
|---|---|
| 이메일 모델 단독 | 문맥 분석만 사용했을 때 성능 |
| URL 모델 단독 | URL 구조 분석만 사용했을 때 성능 |
| 단순 평균 앙상블 | 기본 융합 효과 확인 |
| 가중합 앙상블 | 최적 가중치 탐색 |
| Stacking 앙상블 | 메타 모델 성능 확인 |

### 실험 4. 자동화 처리 성능

| 지표 | 설명 |
|---|---|
| End-to-End Latency | 메일 수신 이벤트부터 판단 완료까지 걸린 시간 |
| Mean Analysis Time | AI 분석 평균 시간 |
| Quarantine Success Rate | 위험 메일 격리 성공률 |
| False Positive Rate | 정상 메일을 위험으로 잘못 격리한 비율 |
| False Negative Rate | 피싱 메일을 놓친 비율 |
| Throughput | 분당 처리 가능한 메일 수 |

### 실험 5. 대시보드 유용성 평가

| 항목 | 설명 |
|---|---|
| 탐지 로그 가시성 | 분석 내역이 시간순으로 확인 가능한가? |
| 위험도 해석성 | 왜 위험한지 모델별 근거가 표시되는가? |
| 운영 편의성 | 격리/검토/정상 상태를 쉽게 구분 가능한가? |

---

## 10. 예상 성능 목표

| 구성 | 현실적 목표 |
|---|---:|
| 이메일 본문 모델 단독 | Accuracy 95~98%, F1 0.95~0.98 |
| URL 모델 단독 | Accuracy 94~97%, F1 0.94~0.97 |
| 앙상블 모델 | Accuracy 96~99%, F1 0.96~0.99 |
| 교차 데이터셋 평가 | Accuracy 85~94% |
| 전체 자동화 처리 시간 | 메일 1건당 3~10초 이내 |
| 대시보드 반영 시간 | 분석 완료 후 1초 이내 |

주의할 점은 단일 데이터셋 내부 평가에서는 매우 높은 정확도가 나올 수 있지만, 실제 최신 피싱 메일이나 다른 출처의 데이터에서는 성능이 낮아질 수 있다는 것이다. 따라서 발표에서는 정확도뿐 아니라 **Recall, F1-score, False Negative Rate, 처리 시간**을 함께 강조해야 한다.

---

## 11. SOC Dashboard 기획

### 11.1 주요 화면

| 화면 | 기능 |
|---|---|
| 실시간 탐지 현황 | 최근 수신 메일, 분석 상태, 위험도 표시 |
| 위험 메일 목록 | 최종 위험도 높은 순으로 정렬 |
| 메일 상세 분석 | 제목, 발신자, 본문 일부, 추출 URL 표시 |
| 모델별 점수 | NLP 점수, URL 점수, 룰 점수, 최종 점수 표시 |
| 판단 근거 | 위험 키워드, 의심 URL feature, 헤더 이상 여부 표시 |
| 자동 대응 로그 | Quarantine, Needs-Review, Normal 처리 내역 |
| 통계 | 일별 탐지 수, 오탐/미탐, 평균 처리 시간 |

### 11.2 대시보드 컬럼 예시

| 수신 시각 | 발신자 | 제목 | NLP 점수 | URL 점수 | 최종 위험도 | 상태 |
|---|---|---|---:|---:|---:|---|
| 2026-05-07 10:21 | security-alert@example.com | 계정 보안 확인 요청 | 0.91 | 0.88 | 0.89 | Quarantined |
| 2026-05-07 10:23 | newsletter@example.com | 주간 뉴스레터 | 0.12 | 0.08 | 0.10 | Normal |
| 2026-05-07 10:25 | support@example.net | 결제 정보 확인 필요 | 0.73 | 0.52 | 0.63 | Needs Review |

---

## 12. 기술 스택

### 12.1 계획 → 실제 사용 기술

| 영역 | 계획 | **실제 구현** |
|---|---|---|
| Mail Event Trigger | Gmail API Push Notification, Pub/Sub | ✅ Gmail API + Google Cloud Pub/Sub |
| Backend | FastAPI, Python | ✅ FastAPI 0.111, Python 3.13, Uvicorn |
| AI/ML | scikit-learn, XGBoost, Transformers | ✅ TF-IDF+SVM (baseline), XGBoost (URL), BERT fine-tuned (NLP main) |
| Database | SQLite for demo, PostgreSQL for 확장 | ✅ **PostgreSQL 16** (Docker Compose), SQLite fallback 지원 |
| Dashboard | Streamlit 또는 React | ✅ Streamlit 1.33 + Plotly |
| Scheduler | APScheduler | ✅ APScheduler (watch 23h 자동 갱신) |
| Cloud | Cloud Run 또는 local + ngrok | ✅ local + ngrok (데모), Docker Compose (DB) |
| Explainability | SHAP, feature importance | ✅ SHAP (XGBoost), NLP 상위 키워드 |
| Auth | — (미계획) | ✅ **Google OAuth 2.0 + JWT** (Access 15분 + Refresh 7일) |
| Logging | Python logging | ✅ structlog 포맷, JSON 로그 |

### 12.2 추가 구현 요소 (계획 외)

| 기술 | 설명 |
|---|---|
| JWT (python-jose) | 대시보드 사용자 인증 — Access/Refresh Token 발급 |
| streamlit-cookies-controller | 브라우저 쿠키로 JWT 세션 영속화 |
| Docker Compose | PostgreSQL 컨테이너 오케스트레이션 |
| psycopg2-binary | PostgreSQL Python 드라이버 |

---

## 13. 구현 일정 및 진행 현황

| 주차 | 작업 | 상태 |
|---|---|---|
| 1주차 | 요구사항 정의, 시스템 아키텍처 설계, 데이터셋 확보 | ✅ 완료 |
| 2주차 | 이메일 데이터 전처리, URL 데이터 전처리 | ✅ 완료 |
| 3주차 | URL feature extractor 구현 (16 feature), XGBoost/RF 학습 스크립트 | ✅ 완료 |
| 4주차 | TF-IDF + SVM baseline, BERT 추론 인터페이스 통합 | ✅ 완료 |
| 5주차 | BERT fine-tuning (팀원 담당, 모델 파일 공유) | ✅ 완료 |
| 6주차 | Ensemble Risk Engine (가중합 + 룰 기반) | ✅ 완료 |
| 7주차 | Gmail API + Pub/Sub Webhook 파이프라인, OAuth 인증 흐름 | ✅ 완료 |
| 8주차 | Gmail message fetch, MIME 파서, URL 추출기 | ✅ 완료 |
| 9주차 | 자동 격리 label, Needs-Review label 처리 | ✅ 완료 |
| 10주차 | SOC Dashboard (Streamlit), JWT 인증 가드, PostgreSQL 전환 | ✅ 완료 |
| 11주차 | URL 모델 학습 실행, NLP 모델 배포, GCP 인프라 설정 | 🔄 진행중 |
| 12주차 | End-to-End 통합 테스트, 성능 평가, 발표 자료 완성 | ⏳ 예정 |

---

## 14. 발표 데모 시나리오

### 데모 목표

메일이 들어오는 순간 자동으로 탐지 파이프라인이 실행되고, 위험 메일이 격리되는 과정을 시각적으로 보여준다.

### 데모 흐름

```text
[사전 준비]
0. FastAPI 서버 + Streamlit 대시보드 실행
   ngrok으로 로컬 서버 외부 공개 (Pub/Sub push 수신용)

[라이브 데모]
1. 발표자가 브라우저에서 SOC Dashboard 접속
2. "Google로 로그인" 클릭 → Google OAuth 동의 화면
3. 로그인 완료 → Gmail watch 자동 등록 + 대시보드 이동
   (JWT Access Token 발급, 브라우저 쿠키에 저장)

4. 발표자가 테스트 피싱 메일을 모니터링 중인 Gmail 계정으로 전송
5. Gmail API watch 이벤트 발생 → Pub/Sub → FastAPI Webhook 호출
6. 서버가 Gmail API로 신규 메일 원문 조회 (MIME 파싱)
7. 본문·발신자·헤더·URL 자동 추출

8. NLP 모델(TF-IDF+SVM 또는 BERT)이 본문 위험도 계산
9. URL 모델(XGBoost)이 악성 URL 위험도 계산
10. Ensemble Engine이 최종 점수 산출
    Final Score = 0.45 × NLP + 0.45 × URL + 0.10 × Rule

11. 위험도 ≥ 0.70 → Quarantine label 적용 + INBOX 제거
12. SOC Dashboard에 🔴 위험 카드 실시간 표시
    (NLP 점수 / URL 점수 / 판단 근거 / 처리 시간 표시)
```

### 발표에서 강조할 메시지

- 기존에는 사람이 피싱 메일을 열람하고 링크를 복사해 분석해야 했다.
- 본 시스템은 메일 수신 이벤트를 트리거로 자동 분석을 시작한다.
- 본문 문맥과 URL 구조를 동시에 분석하므로 단일 모델보다 견고하다.
- 위험도 기반 자동 격리를 통해 SOC triage 시간을 단축할 수 있다.
- 대시보드와 설명 기능을 통해 분석가가 판단 근거를 확인할 수 있다.

---

## 15. 리스크 및 대응 방안

| 리스크 | 설명 | 대응 방안 |
|---|---|---|
| Gmail watch 만료 | watch는 주기적 갱신이 필요 | Scheduler로 매일 watch 재등록 |
| Pub/Sub 중복 메시지 | 동일 이벤트가 여러 번 전달될 수 있음 | messageId/historyId 기반 중복 제거 |
| Gmail payload에 본문 없음 | 알림은 변경 ID 중심 | Gmail API messages.get으로 실제 메일 조회 |
| 오탐으로 정상 메일 격리 | 정상 업무 메일 차단 위험 | 자동 삭제 금지, Quarantine label만 적용 |
| 개인정보 이슈 | 실제 메일 본문 분석은 민감 | 테스트 계정, 익명화 데이터, 최소 권한 사용 |
| URL 접속 위험 | 악성 URL 직접 방문은 위험 | URL 문자열·도메인 메타데이터 중심 분석 |
| 모델 과적합 | 데이터셋 내부 성능만 높을 수 있음 | 교차 데이터셋 평가, 직접 제작 샘플 테스트 |
| OAuth 설정 복잡도 | Gmail API 인증과 GCP 설정 필요 | 데모 계정 1개로 제한, 설정 문서화 |

---

## 16. 안전한 범위 설정

본 프로젝트는 방어적 보안 자동화 프로젝트이며, 다음 원칙을 따른다.

1. 악성 URL에 실제 접속하지 않는다.
2. 첨부파일을 실행하지 않는다.
3. 피싱 페이지 생성이나 공격 절차 재현을 하지 않는다.
4. 실제 사용자 메일이 아닌 테스트 계정과 공개 데이터셋을 사용한다.
5. 자동 삭제 대신 격리 label을 사용한다.
6. 모든 분석 결과는 SOC Dashboard에 기록하여 추적 가능하게 한다.

---

## 17. 최종 정리

이 프로젝트는 기존 피싱 탐지 연구를 단순 모델 성능 비교에서 끝내지 않고, 실제 보안관제 업무 흐름에 맞춰 **메일 수신 이벤트 기반 자동화 파이프라인**으로 확장한다는 점에서 차별성이 있다.

최종 프로젝트 방향은 다음과 같이 정리할 수 있다.

> Gmail API Push Notification과 Google Cloud Pub/Sub를 이용해 신규 이메일 수신을 Webhook 이벤트로 감지하고, FastAPI 기반 분석 서버가 이메일 본문과 URL을 자동 추출한다. 이후 BERT/RoBERTa 기반 NLP 모델과 XGBoost/RandomForest 기반 URL 탐지 모델이 각각 위험도를 계산하며, Ensemble Risk Engine이 최종 피싱 위험도를 산출한다. 위험도가 높은 메일은 Gmail Quarantine label로 자동 격리되고, 전체 분석 과정은 SOC Dashboard에 실시간으로 시각화된다.

이 주제는 다음 장점을 가진다.

- 보안관제 자동화 관점이 명확하다.
- AI 모델 두 종류를 앙상블하므로 AI 요소가 분명하다.
- Gmail API, Pub/Sub, FastAPI, Dashboard를 활용해 실제 시스템처럼 구현 가능하다.
- 발표 데모가 강력하다.
- 공격 구현 없이 방어적 탐지·격리 중심으로 안전하게 수행할 수 있다.

---

---

## 18. 구현 현황 및 파일 구조

### 18.1 전체 디렉터리 구조

```
프로젝트 루트/
├── docker-compose.yml          # PostgreSQL 16 컨테이너
├── backend/
│   ├── .env                    # 환경변수 (비공개)
│   ├── .env.example            # 환경변수 템플릿
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py             # FastAPI 앱 + APScheduler watch 갱신
│   │   ├── config.py           # pydantic-settings 기반 설정
│   │   ├── database.py         # SQLAlchemy (PostgreSQL / SQLite)
│   │   ├── models/
│   │   │   ├── orm.py          # EmailAnalysis, WatchStatus, ProcessedMessage
│   │   │   └── schemas.py      # Pydantic response models
│   │   ├── routers/
│   │   │   ├── webhook.py      # POST /webhook/gmail (Pub/Sub 수신)
│   │   │   ├── dashboard.py    # GET /api/dashboard/* (SOC API)
│   │   │   └── admin.py        # OAuth 흐름, JWT 발급, watch 관리
│   │   └── services/
│   │       ├── auth.py         # JWT 생성/검증 (python-jose)
│   │       ├── gmail_client.py # Gmail API OAuth + 메일 조회/라벨
│   │       ├── email_parser.py # MIME 파싱, URL 추출
│   │       ├── url_extractor.py# 16-feature URL 벡터화
│   │       ├── nlp_model.py    # BERT / TF-IDF / rule-based 추론
│   │       ├── url_model.py    # XGBoost / heuristic 추론
│   │       ├── infer.py        # PhishingClassifier (BERT + TF-IDF 통합)
│   │       ├── ensemble.py     # 가중합 Risk Scoring Engine
│   │       └── action_engine.py# Gmail 라벨 액션 실행
│   ├── models/                 # 학습된 모델 저장 위치
│   │   ├── nlp/model.pkl       # TF-IDF+SVM (학습 후 생성)
│   │   ├── bert/               # BERT fine-tuned (팀원 제공)
│   │   └── url_model.pkl       # XGBoost (학습 후 생성)
│   └── tests/
│       ├── test_auth.py        # JWT 단위 테스트 12개
│       ├── test_nlp_model.py
│       ├── test_url_model.py
│       ├── test_url_extractor.py
│       ├── test_email_parser.py
│       ├── test_ensemble.py
│       ├── test_action_engine.py
│       └── test_dashboard_api.py
├── dashboard/
│   ├── auth_guard.py           # JWT 쿠키 인증 가드
│   └── soc_dashboard.py        # Streamlit SOC UI
├── scripts/
│   ├── train_url_model.py      # XGBoost URL 모델 학습
│   ├── train_nlp_model.py      # TF-IDF+SVM NLP baseline 학습
│   ├── demo_pipeline.py        # 오프라인 데모 파이프라인
│   ├── setup_watch.py          # Gmail watch 초기 설정
│   └── renew_watch.py          # Gmail watch 수동 갱신
└── 데이터셋 분석/
    └── ...
        ├── NLP_MASTER_DATA.csv # 이메일 학습 데이터
        └── URL_MASTER_DATA.csv # URL 학습 데이터 (886,986행)
```

### 18.2 인증 흐름 (구현 완료)

```text
사용자 → Streamlit (8501) 접속
    → JWT 없음 → "Google로 로그인" 버튼
    → FastAPI /auth/login → Google OAuth 동의
    → /auth/callback:
        ① Gmail 토큰 저장 (credentials/token.json)
        ② Gmail watch 자동 등록 (Pub/Sub 연결)
        ③ 로그인 이메일 조회 (getProfile)
        ④ JWT Access (15분) + Refresh (7일) 발급
        ⑤ Streamlit으로 리다이렉트 (?access_token=...&refresh_token=...)
    → Streamlit: 쿠키 저장 → 대시보드 표시
    → Access 만료 시 /auth/refresh 자동 호출 → 재발급
```

### 18.3 실행 방법

```bash
# 1. PostgreSQL 시작
docker-compose up -d db

# 2. 패키지 설치
cd backend && pip install -r requirements.txt

# 3. .env 설정 (GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, PUBSUB_TOPIC 필수)
cp .env.example .env && vi .env

# 4. URL 모델 학습 (최초 1회)
python ../scripts/train_url_model.py \
  --data "../데이터셋 분석/.../URL_MASTER_DATA.csv" \
  --output models/url_model.pkl

# 5. NLP 모델 배치 (팀원 제공 파일 → models/nlp/ 또는 models/bert/)

# 6. 백엔드 실행
uvicorn app.main:app --reload --port 8000

# 7. 대시보드 실행
cd ../dashboard && streamlit run soc_dashboard.py

# 8. (데모) ngrok으로 외부 공개
ngrok http 8000
# → GCP Pub/Sub Push Subscription URL을 ngrok URL로 설정
```

### 18.4 구현 완료 체크리스트

| 항목 | 상태 |
|---|---|
| FastAPI 서버 + 라우터 전체 | ✅ |
| Gmail OAuth 인증 흐름 | ✅ |
| Pub/Sub Webhook 수신 + 중복 제거 | ✅ |
| MIME 이메일 파서 | ✅ |
| URL 16-feature 추출기 | ✅ |
| NLP 모델 (TF-IDF baseline + BERT) | ✅ |
| URL 모델 (XGBoost + heuristic fallback) | ✅ |
| Ensemble Risk Engine (가중합) | ✅ |
| Gmail 자동 격리 라벨 처리 | ✅ |
| SOC Dashboard UI | ✅ |
| JWT 인증 + 쿠키 세션 | ✅ |
| PostgreSQL + Docker Compose | ✅ |
| watch 23시간 자동 갱신 | ✅ |
| 단위 테스트 (8개 파일) | ✅ |
| URL 모델 학습 실행 | 🔄 진행중 |
| NLP 모델 파일 배치 | ⏳ 예정 |
| GCP Pub/Sub 인프라 설정 | ⏳ 예정 |
| ngrok + E2E 통합 테스트 | ⏳ 예정 |

---

## 참고 자료

- Google Developers, Gmail API Push Notifications Guide.
- Google Developers, Gmail API `users.watch` Reference.
- Google Cloud, Pub/Sub Push Subscriptions Documentation.
- Yi et al., *Phishing URL Detection and Interpretability With Machine Learning: A Cross-Dataset Approach*, Security and Privacy, 2026.
- Dandotiya et al., *Real time identification of phishing attacks through machine learning enhanced browser extensions*, Scientific Reports, 2026.
- Al-Subaiey et al., *Novel Interpretable and Robust Web-based AI Platform for Phishing Email Detection*, arXiv, 2024.
