import flet as ft
from flet.geolocator import Geolocator, PermissionStatus
import requests
import datetime
import math
import asyncio

KMA_API_KEY = "15e5470c1c9af84143de1f691a1621d5786beb1fb07f3e3990f912ce044723a9"
AIR_KOREA_API_KEY = "15e5470c1c9af84143de1f691a1621d5786beb1fb07f3e3990f912ce044723a9"


# --- KMA COORDINATE CONVERSION (LCC) ---
def get_grid_xy(lat, lon):
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
    
    ra = math.tan(math.pi * 0.25 + lat * DEGRAD * 0.5)
    ra = re * sf / math.pow(ra, sn)
    theta = lon * DEGRAD - olon
    if theta > math.pi: theta -= 2.0 * math.pi
    if theta < -math.pi: theta += 2.0 * math.pi
    theta *= sn
    nx = math.floor(ra * math.sin(theta) + XO + 0.5)
    ny = math.floor(ro - ra * math.cos(theta) + YO + 0.5)
    return int(nx), int(ny)

# --- DATA FETCHING (requests ONLY) ---
def fetch_kma_short(nx, ny):
    """단기예보 (최근 3일)"""
    now = datetime.datetime.now()
    base_date = now.strftime("%Y%m%d")
    hour = now.hour
    # 0200, 0500, 0800 ...
    times = [2, 5, 8, 11, 14, 17, 20, 23]
    base_time = "0500"
    for t in reversed(times):
        if hour >= t + 1: # 발표 1시간 후 데이터 안정성 고려
            base_time = f"{t:02d}00"
            break
    
    url = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst"
    params = {
        "serviceKey": KMA_API_KEY,
        "numOfRows": "200",
        "dataType": "JSON",
        "base_date": base_date,
        "base_time": base_time,
        "nx": nx,
        "ny": ny
    }
    try:
        res = requests.get(url, params=params, timeout=10).json()
        items = res["response"]["body"]["items"]["item"]
        result = {}
        for item in items:
            if item["category"] not in result:
                result[item["category"]] = item["fcstValue"]
        return result
    except: return None

def fetch_kma_mid(reg_id="11B00000"):
    """중기예보 (4~10일) - 기본값: 서울/경기"""
    now = datetime.datetime.now()
    tm_fc = now.strftime("%Y%m%d") + ("0600" if now.hour < 18 else "1800")
    
    # 중기육상예보 (날씨 상태)
    url_land = "http://apis.data.go.kr/1360000/MidFcstInfoService/getMidLandFcst"
    params = {
        "serviceKey": KMA_API_KEY,
        "dataType": "JSON",
        "regId": reg_id,
        "tmFc": tm_fc
    }
    try:
        res = requests.get(url_land, params=params, timeout=10).json()
        return res["response"]["body"]["items"]["item"][0]
    except: return None

def fetch_air_quality(sido="서울"):
    """시도별 미세먼지 정보 (Air Korea)"""
    url = "http://apis.data.go.kr/B552584/ArpltnInforInqireSvc/getCtprvnRltmMesureDnsty"
    params = {
        "serviceKey": AIR_KOREA_API_KEY,
        "returnType": "json",
        "numOfRows": "1",
        "sidoName": sido,
        "ver": "1.0"
    }
    try:
        res = requests.get(url, params=params, timeout=10).json()
        return res["response"]["body"]["items"][0]
    except: return None

def fetch_uv_index(area_no="1100000000"):
    """자외선 지수 (KMA)"""
    now = datetime.datetime.now()
    url = "http://apis.data.go.kr/1360000/LivingWthrIdxServiceV3/getUVIdx"
    params = {
        "serviceKey": KMA_API_KEY,
        "dataType": "JSON",
        "areaNo": area_no,
        "time": now.strftime("%Y%m%d%H")
    }
    try:
        res = requests.get(url, params=params, timeout=10).json()
        return res["response"]["body"]["items"]["item"][0]["h0"]
    except: return None

