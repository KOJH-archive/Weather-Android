import flet as ft
import requests
import datetime
import math

# --- CONFIGURATION ---
DATA_GO_KR_API_KEY = "15e5470c1c9af84143de1f691a1621d5786beb1fb07f3e3990f912ce044723a9"

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
def fetch_kma_weather(nx, ny):
    now = datetime.datetime.now()
    times = [2, 5, 8, 11, 14, 17, 20, 23]
    hour = now.hour
    base_date = now.strftime("%Y%m%d")
    base_time = "2300"  # 기본값: 전날 23시
    if hour < 2:
        # 자정~새벽 2시: 전날 23시 데이터 사용
        yesterday = now - datetime.timedelta(days=1)
        base_date = yesterday.strftime("%Y%m%d")
        base_time = "2300"
    else:
        for t in reversed(times):
            if hour >= t:
                base_time = f"{t:02d}00"
                break
    
    url = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst"
    params = {
        "serviceKey": DATA_GO_KR_API_KEY,
        "numOfRows": "200",
        "pageNo": "1",
        "dataType": "JSON",
        "base_date": base_date,
        "base_time": base_time,
        "nx": nx,
        "ny": ny
    }
    try:
        res = requests.get(url, params=params, timeout=10)
        items = res.json()["response"]["body"]["items"]["item"]
        data = {}
        for item in items:
            if item["category"] not in data:
                data[item["category"]] = item["fcstValue"]
        return data
    except:
        return None

def fetch_air_quality(city="서울"):
    url = "http://apis.data.go.kr/B552584/ArpltnInforInqireSvc/getCtprvnRltmMesureDnsty"
    params = {
        "serviceKey": DATA_GO_KR_API_KEY,
        "returnType": "json",
        "numOfRows": "1",
        "pageNo": "1",
        "sidoName": city,
        "ver": "1.0"
    }
    try:
        res = requests.get(url, params=params, timeout=5)
        item = res.json()["response"]["body"]["items"][0]
        return {
            "pm10": item["pm10Value"],
            "pm25": item["pm25Value"],
            "grade": item["khaiGrade"]
        }
    except:
        return {"pm10": "--", "pm25": "--", "grade": "--"}

