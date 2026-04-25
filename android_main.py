import flet as ft
import httpx
import datetime
import math
import os
import asyncio
from dotenv import load_dotenv

# 안드로이드 네이티브 연동을 위한 모듈 (빌드 시 필요)
# jnius는 런타임에 직접 import 하도록 변경하여 PC 충돌 방지

# --- CONFIGURATION ---
load_dotenv()
DATA_GO_KR_API_KEY = os.getenv("DATA_GO_KR_API_KEY")

# --- KMA COORDINATE CONVERSION ---
def dfs_xy_conv(v1, v2, mode="to_grid"):
    RE = 6371.00877
    GRID = 5.0
    SLAT1 = 30.0
    SLAT2 = 60.0
    OLON = 126.0
    OLAT = 38.0
    XO = 43
    YO = 136

    DEGRAD = math.pi / 180.0
    re = RE / GRID
    slat1 = SLAT1 * DEGRAD
    slat2 = SLAT2 * DEGRAD
    olon = OLON * DEGRAD
    olat = OLAT * DEGRAD

    sn = math.tan(math.pi * 0.25 + slat2 * 0.5) / math.tan(math.pi * 0.25 + slat1 * 0.5)
    sn = math.log(math.cos(slat1) / math.cos(slat2)) / math.log(sn)
    sf = math.tan(math.pi * 0.25 + slat1 * 0.5)
    sf = math.pow(sf, sn) * math.cos(slat1) / sn
    ro = math.tan(math.pi * 0.25 + olat * 0.5)
    ro = re * sf / math.pow(ro, sn)
    
    if mode == "to_grid":
        ra = math.tan(math.pi * 0.25 + v1 * DEGRAD * 0.5)
        ra = re * sf / math.pow(ra, sn)
        theta = v2 * DEGRAD - olon
        if theta > math.pi: theta -= 2.0 * math.pi
        if theta < -math.pi: theta += 2.0 * math.pi
        theta *= sn
        nx = math.floor(ra * math.sin(theta) + XO + 0.5)
        ny = math.floor(ro - ra * math.cos(theta) + YO + 0.5)
        return nx, ny
    return 0, 0

# --- DATA FETCHING ---
async def fetch_kma_weather(nx, ny):
    now = datetime.datetime.now()
    times = [2, 5, 8, 11, 14, 17, 20, 23]
    hour = now.hour
    base_date = now.strftime("%Y%m%d")
    base_time = "2300"
    if hour < 2:
        yesterday = now - datetime.timedelta(days=1)
        base_date = yesterday.strftime("%Y%m%d")
        base_time = "2300"
    else:
        for t in reversed(times):
            if hour >= t:
                base_time = f"{t:02d}00"
                break
    
    url = "https://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst"
    params = {
        "serviceKey": DATA_GO_KR_API_KEY,
        "numOfRows": "200",
        "dataType": "JSON",
        "base_date": base_date,
        "base_time": base_time,
        "nx": nx,
        "ny": ny
    }
    async with httpx.AsyncClient() as client:
        try:
            res = await client.get(url, params=params, timeout=10)
            items = res.json()["response"]["body"]["items"]["item"]
            data = {}
            for item in items:
                if item["category"] not in data:
                    data[item["category"]] = item["fcstValue"]
            return data
        except: return None

async def fetch_air_quality(city="서울"):
    url = "https://apis.data.go.kr/B552584/ArpltnInforInqireSvc/getCtprvnRltmMesureDnsty"
    params = {
        "serviceKey": DATA_GO_KR_API_KEY,
        "returnType": "json",
        "numOfRows": "1",
        "sidoName": city,
        "ver": "1.0"
    }
    async with httpx.AsyncClient() as client:
        try:
            res = await client.get(url, params=params, timeout=5)
            item = res.json()["response"]["body"]["items"][0]
            return {"pm10": item["pm10Value"], "grade": item["khaiGrade"]}
        except: return {"pm10": "--", "grade": "--"}

async def fetch_location_by_ip():
    # IP를 통해 사용자의 대략적인 위도/경도를 가져오는 무료 API (권한 필요 없음)
    url = "http://ip-api.com/json/"
    async with httpx.AsyncClient() as client:
        try:
            res = await client.get(url, timeout=5)
            data = res.json()
            if data["status"] == "success":
                return data["lat"], data["lon"], data.get("city", "알 수 없음")
        except:
            pass
    return 37.5665, 126.9780, "Seoul" # 실패 시 기본값 (서울)

# --- ON-DEVICE AI (GEMINI NANO) WRAPPER ---
async def get_on_device_briefing(weather_data, air_data, is_android=False):
    # 갤럭시 S24 등 안드로이드 AICore 연동 시뮬레이션
    if is_android:
        try:
            from jnius import autoclass
            # 실제 안드로이드 빌드 시 AICore 호출 로직이 들어갈 자리
            # Context = autoclass('android.content.Context')
            # AICore = autoclass('com.google.android.gms.ai.AiCore')
            return "S24 AI가 실시간 데이터를 분석 중입니다: " + f"기온 {weather_data.get('TMP')}도, 미세먼지 {air_data.get('pm10')}으로 야외 활동에 적합한 날씨입니다."
        except Exception as e:
            print("AICore 연동 실패:", e)
    
    # PC 테스트 또는 Fallback 로직
    return f"현재 기온 {weather_data.get('TMP')}°C이며, {air_data.get('pm10')} 수준의 미세먼지가 관측됩니다. 쾌적한 하루 보내세요."