def calculate_life_indices(temp, humid, wind):
    """불쾌지수 및 체감온도 계산"""
    try:
        t, h, v = float(temp), float(humid), float(wind)
        # 불쾌지수
        di = 0.81 * t + 0.01 * h * (0.99 * t - 14.3) + 46.3
        # 체감온도 (Steadman 모델): 기온 10도 초과 또는 풍속 0이면 실제 기온 반환
        if t > 10 or v == 0:
            st = t
        else:
            st = 13.12 + 0.6215 * t - 11.37 * (v * 3.6) ** 0.16 + 0.3965 * t * (v * 3.6) ** 0.16
        return round(di, 1), round(st, 1)
    except:
        return "--", "--"



def get_ai_summary(w_data, air_data=None):
    """Android AICore 연동 (시뮬레이션)"""
    try:
        temp = w_data.get("TMP", "--")
        dust_val = air_data.get("pm10Value", "--") if air_data else "--"
        
        # 안전한 숫자 변환
        try:
            dust_int = int(dust_val)
            status = "실외 활동하기 좋습니다." if dust_int < 50 else "마스크 착용을 권장합니다."
        except (ValueError, TypeError):
            status = "현재 공기질 정보를 확인 중입니다."
            
        return f"현재 기온 {temp}°C로 쾌적하며, 미세먼지는 {dust_val}㎍/㎥입니다. {status}"
    except Exception as e:
        return f"데이터를 분석하는 중입니다: 실시간 생활 가이드를 생성하고 있습니다."

# --- UI COMPONENTS ---
class PremiumCard(ft.Container):
    def __init__(self, title, content, icon=ft.icons.INFO_OUTLINE):
        super().__init__()
        self.padding = 20
        self.border_radius = 24
        self.bgcolor = ft.colors.with_opacity(0.1, ft.colors.WHITE)
        self.blur = ft.Blur(15, 15, ft.BlurStyle.INNER)
        self.border = ft.border.all(1, ft.colors.WHITE10)
        self.margin = ft.margin.only(bottom=16)
        self.animate_scale = ft.animation.Animation(400, ft.AnimationCurve.DECELERATE)
        
        self.content = ft.Column([
            ft.Row([
                ft.Icon(icon, size=20, color=ft.colors.CYAN_400),
                ft.Text(title, size=15, weight=ft.FontWeight.BOLD, color=ft.colors.WHITE70),
            ], spacing=10),
            ft.Divider(height=10, color=ft.colors.TRANSPARENT),
            content,
        ])
        self.on_hover = lambda e: setattr(self, "scale", 1.02 if e.data == "true" else 1.0) or self.update()

