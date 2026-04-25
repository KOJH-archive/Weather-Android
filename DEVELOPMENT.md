# 📱 Flet 기반 안드로이드 하이브리드 앱 개발 명세서 (Best Practices)

본 문서는 파이썬(Flet)을 활용하여 안드로이드 모바일 어플리케이션을 개발하고 배포하는 과정에서 겪은 수많은 트러블슈팅과 핵심 아키텍처를 정리한 **실무 지침서**입니다. 향후 유사한 어플리케이션을 개발할 때 복사-붙여넣기 및 가이드로 활용할 수 있습니다.

---

## 1. 아키텍처 및 통신 최적화

### 1.1 동기(Sync) vs 비동기(Async) 통신
모바일 환경에서는 0.1초의 멈춤(프리징)도 치명적인 사용자 경험 저하를 낳습니다.
- **Bad**: `requests` (호출하는 동안 UI가 멈춤)
- **Good**: `httpx.AsyncClient` (데이터를 기다리는 동안 UI 애니메이션이 부드럽게 동작)
```python
import httpx
import asyncio

async def fetch_data():
    async with httpx.AsyncClient() as client:
        res = await client.get("https://api.example.com/data")
        return res.json()
```

### 1.2 HTTP 차단 정책 (안드로이드 9 이상)
안드로이드 9(Pie)부터는 보안상 일반 HTTP 통신이 기본적으로 차단됩니다.
- 가급적 모든 API 주소를 `https://`로 변경하여 사용하세요.
- 부득이하게 HTTP를 써야 한다면 `pyproject.toml`에 `usesCleartextTraffic = true`를 반드시 설정해야 합니다.

---

## 2. 안드로이드 모바일 UI/UX 특수성

### 2.1 절대 경로(`os.path`) 사용 금지
PC에서는 `os.path.join(__file__)` 방식이 통하지만, 안드로이드 APK 내부로 패키징되면 경로 구조가 완전히 달라져 앱이 하얗게 멈추는 에러가 발생합니다.
- **해결책**: Flet의 공식 에셋 폴더 지정 방식을 사용합니다.
```python
# 코드 내부 (파일 이름만 사용)
ft.Image(src="weather_bg.png")

# 실행 부 (assets_dir 명시 필수)
if __name__ == "__main__":
    ft.run(main, assets_dir="assets")
```

### 2.2 모바일 Window 속성 접근 금지
안드로이드는 전체화면 기반이므로 `page.window` 객체에 접근하면 에러(Crash)가 발생하여 앱이 튕깁니다.
- **해결책**: 플랫폼 감지를 통해 데스크톱에서만 창 크기를 조절하도록 보호합니다.
```python
is_mobile = page.platform in [ft.PagePlatform.ANDROID, ft.PagePlatform.IOS]
if not is_mobile:
    page.window.width = 400
    page.window.height = 800
```

---

## 3. 하드웨어 네이티브 기능 (GPS 등) 다루기

### 3.1 서드파티 네이티브 플러그인의 한계 (Unknown Control)
Flet에서 파이썬 모듈(`flet-geolocator` 등)을 추가하더라도, **기반이 되는 Flutter의 네이티브(Dart/Java) 코드가 자동 병합되지 않아 화면에 빨간색 에러 상자(Unknown Control)가 뜨는 현상**이 자주 발생합니다.
- **권장 해결책**: 네이티브 권한이 억지로 필요한 플러그인보다는, **IP 기반 위치 추적 API**(`https://ip-api.com/` 등)를 사용하여 권한 승인 절차를 없애고 앱을 가볍게 유지하는 것이 훨씬 안정적입니다.

### 3.2 JNI(네이티브 브릿지) 충돌 방지
안드로이드 기기 고유의 기능(예: S24 온디바이스 AI)을 호출하기 위해 `jnius`를 사용할 때, 파일 최상단에 `import`를 걸어두면 PC에서 코드를 테스트할 때 충돌이 납니다.
- **해결책**: 플랫폼 검사 후, 함수 내부에서 지연(Lazy) 임포트 하세요.
```python
async def run_android_ai(is_android):
    if is_android:
        from jnius import autoclass
        # ... 안드로이드 네이티브 호출 ...
```

---

## 4. API 보안 및 깃허브 액션(CI/CD) 자동 배포

### 4.1 앱 내부 API 키 하드코딩 절대 금지
소스 코드나 `build.yml`에 API 키를 하드코딩하면, 깃허브 공개 시 누구나 키를 탈취할 수 있으며 리버스 엔지니어링의 표적이 됩니다.
- 로컬 개발 시에는 `python-dotenv`를 사용하여 `.env` 파일로 키를 숨깁니다.
- `.env` 파일은 반드시 `.gitignore`에 등록하여 깃허브에 올라가지 않도록 합니다.

### 4.2 GitHub Actions에서 안전하게 API 키 주입하기
클라우드 서버(GitHub Actions)가 APK를 빌드할 때 빈 키값 때문에 **"연결 오류"**가 나는 것을 방지하려면, 깃허브의 **Secrets** 기능을 활용합니다.
1. GitHub 레포지토리 Settings -> Secrets -> `DATA_GO_KR_API_KEY` 등록
2. `build.yml` 내부에 아래 스텝 추가:
```yaml
      - name: Create .env file for API Key
        run: |
          echo "DATA_GO_KR_API_KEY=${{ secrets.DATA_GO_KR_API_KEY }}" > .env
```

### 4.3 Flet 빌드 타겟 명확화
폴더 내에 여러 파이썬 파일(예: `main.py`, `android_main.py`)이 섞여 있으면, 깃허브 빌드 봇이 엉뚱한 파일을 메인으로 잡고 빌드할 수 있습니다.
- **해결책 1**: 헷갈릴 수 있는 예전 파일(`main.py`)은 이름을 변경하거나 지웁니다.
- **해결책 2**: `build.yml` 명령어에 타겟을 100% 명확하게 박아넣습니다.
```bash
# 옵션을 통해 정확한 엔트리 포인트 강제
flet build apk --module-name android_main -vv --yes
```

---

## 5. 결론 (개발 마인드셋)
모바일 하이브리드 앱 개발은 "PC에서 잘 도니까 폰에서도 잘 돌겠지"라는 가정이 가장 위험합니다. 
1. **가볍게(Raw)**: 외부 네이티브 플러그인 의존도를 최대한 낮춥니다.
2. **안전하게(Secure)**: 파일 경로와 API 키 관리는 모바일의 고립된 환경(Sandboxed)을 가정하고 설계합니다.
3. **비동기(Async)**: 모든 네트워크 통신은 UI를 막지 않도록 논블로킹(Non-blocking)으로 구성합니다.
