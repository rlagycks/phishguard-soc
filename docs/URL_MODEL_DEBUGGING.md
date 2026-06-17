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

---

# 2차 트러블슈팅: is_https 제거 및 화이트리스트 도입

**날짜:** 2026-06-17  
**발단:** Stack Overflow 뉴스레터 (`do-not-reply@hello.stackoverflow.email`) URL 점수 0.95  
**결과:** 세 가지 독립적 근본 원인 발견 및 수정 완료

---

## 1. 발단 — 문제 재발

Stack Overflow 뉴스레터가 다시 phishing으로 분류됨.

```
발신: do-not-reply@hello.stackoverflow.email
URL 점수: 0.95 → 최종 스코어 suspicious
```

이전 세션에서 v3 모델로 수정했음에도 불구하고 URL 모델이 0.95를 반환.  
추가 분석 결과, v3에서도 `is_https=True` 에 대한 역편향이 잔존하고 있었다.

---

## 2. 근본 원인 A: `is_https` 역편향 (v3 모델에도 잔존)

### 원인

v3 학습 시 훈련 URL을 모두 `https://` 로 정규화했지만, 이것이 오히려 문제를 악화시켰다.

훈련 데이터 분포:
- 합법 URL 70%: 원본이 프로토콜 없음 → `https://` 추가 후 `is_https=1`
- 피싱 URL: 일부만 `https://`, 대부분 `http://` 또는 프로토콜 없음

XGBoost가 학습한 패턴:
```
is_https=1 → 합법일 가능성 높음 (의도한 방향)
```

그런데 Stack Overflow 뉴스레터 URL은 `http://` 클릭 트래킹 URL → `is_https=0`.  
모델이 `is_https=0` = 피싱으로 분류 → 0.95 반환.

**근본 문제**: `is_https` 는 URL 내용이 아닌 **이메일 발신자의 인프라 선택**을 반영한다. ESP(이메일 서비스 제공자)들은 클릭 트래킹 링크를 `http://` 로 제공하는 경우가 많아 피싱 여부와 무관하다.

### 수정

`is_https` 를 피처 벡터에서 완전 제거하고 15-피처 모델로 재학습:

```python
# url_extractor.py - to_list() 수정
def to_list(self) -> list[float]:
    # is_https 제거: 훈련 데이터 70% 가 scheme-less → http://로 정규화되어
    # is_https=True 가 피싱과 역상관 학습됨
    return [
        self.url_length, self.domain_length, self.path_length,
        self.num_digits, self.num_special_chars,
        int(self.at_symbol), int(self.double_slash), int(self.prefix_suffix_dash),
        self.subdomain_count, int(self.is_ip_address),
        int(self.suspicious_tld), int(self.shortener),
        self.phishing_keyword_count, self.query_param_count, int(self.has_port),
    ]
```

**15-피처 모델 성능:**
- Accuracy: 84.68%
- ROC-AUC: 0.9075
- Feature importance 상위: `suspicious_tld` 0.2493, `is_ip_address` 0.2261

---

## 3. ESP 화이트리스트 도입

재학습 후에도 Stack Overflow 뉴스레터 URL이 여전히 0.95.  
`stackoverflow.email` 도메인의 클릭 트래킹 URL은 본질적으로 안전.

### 수정

`url_model.py` 에 ESP 화이트리스트 추가:

```python
_KNOWN_ESP_DOMAINS = {
    "stackoverflow.email", "sendgrid.net", "mailchimp.com",
    "list-manage.com", "hubspotlinks.com", "amazonses.com",
    # ... 약 20개 주요 ESP
}

def _is_known_esp(url: str) -> bool:
    hostname = urlparse(url).hostname or ""
    registrable = ".".join(hostname.lower().split(".")[-2:])
    return registrable in _KNOWN_ESP_DOMAINS
```

ESP 화이트리스트 히트 시 → 점수 0.05 고정 반환 (early return).

---

## 4. 근본 원인 B: 훈련 데이터 bare-domain 분포 편향

### 발견 경위

is_https 제거 + ESP 화이트리스트 후에도 `https://google.com` 이 **0.997** 반환.

