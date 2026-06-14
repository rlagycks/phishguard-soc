# URL 피싱 모델 오탐 디버깅 기록

**날짜:** 2026-06-13  
**대상:** XGBoost URL 피싱 탐지 모델 (`url_model.pkl`)  
**결과:** v3 모델 배포로 문제 해결

---

## 1. 발단 — 문제 발견

Anthropic 팀으로부터 개인정보 처리방침 업데이트 이메일 수신.  
PhishGuard가 해당 이메일을 **suspicious (0.47)** 으로 분류.

```
발신: Anthropic Team <notice@email.anthropic.com>
제목: 개인정보 처리방침을 업데이트하고 있습니다
최종 스코어: 0.465 → suspicious (임계값: 0.40)
```

URL 분석 결과를 조회하니 정상적인 공식 URL들이 전부 `1.00` 을 반환하고 있었다.

| URL | 점수 |
|-----|------|
| `https://www.anthropic.com/` | **1.00** |
| `https://anthropic.com/privacy` | **1.00** |
| `https://www.anthropic.com/?#footerLogo` | **1.00** |
| `https://www.youtube.com/@anthropic-ai` | **0.98** |
| `https://privacy.anthropic.com` | 0.01 |

---

## 2. 분석 과정

### 2-1. 앙상블 구조 파악

`ensemble.py` 를 분석해 최종 스코어 계산 방식 확인:

```
final = 0.45 × nlp_score + 0.45 × max(url_scores) + 0.10 × rule_score
```

- NLP(BERT): 정상 이메일 → ~0.000 (올바름)
- Rule: +0.05 (noreply 발신자)
- URL: max_score = 1.00 → `0.45 × 1.00 = 0.45` → 최종 0.465

URL 모델이 핵심 문제임을 확인.

### 2-2. 피처 분포 추적

`url_extractor.py` 의 `URLFeatures` 16개 피처를 점검:

```python
url_length, domain_length, path_length, num_digits,
num_special_chars, at_symbol, double_slash, prefix_suffix_dash,
subdomain_count, is_ip_address, is_https, suspicious_tld,
shortener, phishing_keyword_count, query_param_count, has_port
```

`https://www.anthropic.com/` 에 대해 직접 피처를 추출하니 전부 정상값.  
그런데 XGBoost 모델이 **1.00** 을 반환.

---

## 3. 근본 원인 1: 훈련/추론 분포 불일치 (`is_https`)

### 원인

훈련 데이터셋의 URL 형식 확인:

```
br-icloud.com.br           ← 프로토콜 없음
google.com                 ← 프로토콜 없음
paypal-secure-login.net    ← 프로토콜 없음
```

훈련 스크립트 `train_url_model.py` 가 URL 그대로 피처를 추출하고 있었다:

```python
# 수정 전 (버그)
for url in chunk:
    u = str(url).strip()
    rows.append(extract_features(u).to_list())
```

`extract_features("br-icloud.com.br")` → `parsed.scheme = ""` → `is_https = False (0)`

훈련 데이터 전체에서 **합법적 URL도 피싱 URL도 모두 `is_https=0`**.

### 결과

실제 이메일에서 오는 URL은 항상 `https://` 포함 → `is_https=1`.  
XGBoost는 `is_https=1` 자체를 한 번도 합법 데이터로 학습하지 않았음.  
**feature importance 분석: `is_https` 가 전체의 50% 이상을 차지.**

모델 입장에서 `is_https=1` = 피싱.

### 수정

```python
# 수정 후 (train_url_model.py)
for url in chunk:
    u = str(url).strip()
    if not u.startswith("http://") and not u.startswith("https://"):
        u = "https://" + u  # 베어 URL에 프로토콜 추가
    rows.append(extract_features(u).to_list())
```

모든 훈련 URL을 `https://` 정규화 후 피처 추출 → v2 모델 학습.

---

## 4. 근본 원인 2: `at_symbol` 피처 버그 (YouTube 오탐)

### 원인

v2 모델 검증 중 `https://www.youtube.com/@anthropic-ai` 가 **0.98** 반환.

`url_extractor.py` 의 at_symbol 피처:

```python
# 수정 전 (버그)
at_symbol = "@" in url
```

`https://www.youtube.com/@anthropic-ai` → URL 문자열 전체에 `@` 포함 → `at_symbol=1`.

### 실제 피싱에서의 @ 의미

`@` 가 피싱 신호인 경우는 URL의 **authority(netloc) 섹션**에 나타날 때:

```
http://google.com@evil.com/login
         ^^^^^^^
         netloc의 @ → 브라우저는 evil.com으로 이동하지만 사용자는 google.com처럼 보임
```

YouTube 채널 URL의 `/@channel` 은 **path 섹션**이므로 피싱 신호가 아님.

### 수정

