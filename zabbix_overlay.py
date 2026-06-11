import sys
import json
import os
import winreg
import requests
import urllib3
import hashlib
import ctypes
import logging 
import traceback 
import math
import random
from logging.handlers import RotatingFileHandler 
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QMenu, QAction, 
                             QListWidget, QLabel, QPushButton, QHBoxLayout, QMessageBox, 
                             QListWidgetItem, QDialog, QFormLayout, QDialogButtonBox, 
                             QPlainTextEdit, QComboBox, QCheckBox, QFrame, QBoxLayout,
                             QTabWidget, QTextBrowser, QSystemTrayIcon, QWidgetAction, QSizePolicy, QGridLayout, QSizeGrip, QGraphicsDropShadowEffect)
from PyQt5.QtCore import Qt, QPoint, QVariantAnimation, QThread, pyqtSignal, QTimer, QEvent, QSize, QSharedMemory, QPointF
from PyQt5.QtGui import QPainter, QColor, QBrush, QFont, QPen, QFontMetrics, QFontDatabase, QIcon, QPixmap, QPolygonF

# HTTPS 사설 인증서 경고 숨기기
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_build_hash(): 
    try:
        filepath = sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(__file__)
        hasher = hashlib.md5()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        return hasher.hexdigest()[:5].upper()
    except Exception:
        return "DEV01"

APP_VERSION = "v1.0.6" 
BUILD_HASH = get_build_hash() 
shared_mem = None

# ==========================================
# 1. 경로 설정 및 config 폴더 자동 생성 로직
# ==========================================
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable) 
    BUNDLE_DIR = sys._MEIPASS                  
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    BUNDLE_DIR = BASE_DIR

CONFIG_DIR = os.path.join(BASE_DIR, "config")
if not os.path.exists(CONFIG_DIR):
    os.makedirs(CONFIG_DIR)

LANG_DIR = os.path.join(BASE_DIR, "lang")
if not os.path.exists(LANG_DIR):
    os.makedirs(LANG_DIR)

# 다국어 번역 클래스
class Translator:
    def __init__(self):
        self.lang = "ko"
        self.texts = {}

    def load_language(self, lang_code):
        self.lang = lang_code
        lang_file = os.path.join(LANG_DIR, f"{lang_code}.json")
        
        # 파일이 없으면 기본 생성
        if not os.path.exists(lang_file):
            self._create_default_lang_files()
            
        try:
            with open(lang_file, 'r', encoding='utf-8') as f:
                self.texts = json.load(f)
        except Exception as e:
            logger.error(tr_log(f"언어 파일 로드 실패 ({lang_code}): {e}", f"Failed to load lang file ({lang_code}): {e}"))
            self.texts = {}

    def get(self, key, default_text=""):
        # 키값이 없으면 default_text를 반환하고, 그것도 없으면 key 자체를 반환
        return self.texts.get(key, default_text if default_text else key)

    def _create_default_lang_files(self):
        # 한국어 기본 (ko.json)
        ko_data = {
            "msg_already_running": "이미 프로그램이 실행되어 있습니다.",
            "msg_init_setup": "초기 설정 안내",
            "msg_config_created": "설정 파일이 새로 생성되었습니다.\n위치: {path}\n\n프로그램을 종료합니다. 메모장 등으로 파일을 열어\n실제 Zabbix 서버 주소와 계정(또는 API 토큰) 정보로 수정한 후 다시 실행해 주세요.",
            "msg_need_config_change": "설정 변경 필요",
            "msg_zabbix_default": "Zabbix 서버 주소가 초기값 그대로입니다.\n\n{path}\n파일을 열어 실제 서버 정보로 수정해 주세요.",
            "msg_config_error": "설정 파일 오류",
            "msg_config_corrupted": "설정 파일 형식이 손상되어 샘플 파일로 초기화했습니다.\n\n에러 내용: {err}\n\n프로그램을 종료합니다. 설정 파일을 다시 작성해 주세요.",
            "msg_login_failed": "로그인 실패",
            "msg_dns_error": "서버 주소를 찾을 수 없습니다 (DNS 오류)",
            "msg_conn_refused": "서버에서 연결을 거부했습니다",
            "msg_conn_failed": "서버 연결에 실패했습니다",
            "msg_timeout": "서버 응답 시간 초과",
            "msg_unknown_error": "알 수 없는 오류 발생",
            "msg_no_active_issues": "현재 활성화된 장애 없음",
            "msg_api_request_error": "API 요청 오류",
            "msg_no_issues": "✅ 현재 발생한 미해결 내역이 없습니다.",
            "msg_refreshing": "⏳ 새로고침 중...",
            "msg_no_change": "변경할 내용이 없습니다.",
            "msg_update_success": "장애가 업데이트되었습니다.",
            "msg_update_fail": "업데이트 실패:\n{err}",
            "msg_manual_close_denied": "Zabbix 설정에서 수동 클로즈가 허용되지 않은 장애입니다.",
            "msg_no_identifier": "이력을 조회할 수 있는 식별자가 없습니다.",
            "msg_no_item_info": "연결된 아이템 정보를 찾을 수 없습니다.",
            "msg_no_history_data": "[{item_name}] 아이템의 해당 기간({time_period}) 내 데이터가 없습니다.",
            "msg_error_occurred": "오류 발생: {err}",
            "msg_no_messages": "메시지가 없습니다.",
            "msg_log_refresh_fail": "로그 새로고침 실패:\n{err}",
            "msg_no_recent_alerts": "최근 발생한 알림이 없습니다.",
            "msg_no_matching_alerts": "선택한 조건({filter})에 해당하는 알림이 없습니다.",
            "msg_debug_mode_on": "디버그 모드가 켜졌습니다.\nconfig 폴더에 debug.log 파일이 생성됩니다.",
            "msg_server_restored": "✅ Zabbix 서버 연결이 복구되었습니다.",
            "msg_conn_error": "🚨 연결 오류: {err}",
            "sev_disaster": "심각",
            "sev_high": "중증",
            "sev_average": "경미",
            "sev_warning": "경고",
            "sev_info": "정보",
            "sev_not_cls": "미정",
            "sev_system": "기타 (시스템)",
            "sev_no_change": "변경 안함",
            "menu_history": "🕒 최근 알림 히스토리",
            "menu_resize": "크기 조절",
            "menu_always_top": "항상 위 표시",
            "menu_autostart": "부팅 시 자동실행",
            "menu_theme": "모양",
            "theme_circle_1": "원형 (1줄)",
            "theme_circle_2": "원형 (2줄)",
            "theme_rect_1": "사각형 (1줄)",
            "theme_rect_2": "사각형 (2줄)",
            "menu_layout": "배치 방향",
            "layout_vert": "세로 배치",
            "layout_hori": "가로 배치",
            "menu_noti_update": "업데이트 알림 표시 (메시지/심각도 변경)",
            "menu_noti_duration": "알림 유지 시간",
            "noti_off": "알림 끄기",
            "noti_3s": "3초",
            "noti_5s": "5초",
            "noti_7s": "7초 (권장)",
            "noti_10s": "10초",
            "noti_15s": "15초",
            "noti_30s": "30초",
            "noti_manual": "수동 종료 시까지",
            "menu_noti_pos": "알림 위치",
            "pos_br": "우측 하단", "pos_bl": "좌측 하단", "pos_tr": "우측 상단", "pos_tl": "좌측 상단",
            "menu_refresh_int": "새로고침 주기",
            "ref_3s": "3초 (매우 빠름)",
            "ref_5s": "5초 (권장)",
            "ref_10s": "10초",
            "ref_30s": "30초",
            "menu_items_page": "페이지당 표시 개수",
            "item_count": "{cnt}개",
            "menu_lang": "🌐 언어 (Language)",
            "lang_ko": "한국어",
            "lang_en": "English",
            "menu_color_mode": "🎨 컬러 모드 (Color Mode)",
            "mode_dark": "다크 모드 (Dark)",
            "mode_light": "라이트 모드 (Light)",
            "menu_debug": "디버그 모드 (로그 기록)",
            "menu_exit": "프로그램 종료",
            "btn_close": "닫기",
            "btn_refresh": "🔄 새로고침",
            "tab_update": "업데이트",
            "tab_history": "히스토리",
            "tab_log": "메시지 로그",
            "lbl_issue": "이슈",
            "lbl_message": "메시지",
            "lbl_severity": "심각도",
            "lbl_ack": "인지 상태",
            "lbl_close": "장애 클로즈",
            "lbl_occurred": "발생:",
            "title_issue_info": "장애 정보",
            "title_history": "최근 알림 히스토리",
            "title_realtime_history": "🕒 실시간 알림 내역",
            "filter_all": "전체보기",
            "lbl_list": "리스트",
            "lbl_resolved": "복구",
            "lbl_user_msg": "사용자 메시지 ({cnt})",
            "time_1m": "1분", "time_3m": "3분", "time_5m": "5분", "time_10m": "10분", "time_15m": "15분",
            "time_30m": "30분", "time_1h": "1시간", "time_3h": "3시간", "time_6h": "6시간",
            "time_9h": "9시간", "time_12h": "12시간", "time_24h": "24시간",
            "title_run_guide": "실행 안내",
            "title_notice": "안내",
            "title_complete": "완료",
            "title_error": "오류",
            "title_debug_mode": "디버그 모드",
            "menu_clear_all": "🧹 알림 일괄 삭제",
            "lbl_loading_data": "데이터를 불러오는 중입니다...",
            "msg_update_failed_title": "❌ 업데이트 실패",
            "msg_http_error": "HTTP {code} 오류 발생",
            "lbl_unknown_item": "알 수 없는 아이템",
            "lbl_unknown_user": "알 수 없는 사용자 {uid}",
            "btn_ok": "확인",
            "btn_cancel": "취소"
        }
        # 영어 기본 (en.json)
        en_data = {
            "msg_already_running": "Program is already running.",
            "msg_init_setup": "Initial Setup Guide",
            "msg_config_created": "Configuration file has been created.\nPath: {path}\n\nProgram will exit. Please open the file, configure your Zabbix server URL and credentials, and run again.",
            "msg_need_config_change": "Configuration Change Required",
            "msg_zabbix_default": "Zabbix server URL is still default.\n\nPlease edit {path} and set your real server info.",
            "msg_config_error": "Config File Error",
            "msg_config_corrupted": "Config file corrupted and reset to default.\n\nError: {err}\n\nProgram will exit.",
            "msg_login_failed": "Login failed",
            "msg_dns_error": "Server address not found (DNS Error)",
            "msg_conn_refused": "Connection refused by server",
            "msg_conn_failed": "Failed to connect to server",
            "msg_timeout": "Server response timeout",
            "msg_unknown_error": "Unknown error occurred",
            "msg_no_active_issues": "No active issues currently",
            "msg_api_request_error": "API request error",
            "msg_no_issues": "✅ No unresolved issues currently.",
            "msg_refreshing": "⏳ Refreshing...",
            "msg_no_change": "No changes to apply.",
            "msg_update_success": "Issue has been updated.",
            "msg_update_fail": "Update failed:\n{err}",
            "msg_manual_close_denied": "Manual close is not allowed for this issue in Zabbix settings.",
            "msg_no_identifier": "No identifier available to fetch history.",
            "msg_no_item_info": "Could not find linked item information.",
            "msg_no_history_data": "No data found for item [{item_name}] in the specified period ({time_period}).",
            "msg_error_occurred": "Error occurred: {err}",
            "msg_no_messages": "No messages.",
            "msg_log_refresh_fail": "Failed to refresh log:\n{err}",
            "msg_no_recent_alerts": "No recent alerts.",
            "msg_no_matching_alerts": "No alerts found matching the condition ({filter}).",
            "msg_debug_mode_on": "Debug mode is ON.\ndebug.log file will be created in the config folder.",
            "msg_server_restored": "✅ Zabbix server connection restored.",
            "msg_conn_error": "🚨 Connection Error: {err}",
            "sev_disaster": "Disaster",
            "sev_high": "High",
            "sev_average": "Average",
            "sev_warning": "Warning",
            "sev_info": "Info",
            "sev_not_cls": "Unknown",
            "sev_system": "System",
            "sev_no_change": "No change",
            "menu_history": "🕒 Recent Alert History",
            "menu_resize": "Resize",
            "menu_always_top": "Always on Top",
            "menu_autostart": "Run at Startup",
            "menu_theme": "Theme",
            "theme_circle_1": "Circle (1 Row)",
            "theme_circle_2": "Circle (2 Rows)",
            "theme_rect_1": "Rectangle (1 Row)",
            "theme_rect_2": "Rectangle (2 Rows)",
            "menu_layout": "Layout Direction",
            "layout_vert": "Vertical",
            "layout_hori": "Horizontal",
            "menu_noti_update": "Show Update Alerts",
            "menu_noti_duration": "Notification Duration",
            "noti_off": "Off",
            "noti_3s": "3s",
            "noti_5s": "5s",
            "noti_7s": "7s (Recommended)",
            "noti_10s": "10s",
            "noti_15s": "15s",
            "noti_30s": "30s",
            "noti_manual": "Until manual close",
            "menu_noti_pos": "Notification Position",
            "pos_br": "Bottom Right", "pos_bl": "Bottom Left", "pos_tr": "Top Right", "pos_tl": "Top Left",
            "menu_refresh_int": "Refresh Interval",
            "ref_3s": "3s (Very Fast)",
            "ref_5s": "5s (Recommended)",
            "ref_10s": "10s",
            "ref_30s": "30s",
            "menu_items_page": "Items per Page",
            "item_count": "{cnt} items",
            "menu_lang": "🌐 Language",
            "lang_ko": "Korean (한국어)",
            "lang_en": "English",
            "menu_color_mode": "🎨 Color Mode",
            "mode_dark": "Dark Mode",
            "mode_light": "Light Mode",
            "menu_debug": "Debug Mode",
            "menu_exit": "Exit Program",
            "btn_close": "Close",
            "btn_refresh": "🔄 Refresh",
            "tab_update": "Update",
            "tab_history": "History",
            "tab_log": "Message Log",
            "lbl_issue": "Issue",
            "lbl_message": "Message",
            "lbl_severity": "Severity",
            "lbl_ack": "Acknowledge",
            "lbl_close": "Close Problem",
            "lbl_occurred": "Occurred:",
            "title_issue_info": "Issue Information",
            "title_history": "Recent Alert History",
            "title_realtime_history": "🕒 Real-time Alerts",
            "filter_all": "Show All",
            "lbl_list": "List",
            "lbl_resolved": "Resolved",
            "lbl_user_msg": "User Messages ({cnt})",
            "time_1m": "1m", "time_3m": "3m", "time_5m": "5m", "time_10m": "10m", "time_15m": "15m",
            "time_30m": "30m", "time_1h": "1h", "time_3h": "3h", "time_6h": "6h",
            "time_9h": "9h", "time_12h": "12h", "time_24h": "24h",
            "title_run_guide": "Execution Guide",
            "title_notice": "Notice",
            "title_complete": "Complete",
            "title_error": "Error",
            "title_debug_mode": "Debug Mode",
            "menu_clear_all": "🧹 Clear All Alerts",
            "lbl_loading_data": "Loading data...",
            "msg_update_failed_title": "❌ Update Failed",
            "msg_http_error": "HTTP {code} Error",
            "lbl_unknown_item": "Unknown Item",
            "lbl_unknown_user": "Unknown User {uid}",
            "btn_ok": "OK",
            "btn_cancel": "Cancel"
        }
        with open(os.path.join(LANG_DIR, "ko.json"), 'w', encoding='utf-8') as f:
            json.dump(ko_data, f, indent=4, ensure_ascii=False)
        with open(os.path.join(LANG_DIR, "en.json"), 'w', encoding='utf-8') as f:
            json.dump(en_data, f, indent=4, ensure_ascii=False)

# 전역에서 쉽게 쓸 수 있도록 짧은 함수(tr)로 처리...
_translator = Translator()

def tr(key, default_text=""):
    return _translator.get(key, default_text)

# 디버그 로그 전용 다국어 함수 (한국어일 때만 한글, 그 외 모든 언어는 영어 고정)
def tr_log(ko_text, en_text):
    return ko_text if _translator.lang == "ko" else en_text

# OK 버튼 번역 및 커스텀 아이콘으로 적용하는 알림창 함수
def custom_msgbox(icon, title, text, parent=None):
    msg = QMessageBox(icon, title, text, QMessageBox.Ok, parent)
    ok_button = msg.button(QMessageBox.Ok)
    if ok_button:
        ok_button.setText(tr("btn_ok", "확인"))
        ok_button.setCursor(Qt.PointingHandCursor)
    msg.exec_()

LOG_FILE = os.path.join(CONFIG_DIR, "debug.log")
logger = logging.getLogger("ZabbixWidget")
handler = RotatingFileHandler(LOG_FILE, maxBytes=5*1024*1024, backupCount=2, encoding='utf-8')
formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
handler.setFormatter(formatter)
logger.addHandler(handler)

def apply_debug_level(is_debug):
    logger.setLevel(logging.DEBUG if is_debug else logging.WARNING)
    if is_debug:
        logger.debug(tr_log("=== 디버그 모드가 활성화되었습니다 ===", "=== Debug mode activated ==="))

CONFIG_FILE = os.path.join(CONFIG_DIR, "zabbix_overlay_config.json")
REG_APP_NAME = "ZabbixOverlayWidget"
CUSTOM_FONT_FAMILY = ""  

def save_config(config):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4)