훈련 데이터를 직접 분석:

```python
# 훈련 데이터 50,000 샘플 분석
# 조건: url_length == domain_length (bare domain, path 없음)
#        subdomain_count == 0 (www 없음)

# 결과 (url_length 5~24 범위 모두):
# label=0 (합법): 0개
# label=1 (피싱): 수백~수천 개
```

**원인**: 합법 URL 데이터셋은 `https://google.com/search?q=...` 처럼 경로나 쿼리가 있는 형태로 수집. 피싱 URL 데이터셋은 `google.com` 처럼 bare domain 형태로 수집. 결과적으로 모델이 "bare domain = 피싱"으로 학습.

```
훈련 시:  google.com (scheme-less) → url_len=10, dom_len=10, path=0
추론 시:  https://google.com → url_len=10 (scheme 제외), dom_len=10, path=0

→ 훈련 데이터에서 이 패턴은 100% 피싱 레이블 → 점수 0.997
```

### 수정: 합법 도메인 화이트리스트

모델을 다시 학습하지 않고, 잘 알려진 합법 도메인을 화이트리스트로 처리:

```python
_KNOWN_LEGIT_DOMAINS = {
    "google.com", "amazon.com", "microsoft.com", "apple.com",
    "github.com", "stackoverflow.com", "naver.com", "kakao.com",
    "paypal.com", "stripe.com", "youtube.com", "linkedin.com",
    # ... 약 200개 (tech/금융/언론/교육/한국 주요 서비스)
}

def _is_known_legit(url: str) -> bool:
    hostname = urlparse(raw).hostname or ""
    parts = hostname.lower().split(".")
    registrable = ".".join(parts[-2:])
    return registrable in _KNOWN_LEGIT_DOMAINS
```

**등록 도메인(registrable domain) 기준 매칭**으로 우회 공격 방지:
- `mail.google.com` → registrable = `google.com` → 화이트리스트 히트 ✓
- `paypal.com-verify.tk` → registrable = `verify.tk` → 미스 ✓

합법 도메인 화이트리스트 히트 시 → 점수 0.10 고정 반환.

---

## 5. 근본 원인 C: `num_special_chars` 가 ML 판단 역전

### 발견 경위

`http://login.verify-paypal.xyz/account?reset=1` 이 **0.312** 반환 (기대값 > 0.5).

피처 격리 실험:

```
suspicious_tld=1, 나머지=0              → 0.998  (정상)
suspicious_tld=1, kw_count=4           → 0.999  (정상)
url_len=39, dom_len=23, susp_tld=1, kw=4 → 0.712  (낮아짐)
실제 전체 피처 벡터                     → 0.312  (역전!)
```

실제 피처 벡터에서 추가된 값: `num_special_chars=3`, `num_digits=1`, `subdomain_count=1`, `query_param_count=1`.

### 원인

`num_special_chars` 계산 방식:
```python
special_chars = sum(normalized.count(c) for c in "@-_%=?&")
```

쿼리 파라미터 `?reset=1` 에서 `?` 와 `=` 가 각 1회 → special_chars += 2.  
합법적인 뉴스레터, 분석 URL들은 `?utm_source=newsletter&ref=email` 같은 긴 쿼리를 가져 special_chars가 높음.

XGBoost가 학습한 패턴:
```
high num_special_chars → 합법 (뉴스레터/트래킹 URL 패턴)
```

결과적으로 피싱 URL에 쿼리 파라미터가 있으면 점수가 오히려 낮아지는 역효과.

### 수정: Hard Indicator Heuristic Floor

ML 점수가 낮더라도 "이건 무조건 의심"인 조건 충족 시 heuristic 점수를 floor로 사용:

```python
def _has_hard_phishing_indicators(f: URLFeatures) -> bool:
    if f.is_ip_address:   # IP 직접 접근
        return True
    if f.shortener:        # 단축 URL로 목적지 숨김
        return True
    if f.suspicious_tld and f.phishing_keyword_count >= 2:  # 의심 TLD + 키워드 복수
        return True
    return False

# _score_one() 내부
if _has_hard_phishing_indicators(features):
    score = max(score, _heuristic_score(features))
```

