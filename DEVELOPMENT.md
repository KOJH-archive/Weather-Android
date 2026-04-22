# 🌦️ Weather Insight Hub: 개발 가이드 및 레퍼런스

본 문서는 Flet 기반 안드로이드 날씨 앱 프로젝트의 설계 구조와 핵심 기술적 해결 방안을 기록한 개발 문서입니다. 추후 유사한 위치 기반 모바일 앱 개발 시 기초 자료로 활용할 수 있습니다.

---

## 1. 프로젝트 개요
- **목적**: 실시간 위치 정보를 기반으로 기상청 및 에어코리아 데이터를 조회하여 사용자에게 시각화된 날씨 및 생활 정보를 제공.
- **주요 기능**:
  - 사용자 실시간 위치(GPS) 획득 및 기상청 격자 좌표 변환.
  - 날씨, 미세먼지, 자외선 지수 등 공공데이터 API 연동.
  - 비동기 처리를 통한 쾌적한 UI/UX 및 AI 브리핑 시뮬레이션.
  - GitHub Actions를 이용한 자동 Android APK 빌드 파이프라인.

## 2. 기술 스택 (Tech Stack)
- **Framework**: [Flet](https://flet.dev/) (Flutter 기반의 Python UI 프레임워크)
- **Language**: Python 3.11
- **Libraries**:
  - `flet-geolocator`: 모바일 GPS 연동
  - `requests`: REST API 통신
  - `asyncio`: 비동기 이벤트 루프 관리
- **CI/CD**: GitHub Actions (Android SDK/NDK Build)

---

## 3. 핵심 설계 및 코드 포인트

### 3.1 위치 좌표 변환 (LCC 격자 변환)
기상청 API는 위경도 대신 고유의 격자 좌표(nx, ny)를 사용합니다. `get_grid_xy` 함수는 복잡한 투영법 계산을 포함하고 있으므로, 타 위치 기반 기상 앱 개발 시 그대로 복사하여 사용할 수 있습니다.
- **주의**: API 요청 시 좌표값은 반드시 정수(`int`)형이어야 합니다.

### 3.2 안드로이드 ANR(응답 없음) 방지 로직
모바일 앱에서 네트워크 통신 시 UI가 멈추는 현상을 방지하기 위해 `requests`의 동기 호출을 비동기로 래핑했습니다.
```python
# 핵심 패턴: 동기 함수를 별도 스레드에서 병렬 실행
w_data, air_data = await asyncio.gather(
    asyncio.to_thread(fetch_kma_short, nx, ny),
    asyncio.to_thread(fetch_air_quality)
)
```

### 3.3 UI 디자인 (Glassmorphism)
`PremiumCard` 클래스와 `ft.Blur`를 활용하여 현대적이고 고급스러운 반투명 UI를 구현했습니다. 다크 모드 기반의 컬러 팔레트를 유지하여 시인성을 높였습니다.

---

## 4. 안드로이드 빌드 및 배포 가이드

### 4.1 `pyproject.toml` 설정
안드로이드 빌드에 필요한 권한과 메타데이터를 정의합니다.
- **Permissions**: `INTERNET`, `ACCESS_FINE_LOCATION`, `ACCESS_COARSE_LOCATION` 필수.
- **Cleartext**: HTTP API 사용을 위해 `usesCleartextTraffic = true` 설정 필수.

### 4.2 GitHub Actions (`build.yml`) 최적화
모바일 빌드 시 발생할 수 있는 고질적인 문제들을 해결한 설정입니다.
- **Python 버전**: 3.12 대신 안정성이 검증된 **3.11** 사용 (p4a 호환성 문제 해결).
- **메모리 최적화**: `GRADLE_OPTS="-Xmx2048m"`를 통해 빌드 중 OOM 방지.
- **인터랙티브 프롬프트**: `flet build apk --yes` 플래그를 사용하여 CI 환경에서 멈춤 현상 방지.
- **Flutter 환경**: `subosito/flutter-action`을 사용하여 빌드 안정성 확보.

---

## 5. 트러블슈팅 가이드 (Gotchas)
1. **빌드 중 EOFError**: `flet build`가 SDK 설치를 물어볼 때 발생함. 반드시 `--yes` 플래그를 사용할 것.
2. **앱 크래시 (Crash)**: API 호출 결과가 `None`일 때의 예외 처리가 부족하면 앱이 종료됨. 항상 `if data:` 조건문으로 방어 코드를 작성할 것.
3. **HTTP 통신 오류**: 안드로이드 9 이상에서는 보안상 HTTPS만 허용함. `pyproject.toml`의 `usesCleartextTraffic` 설정 확인.

---

## 6. 유지보수 및 확장
- **API 키 변경**: `main.py` 상단의 전역 변수만 수정하면 됩니다.
- **디자인 테마 변경**: `page.bgcolor` 및 `PremiumCard`의 `bgcolor` 수정을 통해 전체 톤앤매너 변경이 가능합니다.
- **기능 확장**: `fetch_...` 형태의 데이터 수집 함수만 추가하면 새로운 생활 정보(예: 교통정보, 미세먼지 예보 등)를 쉽게 추가할 수 있습니다.