def load_config():
    sample_config = {
        "x": 100, "y": 100, "circle_size": 60,
        "zabbix_url": "https://your-zabbix-domain.com/api_jsonrpc.php", 
        "zabbix_api_token": "",  
        "zabbix_user": "YourUsername",                                    
        "zabbix_password": "YourPassword",
        "items_per_page": 5,                               
        "refresh_interval": 5,  
        "noti_duration": 7,     
        "noti_position": "bottom_right", 
        "layout_direction": "vertical", 
        "theme": "circle",      
        "always_on_top": False,
        "autostart": False,
        "history_max_count": 100,
        "debug_mode": False,
        "language": "ko",
        "noti_on_update": True
    }
    
    if not os.path.exists(CONFIG_FILE):
        save_config(sample_config)
        custom_msgbox(QMessageBox.Information, tr("msg_init_setup", "초기 설정 안내"), tr("msg_config_created", "설정 파일이 새로 생성되었습니다.\n위치: {path}\n\n프로그램을 종료합니다. 메모장 등으로 파일을 열어\n실제 Zabbix 서버 주소와 계정(또는 API 토큰) 정보로 수정한 후 다시 실행해 주세요.").format(path=CONFIG_FILE))
        sys.exit(0)
        
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            user_config = json.load(f)
            
        if user_config.get("zabbix_url") == sample_config["zabbix_url"]:
            custom_msgbox(QMessageBox.Warning, tr("msg_need_config_change", "설정 변경 필요"), tr("msg_zabbix_default", "Zabbix 서버 주소가 초기값 그대로입니다.\n\n{path}\n파일을 열어 실제 서버 정보로 수정해 주세요.").format(path=CONFIG_FILE))
            sys.exit(0)
            
        return user_config
        
    except Exception as e:
        save_config(sample_config)
        custom_msgbox(QMessageBox.Warning, tr("msg_config_error", "설정 파일 오류"), tr("msg_config_corrupted", "설정 파일 형식이 손상되어 샘플 파일로 초기화했습니다.\n\n에러 내용: {err}\n\n프로그램을 종료합니다. 설정 파일을 다시 작성해 주세요.").format(err=str(e)))
        sys.exit(0)

def zabbix_api_call(config, method, params):
    url = config.get("zabbix_url", "")
    api_token = config.get("zabbix_api_token", "").strip()
    user = config.get("zabbix_user", "")
    password = config.get("zabbix_password", "")

    headers = {
        'Content-Type': 'application/json-rpc',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0'
    }
    
    if api_token:
        auth_token = api_token
        headers['Authorization'] = f"Bearer {api_token}" 
    else:
        login_payload = {
            "jsonrpc": "2.0",
            "method": "user.login",
            "params": {"username": user, "password": password},
            "id": 1,
            "auth": None
        }
        res = requests.post(url, json=login_payload, headers=headers, timeout=5, verify=False)
        login_data = res.json()

        if "error" in login_data:
            raise Exception(f"{tr('msg_login_failed', '로그인 실패')}: {login_data['error'].get('data', login_data['error'])}")

        auth_token = login_data["result"]

    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "auth": auth_token,
        "id": 2
    }
    logger.debug(tr_log(f"[API 요청] 메서드: {method}, 파라미터: {params}", f"[API Request] Method: {method}, Params: {params}")) 

    res = requests.post(url, json=payload, headers=headers, timeout=5, verify=False)
    data = res.json()

    if "error" in data:
        logger.error(tr_log(f"[API 에러] {data['error']}", f"[API Error] {data['error']}")) 
        raise Exception(data["error"].get("data", str(data["error"])))

    logger.debug(tr_log(f"[API 응답] {method} 호출 성공", f"[API Response] {method} success"))

    return data["result"]

def apply_z_order(widget, is_topmost):
    try:
        hwnd = int(widget.winId())
    except Exception:
        return
        
    HWND_TOPMOST = -1
    HWND_NOTOPMOST = -2
    
    GWL_EXSTYLE = -20
    WS_EX_TOPMOST = 0x00000008
    
    SWP_NOSIZE = 0x0001
    SWP_NOMOVE = 0x0002
    SWP_NOACTIVATE = 0x0010
    SWP_FRAMECHANGED = 0x0020  # ★ 핵심: OS에게 "창 스타일이 바뀌었으니 캐시 버리고 프레임 다시 계산해"라고 명령
    
    flags = SWP_NOSIZE | SWP_NOMOVE | SWP_NOACTIVATE | SWP_FRAMECHANGED
    
    # 윈도우 OS 내부의 확장 스타일 스타일 장부를 가져옴
    current_style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    
    if is_topmost:
        # [OS 캐시 강제 무력화 로직]
        # 1. OS 장부에서 항상 위(TOPMOST) 비트를 완전히 지우고 프레임 갱신 처리
        ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, current_style & ~WS_EX_TOPMOST)
        ctypes.windll.user32.SetWindowPos(hwnd, HWND_NOTOPMOST, 0, 0, 0, 0, flags)
        
        # 2. 그 즉시 다시 장부에 항상 위 비트를 새기고 최상단 좌표 스택으로 재주입
        ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, current_style | WS_EX_TOPMOST)
        ctypes.windll.user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, flags)
    else:
        ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, current_style & ~WS_EX_TOPMOST)
        ctypes.windll.user32.SetWindowPos(hwnd, HWND_NOTOPMOST, 0, 0, 0, 0, flags)

class ZabbixWorker(QThread):
    data_fetched = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def __init__(self, config):
        super().__init__()
        self.config = config
        self.headers = {
            'Content-Type': 'application/json-rpc',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0'
        }

    def _do_post(self, url, payload):
        logger.debug(tr_log(f"[Worker API 요청] {payload.get('method')}", f"[Worker API Request] {payload.get('method')}"))
        res = requests.post(url, json=payload, headers=self.headers, timeout=5, verify=False)
        logger.debug(tr_log(f"[Worker API 응답] {payload.get('method')} -> HTTP 상태: {res.status_code}", f"[Worker API Response] {payload.get('method')} -> HTTP Status: {res.status_code}"))
        return res

    def run(self):
        url = self.config.get("zabbix_url", "")
        api_token = self.config.get("zabbix_api_token", "").strip()
        user = self.config.get("zabbix_user", "")
        password = self.config.get("zabbix_password", "")

        if not url: return

        try:
            logger.debug("-" * 40)
            logger.debug(tr_log("[Worker] Zabbix 백그라운드 데이터 갱신 시작", "[Worker] Zabbix background data update started"))
            if api_token:
                auth_token = api_token
                self.headers['Authorization'] = f"Bearer {api_token}"
            else:
                login_payload = {
                    "jsonrpc": "2.0", "method": "user.login",
                    "params": {"username": user, "password": password},
                    "id": 1, "auth": None
                }
                res = self._do_post(url, login_payload)
                if res.status_code != 200:
                    self.error_occurred.emit(tr("msg_http_error", "HTTP {code} 오류 발생").format(code=res.status_code))
                    return
                res_data = res.json()
                if "error" in res_data:
                    self.error_occurred.emit(tr('msg_login_failed', '로그인 실패'))
                    return
                auth_token = res_data["result"]

            problem_payload = {
                "jsonrpc": "2.0", "method": "problem.get",
                "params": {
                    "output": ["eventid", "name", "severity", "clock", "objectid", "acknowledged", "opdata"],
                    "selectAcknowledges": "extend", 
                    "source": 0, "object": 0, "recent": False, "suppressed": False, 
                    "sortfield": ["eventid"], "sortorder": "DESC"
                },
                "auth": auth_token, "id": 2
            }
            res = self._do_post(url, problem_payload)
            
            if res.status_code != 200:
                self.error_occurred.emit(tr("msg_http_error", "HTTP {code} 오류 발생").format(code=res.status_code))
                return
            
            p_data = res.json()
            if "error" in p_data:
                self.error_occurred.emit(tr('msg_api_request_error', 'API 요청 오류'))
                return
                
            problems = p_data.get("result", [])

            if not problems:
                empty_data = {"5": [], "4": [], "3": [], "2": [], "1": [], "0": []}
                self.data_fetched.emit(empty_data)
                logger.debug(tr_log("[Worker] 갱신 완료: 현재 활성화된 장애 없음", "[Worker] Update complete: No active issues"))
                return

            trigger_ids = [p["objectid"] for p in problems]
            
            trigger_payload = {
                "jsonrpc": "2.0", "method": "trigger.get",
                "params": {
                    "output": ["triggerid", "manual_close", "comments"],
                    "selectHosts": ["name"],
                    "triggerids": trigger_ids,
                    "monitored": True  
                },
                "auth": auth_token, "id": 3
            }
            res2 = self._do_post(url, trigger_payload)
            valid_triggers = res2.json().get("result", [])

            trigger_map = {}
            for t in valid_triggers:
                hosts = t.get("hosts", [])
                host_name = hosts[0].get("name", "Unknown") if hosts else "Unknown"
                trigger_map[t["triggerid"]] = {"name": host_name, "manual_close": str(t.get("manual_close", "0")), "comments": t.get("comments", "")}

            user_ids = set()
            for p in problems:
                for ack in p.get("acknowledges", []):
                    if "userid" in ack and ack["userid"] != "0":
                        user_ids.add(ack["userid"])
            
            user_map = {}
            if user_ids:
                user_payload = {
                    "jsonrpc": "2.0", "method": "user.get",
                    "params": {"output": ["userid", "username", "name", "surname", "alias"], "userids": list(user_ids)},
                    "auth": auth_token, "id": 4
                }
                try:
                    res3 = self._do_post(url, user_payload)
                    users_data = res3.json().get("result", [])
                    for u in users_data:
                        name_str = u.get('name', '').strip()
                        surname_str = u.get('surname', '').strip()
                        
                        # ★ 이름이나 성에 한글이 포함되어 있다면 "성+이름" 순서로 붙여서 출력 (김동균)
                        if any('가' <= c <= '힣' for c in name_str + surname_str):
                            if len(name_str) == 1 and len(surname_str) == 2:
                                # 예: 이름="이", 성="성현" 으로 거꾸로 적은 경우 ➔ "이성현"
                                full_name = f"{name_str}{surname_str}"
                            elif len(surname_str) == 1 and len(name_str) == 2:
                                # 예: 이름="성현", 성="이" 로 올바르게 적은 경우 ➔ "이성현"
                                full_name = f"{surname_str}{name_str}"
                            else:
                                # 한쪽 칸에 통째로 적었거나(이성현 / 공백) 외자 이름 등은 순서대로 병합
                                full_name = f"{surname_str}{name_str}".strip()
                        else: # 영어나 기타 언어면 기존처럼 "이름 성" 유지 (John Smith)
                            full_name = f"{name_str} {surname_str}".strip()
                            
                        if not full_name: full_name = u.get("username", u.get("alias", "Unknown"))
                        user_map[u["userid"]] = full_name
                except Exception:
                    pass 

            categorized_data = {"5": [], "4": [], "3": [], "2": [], "1": [], "0": []}
            for p in problems:
                tid = p["objectid"]
                if tid not in trigger_map: continue 
                sev = str(p["severity"])
                if sev in categorized_data:
                    dt = datetime.fromtimestamp(int(p["clock"])).strftime('%Y-%m-%d %H:%M:%S')
                    host_name = trigger_map[tid]["name"]
                    manual_close = trigger_map[tid]["manual_close"]
                    display_name = f"[{host_name}] {p['name']}"
                    
                    acks = p.get("acknowledges", [])
                    formatted_acks = []
                    for ack in acks:
                        if ack.get("message"):
                            ack_time = datetime.fromtimestamp(int(ack["clock"])).strftime('%Y-%m-%d %H:%M:%S')
                            uid = str(ack.get("userid", "0"))
                            user_name = user_map.get(uid, tr("lbl_unknown_user", "알 수 없는 사용자 {uid}").format(uid=uid))
                            formatted_acks.append({"time": ack_time, "user": user_name, "message": ack["message"]})
                    
                    categorized_data[sev].append({
                        "eventid": p["eventid"], "objectid": tid, "name": display_name, "time": dt, "severity": p["severity"],
                        "acknowledged": p.get("acknowledged", "0"), "acknowledges": formatted_acks,
                        "manual_close": trigger_map[tid]["manual_close"],
                        "opdata": p.get("opdata", ""),
                        "comments": trigger_map[tid].get("comments", "")
                    })
            self.data_fetched.emit(categorized_data)
            logger.debug(tr_log(f"[Worker] 갱신 완료: 총 {len(problems)}건 처리됨", f"[Worker] Update complete: Processed {len(problems)} items"))

        except requests.exceptions.ConnectionError as e:
            err_str = str(e)
            if "NameResolutionError" in err_str or "getaddrinfo failed" in err_str:
                self.error_occurred.emit(tr('msg_dns_error', '서버 주소를 찾을 수 없습니다 (DNS 오류)'))
            elif "Connection refused" in err_str:
                self.error_occurred.emit(tr('msg_conn_refused', '서버에서 연결을 거부했습니다'))
            else:
                self.error_occurred.emit(tr('msg_conn_failed', '서버 연결에 실패했습니다'))
        except requests.exceptions.Timeout:
            self.error_occurred.emit(tr('msg_timeout', '서버 응답 시간 초과'))
        except Exception as e:
            self.error_occurred.emit(tr('msg_unknown_error', '알 수 없는 오류 발생'))

# ==========================================
# 알림창 애니메이션 배경 프레임
# ==========================================
class BubbleBgFrame(QFrame):
    def __init__(self, border_color, parent=None):
        super().__init__(parent)
        self.border_color = border_color
        self.base_color = QColor(border_color) 
        self.bubbles = []
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_bubbles)
        self.timer.start(30)
        
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if not self.bubbles:
            for _ in range(40):
                self.bubbles.append(self.create_bubble(init=True))
                
    def create_bubble(self, init=False):
        w = self.width() if self.width() > 0 else 350
        h = self.height() if self.height() > 0 else 80
        
        x = random.randint(8, w) if init else random.randint(8, 20)
        y = random.randint(4, h - 4)
        
        return {
            'x': x, 'y': y, 'base_y': y,
            'r': random.uniform(1.0, 3.5),                 
            'speed': random.uniform(0.5, 2.5),             
            'opacity': random.uniform(0.3, 0.8),           
            'fade_rate': random.uniform(0.005, 0.015),     
            'sway_speed': random.uniform(0.05, 0.15),      
            'sway_amp': random.uniform(0.5, 2.0),          
            'time': random.uniform(0, 100)
        }
        
    def update_bubbles(self):
        for b in self.bubbles:
            b['time'] += b['sway_speed']
            b['x'] += b['speed'] 
            b['y'] = b['base_y'] + math.sin(b['time']) * b['sway_amp'] 
            b['opacity'] -= b['fade_rate'] 
            
            if b['x'] > self.width() + 10 or b['opacity'] <= 0:
                b.update(self.create_bubble(init=False))
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(44, 62, 80, 242)) 
        painter.drawRoundedRect(self.rect(), 6, 6)
        
        c = self.base_color
        for b in self.bubbles:
            painter.setBrush(QColor(c.red(), c.green(), c.blue(), int(b['opacity'] * 255)))
            painter.drawEllipse(QPointF(b['x'], b['y']), b['r'], b['r'])
            
        bar_rect = self.rect()
        bar_rect.setWidth(8)
        painter.setBrush(c)
        painter.drawRoundedRect(bar_rect, 6, 6)
        painter.drawRect(4, 0, 4, self.height())