async def main(page: ft.Page):
    page.title = "Weather Insight Mobile"
    page.padding = 0
    page.bgcolor = "#000000"
    page.theme_mode = "dark"
    
    # 모바일 환경에서는 window 객체 접근 시 오류가 날 수 있으므로 데스크톱만 설정
    is_mobile = page.platform in [ft.PagePlatform.ANDROID, ft.PagePlatform.IOS]
    if not is_mobile:
        page.window.width = 400
        page.window.height = 800
        page.window.resizable = False
    
    # 네이티브 GPS(flet-geolocator)는 flet build 환경에서 Unknown control 에러를 유발하므로 제거합니다.
    # 대신 IP 기반 위치 추적(fetch_location_by_ip)을 사용합니다.

    # Assets (Flet 공식 에셋 폴더 연동 방식 사용)
    # 안드로이드에서는 os.path 절대 경로가 작동하지 않으므로 ft.run(assets_dir)과 파일명만 사용해야 합니다.
    BG_IMAGE_PATH = "weather_bg.png"

    # --- UI STATE ---
    weather_icon = ft.Icon(ft.Icons.WB_SUNNY, size=100, color="amber")
    temp_text = ft.Text("--°", size=80, weight="bold")
    sky_text = ft.Text("위치 확인 중...", size=24, weight="w300")
    location_text = ft.Text("서울, 대한민국", size=16, color="white70")
    
    humidity_val = ft.Text("--%", size=18, weight="bold")
    wind_val = ft.Text("--m/s", size=18, weight="bold")
    pm10_val = ft.Text("--", size=18, weight="bold")
    
    ai_content = ft.Text("AI 브리핑을 생성하는 중...", size=15, italic=True, color="cyan100")

    def create_mobile_card(title, icon, value_control):
        return ft.Container(
            content=ft.Column([
                ft.Row([ft.Icon(icon, size=16, color="cyan"), ft.Text(title, size=12, color="white38")]),
                value_control,
            ], spacing=2),
            padding=15,
            bgcolor="white10",
            border_radius=15,
            border=ft.Border.all(1, "white10"),
            blur=ft.Blur(10, 10),
            expand=True
        )

    async def update_weather(e=None):
        if e: e.control.disabled = True
        page.update()

        try:
            # 1. 위치 획득 (IP 기반 - 권한 충돌 및 빨간불 에러 없음)
            lat, lon, city_name = await fetch_location_by_ip()
            nx, ny = dfs_xy_conv(lat, lon)
            
            # 한글 도시명 변환 (간단한 매핑)
            city_kr = "서울" if "Seoul" in city_name else "부산" if "Busan" in city_name else "인천" if "Incheon" in city_name else city_name
            location_text.value = f"현재 위치 ({city_kr})"
            
            # 2. 데이터 Fetch
            w, a = await asyncio.gather(fetch_kma_weather(nx, ny), fetch_air_quality(city_kr if city_kr in ["서울","부산","인천","대구","광주","대전","울산","경기","강원","충북","충남","전북","전남","경북","경남","제주","세종"] else "서울"))
            
            if w:
                temp_text.value = f"{w.get('TMP')}°"
                sky_dict = {"1": ft.Icons.WB_SUNNY, "3": ft.Icons.CLOUD_QUEUE, "4": ft.Icons.CLOUD}
                weather_icon.icon = sky_dict.get(w.get("SKY", "1"), ft.Icons.HELP)
                sky_text.value = "맑음" if w.get("SKY")=="1" else "흐림"
                
                humidity_val.value = f"{w.get('REH')}%"
                wind_val.value = f"{w.get('WSD')}m/s"
                pm10_val.value = a.get("pm10")
                
                # 3. 온디바이스 AI 브리핑
                ai_content.value = await get_on_device_briefing(w, a, is_mobile)
            else:
                sky_text.value = "연결 오류"
        except Exception as ex:
            ai_content.value = f"오류: {str(ex)}"
        
        if e: e.control.disabled = False
        page.update()

    # --- MOBILE LAYOUT (SINGLE COLUMN) ---
    content_stack = ft.Stack([
        ft.Image(src=BG_IMAGE_PATH, width=page.width, height=800, fit=ft.BoxFit.COVER),
        ft.Container(expand=True, bgcolor="black45"), # Overlay
        
        ft.Column([
            # Top Header
            ft.Container(
                content=ft.Row([
                    ft.Text("Weather Insight", size=20, weight="bold"),
                    ft.IconButton(ft.Icons.REFRESH, on_click=update_weather)
                ], alignment="spaceBetween"),
                padding=ft.Padding.only(left=25, right=25, top=50)
            ),
            
            # Hero Weather Section
            ft.Container(
                content=ft.Column([
                    weather_icon,
                    temp_text,
                    sky_text,
                    location_text
                ], horizontal_alignment="center", spacing=5),
                padding=30
            ),
            
            # Metrics Grid (Mobile)
            ft.Container(
                content=ft.Row([
                    create_mobile_card("습도", ft.Icons.WATER_DROP, humidity_val),
                    create_mobile_card("풍속", ft.Icons.AIR, wind_val),
                    create_mobile_card("미세먼지", ft.Icons.GRAIN, pm10_val),
                ], spacing=10),
                padding=20
            ),
            
            # AI Perspective (Mobile)
            ft.Container(
                content=ft.Column([
                    ft.Text("S24 On-Device AI Perspective", size=14, weight="bold", color="cyan200"),
                    ft.Container(
                        content=ai_content,
                        padding=20,
                        bgcolor="white10",
                        border_radius=20,
                        border=ft.Border.all(1, "white10"),
                        blur=ft.Blur(15, 15)
                    )
                ], spacing=10),
                padding=20
            )
        ], scroll=ft.ScrollMode.AUTO, expand=True)
    ], expand=True)

    page.add(content_stack)
    await update_weather()

if __name__ == "__main__":
    # 안드로이드 에셋 로드를 위해 assets_dir="assets" 필수 추가
    ft.run(main, assets_dir="assets")
