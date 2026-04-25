# Premium Flet Application 개발 명세서 (Weather Insight 기준)

본 문서는 Flet(v0.84.0+)을 활용한 프리미엄 데스크톱 애플리케이션 개발 시 표준 가이드라인으로 활용하기 위해 작성되었습니다.

---

## 1. 기술 스택 (Tech Stack)
- **Language**: Python 3.10+
- **Framework**: Flet v0.84.0 이상 (Modern UI Library)
- **HTTP Client**: Requests (API 통신용)
- **Execution**: Windows Batch (.bat) with UTF-8 (CHCP 65001)

---

## 2. 핵심 아키텍처 및 로직

### 2.1 기상청 API 연동 (KMA Vilage Forecast)
- **좌표 변환**: 위경도(WGS84)를 기상청 격자 좌표(LCC)로 변환하는 `dfs_xy_conv` 함수 필수 포함.
- **Base Time 처리**: 기상청 API의 발표 시간(0200, 0500...)과 현재 시간을 비교하여 `base_time` 산출.
  - **자정 로직**: 0시~02시 사이에는 전날 23시 데이터를 호출하도록 `timedelta` 처리 필수.

### 2.2 대기질 API 연동 (AirKorea)
- 시도별 실시간 측정 데이터를 가져오며, `khaiGrade`를 기준으로 등급(좋음/보통/나쁨)을 매핑 처리.

---

## 3. UI/UX 디자인 가이드라인 (Premium UI)

### 3.1 디자인 테마
- **Dark Mode**: `#000000` 배경과 투명도 조절된 블랙 오버레이 사용.
- **Glassmorphism**: 
  - `bgcolor="white10"` (또는 투명도 낮은 배경색)
  - `blur=ft.Blur(10, 10)` 속성 적용
  - `border=ft.Border.all(1, "white10")`로 얇은 경계선 추가

### 3.2 레이아웃 구조 (2-Column Dashboard)
- **Hero Panel (Left)**: 주요 상태(기온, 아이콘)를 크게 배치하여 시각적 몰입감 제공.
- **Dashboard Panel (Right)**: 상세 지표들을 카드 형태로 그리드 배치.

---

## 4. Flet v0.84.0+ API 표준 (Critical)

이전 버전과의 호환성 문제 해결을 위해 반드시 다음 명칭을 준수해야 합니다.

| 구분 | 표준 사용법 (0.84.0+) | 주의사항 |
| :--- | :--- | :--- |
| **App 실행** | `ft.run(main)` | `ft.app(target=main)`은 권장되지 않음 |
| **창 관리** | `page.window.width`, `page.window.resizable` | `page.window_width` 등 속성 제거됨 |
| **아이콘** | `ft.Icons.WB_SUNNY` (대문자 I) | `ft.icons` 모듈 대신 `Icons` 클래스 사용 |
| **색상** | `"white10"`, `"black45"` (문자열) | `ft.colors` 참조 오류 방지를 위해 문자열 권장 |
| **정렬** | `ft.Alignment.CENTER` (대문자 A) | `ft.alignment.center` 등 소문자 속성 제거됨 |
| **테두리** | `ft.Border.all()` (대문자 B) | `ft.border.all()` 경고 발생 및 삭제 예정 |
| **여백** | `ft.Margin.only()` (대문자 M) | `ft.margin.only()` 경고 발생 및 삭제 예정 |
| **이미지 맞춤**| `fit=ft.BoxFit.COVER` | `ft.ImageFit` 클래스 제거됨 |

---

## 5. 실행 및 배포 최적화

### 5.1 배치 파일 (.bat) 작성
- 한글 깨짐 방지를 위해 반드시 `chcp 65001` 명령어를 상단에 포함.
- 가상환경(`.venv`)의 존재 여부를 체크하고 자동 활성화하는 로직 포함.

### 5.2 리소스 관리
- 배경 이미지 등 외부 리소스는 절대 경로보다는 프로젝트 내부 상대 경로를 사용하도록 설계 (배포 시 유리).

---

## 6. 트러블슈팅 케이스 (Lessons Learned)
- **IconButton 에러**: `icon` 속성이 비어 있으면 런타임 에러가 발생하므로 반드시 유효한 아이콘 이름을 전달해야 함.
- **VerticalDivider 오류**: `VerticalDivider`는 `Column` 내부에서 `height` 속성을 가질 수 없으므로, 간격 조절은 `ft.Container(height=...)`를 사용하는 것이 안전함.