# ==========================================
# 알림창(ToastWidget) - 2026 모던 UI 적용
# ==========================================
class ToastWidget(QWidget):
    def __init__(self, text, noti_type, duration, manager):
        super().__init__()
        self.manager = manager
        self.is_closing = False 
        
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFixedWidth(360)
        
        self.setWindowOpacity(0.0)
        self.opacity_anim = QVariantAnimation(self)
        self.opacity_anim.setDuration(300) 
        self.opacity_anim.setStartValue(0.0)
        self.opacity_anim.setEndValue(1.0)
        self.opacity_anim.valueChanged.connect(self.setWindowOpacity)
        self.opacity_anim.start()
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        
        is_light = self.manager.config.get("color_mode", "dark") == "light"
        
        border_color = '#EF4444' if noti_type == 'created' else '#10B981' if noti_type == 'resolved' else '#F59E0B'
        bg_color = "rgba(255, 255, 255, 245)" if is_light else "rgba(28, 28, 32, 245)"
        border_line = "rgba(0, 0, 0, 0.1)" if is_light else "rgba(255, 255, 255, 0.08)"
        text_color = "#111827" if is_light else "#F4F4F5"
        btn_color = "#6B7280" if is_light else "#A1A1AA"
        btn_hover_bg = "rgba(0, 0, 0, 0.08)" if is_light else "rgba(255, 255, 255, 0.1)"
        btn_hover_color = "#111827" if is_light else "#F4F4F5"
        
        self.bg_frame = QFrame()
        self.bg_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border-radius: 12px;
                border: 1px solid {border_line};
                border-left: 4px solid {border_color};
            }}
        """)
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(6)
        shadow.setColor(QColor(0, 0, 0, 70 if is_light else 100))
        self.bg_frame.setGraphicsEffect(shadow)
        
        bg_layout = QHBoxLayout(self.bg_frame)
        bg_layout.setContentsMargins(16, 12, 12, 12)
        bg_layout.setSpacing(12)
        
        # HTML 태그 색상 무력화를 위해 text 안의 색상을 일괄 교체
        if is_light:
            text = text.replace('color: #BDC3C7', 'color: #6B7280').replace('color: #F39C12', 'color: #D97706')
            
        lbl = QLabel(text)
        lbl.setTextFormat(Qt.RichText)
        lbl.setStyleSheet(f"color: {text_color}; font-family: 'IBM Plex Sans KR', sans-serif; background: transparent; border: none;")
        lbl.setWordWrap(True)
        
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(24, 24)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet(f"""
            QPushButton {{ color: {btn_color}; background: transparent; border: none; font-size: 14px; border-radius: 6px; }} 
            QPushButton:hover {{ background-color: {btn_hover_bg}; color: {btn_hover_color}; }}
        """)
        close_btn.clicked.connect(self.fade_and_close)
        
        bg_layout.addWidget(lbl, 1)
        bg_layout.addWidget(close_btn, 0, Qt.AlignTop)
        
        layout.addWidget(self.bg_frame)
        self.adjustSize()
        
        if duration > 0: 
            QTimer.singleShot(duration * 1000, self.fade_and_close)
            
    def fade_and_close(self):
        if getattr(self, 'is_closing', False): return
        self.is_closing = True
        
        self.opacity_anim.stop()
        self.opacity_anim.setStartValue(self.windowOpacity())
        self.opacity_anim.setEndValue(0.0)
        self.opacity_anim.setDuration(300) 
        
        try: self.opacity_anim.finished.disconnect()
        except: pass
        
        self.opacity_anim.finished.connect(self.close) 
        self.opacity_anim.start()
        
    def closeEvent(self, event):
        self.manager.remove(self)
        super().closeEvent(event)
        
    def contextMenuEvent(self, event):
        menu = QMenu(self)
        is_light = self.manager.config.get("color_mode", "dark") == "light"
        
        bg_color = "#FFFFFF" if is_light else "#1C1C20"
        text_color = "#2C3E50" if is_light else "#F4F4F5"
        border_color = "#C8D0D8" if is_light else "#3F3F46"
        
        menu.setStyleSheet(f"QMenu {{ background-color: {bg_color}; border: 1px solid {border_color}; padding: 6px; border-radius: 6px; }} QMenu::item {{ padding: 7px 28px 7px 28px; color: {text_color}; }} QMenu::item:selected {{ background-color: #EF4444; color: white; border-radius: 4px; }}")
        
        act_close_all = QAction(tr("menu_clear_all", "🧹 알림 일괄 삭제"), self)
        act_close_all.triggered.connect(self.manager.clear_all)
        menu.addAction(act_close_all)
        menu.exec_(event.globalPos())

# ==========================================
# 알림창 매니저 (위치 정렬)
# ==========================================
class ToastManager:
    def __init__(self, main_widget, config):  
        self.main_widget = main_widget
        self.toasts = []
        self.config = config 

    def show(self, msg, noti_type, duration):
        t = ToastWidget(msg, noti_type, duration, self)
        self.toasts.append(t)
        self.rearrange()
        t.show()

    def rearrange(self):
        target_point = self.main_widget.mapToGlobal(self.main_widget.rect().center())
        screen = QApplication.screenAt(target_point)
        
        if not screen: 
            screen = QApplication.primaryScreen()
            
        if not screen:
            return
            
        geom = screen.availableGeometry()
        
        margin_x, margin_y = 20, 40
        pos_setting = self.config.get("noti_position", "bottom_right")
        
        current_y = geom.bottom() - margin_y if "bottom" in pos_setting else geom.top() + margin_y
            
        for t in reversed(self.toasts):
            x = geom.right() - t.width() - margin_x if "right" in pos_setting else geom.left() + margin_x
            if "bottom" in pos_setting:
                t.move(x, current_y - t.height())
                current_y -= (t.height() + 5)
            else:
                t.move(x, current_y)
                current_y += (t.height() + 5)

    def remove(self, t):
        if t in self.toasts:
            self.toasts.remove(t)
            self.rearrange()
            
    def clear_all(self):
        for t in list(self.toasts):
            t.fade_and_close()


class AlertListWindow(QWidget):
    def __init__(self, title, hex_color, problems_list, items_per_page=5, config=None, owner_window=None):
        super().__init__()
        base_flags = Qt.FramelessWindowHint | Qt.Tool
        if config and config.get("always_on_top", False):
            base_flags |= Qt.WindowStaysOnTopHint
            
        self.setWindowFlags(base_flags)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._is_dragging = False
        self._drag_start_pos = QPoint()
        self.config = config
        self.owner_window = owner_window
        self.hex_color = hex_color
        
        self.is_light = self.config.get("color_mode", "dark") == "light"

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)

        self.bg_widget = QWidget()
        self.bg_widget.setObjectName("alertBgWidget")
        
        # ★ 핵심: 여기서 배경색과 테두리 선 색상이 모드에 따라 바뀌어야 합니다!
        bg_color = "rgba(255, 255, 255, 245)" if self.is_light else "rgba(28, 28, 32, 245)"
        border_color = "rgba(0, 0, 0, 0.1)" if self.is_light else "rgba(255, 255, 255, 0.1)"
        
        self.bg_widget.setStyleSheet(f"""
            QWidget#alertBgWidget {{ 
                background-color: {bg_color}; 
                border-radius: 16px; 
                border: 1px solid {border_color}; 
                border-top: 3px solid {hex_color};
            }}
        """)
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(8)
        shadow.setColor(QColor(0, 0, 0, 70 if self.is_light else 120))
        self.bg_widget.setGraphicsEffect(shadow)

        bg_layout = QVBoxLayout(self.bg_widget)
        bg_layout.setContentsMargins(14, 14, 14, 14)

        header_layout = QHBoxLayout()
        self.problems_list = problems_list
        self.items_per_page = items_per_page
        self.current_page = 0
        self.total_pages = max(1, (len(self.problems_list) + self.items_per_page - 1) // self.items_per_page)

        self.title = title
        self.title_lbl = QLabel()
        self.title_lbl.setStyleSheet(f"color: {hex_color}; font-weight: bold; font-size: 15px; border: none; background: transparent; font-family: 'IBM Plex Sans KR', sans-serif;")

        btn_c = "#4B5563" if self.is_light else "#A1A1AA"
        btn_hover_bg = "rgba(0, 0, 0, 0.08)" if self.is_light else "rgba(255, 255, 255, 0.1)"
        btn_hover_c = "#111827" if self.is_light else "#F4F4F5"

        modern_btn_style = f"""
            QPushButton {{ color: {btn_c}; background: transparent; border: none; font-size: 16px; font-weight: bold; border-radius: 6px; padding: 2px 6px; font-family: Arial, sans-serif; }} 
            QPushButton:hover {{ background-color: {btn_hover_bg}; color: {btn_hover_c}; }}
        """

        self.prev_btn = QPushButton("‹")
        self.prev_btn.setFixedSize(28, 28)
        self.prev_btn.setCursor(Qt.PointingHandCursor)
        sp_prev = self.prev_btn.sizePolicy()
        sp_prev.setRetainSizeWhenHidden(True)
        self.prev_btn.setSizePolicy(sp_prev)
        self.prev_btn.setStyleSheet(modern_btn_style)
        self.prev_btn.clicked.connect(self.go_prev_page)

        self.page_lbl = QLabel()
        self.page_lbl.setStyleSheet(f"color: {btn_c}; font-size: 12px; border: none; background: transparent; font-family: 'IBM Plex Sans KR', sans-serif;")

        self.next_btn = QPushButton("›")
        self.next_btn.setFixedSize(28, 28)
        self.next_btn.setCursor(Qt.PointingHandCursor)
        sp_next = self.next_btn.sizePolicy()
        sp_next.setRetainSizeWhenHidden(True)
        self.next_btn.setSizePolicy(sp_next)
        self.next_btn.setStyleSheet(modern_btn_style)
        self.next_btn.clicked.connect(self.go_next_page)

        self.refresh_btn = QPushButton("↻")
        self.refresh_btn.setFixedSize(28, 28)
        self.refresh_btn.setCursor(Qt.PointingHandCursor)
        self.refresh_btn.setToolTip("새로고침")
        self.refresh_btn.setStyleSheet(modern_btn_style)
        self.refresh_btn.clicked.connect(self.reload_from_server)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(28, 28)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet(modern_btn_style.replace(btn_hover_bg, "rgba(239, 68, 68, 0.15)").replace(btn_hover_c, "#EF4444"))
        close_btn.clicked.connect(self.close)

        header_layout.addWidget(self.title_lbl)
        header_layout.addStretch()
        header_layout.addWidget(self.prev_btn)
        header_layout.addWidget(self.page_lbl)
        header_layout.addWidget(self.next_btn)
        header_layout.addWidget(self.refresh_btn)
        header_layout.addWidget(close_btn)

        self.list_widget = QListWidget()
        self.list_widget.setMouseTracking(True)
        self.list_widget.viewport().setMouseTracking(True)
        self.list_widget.setFocusPolicy(Qt.NoFocus)
        self.list_widget.setSelectionMode(QListWidget.NoSelection)
        self.list_widget.viewport().installEventFilter(self)
        self.list_widget.setWordWrap(True)
        # ★ 수정됨: 스크롤바 정책을 '항상 끔'에서 '필요 시 표시(AsNeeded)'로 변경
        self.list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list_widget.itemDoubleClicked.connect(self.open_issue_editor)

        # ★ 추가됨: 다크/라이트 모드에 맞춘 반투명 스크롤바 색상 변수 설정
        scroll_handle_bg = "rgba(0, 0, 0, 0.2)" if self.is_light else "rgba(255, 255, 255, 0.2)"
        scroll_handle_hover = "rgba(0, 0, 0, 0.4)" if self.is_light else "rgba(255, 255, 255, 0.4)"

        # ★ 수정됨: QListWidget 스크롤바(QScrollBar) 디자인 추가
        self.list_widget.setStyleSheet(f"""
            QListWidget {{ background-color: transparent; border: none; outline: none; }}
            QListWidget::item {{ padding: 2px 0px; margin: 0px; background-color: transparent; border: none; }}
            
            /* 모던 반투명 스크롤바 디자인 */
            QScrollBar:vertical {{ background: transparent; width: 6px; margin: 2px 2px 2px 0px; }}
            QScrollBar::handle:vertical {{ background: {scroll_handle_bg}; min-height: 30px; border-radius: 3px; }}
            QScrollBar::handle:vertical:hover {{ background: {scroll_handle_hover}; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; border: none; background: none; }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}
        """)

        bg_layout.addLayout(header_layout)
        bg_layout.addWidget(self.list_widget)
        main_layout.addWidget(self.bg_widget)

        self.refresh_page()

    def create_issue_item_widget(self, issue_data):
        card_widget = QWidget()
        
        card_bg = "rgba(0, 0, 0, 0.03)" if self.is_light else "rgba(255, 255, 255, 0.04)"
        card_hover = "rgba(0, 0, 0, 0.06)" if self.is_light else "rgba(255, 255, 255, 0.08)"
        title_color = "#111827" if self.is_light else "#F4F4F5"
        content_color = "#6B7280" if self.is_light else "#A1A1AA"
        time_color = "#9CA3AF" if self.is_light else "#71717A"
        
        card_widget.setStyleSheet(f"""
            QWidget {{ background-color: {card_bg}; border-radius: 10px; }}
            QWidget:hover {{ background-color: {card_hover}; }}
        """)
        
        outer_layout = QVBoxLayout(card_widget)
        outer_layout.setContentsMargins(12, 12, 12, 12) 
        outer_layout.setSpacing(6)
        
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        dot_lbl = QLabel("●")
        dot_lbl.setStyleSheet(f"color: {self.hex_color}; font-size: 11px; background: transparent; border: none;")
        dot_lbl.setFixedWidth(16)
        
        safe_title = issue_data['name'].replace('<', '&lt;').replace('>', '&gt;')
        title_lbl = QLabel(f"<span style='font-family: \"IBM Plex Sans KR\", sans-serif; color: {title_color}; font-size: 13px; font-weight: bold;'>{safe_title}</span>")
        title_lbl.setStyleSheet("background: transparent; border: none;")
        title_lbl.setWordWrap(True)
        
        header_layout.addWidget(dot_lbl, 0, Qt.AlignTop)
        header_layout.addWidget(title_lbl, 1)
        outer_layout.addLayout(header_layout)
        
        content = issue_data.get('opdata', '').strip()
        if content:
            safe_content = content.replace('<', '&lt;').replace('>', '&gt;').replace('\n', '<br>')
            content_lbl = QLabel(f"<span style='font-family: \"IBM Plex Sans KR\", sans-serif; color: {content_color}; font-size: 12px;'>{safe_content}</span>")
            content_lbl.setStyleSheet("background: transparent; border: none;")
            content_lbl.setWordWrap(True)
            content_lbl.setContentsMargins(20, 0, 0, 0)
            outer_layout.addWidget(content_lbl)
            
        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(20, 4, 0, 0)
        
        time_lbl = QLabel(issue_data['time'])
        time_lbl.setStyleSheet(f"color: {time_color}; font-size: 11px; border: none; background: transparent; font-family: 'IBM Plex Sans KR', sans-serif;")
        
        footer_layout.addWidget(time_lbl)
        footer_layout.addStretch()
        
        if str(issue_data.get("acknowledged", "0")) == "1":
            ack_lbl = QLabel("✓")
            ack_lbl.setStyleSheet("color: #10B981; font-size: 14px; font-weight: bold; background: transparent; border: none;")
            footer_layout.addWidget(ack_lbl)
            
        outer_layout.addLayout(footer_layout)
        
        wrapper = QWidget()
        wrapper.setStyleSheet("background: transparent; border: none;")
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(4, 4, 4, 4)
        wrapper_layout.addWidget(card_widget)
        
        return wrapper

    def eventFilter(self, obj, event):
        if obj == self.list_widget.viewport() and event.type() == QEvent.Leave:
            self.list_widget.clearSelection()
            self.list_widget.setCurrentRow(-1)
            self.list_widget.viewport().update()
        return super().eventFilter(obj, event)

    def refresh_page(self):
        self.list_widget.clear()
        total_count = len(self.problems_list)
        start = self.current_page * self.items_per_page
        end = start + self.items_per_page
        page_items = self.problems_list[start:end]

        self.title_lbl.setText(f"{self.title} {tr('lbl_list', '리스트')} ({total_count})")
        self.page_lbl.setText(f"{self.current_page + 1}/{self.total_pages}")
        
        self.prev_btn.setVisible(self.current_page > 0)
        self.next_btn.setVisible(self.current_page < self.total_pages - 1)
        self.page_lbl.setVisible(self.total_pages > 1)
        
        total_height = 52 + 28 # 헤더 높이 + 컨테이너 패딩
        
        if not page_items:
            item = QListWidgetItem(tr("msg_no_issues", "✅ 현재 발생한 미해결 내역이 없습니다."))
            item.setFlags(Qt.NoItemFlags)
            item.setSizeHint(QSize(0, 60))
            self.list_widget.addItem(item)
            total_height += 60
        else:
            font = QFont()
            if CUSTOM_FONT_FAMILY: font.setFamily(CUSTOM_FONT_FAMILY)
            font.setPixelSize(13)
            fm = QFontMetrics(font)
            
            for p in page_items:
                item = QListWidgetItem()
                item.setData(Qt.UserRole, p)
                widget = self.create_issue_item_widget(p)
                
                content = p.get('opdata', '').strip()
                name_text = f"● {p['name']}\n{content}" if content else f"● {p['name']}"
                
                rect = fm.boundingRect(0, 0, 310, 2000, Qt.TextWordWrap | Qt.AlignLeft, name_text)
                
                # 🛠 카드 디자인 적용으로 상하 여백이 늘어났으므로 넉넉하게 높이 계산 (+85)
                calc_height = max(85, rect.height() + 85)
                
                item.setSizeHint(QSize(0, calc_height))
                self.list_widget.addItem(item)
                self.list_widget.setItemWidget(item, widget)
                total_height += calc_height

        self.resize(440, max(150, total_height)) # 창 너비도 살짝 넓혀 가독성 향상

    def go_prev_page(self):
        if self.current_page > 0:
            logger.debug(tr_log(f"[UI 액션] 리스트 이전 페이지 클릭 ({self.current_page + 1} -> {self.current_page})", f"[UI Action] List previous page clicked ({self.current_page + 1} -> {self.current_page})"))
            self.current_page -= 1
            self.refresh_page()

    def go_next_page(self):
        if self.current_page < self.total_pages - 1:
            logger.debug(tr_log(f"[UI 액션] 리스트 다음 페이지 클릭 ({self.current_page + 1} -> {self.current_page + 2})", f"[UI Action] List next page clicked ({self.current_page + 1} -> {self.current_page + 2})"))
            self.current_page += 1
            self.refresh_page()

    def reload_from_server(self):
        logger.debug(tr_log(f"[UI 액션] 알림 리스트 수동 새로고침 버튼 클릭", "[UI Action] Alert list manual refresh button clicked"))
        self.set_refreshing_state(True)
        if self.owner_window: self.owner_window.fetch_zabbix_data()

    def set_refreshing_state(self, refreshing=True):
        if refreshing:
            self.title_lbl.setText(tr("msg_refreshing", "⏳ 새로고침 중..."))  
            self.refresh_btn.setEnabled(False)
        else:
            self.refresh_btn.setEnabled(True)
            self.refresh_page()  

    def open_issue_editor(self, item):
        issue_data = item.data(Qt.UserRole)
        if not issue_data: return

        dlg = IssueActionDialog(issue_data, self)
        if dlg.exec_() != QDialog.Accepted: return

        values = dlg.get_values()
        action = 0
        params = {"eventids": [issue_data["eventid"]]}
        
        curr_ack = str(issue_data.get("acknowledged", "0")) == "1"
        if values["acknowledge"] and not curr_ack: action |= 2
        elif not values["acknowledge"] and curr_ack: action |= 16

        if values["message"]:
            action |= 4
            params["message"] = values["message"]
        if values["severity"] is not None:
            action |= 8
            params["severity"] = values["severity"]
        if values["close"]: action |= 1

        if action == 0:
            custom_msgbox(QMessageBox.Information, tr("title_notice", "안내"), tr("msg_no_change", "변경할 내용이 없습니다."), self)
            return
        params["action"] = action
        try:
            logger.debug(tr_log(f"[UI 액션] 장애 이벤트 업데이트 실행 - params: {params}", f"[UI Action] Issue event update executed - params: {params}"))
            zabbix_api_call(self.config, "event.acknowledge", params)
            custom_msgbox(QMessageBox.Information, tr("title_complete", "완료"), tr("msg_update_success", "장애가 업데이트되었습니다."), self)
            if self.owner_window: self.owner_window.fetch_zabbix_data()
            else: self.refresh_page()
        except Exception as e:
            custom_msgbox(QMessageBox.Critical, tr("title_error", "오류"), tr("msg_update_fail", "업데이트 실패:\n{err}").format(err=str(e)), self)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._is_dragging = True
            self._drag_start_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._is_dragging and (event.buttons() & Qt.LeftButton):
            new_pos = event.globalPos() - self._drag_start_pos
            screen = QApplication.screenAt(event.globalPos())
            if not screen: screen = QApplication.primaryScreen()
            rect = screen.availableGeometry()
            nx = max(rect.left(), min(new_pos.x(), rect.right() - self.width()))
            ny = max(rect.top(), min(new_pos.y(), rect.bottom() - self.height()))
            self.move(nx, ny)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._is_dragging = False
            event.accept()
            
    def closeEvent(self, event):
        logger.debug(tr_log(f"[UI 액션] '{self.title}' 알림 리스트 창 닫기", f"[UI Action] '{self.title}' alert list window closed"))
        super().closeEvent(event)

class IssueActionDialog(QDialog):
    def __init__(self, issue_data, parent=None):
        super().__init__(parent)
        self.issue_data = issue_data
        self.config = self.parent().config if self.parent() and hasattr(self.parent(), 'config') else {}
        self.is_light = self.config.get("color_mode", "dark") == "light"
        
        self.setWindowTitle(tr("title_issue_info", "장애 정보"))
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint) 
        
        # ★ 수정 1: 탭 전환 시 창이 울렁거리지 않도록 넉넉한 크기로 강제 고정
        self.setFixedSize(760, 540)

        # 🎨 모드에 따른 색상 동적 할당
        bg_color = "#F9FAFB" if self.is_light else "#1C1C20"
        text_color = "#111827" if self.is_light else "#F4F4F5"
        pane_bg = "#FFFFFF" if self.is_light else "#2A2A30"
        border_color = "#D1D5DB" if self.is_light else "#3F3F46"
        input_bg = "#FFFFFF" if self.is_light else "#18181B"
        tab_bg = "#E5E7EB" if self.is_light else "#18181B"
        tab_sel_bg = "#FFFFFF" if self.is_light else "#2A2A30"
        tab_sel_color = "#2563EB" if self.is_light else "#60A5FA"
        scroll_bg = "#D1D5DB" if self.is_light else "#3F3F46"
        scroll_hover = "#9CA3AF" if self.is_light else "#52525B"
        dim_text = "#6B7280" if self.is_light else "#A1A1AA"

        arrow_url = get_arrow_path()
        
        # ★ 수정 2: QTabBar::tab 에 min-width: 140px; 를 추가하여 글자 잘림 방지
        self.setStyleSheet(f"""
            QDialog {{ background-color: {bg_color}; font-family: 'IBM Plex Sans KR', sans-serif; font-size: 13px; color: {text_color}; }}
            
            /* ★ QCheckBox:disabled 속성 추가로 비활성화 시 글자색을 흐리게 만듦 */
            QLabel, QCheckBox {{ color: {text_color}; }}
            QCheckBox:disabled {{ color: {dim_text}; }}
            
            /* 탭 디자인 */
            QTabWidget::pane {{ border: 1px solid {border_color}; border-radius: 8px; background: {pane_bg}; padding: 4px; }}
            QTabBar::tab {{ background: {tab_bg}; border: 1px solid {border_color}; border-bottom: none; padding: 8px 0px; min-width: 140px; margin-right: 4px; border-top-left-radius: 8px; border-top-right-radius: 8px; color: {dim_text}; font-weight: bold; }}
            QTabBar::tab:selected {{ background: {tab_sel_bg}; color: {tab_sel_color}; border-bottom: 2px solid {tab_sel_color}; }}
            QTabBar::tab:hover:!selected {{ background: {border_color}; }}
            
            /* 입력창 디자인 */
            QPlainTextEdit, QComboBox {{ background-color: {input_bg}; color: {text_color}; border: 1px solid {border_color}; border-radius: 6px; padding: 6px; outline: none; }}
            QPlainTextEdit:focus, QComboBox:focus {{ border: 1px solid {tab_sel_color}; }}
            
            /* 콤보박스 디자인 */
            QComboBox::drop-down {{ subcontrol-origin: padding; subcontrol-position: top right; width: 24px; border-left-width: 0px; }}
            QComboBox::down-arrow {{ image: url('{arrow_url}'); width: 16px; height: 16px; }}
            QComboBox QAbstractItemView {{ background-color: {pane_bg}; color: {text_color}; selection-background-color: {border_color}; selection-color: {text_color}; outline: none; border: 1px solid {border_color}; border-radius: 6px; padding: 4px; }}
            
            /* 일반 버튼 디자인 */
            QPushButton {{ padding: 6px 14px; border: 1px solid {border_color}; border-radius: 6px; background-color: {pane_bg}; color: {text_color}; font-weight: bold; }} 
            QPushButton:hover {{ background-color: {border_color}; }}
            
            /* 스크롤바 디자인 */
            QScrollBar:vertical {{ background: transparent; width: 10px; margin: 0px; }}
            QScrollBar::handle:vertical {{ background: {scroll_bg}; min-height: 30px; border-radius: 5px; margin: 2px; }}
            QScrollBar::handle:vertical:hover {{ background: {scroll_hover}; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; border: none; background: none; }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}
            
            QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 0px; }}
            QScrollBar::handle:horizontal {{ background: {scroll_bg}; min-width: 30px; border-radius: 5px; margin: 2px; }}
            QScrollBar::handle:horizontal:hover {{ background: {scroll_hover}; }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0px; border: none; background: none; }}
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: none; }}
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        self.tabs = QTabWidget()
        
        # -----------------------------------
        # [1] 업데이트 탭
        # -----------------------------------
        self.tab_update = QWidget()
        layout_update = QFormLayout(self.tab_update)
        layout_update.setLabelAlignment(Qt.AlignTop) 
        layout_update.setContentsMargins(16, 16, 16, 16)
        layout_update.setSpacing(12)
        
        self.message_edit = QPlainTextEdit()
        
        self.severity_combo = QComboBox()
        self.severity_combo.addItems([tr("sev_no_change", "변경 안함"), tr("sev_not_cls", "미정"), tr("sev_info", "정보"), tr("sev_warning", "경고"), tr("sev_average", "경미"), tr("sev_high", "중증"), tr("sev_disaster", "심각")])
        self.severity_combo.setItemData(0, None)
        for i in range(1, 7): self.severity_combo.setItemData(i, i-1)

        self.ack_check = QCheckBox(tr("lbl_ack", "인지 상태"))
        self.ack_check.setChecked(str(issue_data.get("acknowledged", "0")) == "1")
        
        self.close_check = QCheckBox(tr("lbl_close", "장애 클로즈"))
        if str(issue_data.get("manual_close", "0")) == "0":
            self.close_check.setEnabled(False)
            # ★ 추가됨: 비활성화된 이유를 사용자가 즉시 알 수 있도록 텍스트 추가
            self.close_check.setText(self.close_check.text() + " (수동 클로즈 불가)")
            self.close_check.setToolTip(tr("msg_manual_close_denied", "Zabbix 설정에서 수동 클로즈가 허용되지 않은 장애입니다."))

        issue_name_lbl = QLabel(issue_data.get("name", ""))
        issue_name_lbl.setWordWrap(True) 
        issue_name_lbl.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        issue_name_lbl.setMinimumWidth(500)
        issue_name_lbl.setStyleSheet(f"font-weight: bold; color: {text_color};")
        
        layout_update.addRow(tr("lbl_issue", "이슈"), issue_name_lbl)
        layout_update.addRow(tr("lbl_message", "메시지"), self.message_edit)
        layout_update.addRow(tr("lbl_severity", "심각도"), self.severity_combo)
        layout_update.addRow("", self.ack_check)
        layout_update.addRow("", self.close_check)
        self.tabs.addTab(self.tab_update, tr("tab_update", "업데이트"))
        
        # -----------------------------------
        # [2] 히스토리 탭
        # -----------------------------------
        self.tab_history = QWidget()
        layout_history = QVBoxLayout(self.tab_history)
        layout_history.setContentsMargins(12, 12, 12, 12)
        
        history_header = QHBoxLayout()
        
        self.item_combo = QComboBox()
        # ★ 수정 3: 빈 공간이 생기면 콤보박스가 알아서 늘어나도록 설정 (창 팽창 방지)
        self.item_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.item_combo.setMinimumWidth(150) 
        self.item_combo.currentIndexChanged.connect(self.on_history_filter_changed)
        history_header.addWidget(self.item_combo, 1) # 빈 공간을 콤보박스가 채움

        # (기존에 있던 addStretch()는 삭제됨)
        
        self.time_range_lbl = QLabel()
        self.time_range_lbl.setStyleSheet(f"color: {dim_text}; font-size: 11px; margin-left: 15px; margin-right: 15px;")
        history_header.addWidget(self.time_range_lbl)

        self.time_combo = QComboBox()
        time_options = [
            (tr("time_1m", "1분"), 60), (tr("time_3m", "3분"), 180), (tr("time_5m", "5분"), 300), (tr("time_10m", "10분"), 600), (tr("time_15m", "15분"), 900), 
            (tr("time_30m", "30분"), 1800), (tr("time_1h", "1시간"), 3600), (tr("time_3h", "3시간"), 10800), (tr("time_6h", "6시간"), 21600), 
            (tr("time_9h", "9시간"), 32400), (tr("time_12h", "12시간"), 43200), (tr("time_24h", "24시간"), 86400)
        ]
        for text, seconds in time_options:
            self.time_combo.addItem(text, seconds)
        self.time_combo.setCurrentIndex(6) 
        self.time_combo.currentIndexChanged.connect(self.on_history_filter_changed)
        history_header.addWidget(self.time_combo)

        self.btn_refresh_history = QPushButton(tr("btn_refresh", "🔄 새로고침"))
        self.btn_refresh_history.setCursor(Qt.PointingHandCursor)
        self.btn_refresh_history.clicked.connect(self.refresh_history_data)
        history_header.addWidget(self.btn_refresh_history)

        layout_history.addLayout(history_header)

        self.history_browser = QTextBrowser()
        self.history_browser.setStyleSheet(f"background-color: {pane_bg}; border: 1px solid {border_color}; border-radius: 6px;")
        self.history_browser.setHtml(f"<p style='color: {dim_text}; margin: 10px;'>{tr('lbl_loading_data', '데이터를 불러오는 중입니다...')}</p>")
        layout_history.addWidget(self.history_browser)
        
        self.tabs.addTab(self.tab_history, tr("tab_history", "히스토리"))
        
        # -----------------------------------
        # [3] 메시지 로그 탭
        # -----------------------------------
        self.tab_log = QWidget()
        layout_log = QVBoxLayout(self.tab_log)
        layout_log.setContentsMargins(12, 12, 12, 12)
        
        log_header = QHBoxLayout()
        log_header.addStretch() 
        self.btn_refresh_log = QPushButton(tr("btn_refresh", "🔄 새로고침"))
        self.btn_refresh_log.setCursor(Qt.PointingHandCursor)
        self.btn_refresh_log.clicked.connect(self.refresh_log_data)
        log_header.addWidget(self.btn_refresh_log)
        layout_log.addLayout(log_header)

        self.log_browser = QTextBrowser()
        self.log_browser.setStyleSheet(f"background-color: {pane_bg}; border: 1px solid {border_color}; border-radius: 6px;")
        layout_log.addWidget(self.log_browser)
        
        self.tabs.addTab(self.tab_log, tr("tab_log", "메시지 로그"))
        self.render_logs(issue_data.get("acknowledges", []))

        main_layout.addWidget(self.tabs)
        
        QTimer.singleShot(100, self.refresh_history_data)
        
        # 하단 확인/취소 버튼 영역
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 8, 0, 0)
        btn_layout.addStretch()

        # 모던한 Blue, Red 색상 버튼 적용
        self.btn_ok = QPushButton(tr("btn_ok", "확인"))
        self.btn_ok.setCursor(Qt.PointingHandCursor)
        ok_bg = "#3B82F6" if self.is_light else "#2563EB"
        ok_hover = "#2563EB" if self.is_light else "#1D4ED8"
        self.btn_ok.setStyleSheet(f"QPushButton {{ padding: 8px 24px; background-color: {ok_bg}; color: white; border: none; border-radius: 6px; font-weight: bold; font-family: 'IBM Plex Sans KR', sans-serif; }} QPushButton:hover {{ background-color: {ok_hover}; }}")
        self.btn_ok.clicked.connect(self.accept)

        self.btn_cancel = QPushButton(tr("btn_cancel", "취소"))
        self.btn_cancel.setCursor(Qt.PointingHandCursor)
        can_bg = "#EF4444" if self.is_light else "#DC2626"
        can_hover = "#DC2626" if self.is_light else "#B91C1C"
        self.btn_cancel.setStyleSheet(f"QPushButton {{ padding: 8px 24px; background-color: {can_bg}; color: white; border: none; border-radius: 6px; font-weight: bold; font-family: 'IBM Plex Sans KR', sans-serif; }} QPushButton:hover {{ background-color: {can_hover}; }}")
        self.btn_cancel.clicked.connect(self.reject)

        btn_layout.addWidget(self.btn_ok)
        btn_layout.addWidget(self.btn_cancel)
        main_layout.addLayout(btn_layout)

    def get_values(self):
        return {
            "message": self.message_edit.toPlainText().strip(),
            "severity": self.severity_combo.currentData(),
            "acknowledge": self.ack_check.isChecked(),
            "close": self.close_check.isChecked()
        }
        
    def on_history_filter_changed(self):
        if self.item_combo.count() == 0: return
        self.refresh_history_data()

    def refresh_history_data(self):
        self.btn_refresh_history.setText(tr("msg_refreshing", "⏳ 새로고침 중..."))
        self.btn_refresh_history.setEnabled(False)
        self.item_combo.setEnabled(False)
        self.time_combo.setEnabled(False)
        QApplication.processEvents()
        
        # HTML 내부 색상 변수 지정
        text_c = "#374151" if self.is_light else "#E4E4E7"
        date_c = "#2563EB" if self.is_light else "#60A5FA"
        dim_c = "#6B7280" if self.is_light else "#A1A1AA"
        err_c = "#EF4444" if self.is_light else "#F87171"
        line_c = "#E5E7EB" if self.is_light else "#3F3F46"

        try:
            objectid = self.issue_data.get("objectid") 
            if not objectid:
                self.history_browser.setHtml(f"<p style='color: {err_c}; margin: 10px;'>이력을 조회할 수 있는 식별자가 없습니다.</p>")
                return

            if self.item_combo.count() == 0:
                trigger_params = {
                    "output": ["triggerid"],
                    "triggerids": [objectid],
                    "selectItems": ["itemid", "value_type", "name"]
                }
                triggers = zabbix_api_call(self.config, "trigger.get", trigger_params)
                
                if not triggers or not triggers[0].get("items"):
                    self.history_browser.setHtml(f"<p style='color: {dim_c}; margin: 10px;'>연결된 아이템 정보를 찾을 수 없습니다.</p>")
                    return
                    
                self.item_combo.blockSignals(True)
                for item in triggers[0]["items"]:
                    self.item_combo.addItem(item.get("name", tr("lbl_unknown_item", "알 수 없는 아이템")), (item["itemid"], item["value_type"]))
                self.item_combo.blockSignals(False)
            
            selected_item_data = self.item_combo.currentData()
            if not selected_item_data: return
                
            itemid, value_type = selected_item_data
            item_name = self.item_combo.currentText()
            time_limit_seconds = self.time_combo.currentData()
            
            now_ts = int(datetime.now().timestamp())
            time_from = now_ts - time_limit_seconds
            
            str_now = datetime.fromtimestamp(now_ts).strftime('%Y-%m-%d %H:%M:%S')
            str_from = datetime.fromtimestamp(time_from).strftime('%Y-%m-%d %H:%M:%S')
            self.time_range_lbl.setText(f"{str_from} ~ {str_now}")
            
            history_params = {
                "output": "extend",
                "history": value_type, 
                "itemids": [itemid],
                "time_from": time_from,
                "sortfield": "clock",
                "sortorder": "DESC",
                "limit": 100 
            }
            histories = zabbix_api_call(self.config, "history.get", history_params)
            
            if not histories:
                self.history_browser.setHtml(f"<p style='color: {dim_c}; margin: 14px;'>[{item_name}] 아이템의 해당 기간({self.time_combo.currentText()}) 내 데이터가 없습니다.</p>")
            else:
                html = "<div style='margin: 10px;'>"
                for h in histories:
                    dt = datetime.fromtimestamp(int(h["clock"])).strftime('%Y-%m-%d %H:%M:%S')
                    value = h.get("value", "").replace('<', '&lt;').replace('>', '&gt;').replace('\n', '<br>')
                    
                    html += f"<div style='margin-bottom: 12px;'>"
                    html += f"<span style='color: {date_c}; font-weight: bold; font-size: 12px;'>[{dt}]</span><br>"
                    html += f"<span style='color: {text_c}; font-size: 13px; font-family: Consolas, monospace;'>{value}</span>"
                    html += f"</div><hr style='border: 0; border-top: 1px dashed {line_c};'>"
                    
                html += "</div>"
                self.history_browser.setHtml(html)
                
        except Exception as e:
            self.history_browser.setHtml(f"<p style='color: {err_c}; margin: 10px;'>오류 발생: {e}</p>")
        finally:
            self.btn_refresh_history.setText(tr("btn_refresh", "🔄 새로고침"))
            self.btn_refresh_history.setEnabled(True)
            self.item_combo.setEnabled(True)
            self.time_combo.setEnabled(True)

    def render_logs(self, acks):
        valid_acks = [ack for ack in acks if ack.get("message", "").strip()]
        self.tabs.setTabText(2, tr("lbl_user_msg", "사용자 메시지 ({cnt})").format(cnt=len(valid_acks)))
        
        text_c = "#374151" if self.is_light else "#E4E4E7"
        date_c = "#2563EB" if self.is_light else "#60A5FA"
        dim_c = "#6B7280" if self.is_light else "#A1A1AA"
        line_c = "#E5E7EB" if self.is_light else "#3F3F46"

        if not valid_acks:
            self.log_browser.setHtml(f"<p style='color: {dim_c}; margin: 14px;'>{tr('msg_no_messages', '메시지가 없습니다.')}</p>")
        else:
            log_html = "<div style='margin: 10px;'>"
            for ack in valid_acks:
                time_str = ack.get('time', '')
                user_str = ack.get('user', 'Unknown User')
                msg_str = ack.get('message', '').replace(chr(10), '<br>')
                log_html += f"<div style='margin-bottom: 15px;'><span style='color: {date_c}; font-weight: bold;'>[{time_str}] {user_str}</span><br><span style='color: {text_c};'>{msg_str}</span></div><hr style='border: 0; border-top: 1px dashed {line_c};'>"
            self.log_browser.setHtml(log_html + "</div>")

    def refresh_log_data(self):
        self.btn_refresh_log.setText(tr("msg_refreshing", "⏳ 새로고침 중..."))
        self.btn_refresh_log.setEnabled(False)
        QApplication.processEvents() 
        
        try:
            params = {
                "eventids": [self.issue_data["eventid"]],
                "selectAcknowledges": "extend",
                "source": 0, "object": 0
            }
            problems = zabbix_api_call(self.config, "problem.get", params)
            
            if problems:
                acks = problems[0].get("acknowledges", [])
                user_ids = list({ack["userid"] for ack in acks if "userid" in ack and ack["userid"] != "0"})
                user_map = {}
                if user_ids:
                    user_res = zabbix_api_call(self.config, "user.get", {
                        "output": ["userid", "name", "surname", "username", "alias"], 
                        "userids": user_ids
                    })
                    for u in user_res:
                        name_str = u.get('name', '').strip()
                        surname_str = u.get('surname', '').strip()
                        
                        if any('가' <= c <= '힣' for c in name_str + surname_str):
                            if len(name_str) == 1 and len(surname_str) == 2: full_name = f"{name_str}{surname_str}"
                            elif len(surname_str) == 1 and len(name_str) == 2: full_name = f"{surname_str}{name_str}"
                            else: full_name = f"{surname_str}{name_str}".strip()
                        else: full_name = f"{name_str} {surname_str}".strip()

                        if not full_name: full_name = u.get("username", u.get("alias", "Unknown"))
                        user_map[u["userid"]] = full_name
                
                formatted_acks = []
                for ack in acks:
                    if ack.get("message"):
                        ack_time = datetime.fromtimestamp(int(ack["clock"])).strftime('%Y-%m-%d %H:%M:%S')
                        uid = str(ack.get("userid", "0"))
                        user_name = user_map.get(uid, tr("lbl_unknown_user", "알 수 없는 사용자 {uid}").format(uid=uid))
                        formatted_acks.append({"time": ack_time, "user": user_name, "message": ack["message"]})
                        
                self.render_logs(formatted_acks)
                
        except Exception as e:
            custom_msgbox(QMessageBox.Warning, tr("title_error", "오류"), tr("msg_log_refresh_fail", "로그 새로고침 실패:\n{err}").format(err=str(e)), self)
        finally:
            self.btn_refresh_log.setText(tr("btn_refresh", "🔄 새로고침"))
            self.btn_refresh_log.setEnabled(True)