Heuristic 점수 계산:
```
http://login.verify-paypal.xyz/account?reset=1:
  is_https=False  → +0.15
  suspicious_tld  → +0.20
  kw_count=4      → +0.40 (0.10 × 4)
  합계             → 0.75
```

ML 0.312 → `max(0.312, 0.75)` = **0.75**.

---

## 6. Suspicious TLD 목록 확장

`http://www.kolibri.icu` 가 0.172 반환. `.icu` 가 목록에 없었음.

```python
# url_extractor.py 수정 전
_SUSPICIOUS_TLDS = {
    ".xyz", ".top", ".club", ".site", ".online", ".info", ".biz",
    ".tk", ".ml", ".ga", ".cf", ".gq",
}

# 수정 후 (피싱 캠페인에 자주 등장하는 TLD 추가)
_SUSPICIOUS_TLDS = {
    ".xyz", ".top", ".club", ".site", ".online", ".info", ".biz",
    ".tk", ".ml", ".ga", ".cf", ".gq",
    ".icu", ".cyou", ".monster", ".buzz", ".rest", ".sbs",
    ".wang", ".vip", ".win", ".loan", ".click", ".link",
}
```

---

## 7. 최종 결과

| URL | 수정 전 | 수정 후 |
|-----|---------|---------|
| `https://google.com` | **0.997** ❌ | **0.100** ✓ (화이트리스트) |
| `https://stackoverflow.com` | 0.95 ❌ | **0.100** ✓ (화이트리스트) |
| `https://naver.com` | ~0.99 ❌ | **0.100** ✓ (화이트리스트) |
| `http://login.verify-paypal.xyz/account?reset=1` | **0.312** ❌ | **0.750** ✓ (heuristic floor) |
| `http://www.kolibri.icu` | **0.172** ❌ | **0.938** ✓ (.icu TLD 추가) |
| `http://192.168.1.1/phishing` | 0.997 ✓ | 0.998 ✓ |
| `http://bit.ly/2xABCDEF` | 0.974 ✓ | 0.974 ✓ |

---

## 8. 잔존 제약사항

### vojxua.iheys.in (0.233)

`http://www.vojxua.iheys.in` 같은 DGA(도메인 생성 알고리즘) 스타일 도메인이 낮은 점수 반환.

**원인:** `.in` 은 인도 합법 ccTLD → suspicious TLD 아님. 현재 피처 벡터에 "도메인 문자 무작위성" 피처 없음.

**해결책 (미적용):** 도메인의 entropy(문자 분포 무작위성) 피처 추가 후 재학습 필요.

---

## 9. 방어 계층 구조 정리

수정 후 `_score_one()` 의 처리 순서:

```
1. ESP 화이트리스트 히트? → 0.05 반환 (뉴스레터 트래킹 URL)
2. 합법 도메인 화이트리스트 히트? → 0.10 반환 (well-known 도메인)
3. XGBoost ML 점수 계산
4. Hard indicator 존재? → max(ML, heuristic) 적용
5. 최종 점수 반환
```

---

## 10. 교훈

1. **훈련 데이터 수집 방식 확인**: 합법/피싱 URL을 어떤 형태로 수집했는지에 따라 특정 패턴이 편향될 수 있다. bare domain vs full URL, scheme 유무 등을 사전에 확인해야 한다.

2. **피처 상호작용 격리 실험**: ML 모델이 예상과 다른 점수를 낼 때, 피처를 하나씩 추가하며 어느 피처가 판단을 역전시키는지 파악하는 격리 실험이 유효하다.

3. **Heuristic과 ML의 상호보완**: ML 모델은 훈련 분포 외 케이스에서 실패할 수 있다. "이 조건이면 무조건 의심"이라는 명확한 규칙이 있을 때는 heuristic을 safety net으로 사용한다.

4. **화이트리스트는 band-aid**: 합법 도메인 화이트리스트는 훈련 데이터 편향의 임시 해결책이다. 장기적으로는 Tranco Top-1M 등 high-quality 합법 URL을 bare domain 형태로 추가하여 재학습하는 것이 근본 해결책이다.