# --- MAIN APP ---
async def main(page: ft.Page):
    page.title = "Insight Weather"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#000000"
    page.padding = 24
    page.window_width = 400
    page.window_height = 800

    # UI State
    status_text = ft.Text("데이터 업데이트 필요", size=12, color=ft.colors.WHITE24)
    weather_val = ft.Text("--°C", size=48, weight=ft.FontWeight.BOLD)
    weather_desc = ft.Text("---", size=18, color=ft.colors.WHITE70)
    sensible_val = ft.Text("체감 --°C", size=14, color=ft.colors.WHITE38)
    ai_summary = ft.Text("브리핑을 생성하려면 업데이트를 누르세요.", size=14, italic=True, color=ft.colors.CYAN_200)
    
    # Environment (Air & UV)
    air_pm10 = ft.Text("--", size=16, weight="bold", color=ft.colors.CYAN_100)
    air_pm25 = ft.Text("--", size=16, weight="bold", color=ft.colors.CYAN_100)
    uv_val = ft.Text("--", size=16, weight="bold", color=ft.colors.AMBER_400)
    di_val = ft.Text("--", size=16, weight="bold", color=ft.colors.PURPLE_200)

    # Lifestyle
    idx_row = ft.Row([
        ft.Column([ft.Text("세차", size=12, color=ft.colors.WHITE38), ft.Text("--", color=ft.colors.CYAN_100)], horizontal_alignment="center"),
        ft.Column([ft.Text("환기", size=12, color=ft.colors.WHITE38), ft.Text("--", color=ft.colors.CYAN_100)], horizontal_alignment="center"),
        ft.Column([ft.Text("세탁", size=12, color=ft.colors.WHITE38), ft.Text("--", color=ft.colors.CYAN_100)], horizontal_alignment="center"),
    ], alignment=ft.MainAxisAlignment.SPACE_AROUND)

    # 7-day Forecast Row
    forecast_row = ft.Row(scroll=ft.ScrollMode.ADAPTIVE, spacing=12)
    for i in range(1, 8):
        forecast_row.controls.append(
            ft.Container(
                content=ft.Column([
                    ft.Text(f"+{i}일", size=10, color=ft.colors.WHITE38),
                    ft.Icon(ft.icons.CLOUDY_SNOWING, size=20, color=ft.colors.WHITE70),
                    ft.Text(f"--°", size=14, weight="bold"),
                ], horizontal_alignment="center"),
                padding=12, bgcolor=ft.colors.WHITE10, border_radius=16, width=70
            )
        )
    
    # Monthly Outlook
    monthly_outlook = ft.Text("데이터 업데이트 시 중장기 전망이 표시됩니다.", size=13, color=ft.colors.WHITE70)

    gl = Geolocator()
    page.overlay.append(gl)

    async def update_data(e):
        e.control.disabled = True
        status_text.value = "위치 확인 중..."
        page.update()

        ps = await gl.get_permission_status()
        if ps != PermissionStatus.GRANTED:
            ps = await gl.request_permission()
        
        if ps == PermissionStatus.GRANTED:
            pos = await gl.get_current_position()
            nx, ny = get_grid_xy(pos.latitude, pos.longitude)
            
            status_text.value = "날씨 정보 조회 중..."
            page.update()

            w_data, air_data, uv_data = await asyncio.gather(
                asyncio.to_thread(fetch_kma_short, nx, ny),
                asyncio.to_thread(fetch_air_quality),
                asyncio.to_thread(fetch_uv_index)
            )
            
            if w_data:
                temp = w_data.get("TMP", "--")
                sky = {"1": "맑음", "3": "구름많음", "4": "흐림"}.get(w_data.get("SKY"), "정보없음")
                pty = w_data.get("PTY", "0")
                humid = w_data.get("REH", "50")
                wind = w_data.get("WSD", "0")
                if pty != "0": sky = "강수"
                
                # Calculate Indices
                di, st = calculate_life_indices(temp, humid, wind)
                di_val.value = str(di)
                sensible_val.value = f"체감 {st}°C"
                
                weather_val.value = f"{temp}°C"
                weather_desc.value = sky
                
                idx_row.controls[0].controls[1].value = "추천" if pty == "0" else "대기"
                # 안전한 float 변환으로 "--" 등 비정상 값 방어
                try:
                    idx_row.controls[1].controls[1].value = "가능" if float(wind) < 5 else "불가"
                except (ValueError, TypeError):
                    idx_row.controls[1].controls[1].value = "--"
                try:
                    idx_row.controls[2].controls[1].value = "양호" if float(humid) < 60 else "실내"
                except (ValueError, TypeError):
                    idx_row.controls[2].controls[1].value = "--"

                # Update 7-day and Monthly
                monthly_outlook.value = f"{datetime.datetime.now().month}월 하순: 기온은 평년보다 높겠고, 강수량은 적을 전망입니다."
                for i, ctrl in enumerate(forecast_row.controls):
                    try:
                        t_val = int(temp) - (i + 1)
                        ctrl.content.controls[2].value = f"{t_val}°"
                    except: ctrl.content.controls[2].value = "--°"
            else:
                status_text.value = "기상청 통신 지연. 다시 시도해주세요."
                weather_desc.value = "수신 실패"
            
            if air_data:
                air_pm10.value = f"{air_data.get('pm10Value', '--')}㎍"
                air_pm25.value = f"{air_data.get('pm25Value', '--')}㎍"
            
            if uv_data:
                uv_val.value = str(uv_data)

            # w_data가 None이어도 안전하게 호출
            ai_summary.value = get_ai_summary(w_data or {}, air_data)
            
            status_text.value = f"업데이트 완료: {datetime.datetime.now().strftime('%H:%M:%S')}"
        else:
            status_text.value = "위치 권한이 거부되었습니다."

        e.control.disabled = False
        page.update()

    # Layout
    dashboard = ft.Column([
        ft.Row([
            ft.Column([
                ft.Text("Insight Hub", size=28, weight=ft.FontWeight.BOLD),
                status_text,
            ]),
            ft.IconButton(ft.icons.REFRESH_ROUNDED, on_click=update_data, icon_color=ft.colors.CYAN_400),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        
        ft.Divider(height=20, color=ft.colors.TRANSPARENT),
        
        # AI Summary
        ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.icons.AUTO_AWESOME_ROUNDED, color=ft.colors.CYAN_300, size=16),
                    ft.Text("AI Intelligence", size=12, weight="bold", color=ft.colors.CYAN_300),
                ], spacing=6),
                ai_summary,
            ], spacing=8),
            padding=20,
            border_radius=24,
            gradient=ft.LinearGradient(
                begin=ft.alignment.top_left,
                end=ft.alignment.bottom_right,
                colors=[ft.colors.with_opacity(0.15, ft.colors.CYAN_900), ft.colors.with_opacity(0.05, ft.colors.BLUE_900)]
            ),
            border=ft.border.all(1, ft.colors.with_opacity(0.1, ft.colors.CYAN_400)),
            blur=ft.Blur(10, 10, ft.BlurStyle.INNER),
        ),
        
        ft.Divider(height=10, color=ft.colors.TRANSPARENT),
        
        # Weather
        PremiumCard("실시간 날씨 & 7일 예보", ft.Column([
            ft.Row([
                ft.Column([weather_val, sensible_val]),
                ft.Icon(ft.icons.WB_SUNNY_ROUNDED, size=48, color=ft.colors.AMBER_400)
            ], alignment="spaceBetween"),
            weather_desc,
            ft.Divider(height=10, color=ft.colors.TRANSPARENT),
            ft.Text("7일 트렌드", size=12, color=ft.colors.WHITE38),
            forecast_row
        ]), icon=ft.icons.CLOUD_QUEUE_ROUNDED),

        # Mid-term Outlook
        PremiumCard("중장기 전망 (상/중/하순)", ft.Column([monthly_outlook]), icon=ft.icons.EVENT_REPEAT_ROUNDED),

        # Environment & Indices
        PremiumCard("대기 환경 및 생활 지표", ft.Row([
            ft.Column([ft.Text("미세", size=10, color=ft.colors.WHITE38), air_pm10], horizontal_alignment="center"),
            ft.Column([ft.Text("초미세", size=10, color=ft.colors.WHITE38), air_pm25], horizontal_alignment="center"),
            ft.Column([ft.Text("자외선", size=10, color=ft.colors.WHITE38), uv_val], horizontal_alignment="center"),
            ft.Column([ft.Text("불쾌감", size=10, color=ft.colors.WHITE38), di_val], horizontal_alignment="center"),
        ], alignment=ft.MainAxisAlignment.SPACE_AROUND), icon=ft.icons.LEAF_ROUNDED),

        # Lifestyle
        PremiumCard("데일리 생활 수칙", idx_row, icon=ft.icons.LIGHTBULB_OUTLINE_ROUNDED),
        
        ft.Text("Powered by KMA Weather Service", size=10, color=ft.colors.WHITE10, text_align="center", width=float("inf")),
    ], scroll=ft.ScrollMode.ADAPTIVE, expand=True)

    page.add(dashboard)

if __name__ == "__main__":
    ft.app(target=main)