class AlertCircle(QWidget):
    def __init__(self, hex_color, severity_name):
        super().__init__()
        self.circle_color = QColor(hex_color)
        self.severity_name = severity_name
        self.problems = [] 
        self.alert_count = 0
        self.is_first_load = True
        self.is_error_state = False
        self.error_char = ""
        self._is_dragging = False
        self._drag_start_pos = QPoint()
        self.list_window = None

        self.current_opacity = 1.0
        self.opacity_anim = QVariantAnimation()
        self.opacity_anim.setDuration(250) 
        self.opacity_anim.valueChanged.connect(self._update_opacity)

        self.is_highlighted = False
        self.blink_toggle = False
        self.highlight_type = "created" 
        
        self.highlight_timer = QTimer(self)
        self.highlight_timer.setSingleShot(True)
        self.highlight_timer.timeout.connect(self.clear_highlight)

        self.blink_toggle_timer = QTimer(self)
        self.blink_toggle_timer.timeout.connect(self._toggle_blink_state)
        
    def set_error_state(self, char):
        self.is_error_state = True
        self.error_char = char
        self.blink_toggle = True
        self.blink_toggle_timer.start(500) 
        self.update()

    def clear_error_state(self):
        self.is_error_state = False
        self.error_char = ""
        self.blink_toggle_timer.stop()
        self.blink_toggle = False
        self.update()
    
    def trigger_highlight(self, highlight_type):
        self.highlight_type = highlight_type
        self.is_highlighted = True
        self.blink_toggle = True
        self.update()
        self.blink_toggle_timer.start(300) 
        self.highlight_timer.start(3000)

    def _toggle_blink_state(self):
        self.blink_toggle = not self.blink_toggle
        self.update()

    def clear_highlight(self):
        if self.is_error_state: return
        self.is_highlighted = False
        self.blink_toggle = False
        self.blink_toggle_timer.stop()
        self.update()

    def update_data(self, problems_list):
        if self.is_first_load:
            self.problems = problems_list
            self.alert_count = len(problems_list)
            self.is_first_load = False
            
            target_opacity = 1.0 if self.alert_count > 0 else 0.3
            if not self.underMouse() and self.current_opacity != target_opacity:
                self.opacity_anim.stop()
                self.opacity_anim.setStartValue(self.current_opacity)
                self.opacity_anim.setEndValue(target_opacity)
                self.opacity_anim.start()
            self.update()
            return

        old_ids = {str(p['eventid']) for p in self.problems}
        new_ids = {str(p['eventid']) for p in problems_list}

        created = [p for p in problems_list if str(p['eventid']) not in old_ids]
        resolved = [p for p in self.problems if str(p['eventid']) not in new_ids]

        self.problems = problems_list
        self.alert_count = len(problems_list)

        if created:
            self.trigger_highlight('created')
        elif resolved:
            self.trigger_highlight('resolved')
            
        target_opacity = 1.0 if self.alert_count > 0 else 0.3
        if self.current_opacity != target_opacity and not self.underMouse():
            self.current_opacity = target_opacity
        self.update()

    def _update_opacity(self, value):
        self.current_opacity = value
        self.update() 

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        theme = self.window().config.get("theme", "circle")
        is_light = self.window().config.get("color_mode", "dark") == "light"
        
        # ★ 핵심 1: 애니메이션 진행도를 0.0 ~ 1.0 사이의 비율로 정규화
        progress = max(0.0, min(1.0, (self.current_opacity - 0.3) / 0.7))
        
        base_bg = QColor(255, 255, 255, 240) if is_light else QColor(28, 28, 32, 230)

        if self.is_error_state:
            glow_color = QColor(231, 76, 60)
            border_color = glow_color if self.blink_toggle else (QColor(0, 0, 0, 30) if is_light else QColor(255, 255, 255, 50))
            text_color = glow_color if self.blink_toggle else (QColor(31, 41, 55) if is_light else QColor(255, 255, 255))
            num_color = text_color
        else:
            if self.is_highlighted:
                if is_light:
                    glow_color = QColor(31, 41, 55) if self.highlight_type == 'created' else QColor(16, 185, 129)
                else:
                    glow_color = QColor(255, 255, 255) if self.highlight_type == 'created' else QColor(46, 204, 113)
                    
                border_color = glow_color if self.blink_toggle else self.circle_color
                text_color = glow_color if self.blink_toggle else (QColor(31, 41, 55) if is_light else QColor(255, 255, 255))
                num_color = text_color
            else:
                glow_color = self.circle_color
                
                # 부드러운 테두리 투명도 보간 (흐릿함 -> 선명함)
                active_border_alpha = 255 if is_light else 180
                current_border_alpha = int(active_border_alpha * (0.3 + 0.7 * progress))
                border_color = QColor(glow_color.red(), glow_color.green(), glow_color.blue(), current_border_alpha)
                
                active_text = QColor(31, 41, 55) if is_light else QColor(255, 255, 255)
                inactive_text = QColor(156, 163, 175) if is_light else QColor(113, 113, 122) # 회색
                
                if self.alert_count == 0:
                    # ★ 핵심 2: 글자색을 회색 -> 원래 색상으로 프레임마다 부드럽게 섞어줌 (깜빡임 제거)
                    r = int(inactive_text.red() + (active_text.red() - inactive_text.red()) * progress)
                    g = int(inactive_text.green() + (active_text.green() - inactive_text.green()) * progress)
                    b = int(inactive_text.blue() + (active_text.blue() - inactive_text.blue()) * progress)
                    text_color = QColor(r, g, b)
                    
                    # 숫자 색상도 동일하게 서서히 밝아지도록 보간
                    dim_num = QColor(glow_color.red(), glow_color.green(), glow_color.blue(), 80)
                    nr = int(dim_num.red() + (glow_color.red() - dim_num.red()) * progress)
                    ng = int(dim_num.green() + (glow_color.green() - dim_num.green()) * progress)
                    nb = int(dim_num.blue() + (glow_color.blue() - dim_num.blue()) * progress)
                    na = int(dim_num.alpha() + (glow_color.alpha() - dim_num.alpha()) * progress)
                    num_color = QColor(nr, ng, nb, na)
                else:
                    text_color = active_text
                    num_color = glow_color

        painter.setBrush(QBrush(base_bg))
        pen_width = 3 if self.is_highlighted or self.is_error_state else 2
        painter.setPen(QPen(border_color, pen_width))
        
        rect = self.rect().adjusted(2, 2, -2, -2)
        if "rectangle" in theme:
            painter.drawRoundedRect(rect, 12, 12)
        else:
            painter.drawEllipse(rect)

        if self.is_error_state:
            painter.setPen(text_color)
            font = QFont("IBM Plex Sans KR") 
            font.setPixelSize(int(self.width() * 0.4)) 
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(0, 0, self.width(), self.height(), Qt.AlignCenter, self.error_char)
            return

        painter.setPen(text_color)
        font = QFont("IBM Plex Sans KR") 
        font.setBold(True) 
        
        # ★ 수정 1: 시작 폰트 크기를 다시 큼직하게(0.24) 잡습니다. (짧은 한글을 위해)
        pixel_size = int(self.width() * 0.24)
        font.setPixelSize(pixel_size)
        fm = QFontMetrics(font)
        
        # ★ 수정 2: 글자의 가로 길이가 여백 한계치(너비 - 20px)를 넘을 때만 강제로 폰트를 줄입니다.
        # (영어처럼 긴 단어만 이 반복문을 타면서 크기가 작아집니다)
        max_text_width = self.width() - 20
        while fm.boundingRect(self.severity_name).width() > max_text_width and pixel_size > 8:
            pixel_size -= 1
            font.setPixelSize(pixel_size)
            fm = QFontMetrics(font)

        painter.setFont(font)
        painter.drawText(0, int(self.height() * 0.15), self.width(), int(self.height() * 0.35), Qt.AlignCenter, self.severity_name)

        # 알림 숫자 라벨 (하단) - 숫자 크기도 보기 좋게 0.34로 살짝 키웠습니다
        font.setPixelSize(int(self.width() * 0.34))
        painter.setFont(font)
        
        # 적용된 보간 색상으로 렌더링
        painter.setPen(num_color)
        painter.drawText(0, int(self.height() * 0.45), self.width(), int(self.height() * 0.45), Qt.AlignCenter, str(self.alert_count))

    def enterEvent(self, event):
        if self.is_error_state: return 
        self.opacity_anim.stop()
        self.opacity_anim.setStartValue(self.current_opacity)
        self.opacity_anim.setEndValue(1.0) 
        self.opacity_anim.start()

    def leaveEvent(self, event):
        if self.is_error_state: return
        self.opacity_anim.stop()
        self.opacity_anim.setStartValue(self.current_opacity)
        target_opacity = 1.0 if self.is_first_load else (0.3 if self.alert_count == 0 else 1.0)
        self.opacity_anim.setEndValue(target_opacity)
        self.opacity_anim.start()

    def contextMenuEvent(self, event):
        self.window().main_menu.exec_(event.globalPos())

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._is_dragging = False
            self._drag_start_pos = event.globalPos() - self.window().pos()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self._is_dragging = True
            new_pos = event.globalPos() - self._drag_start_pos
            screen = QApplication.screenAt(event.globalPos())
            if not screen: screen = QApplication.primaryScreen()
            rect = screen.availableGeometry()
            margin = 30  
            nx, ny = new_pos.x(), new_pos.y()
            win_w, win_h = self.window().width(), self.window().height()
            
            if abs(nx - rect.left()) < margin: nx = rect.left()
            elif abs(nx + win_w - rect.right()) < margin: nx = rect.right() - win_w
            if abs(ny - rect.top()) < margin: ny = rect.top()
            elif abs(ny + win_h - rect.bottom()) < margin: ny = rect.bottom() - win_h
            
            # 1. 메인 창 이동
            self.window().move(nx, ny)
            
            # 2. 메인 창이 이동하자마자 자석처럼 리스트 창의 위치를 업데이트
            self.update_list_position()
            
            # 혹시 다른 원의 리스트 창이 열려있다면 그것도 끌고 옴
            if hasattr(self.window(), 'circles'):
                for circle in self.window().circles:
                    if circle != self and getattr(circle, 'list_window', None) and circle.list_window.isVisible():
                        circle.update_list_position()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.is_error_state: return 
            if not self._is_dragging:
                if not self.window().is_resize_mode:
                    self.window().toggle_circle_list(self)
            else:
                self.window().save_current_settings()

    # 리스트 창의 위치만 계산하는 전용 모듈
    def update_list_position(self):
        try:
            if not getattr(self, 'list_window', None): return
            
            screen = QApplication.screenAt(self.mapToGlobal(self.rect().center()))
            if not screen: screen = QApplication.primaryScreen()
            if not screen: return
                
            rect = screen.availableGeometry()
            layout_dir = self.window().config.get("layout_direction", "vertical")
            theme = self.window().config.get("theme", "circle")

            if "2x3" in theme:
                main_win = self.window()
                win_tl = main_win.mapToGlobal(QPoint(0, 0))
                margin = 15
                visual_left = win_tl.x() + margin
                visual_right = win_tl.x() + main_win.width() - margin
                visual_top = win_tl.y() + margin
                visual_bottom = win_tl.y() + main_win.height() - margin
                
                center_x = win_tl.x() + main_win.width() // 2
                center_y = win_tl.y() + main_win.height() // 2

                if layout_dir == "vertical":
                    right_x = visual_right + 10
                    left_x = visual_left - self.list_window.width() - 10
                    target_y = center_y - self.list_window.height() // 2
                    if target_y < rect.top(): target_y = rect.top()
                    elif target_y + self.list_window.height() > rect.bottom(): target_y = rect.bottom() - self.list_window.height()
                    if right_x + self.list_window.width() <= rect.right(): target_x = right_x
                    elif left_x >= rect.left(): target_x = left_x
                    else: target_x = max(rect.left(), min(right_x, rect.right() - self.list_window.width()))
                else:
                    bottom_y = visual_bottom + 10
                    top_y = visual_top - self.list_window.height() - 10
                    target_x = center_x - self.list_window.width() // 2
                    if target_x < rect.left(): target_x = rect.left()
                    elif target_x + self.list_window.width() > rect.right(): target_x = rect.right() - self.list_window.width()
                    if bottom_y + self.list_window.height() <= rect.bottom(): target_y = bottom_y
                    elif top_y >= rect.top(): target_y = top_y
                    else: target_y = max(rect.top(), min(bottom_y, rect.bottom() - self.list_window.height()))

            elif layout_dir == "vertical":
                circle_top_left = self.mapToGlobal(self.rect().topLeft())
                circle_top_right = self.mapToGlobal(self.rect().topRight())
                right_x = circle_top_right.x() + 10
                left_x = circle_top_left.x() - self.list_window.width() - 10
                target_y = circle_top_left.y() + (self.height() - self.list_window.height()) // 2
                if target_y < rect.top(): target_y = rect.top()
                elif target_y + self.list_window.height() > rect.bottom(): target_y = rect.bottom() - self.list_window.height()
                if right_x + self.list_window.width() <= rect.right(): target_x = right_x
                elif left_x >= rect.left(): target_x = left_x
                else: target_x = max(rect.left(), min(right_x, rect.right() - self.list_window.width()))
            else:
                circle_top_left = self.mapToGlobal(self.rect().topLeft())
                circle_bottom_left = self.mapToGlobal(self.rect().bottomLeft())
                bottom_y = circle_bottom_left.y() + 10
                top_y = circle_top_left.y() - self.list_window.height() - 10
                target_x = circle_top_left.x() + (self.width() - self.list_window.width()) // 2
                if target_x < rect.left(): target_x = rect.left()
                elif target_x + self.list_window.width() > rect.right(): target_x = rect.right() - self.list_window.width()
                if bottom_y + self.list_window.height() <= rect.bottom(): target_y = bottom_y
                elif top_y >= rect.top(): target_y = top_y
                else: target_y = max(rect.top(), min(bottom_y, rect.bottom() - self.list_window.height()))

            self.list_window.move(target_x, target_y)
        except Exception as e:
            pass

    def show_list_window(self):
        self.list_window = AlertListWindow(
            self.severity_name, self.circle_color.name(), self.problems,
            self.window().config.get("items_per_page", 5), self.window().config, self.window()
        )
        # 리스트 창이 생성되자마자 알맞은 위치로 이동시킴
        self.update_list_position()
        self.list_window.show()

