# 🚀 Flet 기반 안드로이드 날씨 앱: Zero-to-Hero 개발 마스터 가이드

본 문서는 파이썬(Flet)을 활용하여 "아무것도 없는 상태에서 완벽하게 동작하는 안드로이드 앱"을 만들기까지의 **A to Z 개발 과정과 모든 트러블슈팅 노하우**를 담은 궁극의 마스터 명세서입니다. 
향후 AI에게 이 문서만 학습시켜도 단 한 번의 에러 없이 완벽한 앱을 찍어낼 수 있도록 상세하게 기록되었습니다.

---

## 🛠️ Step 1. 프로젝트 초기 환경 셋팅 (Project Setup)

가장 흔한 에러는 환경 설정 단계에서 발생합니다.

### 1.1 의존성 관리 및 패키지 설치
무겁고 충돌이 잦은 패키지 대신, 가장 가볍고 빠른 도구만 사용합니다.
- `flet`: 앱 UI 및 모바일 빌드 엔진
- `httpx`: 모바일 UI 프리징(멈춤)을 막기 위한 **비동기 전용 HTTP 라이브러리** (`requests` 사용 절대 금지)
- `python-dotenv`: 로컬 테스트 시 API 키 보안을 위한 환경변수 관리

### 1.2 `pyproject.toml` 구성 (안드로이드 빌드용)
Flet 빌드 엔진이 모바일 앱을 만들 때 참조하는 핵심 파일입니다. 권한과 시작 파일을 명확히 해야 합니다.
```toml
[tool.flet]
product = "Weather Insight Hub"
org = "org.insight"
module-name = "android_main" # 중요: 여러 파일이 섞여 있을 때 빌드할 대상을 정확히 강제합니다.

[tool.flet.android]
usesCleartextTraffic = true # HTTP 통신 차단 해제 (단, 가급적 HTTPS 사용 권장)

[tool.flet.android.permissions]
# GPS 권한 대신 IP 기반 위치 조회를 사용하면 권한 설정이 필요 없어 앱이 매우 가벼워집니다.
INTERNET = true
```

---

## 🎨 Step 2. 크로스 플랫폼 UI 설계 (UI/UX Architecture)

안드로이드(모바일)와 PC(데스크톱)의 환경 차이를 극복하는 코드를 작성해야 합니다.

### 2.1 절대 경로(`os.path`) 사용 금지 및 에셋 로드
안드로이드 APK 내부에서는 `os.path.abspath(__file__)` 방식이 통하지 않아 앱이 하얗게 멈춥니다.
**반드시 Flet의 공식 에셋 폴더 연동 방식을 사용해야 합니다.**
```python
# Bad: 안드로이드에서 파일 못 찾음 에러 발생
# BG_IMAGE_PATH = os.path.join(current_dir, "assets", "weather_bg.png")
# ft.Image(src=BG_IMAGE_PATH)

# Good: 파일명만 적어주고, ft.run()에서 폴더를 명시
ft.Image(src="weather_bg.png")

if __name__ == "__main__":
    ft.run(main, assets_dir="assets") # 필수!
```

### 2.2 모바일 Window 객체 접근 예외 처리
안드로이드 기기는 무조건 전체 화면이므로 `page.window.width`를 건드리면 앱이 즉시 강제 종료됩니다.
```python
# 플랫폼 감지 로직으로 PC 환경에서만 창 크기 조절
is_mobile = page.platform in [ft.PagePlatform.ANDROID, ft.PagePlatform.IOS]
if not is_mobile:
    page.window.width = 400
    page.window.height = 800
    page.window.resizable = False
```

---

## 📡 Step 3. 데이터 통신 및 네이티브 하드웨어 (Core Logic)

### 3.1 동기(Sync) 통신 배제 -> 100% 비동기화
앱에서 "데이터 로딩 중..." 애니메이션이 부드럽게 돌아가려면 `asyncio`와 `httpx`가 필수입니다.
```python
async def fetch_weather_data():
    async with httpx.AsyncClient() as client:
        # 안드로이드 네트워크 차단 정책(보안)을 피하기 위해 반드시 https:// 사용
        res = await client.get("https://apis.data.go.kr/...", timeout=10)
        return res.json()
```

