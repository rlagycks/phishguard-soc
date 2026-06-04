# 악성 url 탐지 모델

담당자: 영주 강
마지막 수정일: 2026년 5월 12일 오전 2:00 (GMT+9)
유형: 🗂 기획 및 설계

## 1. 탐지모델

이번 프로젝트에서 **URL 탐지 모델** 파트를 맡았다.

악성 메일에는 피싱 사이트나 악성 파일 다운로드 페이지로 연결되는 URL이 포함될 수 있기 때문에, URL의 특징을 분석해서 정상 URL과 악성 URL을 구분하는 모델을 구현하였다.

## 2. 모델 목적

URL을 입력했을 때 해당 URL이 정상 URL인지
악성 URL로 의심되는지 판단 하는 것이 목적이다

## 3. 데이터 구성

URL과 라벨을 이용해 데이터를 구성하였다.

| label | 의미 |
| --- | --- |
| 0 | 정상 URL |
| 1 | 악성 URL |

예시 데이터는 다음과 같다.

| URL | label |
| --- | --- |
| `https://www.naver.com` | 0 |
| `https://www.google.com` | 0 |
| `http://bank-account-verify-login.com` | 1 |
| `http://192.168.0.1/login/verify` | 1 |

## 4. URL 특징 추출

URL을 그대로 사용하는 것이 아니라, URL에서 몇 가지 특징을 뽑아서 모델에 입력하였다.

| 특징 | 설명 |
| --- | --- |
| URL 길이 | 주소가 너무 긴지 확인 |
| 숫자 개수 | URL 안에 숫자가 많은지 확인 |
| 특수문자 개수 | `?`, `=`, `&`, `-` 등의 개수 확인 |
| HTTPS 여부 | `https://` 사용 여부 확인 |
| IP 주소 포함 여부 | 도메인 대신 IP 주소를 사용하는지 확인 |
| 의심 키워드 포함 여부 | `login`, `verify`, `bank`, `update` 등 포함 여부 확인 |

## 5. 사용한 모델

분류 모델로 **Random Forest**를 사용하였다.

Random Forest는 여러 개의 결정 트리를 이용해 결과를 판단하는 모델로, 정상 URL과 악성 URL을 구분하는 데 적합하다고 판단하였다.

**6. 핵심 코드**

def extract_features(url):
features = {
"url_length": len(url),
"dot_count": url.count("."),
"hyphen_count": url.count("-"),
"digit_count": sum(char.isdigit() for char in url),
"has_https": 1 if url.startswith("https") else 0,
"has_suspicious_keyword": has_suspicious_keyword(url)
}

```
return features
```

위 코드는 URL에서 길이, 점 개수, 하이픈 개수, 숫자 개수, HTTPS 여부, 의심 키워드 포함 여부를 추출하는 부분이다.

이렇게 추출한 값들을 이용해 모델이 정상 URL과 악성 URL을 분류한다

## 7. 실행 결과

| 입력 URL | 예측 결과 |
| --- | --- |
| `https://www.naver.com` | 정상 URL |
| `https://www.google.com` | 정상 URL |
| `http://bank-account-verify-login.com` | 악성 URL 의심 |
| `http://192.168.0.1/login/verify` | 악성 URL 의심 |

## 8. 한계점

이번 모델은 URL 문자열만 보고 판단하기 때문에 완벽한 보안 탐지 시스템은 아니다.

정상 URL처럼 보이도록 정교하게 만든 악성 URL은 탐지하기 어려울 수 있고, 실제 웹페이지 내용까지 분석하지는 못한다.

---

## 9. 개선 방향

추후에는 더 많은 실제 URL 데이터를 사용하고, 웹페이지 내용이나 리다이렉션 여부까지 함께 분석하면 더 정확한 탐지가 가능할 것이다.