```python
# 수정 후 (url_extractor.py)
at_symbol = "@" in parsed.netloc   # netloc에서만 확인
```

---

## 5. v3 모델 학습 및 배포

### 학습 과정

두 가지 수정사항을 모두 적용 후 v3 재학습:

1. `train_url_model.py`: 훈련 URL 정규화 (`https://` 접두사 추가)
2. `url_extractor.py`: `at_symbol` netloc 한정 검사

```bash
# EC2에서 실행
cd ~/phishguard
python scripts/train_url_model.py
# 학습 완료: models/url_model_v3.pkl (1,061,815 bytes)
# 학습 일시: 2026-06-13 10:39 UTC
```

### Feature Importance (v3)

| 피처 | 중요도 |
|------|--------|
| `is_https` | 0.6947 |
| `prefix_suffix_dash` | 0.0626 |
| `suspicious_tld` | 0.0503 |
| `subdomain_count` | 0.0421 |
| `at_symbol` | **0.0000** ← 버그 수정 후 모델이 무의미하다고 학습 |

### 배포

```bash
# 백업
cp models/url_model.pkl models/url_model_backup_20260613_195359.pkl

# 교체
cp models/url_model_v3.pkl models/url_model.pkl

# 서비스 재시작
sudo systemctl restart phishguard
```

---

## 6. 검증 결과

### Anthropic 이메일 URL 점수 비교

| URL | 수정 전 | v3 수정 후 |
|-----|---------|-----------|
| `https://www.anthropic.com/` | 1.000 | **0.295** ✓ |
| `https://anthropic.com/privacy` | 1.000 | **0.149** ✓ |
| `https://privacy.anthropic.com` | 0.010 | 0.031 ✓ |
| `https://www.anthropic.com/?#footerLogo` | 1.000 | **0.272** ✓ |
| `https://www.linkedin.com/showcase/claude/` | ~1.000 | 0.509 (경계) |
| `https://www.youtube.com/@anthropic-ai` | **0.980** | **0.352** ✓ |
| `https://x.com/anthropic` | ~1.000 | 0.845 (제한 사항) |

### 최종 스코어 변화

```
이전: 0.45×0.000 + 0.45×1.000 + 0.10×0.15 = 0.465 → suspicious ❌
v3:  0.45×0.000 + 0.45×0.845 + 0.10×0.15 = 0.395 → normal    ✓
```

### 피싱 URL 탐지 정확도 유지

| 피싱 URL 예시 | v3 점수 |
|------|--------|
| `http://paypal.com.verify-account.net/login` | 0.999 |
| `http://192.168.1.1/admin/login` | 1.000 |
| `http://bit.ly/suspicious` | 0.999 |

피싱 탐지 능력은 그대로 유지.

---

## 7. 잔존 제약사항

### x.com (0.845)

`https://x.com/anthropic` 이 여전히 0.845를 반환.

**원인:** Twitter가 2022년 10월 x.com으로 리브랜딩. 훈련 데이터셋은 그 이전 시점 기준이라 x.com이 합법 도메인으로 등록되지 않음. `domain_length=5` (매우 짧음) + 서브도메인 없음이 피싱 패턴과 유사하게 학습됨.

**현재 영향:** NLP가 0에 가까운 정상 이메일은 최종 스코어 0.395로 normal 유지. NLP가 미세하게 올라가면 suspicious로 뒤집힐 가능성 있음 (마진 0.005).

**해결책 (미적용):** x.com을 합법 도메인으로 훈련 데이터에 추가 → v4 모델 학습.

### LinkedIn (0.509)

`https://www.linkedin.com/showcase/claude/` 가 0.509.  
모델 결정 경계에 걸려 있으나, max URL score가 x.com으로 결정되므로 최종 스코어에 직접 영향 없음.

---

## 8. 교훈

1. **훈련-추론 분포 일치 필수**: 훈련 데이터의 URL 형식과 추론 시 입력 형식이 다르면 모델이 의도치 않은 피처를 학습한다. URL 정규화는 훈련과 추론에서 동일하게 적용해야 한다.

2. **피처 정의의 정확성**: `at_symbol` 처럼 도메인 지식이 필요한 피처는 정확한 의미를 반영해야 한다. `@` 는 URL 전체가 아닌 netloc 섹션에서만 피싱 신호다.

3. **Feature Importance로 버그 발견**: 수정 후 `at_symbol` importance가 0.000이 된 것은 모델 자체가 "이 피처는 의미 없다"는 것을 확인한 결과. Feature importance는 피처 품질 검증 도구로 활용 가능.

4. **임계값 마진 모니터링**: x.com 사례처럼 단일 URL 이상값이 최종 스코어를 결정 경계 근처로 밀 수 있다. 마진이 0.01 이하인 경우 별도 모니터링 필요.