async def main(page: ft.Page):
    page.title = "Weather Insight Premium"
    page.theme_mode = "dark"
    page.bgcolor = "#000000"
    page.padding = 0
    page.window.width = 1000
    page.window.height = 700
    page.window.resizable = False

    # 이미지 경로 (생성된 이미지 사용)
    BG_IMAGE_PATH = r"C:\Users\jongh\.gemini\antigravity\brain\5a0c5913-812e-4b37-9854-3bd0c7ec11f7\weather_bg_dark_1777123223814.png"

    # --- UI COMPONENTS ---
    weather_icon = ft.Icon(ft.Icons.WB_SUNNY, size=150, color="amber")
    temp_text = ft.Text("--°", size=100, weight="bold")
    sky_text = ft.Text("날씨 정보를 불러오는 중...", size=30, weight="w300")
    
    # Details Card Components
    humidity_val = ft.Text("--%", size=20, weight="bold")
    wind_val = ft.Text("--m/s", size=20, weight="bold")
    pm10_val = ft.Text("--", size=20, weight="bold")
    pm_grade_text = ft.Text("--", size=14, color="white70")
    
    ai_content = ft.Text(
        "인사이트 업데이트 버튼을 눌러 AI 브리핑을 생성하세요.",
        size=16,
        italic=True,
        color="white70",
        selectable=True
    )

    last_update = ft.Text("최근 업데이트: --:--", size=12, color="white30")

    def create_metric_card(title, icon, value_control, sub_text=None):
        content_items = [
            ft.Row([ft.Icon(icon, size=18, color="cyan"), ft.Text(title, size=14, color="white70")]),
            value_control,
        ]
        if sub_text:
            content_items.append(sub_text)
            
        return ft.Container(
            content=ft.Column(content_items, spacing=5),
            padding=20,
            bgcolor="white10",
            border_radius=20,
            border=ft.Border.all(1, "white10"),
            blur=ft.Blur(10, 10),
            expand=True
        )

    async def update_data(e=None):
        if e: e.control.disabled = True
        page.update()
        
        try:
            nx, ny = dfs_xy_conv(37.5665, 126.9780)
            w = fetch_kma_weather(nx, ny)
            a = fetch_air_quality("서울")
            
            if w:
                temp_text.value = f"{w.get('TMP')}°"
                sky_dict = {
                    "1": {"text": "맑음", "icon": ft.Icons.WB_SUNNY, "color": "amber"},
                    "3": {"text": "구름많음", "icon": ft.Icons.CLOUD_QUEUE, "color": "blueGrey100"},
                    "4": {"text": "흐림", "icon": ft.Icons.CLOUD, "color": "blueGrey300"}
                }
                sky_data = sky_dict.get(w.get("SKY", "1"), {"text": "정보없음", "icon": ft.Icons.HELP_OUTLINE, "color": "white"})
                if w.get("PTY", "0") != "0":
                    sky_data = {"text": "비/눈", "icon": ft.Icons.BEACH_ACCESS, "color": "lightBlue200"}
                
                sky_text.value = sky_data["text"]
                weather_icon.icon = sky_data["icon"]
                weather_icon.color = sky_data["color"]
                
                humidity_val.value = f"{w.get('REH')}%"
                wind_val.value = f"{w.get('WSD')}m/s"
                
                pm10_val.value = a.get('pm10')
                pm_grade = "좋음" if a.get("grade") == "1" else "보통" if a.get("grade") == "2" else "나쁨"
                pm_grade_text.value = f"상태: {pm_grade}"
                pm_grade_text.color = "lightGreen" if pm_grade == "좋음" else "amber" if pm_grade == "보통" else "redAccent"
                
                ai_content.value = f"오늘 서울은 최고 {w.get('TMP')}°C까지 올라가며, 전반적으로 {sky_data['text']} 날씨가 이어질 것으로 보입니다. 습도는 {w.get('REH')}%로 적당하며, 야외 활동 시 {pm_grade} 수준의 미세먼지 농도를 참고하시기 바랍니다."
                
                now = datetime.datetime.now()
                last_update.value = f"최근 업데이트: {now.strftime('%H:%M:%S')}"
            else:
                sky_text.value = "데이터를 불러올 수 없습니다."
        except Exception as ex:
            ai_content.value = f"오류 발생: {str(ex)}"
        
        if e: e.control.disabled = False
        page.update()

    # --- LAYOUT ---
    
    # Left Panel: Hero Weather
    left_panel = ft.Container(
        content=ft.Column([
            ft.Text("Weather Insight", size=24, weight="bold", color="white"),
            ft.Container(height=50),
            weather_icon,
            temp_text,
            sky_text,
            ft.Container(height=20),
            ft.Text("Seoul, South Korea", size=18, color="white70"),
        ], horizontal_alignment="center", spacing=0),
        padding=50,
        width=400,
    )

    # Right Panel: Details Dashboard
    right_panel = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Text("Dashboard", size=20, weight="bold"),
                ft.Row([
                    last_update,
                    ft.IconButton(icon=ft.Icons.REFRESH, on_click=update_data, icon_color="white70")
                ], spacing=10)
            ], alignment="spaceBetween"),
            ft.Divider(height=20, color="white10"),
            
            # Metrics Grid
            ft.Row([
                create_metric_card("Humidity", ft.Icons.WATER_DROP, humidity_val),
                create_metric_card("Wind Speed", ft.Icons.AIR, wind_val),
                create_metric_card("Air Quality", ft.Icons.GRAIN, pm10_val, pm_grade_text),
            ], spacing=20),
            
            ft.Container(height=20),
            
            # AI Briefing Section
            ft.Text("AI Perspective", size=18, weight="bold", color="cyan200"),
            ft.Container(
                content=ai_content,
                padding=25,
                bgcolor="white10",
                border_radius=20,
                border=ft.Border.all(1, "white10"),
                blur=ft.Blur(10, 10),
                expand=True
            ),
            
            ft.Container(
                content=ft.Text("Powered by KMA & AICore", size=10, color="white24"),
                alignment=ft.Alignment.CENTER_RIGHT,
                margin=ft.Margin.only(top=10)
            )
        ], spacing=10),
        padding=40,
        expand=True,
    )

    # Main Stack: Background + Content
    page.add(
        ft.Stack([
            # Background Image
            ft.Image(
                src=BG_IMAGE_PATH,
                width=1000,
                height=700,
                fit=ft.BoxFit.COVER,
            ),
            # Dark Overlay for readability
            ft.Container(
                width=1000,
                height=700,
                bgcolor="black45",
            ),
            # Main Content Row
            ft.Row([
                left_panel,
                right_panel,
            ], spacing=0, width=1000, height=700)
        ], width=1000, height=700)
    )

    # Initial Fetch
    await update_data()

if __name__ == "__main__":
    ft.run(main)