### 3.2 GPS 센서 연동의 함정 (Unknown Control 해결)
`flet-geolocator` 같은 서드파티 네이티브 플러그인은 Flet 빌드 시 네이티브 코드(Dart/Java)가 병합되지 않아 **빨간 화면(Unknown Control) 에러**를 유발할 확률이 높습니다.
- **실무 해결책**: 네이티브 권한을 우회하는 **IP 기반 실시간 위치 추적 API**(`https://ip-api.com/json/` 등)를 사용하여 권한 팝업 없이 0.1초 만에 위경도를 가져오는 것이 모바일 앱 구동 안정성에 100배 유리합니다.

### 3.3 안드로이드 네이티브(JNI) 라이브러리 충돌 방지
갤럭시 S24 온디바이스 AI(Gemini Nano) 등 안드로이드 전용 네이티브 모듈(`jnius`)을 코드 상단에 Import 하면 PC에서 테스트할 때 무조건 튕깁니다.
- **해결책**: 플랫폼 검사 후 지연 호출(Lazy Import) 사용.
```python
async def run_ai_briefing(is_mobile):
    if is_mobile:
        from jnius import autoclass
        # 모바일에서만 실행되는 네이티브 코드
```

---

## ☁️ Step 4. 보안 및 CI/CD 자동 배포 (GitHub Actions)

가장 완벽하게 코드를 짰어도, 깃허브 배포 설정이 잘못되면 빈 껍데기 앱이 나옵니다.

### 4.1 치명적 실수: API 키 하드코딩
소스코드나 빌드 설정(`build.yml`)에 API 키를 날것(Raw)으로 적으면 해킹의 표적이 됩니다.
- 코드에서는 반드시 `os.getenv("DATA_GO_KR_API_KEY")`로 불러옵니다.
- `.env` 파일은 `.gitignore`에 등록하여 깃허브에 절대 올리지 않습니다.

### 4.2 GitHub Actions "연결 오류" 완벽 해결법
깃허브 서버가 APK를 구울 때 `.env` 파일이 없어서 API 키가 비어버리는 문제("연결 오류" 텍스트 발생)를 막아야 합니다.
1. 깃허브 레포지토리 Settings -> Secrets -> `DATA_GO_KR_API_KEY` 값 등록
2. `.github/workflows/build.yml` 내부에 **키 자동 주입 스크립트** 작성:
```yaml
      - name: Install Python Dependencies
        run: |
          pip install --upgrade pip
          pip install flet httpx python-dotenv # 정확한 라이브러리 설치 강제

      - name: Create .env file for API Key
        # Secrets에서 키를 빼내어 일회용 .env 파일을 생성 (보안 완벽 유지)
        run: |
          echo "DATA_GO_KR_API_KEY=${{ secrets.DATA_GO_KR_API_KEY }}" > .env

      - name: Build APK with Flet
        # --module-name 옵션을 통해 엉뚱한 파일(main.py)이 빌드되는 것을 원천 차단
        run: |
          export GRADLE_OPTS="-Xmx2048m -Dorg.gradle.daemon=false"
          flet build apk --module-name android_main -vv --yes
```

---

## 🎯 최종 학습(프롬프트) 요약 가이드
이 문서를 기반으로 AI가 다음 앱을 개발할 때 지켜야 할 **3대 절대 규칙**:
1. **Never Sync**: 모든 UI 업데이트와 네트워크 호출은 `async`/`await`로 짤 것. (`requests` 절대 금지)
2. **Never Absolute Path**: 안드로이드 에셋 로딩은 무조건 `assets_dir="assets"` 선언 후 파일명만 쓸 것.
3. **Never Trust Native Plugins**: 검증되지 않은 모바일 센서 플러그인 대신, 웹 기반 REST API(예: IP 기반 위치추적) 우회로를 최우선으로 고려할 것.