def get_arrow_path():
    arrow_path = os.path.join(CONFIG_DIR, "down_arrow.png")
    if not os.path.exists(arrow_path):
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor("#7F8C8D"))
        painter.setPen(Qt.NoPen)
        painter.drawPolygon(QPolygonF([QPointF(3, 6), QPointF(13, 6), QPointF(8, 12)]))
        painter.end()
        pixmap.save(arrow_path, "PNG")
    return arrow_path.replace("\\", "/")

# ==========================================
# ★ 최근 알림 히스토리 뷰어 창 (필터링 & 자동 새로고침)
# ==========================================
class AlertHistoryDialog(QDialog):
    def __init__(self, main_widget, parent=None):
        super().__init__(parent)
        self.main_widget = main_widget  # 실시간 데이터를 불러오기 위해 메인 위젯을 연결
        max_count = self.main_widget.config.get('history_max_count', 100)
        self.setWindowTitle(f"{tr('title_history', '최근 알림 히스토리')} (Max {max_count})")
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint) 
        self.resize(550, 450)
        
        self.setStyleSheet("""
            QDialog { background-color: #FFFFFF; }
            QScrollBar:vertical { background: transparent; width: 10px; margin: 0px; }
            QScrollBar::handle:vertical { background: #E0E0E0; min-height: 30px; border-radius: 5px; margin: 2px; }
            QScrollBar::handle:vertical:hover { background: #C0C0C0; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; border: none; background: none; }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
        """)
        
        layout = QVBoxLayout(self)
        
        # 상단 레이아웃 (제목 & 필터)
        header_layout = QHBoxLayout()
        header_lbl = QLabel(tr("title_realtime_history", "🕒 실시간 알림 내역"))
        header_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #2C3E50; font-family: 'IBM Plex Sans KR', sans-serif;")
        header_layout.addWidget(header_lbl)
        
        header_layout.addStretch()
        
        # ★ 콤보박스 화살표 복구 (자동 생성된 PNG 이미지 활용)
        self.filter_combo = QComboBox()
        self.filter_combo.addItems([tr("filter_all", "전체보기"), tr("sev_disaster", "심각"), tr("sev_high", "중증"), tr("sev_average", "경미"), tr("sev_warning", "경고"), tr("sev_info", "정보"), tr("sev_not_cls", "미정"), tr("sev_system", "기타 (시스템)")])
        self.filter_combo.setCursor(Qt.PointingHandCursor)
        
        arrow_url = get_arrow_path()
        self.filter_combo.setStyleSheet("""
            QComboBox {
                font-family: 'IBM Plex Sans KR', sans-serif; 
                padding: 4px 8px; 
                font-size: 12px; 
                background-color: #F8F9FA;
                border: 1px solid #C8D0D8;
                border-radius: 4px;
            }
            QComboBox::drop-down { 
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 24px;
                border-left-width: 0px;
            }
            QComboBox::down-arrow { 
                image: url('""" + arrow_url + """');
                width: 16px; height: 16px;
            }
            QComboBox QAbstractItemView {
                background-color: #FFFFFF;
                border: 1px solid #C8D0D8;
                selection-background-color: #E5E7EB;
                selection-color: #2C3E50;
                outline: none;
            }
        """)
        self.filter_combo.currentIndexChanged.connect(self.update_view)
        header_layout.addWidget(self.filter_combo)
        
        layout.addLayout(header_layout)
        
        self.browser = QTextBrowser()
        self.browser.setStyleSheet("background-color: #F8F9FA; border: 1px solid #C8D0D8; font-family: 'IBM Plex Sans KR', sans-serif; font-size: 12px;")
        layout.addWidget(self.browser)
        
        close_btn = QPushButton(tr("btn_close", "닫기"))
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("QPushButton { padding: 6px 20px; background-color: #E74C3C; color: white; border: none; border-radius: 4px; font-weight: bold; font-family: 'IBM Plex Sans KR', sans-serif; } QPushButton:hover { background-color: #C0392B; }")
        close_btn.clicked.connect(self.close)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)
        
        # 자동 새로고침 타이머 (1초마다 데이터 변경 감지)
        self.last_history_len = -1
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_auto_refresh)
        self.timer.start(1000) 
        
        self.update_view()
        
    def check_auto_refresh(self):
        current_len = len(self.main_widget.alert_history)
        if current_len == 0:
            if self.last_history_len != 0: self.update_view()
        else:
            top_item_time = self.main_widget.alert_history[0]['time']
            # 개수가 변했거나, 가장 최신 알림의 시간이 달라졌다면 즉시 화면 갱신 처리
            if current_len != self.last_history_len or getattr(self, 'last_top_time', '') != top_item_time:
                self.update_view()
                self.last_top_time = top_item_time
        
    def update_view(self):
        self.last_history_len = len(self.main_widget.alert_history)
        history_data = self.main_widget.alert_history
        filter_text = self.filter_combo.currentText()
        
        if not history_data:
            self.browser.setHtml(f"<p style='color: gray; padding: 10px;'>{tr('msg_no_recent_alerts', '최근 발생한 알림이 없습니다.')}</p>")
            return
            
        color_map = {
            "심각": "#E74C3C",  # 빨강
            "중증": "#E67E22",  # 진주황
            "경미": "#F39C12",  # 주황 (기존 위젯 색상 동일)
            "경고": "#F1C40F",  # 노랑
            "정보": "#3498DB",  # 파랑
            "미정": "#95A5A6",  # 회색
            "🚨 시스템": "#E74C3C",
            "✅ 시스템": "#2ECC71"
        }
            
        html = "<div style='padding: 5px;'>"
        match_count = 0
        for item in history_data:
            lvl = item['level']
            
            # ★ 필터링 로직
            if filter_text != "전체보기":
                if filter_text == "기타 (시스템)":
                    if lvl not in ["🚨 시스템", "✅ 시스템"]: continue
                else:
                    if lvl != filter_text: continue
                    
            # 딕셔너리에서 색상을 찾아오고, 없으면 기본 진남색 적용
            color = color_map.get(lvl, "#2C3E50")
            
            html += f"<div style='margin-bottom: 10px;'>"
            html += f"<span style='color: #7F8C8D; font-size: 11px;'>[{item['time']}]</span> "
            html += f"<strong style='color: {color};'>[{lvl}]</strong> "
            msg_html = item['msg'].replace('\n', '<br>')
            html += f"<span style='color: #2C3E50;'>{msg_html}</span>"
            html += f"</div><hr style='border: 0; border-top: 1px dashed #E5E7EB;'>"
            match_count += 1
            
        html += "</div>"
        
        if match_count == 0:
            html = f"<p style='color: gray; padding: 10px;'>선택한 조건({filter_text})에 해당하는 알림이 없습니다.</p>"
            
        self.browser.setHtml(html)

class ZabbixDesktopWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.config = load_config()
        apply_debug_level(self.config.get("debug_mode", False))
        self.toast_manager = ToastManager(self, self.config)
        self.is_resize_mode = False
        self.in_error_state = False 
        self.alert_history = []
        self._resize_corner = None
        self._resize_start_global = QPoint()
        self._resize_start_size = 0
        self._resize_start_geometry = None
        self._is_moving = False
        self._move_start_pos = QPoint()
        self._backup_size = 0
        self._backup_pos = QPoint()
        
        self.initUI()
        self.init_global_menu() 
        self.init_system_tray() 
        self.setMouseTracking(True)
        
        for screen in QApplication.screens():
            screen.availableGeometryChanged.connect(self.ensure_within_screen)
        
        self.api_timer = QTimer(self)
        self.api_timer.timeout.connect(self.fetch_zabbix_data)
        self.api_timer.start(self.config["refresh_interval"] * 1000) 
        self.fetch_zabbix_data()

    def initUI(self):
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        flags = Qt.FramelessWindowHint | Qt.Tool
        if self.config.get("always_on_top", False): flags |= Qt.WindowStaysOnTopHint
        else: flags |= Qt.WindowStaysOnBottomHint
        self.setWindowFlags(flags)
        
        self.main_layout = QGridLayout()
        self.main_layout.setSpacing(0 if "rectangle" in self.config.get("theme", "") else 15)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        
        self.circle_disaster = AlertCircle("#E74C3C", tr("sev_disaster", "심각"))  
        self.circle_high     = AlertCircle("#E67E22", tr("sev_high", "중증"))  
        self.circle_average  = AlertCircle("#F39C12", tr("sev_average", "경미"))  
        self.circle_warning  = AlertCircle("#F1C40F", tr("sev_warning", "경고"))  
        self.circle_info     = AlertCircle("#3498DB", tr("sev_info", "정보"))  
        self.circle_not_cls  = AlertCircle("#95A5A6", tr("sev_not_cls", "미정")) 
        
        self.circles = [self.circle_disaster, self.circle_high, self.circle_average, self.circle_warning, self.circle_info, self.circle_not_cls]
        
        for circle in self.circles:
            circle.setFixedSize(self.config["circle_size"], self.config["circle_size"])
            
        self.setLayout(self.main_layout)
        self.apply_layout_direction() 
        self.move(self.config["x"], self.config["y"])
        self.ensure_within_screen() 
        
        self.resize_ui_container = QWidget(self)
        self.resize_ui_container.setStyleSheet("background-color: rgba(44, 62, 80, 230); border-radius: 8px; border: 1px solid #7F8C8D;")
        ui_layout = QHBoxLayout(self.resize_ui_container)
        ui_layout.setContentsMargins(15, 8, 15, 8)
        
        self.btn_apply = QPushButton(f"✅ {tr('btn_ok', '확인')}")
        self.btn_cancel_resize = QPushButton(f"❌ {tr('btn_cancel', '취소')}")
        
        btn_style = """
            QPushButton { color: white; background-color: rgba(255, 255, 255, 30); border: 1px solid #BDC3C7; border-radius: 4px; padding: 6px 12px; font-weight: bold; font-family: 'IBM Plex Sans KR', sans-serif; outline: none; }
            QPushButton:hover { background-color: rgba(255, 255, 255, 60); }
        """
        self.btn_apply.setStyleSheet(btn_style)
        self.btn_cancel_resize.setStyleSheet(btn_style)
        self.btn_apply.setCursor(Qt.PointingHandCursor)
        self.btn_cancel_resize.setCursor(Qt.PointingHandCursor)
        
        self.btn_apply.clicked.connect(self.apply_resize)
        self.btn_cancel_resize.clicked.connect(self.cancel_resize)
        
        ui_layout.addWidget(self.btn_apply)
        ui_layout.addWidget(self.btn_cancel_resize)
        self.resize_ui_container.hide()
        
    def update_menu_style(self):
        is_light = self.config.get("color_mode", "dark") == "light"
        
        bg_color = "#FFFFFF" if is_light else "#1C1C20"
        text_color = "#2C3E50" if is_light else "#F4F4F5"
        border_color = "#C8D0D8" if is_light else "#3F3F46"
        sel_bg = "#3498DB" if is_light else "#2563EB"
        sep_color = "#E5E7EB" if is_light else "#3F3F46"
        
        menu_style = f"""
            QMenu {{ 
                background-color: {bg_color}; 
                border: 1px solid {border_color}; 
                padding: 6px; 
            }} 
            QMenu::item {{ 
                padding: 7px 28px 7px 28px; 
                color: {text_color};
            }} 
            QMenu::item:selected {{ 
                background-color: {sel_bg}; 
                color: white; 
                border-radius: 4px;
            }} 
            QMenu::separator {{ 
                height: 1px; 
                background: {sep_color}; 
                margin: 4px 8px; 
            }}
        """
        self.main_menu.setStyleSheet(menu_style)

    def ensure_within_screen(self, *args):
        # ★ 핵심: 무조건 1번 모니터가 아니라, 현재 위젯 좌표가 속한 모니터를 동적으로 찾음
        screen = QApplication.screenAt(self.pos())
        if not screen: 
            screen = QApplication.primaryScreen()
        if not screen: return
        
        rect = screen.availableGeometry()
        win_geom = self.geometry()
        
        nx = win_geom.x()
        ny = win_geom.y()
        
        if nx + win_geom.width() > rect.right():
            nx = rect.right() - win_geom.width()
        if ny + win_geom.height() > rect.bottom():
            ny = rect.bottom() - win_geom.height()
            
        if nx < rect.left(): nx = rect.left()
        if ny < rect.top(): ny = rect.top()
        
        if nx != win_geom.x() or ny != win_geom.y():
            logger.debug(tr_log(f"[UI 액션] 해상도 변경 감지: 위치 자동 보정 ({win_geom.x()},{win_geom.y()} -> {nx},{ny})", f"[UI Action] Resolution change detected: Position auto-corrected ({win_geom.x()},{win_geom.y()} -> {nx},{ny})"))
            self.move(nx, ny)
            self.save_current_settings()
            
            for circle in self.circles:
                if getattr(circle, 'list_window', None) and circle.list_window.isVisible():
                    circle.list_window.close()
        
    def apply_layout_direction(self):
        for circle in self.circles:
            self.main_layout.removeWidget(circle)
            
        direction = self.config.get("layout_direction", "vertical")
        theme = self.config.get("theme", "circle")
        
        for i, circle in enumerate(self.circles):
            if "2x3" in theme:  
                if direction == "horizontal":
                    self.main_layout.addWidget(circle, i // 3, i % 3)
                else:
                    self.main_layout.addWidget(circle, i // 2, i % 2)
            elif direction == "horizontal":
                self.main_layout.addWidget(circle, 0, i)
            else:
                self.main_layout.addWidget(circle, i, 0)
                
        self.adjustSize()

    def init_global_menu(self):
        self.main_menu = QMenu(self)
        self.update_menu_style()  # ★ 추가됨: 동적 스타일 적용
        self.main_menu.aboutToShow.connect(self.sync_menu_states)

        self.act_history = QAction(tr("menu_history", "🕒 최근 알림 히스토리"), self.main_menu)
        self.act_history.triggered.connect(self.show_history_dialog)
        self.main_menu.addAction(self.act_history)
        self.main_menu.addSeparator()

        self.act_resize = QAction(tr("menu_resize", "크기 조절"), self.main_menu, checkable=True)
        self.act_resize.triggered.connect(self.toggle_resize_mode)
        self.main_menu.addAction(self.act_resize)

        self.act_top = QAction(tr("menu_always_top", "항상 위 표시"), self.main_menu, checkable=True)
        self.act_top.triggered.connect(self.toggle_always_on_top)
        self.main_menu.addAction(self.act_top)

        self.act_auto = QAction(tr("menu_autostart", "부팅 시 자동실행"), self.main_menu, checkable=True)
        self.act_auto.triggered.connect(self.toggle_autostart)
        self.main_menu.addAction(self.act_auto)
        
        self.main_menu.addSeparator()

        theme_menu = self.main_menu.addMenu(tr("menu_theme", "모양"))
        self.act_circle = QAction(tr("theme_circle_1", "원형 (1줄)"), theme_menu, checkable=True)
        self.act_circle_2 = QAction(tr("theme_circle_2", "원형 (2줄)"), theme_menu, checkable=True) 
        self.act_rect = QAction(tr("theme_rect_1", "사각형 (1줄)"), theme_menu, checkable=True)
        self.act_rect_2 = QAction(tr("theme_rect_2", "사각형 (2줄)"), theme_menu, checkable=True) 
        self.act_circle.triggered.connect(lambda: self.set_theme("circle"))
        self.act_circle_2.triggered.connect(lambda: self.set_theme("circle_2x3")) 
        self.act_rect.triggered.connect(lambda: self.set_theme("rectangle"))
        self.act_rect_2.triggered.connect(lambda: self.set_theme("rectangle_2x3")) 
        theme_menu.addAction(self.act_circle)
        theme_menu.addAction(self.act_circle_2) 
        theme_menu.addAction(self.act_rect)
        theme_menu.addAction(self.act_rect_2) 

        layout_menu = self.main_menu.addMenu(tr("menu_layout", "배치 방향"))
        self.act_vert = QAction(tr("layout_vert", "세로 배치"), layout_menu, checkable=True)
        self.act_hori = QAction(tr("layout_hori", "가로 배치"), layout_menu, checkable=True)
        self.act_vert.triggered.connect(lambda: self.set_layout_direction("vertical"))
        self.act_hori.triggered.connect(lambda: self.set_layout_direction("horizontal"))
        layout_menu.addAction(self.act_vert)
        layout_menu.addAction(self.act_hori)

        self.main_menu.addSeparator()

        # ★ 추가됨: 업데이트 알림 On/Off 스위치
        self.act_noti_update = QAction(tr("menu_noti_update", "업데이트 알림 표시 (메시지/심각도 변경)"), self.main_menu, checkable=True)
        self.act_noti_update.triggered.connect(self.toggle_noti_update)
        self.main_menu.addAction(self.act_noti_update)
        self.main_menu.addSeparator()

        noti_menu = self.main_menu.addMenu(tr("menu_noti_duration", "알림 유지 시간"))
        self.dict_noti = {}
        noti_options = {0: tr("noti_off", "알림 끄기"), 3: tr("noti_3s", "3초"), 5: tr("noti_5s", "5초"), 7: tr("noti_7s", "7초 (권장)"), 10: tr("noti_10s", "10초"), 15: tr("noti_15s", "15초"), 30: tr("noti_30s", "30초"), -1: tr("noti_manual", "수동 종료 시까지")}
        for secs, label in noti_options.items():
            act = QAction(label, noti_menu, checkable=True)
            act.triggered.connect(lambda checked, s=secs: self.set_noti_duration(s))
            noti_menu.addAction(act)
            self.dict_noti[secs] = act

        pos_menu = self.main_menu.addMenu(tr("menu_noti_pos", "알림 위치"))
        self.dict_pos = {}
        for key, label_key, def_label in [("bottom_right", "pos_br", "우측 하단"), ("bottom_left", "pos_bl", "좌측 하단"), ("top_right", "pos_tr", "우측 상단"), ("top_left", "pos_tl", "좌측 상단")]:
            act = QAction(tr(label_key, def_label), pos_menu, checkable=True)
            act.triggered.connect(lambda checked, k=key: self.set_noti_position(k))
            pos_menu.addAction(act)
            self.dict_pos[key] = act

        refresh_menu = self.main_menu.addMenu(tr("menu_refresh_int", "새로고침 주기"))
        self.dict_ref = {}
        ref_options = {3: tr("ref_3s", "3초 (매우 빠름)"), 5: tr("ref_5s", "5초 (권장)"), 10: tr("ref_10s", "10초"), 30: tr("ref_30s", "30초")}
        for secs, label in ref_options.items():
            act = QAction(label, refresh_menu, checkable=True)
            act.triggered.connect(lambda checked, s=secs: self.set_refresh_interval(s))
            refresh_menu.addAction(act)
            self.dict_ref[secs] = act

        page_menu = self.main_menu.addMenu(tr("menu_items_page", "페이지당 표시 개수"))
        self.dict_page = {}
        for cnt in [3, 5, 7, 10, 15]:
            act = QAction(tr("item_count", "{cnt}개").format(cnt=cnt), page_menu, checkable=True)
            act.triggered.connect(lambda checked, c=cnt: self.set_items_per_page(c))
            page_menu.addAction(act)
            self.dict_page[cnt] = act
            
        self.main_menu.addSeparator()
        
        # (기존 코드) 언어 설정 메뉴 부분
        lang_menu = self.main_menu.addMenu(tr("menu_lang", "🌐 언어 (Language)"))
        self.act_lang_ko = QAction(tr("lang_ko", "한국어"), lang_menu, checkable=True)
        self.act_lang_en = QAction(tr("lang_en", "English"), lang_menu, checkable=True)
        self.act_lang_ko.triggered.connect(lambda: self.set_language("ko"))
        self.act_lang_en.triggered.connect(lambda: self.set_language("en"))
        lang_menu.addAction(self.act_lang_ko)
        lang_menu.addAction(self.act_lang_en)

        # ★ 여기에 새로운 '테마 색상' 메뉴 추가
        color_mode_menu = self.main_menu.addMenu(tr("menu_color_mode", "🎨 컬러 모드 (Color Mode)"))
        self.act_mode_dark = QAction(tr("mode_dark", "다크 모드 (Dark)"), color_mode_menu, checkable=True)
        self.act_mode_light = QAction(tr("mode_light", "라이트 모드 (Light)"), color_mode_menu, checkable=True)
        self.act_mode_dark.triggered.connect(lambda: self.set_color_mode("dark"))
        self.act_mode_light.triggered.connect(lambda: self.set_color_mode("light"))
        color_mode_menu.addAction(self.act_mode_dark)
        color_mode_menu.addAction(self.act_mode_light)
        
        # (기존 코드) 디버그 모드 계속...
        self.act_debug = QAction(tr("menu_debug", "디버그 모드 (로그 기록)"), self.main_menu, checkable=True)
        self.act_debug.triggered.connect(self.toggle_debug_mode)
        self.main_menu.addAction(self.act_debug)
        
        exit_action = QAction(tr("menu_exit", "프로그램 종료"), self.main_menu)
        exit_action.triggered.connect(lambda: QApplication.instance().exit(0))
        self.main_menu.addAction(exit_action)

        self.main_menu.addSeparator()
        version_action = QWidgetAction(self.main_menu)
        version_widget = QWidget()
        version_widget.setStyleSheet("background: transparent;")
        v_layout = QHBoxLayout(version_widget)
        v_layout.setContentsMargins(12, 4, 12, 4)
        
        hash_lbl = QLabel(f"#{BUILD_HASH}")
        hash_lbl.setStyleSheet("color: #BDC3C7; font-size: 10px; font-family: 'IBM Plex Sans KR', sans-serif;")
        ver_lbl = QLabel(APP_VERSION)
        ver_lbl.setStyleSheet("color: #95A5A6; font-size: 10px; font-weight: bold; font-family: 'IBM Plex Sans KR', sans-serif;")
        
        v_layout.addWidget(hash_lbl)
        v_layout.addStretch()
        v_layout.addWidget(ver_lbl)
        
        version_action.setDefaultWidget(version_widget)
        version_action.setEnabled(False) 
        self.main_menu.addAction(version_action)

    # ★ 수정됨: config.json에 설정된 history_max_count 값만큼 잘라내서 저장
    def add_history_log(self, level, msg):
        dt = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.alert_history.insert(0, {"time": dt, "level": level, "msg": msg})
        
        max_count = self.config.get("history_max_count", 100)
        if len(self.alert_history) > max_count:
            self.alert_history = self.alert_history[:max_count]

    # ★ 수정됨: 다이얼로그에 메인 위젯(self)을 통째로 넘겨서 실시간 갱신이 가능하도록 함
    def show_history_dialog(self):
        logger.debug(tr_log("[UI 액션] 알림 히스토리 다이얼로그 열기", "[UI Action] Alert history dialog opened"))
        dlg = AlertHistoryDialog(self, self)
        dlg.exec_()

    def sync_menu_states(self):
        logger.debug(tr_log("[UI 액션] 설정 메뉴(우클릭) 열기", "[UI Action] Settings menu (right-click) opened"))
        self.act_resize.setChecked(self.is_resize_mode)
        self.act_top.setChecked(self.config.get("always_on_top", False))
        self.act_auto.setChecked(self.config.get("autostart", False))
        self.act_circle.setChecked(self.config.get("theme", "circle") == "circle")
        self.act_circle_2.setChecked(self.config.get("theme", "circle") == "circle_2x3") 
        self.act_rect.setChecked(self.config.get("theme", "circle") == "rectangle")
        self.act_rect_2.setChecked(self.config.get("theme", "circle") == "rectangle_2x3") 
        self.act_vert.setChecked(self.config.get("layout_direction", "vertical") == "vertical")
        self.act_hori.setChecked(self.config.get("layout_direction", "vertical") == "horizontal")
        current_lang = self.config.get("language", "ko")
        self.act_lang_ko.setChecked(current_lang == "ko")
        self.act_lang_en.setChecked(current_lang == "en")
        
        # ★ 추가됨: 다크/라이트 모드 체크 상태 동기화
        current_color_mode = self.config.get("color_mode", "dark")
        self.act_mode_dark.setChecked(current_color_mode == "dark")
        self.act_mode_light.setChecked(current_color_mode == "light")
        
        for val, act in self.dict_noti.items(): act.setChecked(val == self.config.get("noti_duration", 7))
        for val, act in self.dict_pos.items(): act.setChecked(val == self.config.get("noti_position", "bottom_right"))
        for val, act in self.dict_ref.items(): act.setChecked(val == self.config.get("refresh_interval", 5))
        for val, act in self.dict_page.items(): act.setChecked(val == self.config.get("items_per_page", 5))
        self.act_debug.setChecked(self.config.get("debug_mode", False)) 
        self.act_noti_update.setChecked(self.config.get("noti_on_update", True))

    # 언어 변경 실행 함수
    def set_language(self, lang_code):
        if self.config.get("language") == lang_code: return
        self.config["language"] = lang_code
        self.save_current_settings()
        
        _translator.load_language(lang_code)
        
        self.api_timer.stop()
        for circle in self.circles:
            if getattr(circle, 'list_window', None) and circle.list_window.isVisible():
                circle.list_window.close()
                
        # ★ 추가됨: 앱 재시작 시 떠있는 알림(Toast)이 참조 오류를 일으키지 않도록 즉시 강제 파괴
        for t in list(self.toast_manager.toasts):
            t.is_closing = True
            t.close()
        self.toast_manager.toasts.clear()
                
        if hasattr(self, 'tray') and self.tray is not None:
            self.tray.hide()
            
        QApplication.instance().exit(1337)

    def set_color_mode(self, mode):
        logger.debug(tr_log(f"[UI 액션] 컬러 모드 변경: {mode}", f"[UI Action] Color mode changed: {mode}"))
        self.config["color_mode"] = mode
        self.save_current_settings()
        
        self.update_menu_style()  # ★ 추가됨: 메뉴 스타일 즉시 갱신
        
        # 열려있는 창 모두 닫기 및 즉시 색상 업데이트
        for circle in self.circles:
            if getattr(circle, 'list_window', None) and circle.list_window.isVisible():
                circle.list_window.close()
            circle.update()
        
        self.toast_manager.clear_all()
        self.update()

    def init_system_tray(self):
        self.tray = QSystemTrayIcon(self)
        
        icon_path = os.path.join(BUNDLE_DIR, "zabbix_icon.ico")
        if not os.path.exists(icon_path): icon_path = os.path.join(CONFIG_DIR, "zabbix_icon.ico")
            
        if os.path.exists(icon_path):
            self.tray.setIcon(QIcon(icon_path))
        else:
            # 아이콘 파일이 없을 때만 기존 빨간 Z 로고 렌더링
            pixmap = QPixmap(64, 64)
            pixmap.fill(Qt.transparent)
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setBrush(QColor("#E74C3C"))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(2, 2, 60, 60)
            painter.setPen(QPen(Qt.white, 6))
            font = painter.font()
            font.setPixelSize(38)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(0, 0, 64, 64, Qt.AlignCenter, "Z")
            painter.end()
            self.tray.setIcon(QIcon(pixmap))
            
        self.tray.setToolTip(f"Zabbix Overlay Widget {APP_VERSION}")
        self.tray.setContextMenu(self.main_menu)
        self.tray.show()

    def toggle_circle_list(self, target_circle):
        logger.debug(tr_log(f"[UI 액션] '{target_circle.severity_name}' 알림 리스트 열기/닫기 클릭", f"[UI Action] '{target_circle.severity_name}' alert list open/close clicked"))
        for circle in self.circles:
            if circle != target_circle and getattr(circle, 'list_window', None) and circle.list_window.isVisible():
                circle.list_window.close()
        if getattr(target_circle, 'list_window', None) and target_circle.list_window.isVisible():
            target_circle.list_window.close()
        else:
            target_circle.show_list_window()

    def set_noti_duration(self, val):
        logger.debug(tr_log(f"[UI 액션] 알림 유지 시간 변경: {val}초", f"[UI Action] Notification duration changed: {val}s"))
        self.config["noti_duration"] = val
        self.save_current_settings()

    def set_noti_position(self, val):
        logger.debug(tr_log(f"[UI 액션] 알림 위치 변경: {val}", f"[UI Action] Notification position changed: {val}"))
        self.config["noti_position"] = val
        self.save_current_settings()
        self.toast_manager.rearrange()

    def set_refresh_interval(self, val):
        logger.debug(tr_log(f"[UI 액션] 새로고침 주기 변경: {val}초", f"[UI Action] Refresh interval changed: {val}s"))
        self.config["refresh_interval"] = val
        self.save_current_settings()
        self.api_timer.setInterval(val * 1000)

    def set_items_per_page(self, count):
        logger.debug(tr_log(f"[UI 액션] 리스트 페이지당 개수 변경: {count}개", f"[UI Action] Items per page changed: {count}"))
        self.config["items_per_page"] = count
        self.save_current_settings()
        for circle in self.circles:
            if getattr(circle, 'list_window', None) and circle.list_window.isVisible():
                circle.list_window.items_per_page = count
                circle.list_window.total_pages = max(1, (len(circle.list_window.problems_list) + count - 1) // count)
                if circle.list_window.current_page >= circle.list_window.total_pages:
                    circle.list_window.current_page = max(0, circle.list_window.total_pages - 1)
                circle.list_window.refresh_page()

    def set_theme(self, theme):
        logger.debug(tr_log(f"[UI 액션] 테마(모양) 변경: {theme}", f"[UI Action] Theme changed: {theme}"))
        self.config["theme"] = theme
        self.save_current_settings()
        self.main_layout.setSpacing(0 if "rectangle" in theme else 15)
        self.apply_layout_direction()
        for circle in self.circles: circle.update()

    def set_layout_direction(self, direction):
        logger.debug(tr_log(f"[UI 액션] 배치 방향 변경: {direction}", f"[UI Action] Layout direction changed: {direction}"))
        self.config["layout_direction"] = direction
        self.save_current_settings()
        self.apply_layout_direction()

    def toggle_always_on_top(self):
        logger.debug(tr_log(f"[UI 액션] 항상 위 표시 토글 변경: {self.act_top.isChecked()}", f"[UI Action] Always on top toggle changed: {self.act_top.isChecked()}"))
        self.config["always_on_top"] = self.act_top.isChecked()
        self.save_current_settings()
        
        self.api_timer.stop()
        
        # 1. 알림 리스트 창 안전 종료
        for circle in self.circles:
            if getattr(circle, 'list_window', None) and circle.list_window.isVisible():
                circle.list_window.close()
                circle.list_window.deleteLater()
                
        # 2. ★ 핵심: 떠 있는 Toast(알림창)들을 강제 파괴하여 C++ 참조 오류(Crash) 원천 차단
        for t in list(self.toast_manager.toasts):
            try:
                t.opacity_anim.stop()
                t.close()
                t.deleteLater()
            except:
                pass
        self.toast_manager.toasts.clear()
                
        if hasattr(self, 'tray') and self.tray is not None:
            self.tray.hide()
            
        # OS의 윈도우 포커스 탈취 방지 정책을 우회하기 위해 가장 확실한 방법인 "앱 재시작" 수행
        QApplication.instance().exit(1337)

    def fetch_zabbix_data(self):
        # ★ 추가: 기존 통신 스레드가 아직 일하고 있다면, 충돌 방지를 위해 이번 턴은 건너뜀
        if hasattr(self, 'worker') and self.worker.isRunning():
            logger.debug(tr_log("[API 갱신] 이전 통신이 아직 진행 중이므로 이번 요청은 건너뜁니다.", "[API Update] Previous request is still running, skipping this turn."))
            return
            
        logger.debug(tr_log("[API 갱신] 타이머 또는 수동 조작에 의해 Zabbix 데이터 갱신 요청", "[API Update] Zabbix data update requested by timer or manual action"))
        
        # 주기적으로 최상단 속성 및 실제 화면 컴포지팅 레이어 강제 재조립
        if self.config.get("always_on_top", False):
            apply_z_order(self, True)
            self.repaint()  # ★ 중요: Qt가 OS DWM에게 새로운 그래픽 버퍼를 강제로 밀어 넣어서 크롬의 독점 화면을 깨버림
            
            # 혹시 열려있는 알림 상세 리스트 창이 있다면 걔도 같이 밀어 올려줌
            for circle in self.circles:
                if getattr(circle, 'list_window', None) and circle.list_window.isVisible():
                    apply_z_order(circle.list_window, True)
                    circle.list_window.repaint()
                    
        self.worker = ZabbixWorker(self.config)
        self.worker.data_fetched.connect(self.on_data_fetched)
        self.worker.error_occurred.connect(self.on_api_error)
        self.worker.start()

    def on_data_fetched(self, categorized_data):
        if self.in_error_state:
            self.in_error_state = False
            logger.debug(tr_log("[API 상태] Zabbix 서버 연결 복구됨", "[API Status] Zabbix server connection restored"))
            # ★ 추가됨: 시스템 복구 알림 기록
            self.add_history_log("✅ 시스템", "Zabbix 서버 연결이 복구되었습니다.")
            if self.config.get("noti_duration", 7) != 0:
                self.toast_manager.show("✅ Zabbix 서버 연결이 복구되었습니다.", "resolved", self.config.get("noti_duration", 7))
            for circle in self.circles: circle.clear_error_state()

        # ★ 1. 알림 누락 방지 및 '복구/업데이트 알림'을 찾기 위해 기존 데이터 저장
        old_problems_dict = {}
        for c in self.circles:
            for p in c.problems:
                old_problems_dict[str(p['eventid'])] = (c.severity_name, p)

        new_problems = []
        updated_problems = [] # ★ 추가: 심각도 변경, 메시지 추가 등을 담을 리스트
        current_problems_set = set()

        # 2. 원형 위젯 데이터 업데이트 및 '새로운/업데이트 알림' 검출
        mapping = [
            ("5", self.circle_disaster, tr("sev_disaster", "심각")),
            ("4", self.circle_high, tr("sev_high", "중증")),
            ("3", self.circle_average, tr("sev_average", "경미")),
            ("2", self.circle_warning, tr("sev_warning", "경고")),
            ("1", self.circle_info, tr("sev_info", "정보")),
            ("0", self.circle_not_cls, tr("sev_not_cls", "미정"))
        ]

        for sev_key, circle, sev_name in mapping:
            sev_data = categorized_data.get(sev_key, [])
            circle.update_data(sev_data)
            
            for p in sev_data:
                ev_id = str(p['eventid'])
                current_problems_set.add(ev_id)
                # 기존에 없던 ID면 '발생'으로 추가
                if ev_id not in old_problems_dict:
                    new_problems.append((sev_name, p))
                else:
                    # ★ 추가됨: 기존에 있던 이벤트라도 심각도가 변했거나 메시지(ack)가 늘어났는지 체크!
                    old_sev_name, old_p = old_problems_dict[ev_id]
                    old_ack_count = len(old_p.get("acknowledges", []))
                    new_ack_count = len(p.get("acknowledges", []))
                    
                    if sev_name != old_sev_name or new_ack_count > old_ack_count:
                        updated_problems.append((sev_name, p, old_sev_name, new_ack_count > old_ack_count))

        # ★ 2-1. 기존엔 있었는데 이번 통신에 사라진 ID면 '복구'로 추가!
        resolved_problems = []
        for ev_id, (s_name, p) in old_problems_dict.items():
            if ev_id not in current_problems_set:
                resolved_problems.append((s_name, p))

        # 3. 발생, 복구, 업데이트 알림 팝업 띄우기 & 히스토리에 기록하기
        if getattr(self, '_first_load_done', False):
            
            # [🚨 장애 발생 팝업 처리]
            for s_name, p in new_problems:
                safe_title = p['name'].replace('<', '&lt;').replace('>', '&gt;')
                content = p.get("opdata", "").strip()
                
                if content:
                    safe_content = content.replace('<', '&lt;').replace('>', '&gt;').replace('\n', '<br>')
                    history_msg = f"{safe_title}<br>💡 {safe_content}"
                    toast_msg = f"<span style='font-family: \"IBM Plex Sans KR\", sans-serif; font-size: 13px; font-weight: bold;'>[{s_name}] {safe_title}</span><br><span style='font-family: \"IBM Plex Sans KR\", sans-serif; color: #BDC3C7; font-size: 11px; font-weight: normal;'>💡 {safe_content}</span>"
                else:
                    history_msg = safe_title
                    toast_msg = f"<span style='font-family: \"IBM Plex Sans KR\", sans-serif; font-size: 13px; font-weight: bold;'>[{s_name}] {safe_title}</span>"

                self.add_history_log(s_name, history_msg) 
                if self.config.get("noti_duration", 7) != 0:
                    self.toast_manager.show(toast_msg, 'created', self.config.get("noti_duration", 7))
                    
            # ★ [🔄 장애 업데이트 팝업 처리]
            if self.config.get("noti_on_update", True):
                for s_name, p, old_s_name, is_new_msg in updated_problems:
                    safe_title = p['name'].replace('<', '&lt;').replace('>', '&gt;')
                    
                    update_details = []
                    if s_name != old_s_name:
                        update_details.append(tr("lbl_sev_changed", "심각도 변경({old}➔{new})").format(old=old_s_name, new=s_name))
                    if is_new_msg:
                        update_details.append(tr("lbl_msg_added", "메시지 추가"))
                        
                    detail_str = ", ".join(update_details)
                    
                    toast_msg = f"<span style='font-family: \"IBM Plex Sans KR\", sans-serif; font-size: 13px; font-weight: bold;'>[{tr('lbl_updated', '업데이트')}: {s_name}] {safe_title}</span><br><span style='font-family: \"IBM Plex Sans KR\", sans-serif; color: #F39C12; font-size: 11px; font-weight: bold;'>💡 {detail_str}</span>"
                    
                    self.add_history_log(s_name, f"({tr('lbl_updated', '업데이트')}: {detail_str}) {safe_title}") 
                    if self.config.get("noti_duration", 7) != 0:
                        self.toast_manager.show(toast_msg, 'updated', self.config.get("noti_duration", 7))

            # ★ [✅ 장애 복구 팝업 처리]
            for s_name, p in resolved_problems:
                safe_title = p['name'].replace('<', '&lt;').replace('>', '&gt;')
                toast_msg = f"<span style='font-family: \"IBM Plex Sans KR\", sans-serif; font-size: 13px; font-weight: bold;'>[{tr('lbl_resolved', '복구')}] {safe_title}</span>"
                
                self.add_history_log("✅ 시스템", f"[{s_name}] 복구됨: {safe_title}") 
                if self.config.get("noti_duration", 7) != 0:
                    self.toast_manager.show(toast_msg, 'resolved', self.config.get("noti_duration", 7))
                
        self._first_load_done = True

        # 4. 열려있는 리스트 창 새로고침
        for circle in self.circles:
            if getattr(circle, 'list_window', None) and circle.list_window.isVisible():
                circle.list_window.problems_list = circle.problems
                circle.list_window.total_pages = max(1, (len(circle.list_window.problems_list) + circle.list_window.items_per_page - 1) // circle.list_window.items_per_page)
                if circle.list_window.current_page >= circle.list_window.total_pages:
                    circle.list_window.current_page = max(0, circle.list_window.total_pages - 1)
                circle.list_window.set_refreshing_state(False)

    def on_api_error(self, error_msg):
        for circle in self.circles:
            if getattr(circle, 'list_window', None) and circle.list_window.isVisible():
                circle.list_window.set_refreshing_state(False)
                circle.list_window.title_lbl.setText(tr("msg_update_failed_title", "❌ 업데이트 실패"))

        if not self.in_error_state:
            self.in_error_state = True
            logger.error(tr_log(f"[API 상태] Zabbix 서버 연결 끊김: {error_msg}", f"[API Status] Zabbix server connection lost: {error_msg}"))
            self.add_history_log("🚨 시스템", f"서버 연결 끊김 ({error_msg})")
            if self.config.get("noti_duration", 7) != 0:
                self.toast_manager.show(f"🚨 연결 오류: {error_msg}", "error", self.config.get("noti_duration", 7))
            for i, char in enumerate(["E", "R", "R", "O", "R", "!"]):
                self.circles[i].set_error_state(char)

    def toggle_autostart(self):
        enable = self.act_auto.isChecked()
        logger.debug(tr_log(f"[UI 액션] 부팅 시 자동실행 토글 변경: {enable}", f"[UI Action] Autostart toggle changed: {enable}"))
        self.config["autostart"] = enable
        self.save_current_settings()
        
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_ALL_ACCESS)
        if enable:
            if getattr(sys, 'frozen', False): command = f'"{sys.executable}"'
            else: command = f'"{sys.executable.replace("python.exe", "pythonw.exe")}" "{os.path.abspath(sys.argv[0])}"'
            winreg.SetValueEx(key, REG_APP_NAME, 0, winreg.REG_SZ, command)
        else:
            try: winreg.DeleteValue(key, REG_APP_NAME)
            except FileNotFoundError: pass
        winreg.CloseKey(key)

    # ★ 추가됨: 업데이트 알림 토글 스위치 동작 함수
    def toggle_noti_update(self):
        enable = self.act_noti_update.isChecked()
        logger.debug(tr_log(f"[UI 액션] 업데이트 알림 토글 변경: {enable}", f"[UI Action] Update notification toggle changed: {enable}"))
        self.config["noti_on_update"] = enable
        self.save_current_settings()

    def toggle_resize_mode(self):
        self.is_resize_mode = not self.is_resize_mode
        logger.debug(tr_log(f"[UI 액션] 크기 조절 모드 변경: {self.is_resize_mode}", f"[UI Action] Resize mode changed: {self.is_resize_mode}"))
        
        if self.is_resize_mode:
            self._backup_size = self.config["circle_size"]
            self._backup_pos = self.pos()
            self.resize_ui_container.show()
            self.resizeEvent(None) # 버튼들을 중앙으로 정렬
        else:
            self.resize_ui_container.hide()
            
        self.act_resize.setChecked(self.is_resize_mode)
        self.update() 
        
    def apply_resize(self):
        logger.debug(tr_log("[UI 액션] 크기 조절 적용", "[UI Action] Resize applied"))
        self.save_current_settings()
        self.toggle_resize_mode()

    def cancel_resize(self):
        logger.debug(tr_log("[UI 액션] 크기 조절 취소", "[UI Action] Resize canceled"))
        self._apply_circle_size(self._backup_size)
        self.move(self._backup_pos)
        self.save_current_settings()
        self.toggle_resize_mode()

    def resizeEvent(self, event):
        if event: super().resizeEvent(event)
        # 창 크기가 변할 때마다 적용/취소 메뉴를 항상 중앙에 유지
        if hasattr(self, 'resize_ui_container') and self.resize_ui_container.isVisible():
            self.resize_ui_container.adjustSize()
            cw = self.resize_ui_container.width()
            ch = self.resize_ui_container.height()
            self.resize_ui_container.move((self.width() - cw) // 2, (self.height() - ch) // 2)
        
    def toggle_debug_mode(self):
        is_debug = self.act_debug.isChecked()
        self.config["debug_mode"] = is_debug
        self.save_current_settings()
        apply_debug_level(is_debug)
        logger.debug(tr_log(f"[UI 액션] 디버그 모드 토글: {is_debug}", f"[UI Action] Debug mode toggle: {is_debug}"))
        if is_debug:
            custom_msgbox(QMessageBox.Information, tr("title_debug_mode", "디버그 모드"), tr("msg_debug_mode_on", "디버그 모드가 켜졌습니다.\nconfig 폴더에 debug.log 파일이 생성됩니다."), self)

    def save_current_settings(self):
        self.config["x"] = self.x()
        self.config["y"] = self.y()
        logger.debug(tr_log(f"[설정 저장] 현재 창 좌표: ({self.x()}, {self.y()}) / 위젯 크기: {self.config.get('circle_size')}", f"[Settings Saved] Current window coords: ({self.x()}, {self.y()}) / Widget size: {self.config.get('circle_size')}"))
        save_config(self.config)
    
    def paintEvent(self, event):
        if not self.is_resize_mode: return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 1. 배경을 약간 어둡게
        painter.setBrush(QColor(0, 0, 0, 120))
        painter.setPen(Qt.NoPen)
        painter.drawRect(self.rect())

        # 2. 테두리 (파란색 점선으로 강조)
        painter.setPen(QPen(QColor("#3498DB"), 2, Qt.DashLine))
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(2, 2, self.width() - 4, self.height() - 4)

        # 3. 크기 조절 핸들
        painter.setBrush(QColor(255, 255, 255))
        painter.setPen(QPen(QColor(0, 0, 0), 1))
        s = 10
        painter.drawRect(0, 0, s, s)  
        painter.drawRect(self.width() - s - 1, 0, s, s)  
        painter.drawRect(0, self.height() - s - 1, s, s)  
        painter.drawRect(self.width() - s - 1, self.height() - s - 1, s, s)

    def mousePressEvent(self, event):
        if self.is_resize_mode and event.button() == Qt.LeftButton:
            corner = self._get_resize_corner(event.pos())
            if corner:
                self._resize_corner = corner
                self._resize_start_global = event.globalPos()
                self._resize_start_size = self.config["circle_size"]
                self._resize_start_geometry = self.geometry()
                event.accept()
                return
            else: # 크기 조절 모드에서 배경을 클릭했을 때 창 이동 가능하게 처리
                self._is_moving = True
                self._move_start_pos = event.globalPos() - self.pos()
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.is_resize_mode: 
            self._update_resize_cursor(event.pos())
            # 창 이동 처리
            if self._is_moving and (event.buttons() & Qt.LeftButton):
                self.move(event.globalPos() - self._move_start_pos)
                event.accept()
                return
        else: 
            self.unsetCursor()

        # 크기 조절(모서리 드래그) 처리
        if self._resize_corner and (event.buttons() & Qt.LeftButton):
            dx = event.globalPos().x() - self._resize_start_global.x()
            dy = event.globalPos().y() - self._resize_start_global.y()

            if self._resize_corner == "BR": delta = (dx + dy) / 2
            elif self._resize_corner == "TL": delta = -(dx + dy) / 2
            elif self._resize_corner == "TR": delta = (dx - dy) / 2
            elif self._resize_corner == "BL": delta = (-dx + dy) / 2
            else: delta = 0

            self._apply_circle_size(self._resize_start_size + delta, self._resize_corner, self._resize_start_geometry)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.is_resize_mode and event.button() == Qt.LeftButton:
            if self._is_moving:
                self._is_moving = False
                event.accept()
                return
            if self._resize_corner:
                logger.debug(tr_log(f"[UI 액션] 크기 조절 중: 사이즈 {self.config['circle_size']}px", f"[UI Action] Resizing: Size {self.config['circle_size']}px"))
                self._resize_corner = None
                self._resize_start_geometry = None
                self._update_resize_cursor(event.pos())
                event.accept()
                return
        super().mouseReleaseEvent(event)

    def _get_resize_corner(self, pos):
        m, x, y = 20, pos.x(), pos.y()
        if x <= m and y <= m: return "TL"
        elif x >= self.width() - m and y <= m: return "TR"
        elif x <= m and y >= self.height() - m: return "BL"
        elif x >= self.width() - m and y >= self.height() - m: return "BR"
        return None
    
    def _update_resize_cursor(self, pos):
        c = self._get_resize_corner(pos)
        if c in ("TL", "BR"): self.setCursor(Qt.SizeFDiagCursor)
        elif c in ("TR", "BL"): self.setCursor(Qt.SizeBDiagCursor)
        else: self.unsetCursor()

    def _apply_circle_size(self, new_size, anchor_corner=None, start_geom=None):
        new_size = max(40, min(150, int(round(new_size))))
        if new_size == self.config["circle_size"] and anchor_corner is None: return

        self.config["circle_size"] = new_size
        for circle in self.circles: circle.setFixedSize(new_size, new_size)
        self.adjustSize()

        if anchor_corner and start_geom:
            sx, sy, sw, sh = start_geom.x(), start_geom.y(), start_geom.width(), start_geom.height()
            if anchor_corner == "TL": self.move(sx + sw - self.width(), sy + sh - self.height())
            elif anchor_corner == "TR": self.move(sx, sy + sh - self.height())
            elif anchor_corner == "BL": self.move(sx + sw - self.width(), sy)
            elif anchor_corner == "BR": self.move(sx, sy)
    
# ==========================================
# ★ 프로그램 시작점
# ==========================================
if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    app.setQuitOnLastWindowClosed(False)  
    
    icon_path = os.path.join(BUNDLE_DIR, "zabbix_icon.ico")
    if not os.path.exists(icon_path): icon_path = os.path.join(CONFIG_DIR, "zabbix_icon.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    shared_mem = QSharedMemory("ZabbixOverlayWidget_Unique_Instance_Lock")
    if not shared_mem.create(1):
            custom_msgbox(QMessageBox.Warning, tr("title_run_guide", "실행 안내"), tr("msg_already_running", "이미 프로그램이 실행되어 있습니다."))
            sys.exit(0)

    font_filenames = ["IBMPlexSansKR-Regular.ttf"]
    loaded_main_font = "Malgun Gothic" # 못 찾았을 때의 기본값
    
    for font_filename in font_filenames:
        font_search_paths = [
            os.path.join(BUNDLE_DIR, font_filename),
            os.path.join(CONFIG_DIR, font_filename),
            os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Fonts', font_filename)
        ]
        for path in font_search_paths:
            if os.path.exists(path):
                font_id = QFontDatabase.addApplicationFont(path)
                if font_id != -1:
                    families = QFontDatabase.applicationFontFamilies(font_id)
                    if families:
                        print(f"✅ 폰트 로드 성공! 파일: {font_filename} -> 진짜 폰트 이름: {families[0]}")
                        # 첫 번째 폰트(IBM)를 전역 기본 폰트로 설정하기 위한 변수 저장
                        if "IBM" in font_filename or "IBMPlex" in families[0]:
                            loaded_main_font = families[0]
                break 
                
    # 진짜 이름으로 전역 폰트 강제 적용 (IBM 폰트)
    app_font = QFont(loaded_main_font, 10)  
    app_font.setStyleHint(QFont.SansSerif)
    app.setFont(app_font)
    
    # 임시로 config를 읽어서 언어 로드
    temp_config = load_config()
    _translator.load_language(temp_config.get("language", "ko"))
    
    while True:
        widget = ZabbixDesktopWidget()
        widget.show()
        
        if widget.config.get("always_on_top", False):
            apply_z_order(widget, True)

        exit_code = app.exec_()
        
        if exit_code == 1337:
            widget.deleteLater()
            continue
        else:
            break
            
    sys.exit(exit_code)