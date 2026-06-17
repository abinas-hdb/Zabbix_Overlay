import sys
import json
import os
import winreg
import requests
import urllib3
import hashlib
import ctypes
import logging 
from logging.handlers import RotatingFileHandler 
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QMenu, QAction, 
                             QListWidget, QLabel, QPushButton, QHBoxLayout, QMessageBox, 
                             QListWidgetItem, QDialog, QFormLayout, 
                             QPlainTextEdit, QComboBox, QCheckBox, QFrame,
                             QTabWidget, QTextBrowser, QSystemTrayIcon, QWidgetAction, QSizePolicy, QGridLayout, QGraphicsDropShadowEffect, QScrollBar, QSpinBox)
from PyQt5.QtGui import QPainter, QColor, QBrush, QFont, QPen, QFontMetrics, QFontDatabase, QIcon, QPixmap, QPolygonF
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QVariantAnimation, QTimer, QPoint, QPointF, QEvent, QSize, QSharedMemory

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

APP_VERSION = "v1.0.7" 
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
            "btn_cancel": "취소",
            "menu_custom": "직접 입력...",
            "custom_sec_format": "직접 입력... ({val}초)",
            "custom_item_format": "직접 입력... ({val}개)",
            "title_custom_noti": "알림 유지 시간",
            "msg_custom_noti": "알림 유지 시간을 초 단위로 입력하세요.\n(0: 끄기, -1: 수동 종료)",
            "title_custom_ref": "새로고침 주기",
            "msg_custom_ref": "새로고침 주기를 초 단위로 입력하세요.\n(최소 1초 이상)",
            "title_custom_page": "페이지당 표시 개수",
            "msg_custom_page": "리스트에 한 번에 표시할 알림 개수를 입력하세요.\n(최소 1개 이상)",
            "menu_use_win_noti": "Windows 기본 알림 사용",
            "menu_noti_settings": "🔔 알림 동작 설정",
            "menu_use_custom_noti": "자체 UI 알림 사용",
            "menu_save_state": "상태 기억하기 (히스토리/안 읽음)",
            "lbl_cannot_close": " (수동 클로즈 불가)"
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
            "btn_cancel": "Cancel",
            "menu_custom": "Custom...",
            "custom_sec_format": "Custom... ({val}s)",
            "custom_item_format": "Custom... ({val} items)",
            "title_custom_noti": "Notification Duration",
            "msg_custom_noti": "Enter duration in seconds.\n(0: Off, -1: Manual close)",
            "title_custom_ref": "Refresh Interval",
            "msg_custom_ref": "Enter refresh interval in seconds.\n(Min: 1s)",
            "title_custom_page": "Items per Page",
            "msg_custom_page": "Enter number of alerts to display per page.\n(Min: 1)",
            "menu_use_win_noti": "Use Windows Native Notification",
            "menu_noti_settings": "🔔 Notification Behaviors",
            "menu_use_custom_noti": "Use Custom UI Notification",
            "menu_save_state": "Remember State (History/Unread)",
            "lbl_cannot_close": " (Cannot close manually)"
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

# Zabbix 사용자 장부 데이터를 기반으로 다국어/한국어 이름을 올바르게 포맷팅하는 함수
def format_zabbix_user_name(u):
    name_str = u.get('name', '').strip()
    surname_str = u.get('surname', '').strip()
    
    # 이름이나 성에 한글이 포함되어 있다면 "성+이름" 순서로 붙여서 출력 (예: 김동균)
    if any('가' <= c <= '힣' for c in name_str + surname_str):
        if len(name_str) == 1 and len(surname_str) == 2:
            full_name = f"{name_str}{surname_str}"
        elif len(surname_str) == 1 and len(name_str) == 2:
            full_name = f"{surname_str}{name_str}"
        else:
            full_name = f"{surname_str}{name_str}".strip()
    else: # 영어나 기타 언어면 기존처럼 "이름 성" 유지 (예: John Smith)
        full_name = f"{name_str} {surname_str}".strip()
        
    if not full_name: 
        full_name = u.get("username", u.get("alias", "Unknown"))
        
    return full_name

def apply_debug_level(is_debug):
    logger.setLevel(logging.DEBUG if is_debug else logging.WARNING)
    if is_debug:
        logger.debug(tr_log("=== 디버그 모드가 활성화되었습니다 ===", "=== Debug mode activated ==="))

CONFIG_FILE = os.path.join(CONFIG_DIR, "zabbix_overlay_config.json")
STATE_FILE = os.path.join(CONFIG_DIR, "zabbix_overlay_state.json") # ★ 추가됨
REG_APP_NAME = "ZabbixOverlayWidget"
CUSTOM_FONT_FAMILY = ""  

def save_config(config):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4)

# ==========================================
# ★ 추가됨: 첫 실행 시 언어 선택 다이얼로그
# ==========================================
class InitialLangDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_lang = "" # ★ 수정됨: 기본값을 강제로 지정하지 않고 비워둠
        self.setWindowTitle("Select Language / 언어 선택")
        self.setFixedSize(340, 160)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        # 프로그램 실행 극초기이므로 테마 설정 전 기본 다크 모드 스타일 강제 적용
        self.setStyleSheet("""
            QDialog { background-color: #1C1C20; color: #F4F4F5; font-family: 'IBM Plex Sans KR', sans-serif; }
            QLabel { color: #F4F4F5; font-size: 14px; font-weight: bold; }
            QPushButton { 
                padding: 12px; background-color: #2A2A30; color: #F4F4F5; 
                border: 1px solid #3F3F46; border-radius: 6px; font-size: 14px; font-weight: bold;
            }
            QPushButton:hover { background-color: #3B82F6; color: white; border-color: #3B82F6; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 25, 20, 20)
        layout.setSpacing(15)

        lbl = QLabel("Please select your language.\n언어를 선택해 주세요.")
        lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl)

        btn_layout = QHBoxLayout()
        btn_ko = QPushButton("한국어")
        btn_en = QPushButton("English")

        btn_ko.setCursor(Qt.PointingHandCursor)
        btn_en.setCursor(Qt.PointingHandCursor)

        btn_ko.clicked.connect(lambda: self.select_lang("ko"))
        btn_en.clicked.connect(lambda: self.select_lang("en"))

        btn_layout.addWidget(btn_ko)
        btn_layout.addWidget(btn_en)
        layout.addLayout(btn_layout)

    def select_lang(self, lang):
        self.selected_lang = lang
        self.accept()

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
        "save_history_state": True, # ★ 추가됨 (기본값 켜짐)
        "language": "",  # ★ 수정됨: 기본값을 빈 문자열로 비워둠
        "noti_on_update": True
    }
    
    if not os.path.exists(CONFIG_FILE):
        # ★ 설정 파일 생성 전 언어부터 묻기
        lang_dlg = InitialLangDialog()
        lang_dlg.exec_()
        
        # ==========================================
        # ★ 추가됨: X 버튼을 눌러서 언어 선택을 안 하고 닫았다면 프로그램 즉시 종료
        # ==========================================
        if not lang_dlg.selected_lang:
            sys.exit(0)
        
        sample_config["language"] = lang_dlg.selected_lang
        save_config(sample_config)
        
        # 선택한 언어로 번역기 즉시 장전 (안내 메시지 번역을 위함)
        _translator.load_language(lang_dlg.selected_lang)
        
        custom_msgbox(QMessageBox.Information, tr("msg_init_setup", "초기 설정 안내"), tr("msg_config_created", "설정 파일이 새로 생성되었습니다.\n위치: {path}\n\n프로그램을 종료합니다. 메모장 등으로 파일을 열어\n실제 Zabbix 서버 주소와 계정(또는 API 토큰) 정보로 수정한 후 다시 실행해 주세요.").format(path=CONFIG_FILE))
        sys.exit(0)
        
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            user_config = json.load(f)
            
        # ★ 추가됨: 언어 설정이 비어있으면(무시하고 넘겼거나 구버전) 다시 언어 선택 창 띄우기
        if not user_config.get("language"):
            lang_dlg = InitialLangDialog()
            lang_dlg.exec_()
            # ==========================================
            # ★ 추가됨: 여기서도 X를 눌러 취소했으면 억지로 진행하지 않고 강제 종료
            # ==========================================
            if not lang_dlg.selected_lang:
                sys.exit(0)
                
            user_config["language"] = lang_dlg.selected_lang
            save_config(user_config)
            
        # ★ 중요: Zabbix URL 경고창 등을 띄우기 전에, 무조건 번역기부터 해당 언어로 장전!
        _translator.load_language(user_config.get("language", "en"))
            
        if user_config.get("zabbix_url") == sample_config["zabbix_url"]:
            custom_msgbox(QMessageBox.Warning, tr("msg_need_config_change", "설정 변경 필요"), tr("msg_zabbix_default", "Zabbix 서버 주소가 초기값 그대로입니다.\n\n{path}\n파일을 열어 실제 서버 정보로 수정해 주세요.").format(path=CONFIG_FILE))
            sys.exit(0)
            
        return user_config
        
    except Exception as e:
        save_config(sample_config)
        # 에러 발생 시에는 최후의 수단으로 한국어(기본값)로 에러 상황 렌더링
        _translator.load_language("ko")
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
                        user_map[u["userid"]] = format_zabbix_user_name(u)
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

class ModernScrollBar(QScrollBar):
    def __init__(self, is_light, parent=None):
        super().__init__(Qt.Vertical, parent)
        self.is_light = is_light
        # 다크/라이트 모드에 맞춘 스크롤바 색상
        self.bg_color = "rgba(0, 0, 0, 0.2)" if is_light else "rgba(255, 255, 255, 0.2)"
        self.hover_color = "rgba(0, 0, 0, 0.4)" if is_light else "rgba(255, 255, 255, 0.4)"
        
        # ★ 수정: 평소(thin)일 때 좌우 마진을 7px씩 주어, 중앙에 4px 두께로 이쁘게 위치시킵니다. (7 + 4 + 7 = 18px)
        self.current_margin = 7  
        self.current_color = self.bg_color
        
        # 스무스 애니메이션 세팅 (0.15초)
        self.anim = QVariantAnimation(self)
        self.anim.setDuration(150)
        self.anim.valueChanged.connect(self.update_margin)
        
        self.update_margin(self.current_margin)
        self.setCursor(Qt.PointingHandCursor)

    def enterEvent(self, event):
        self.current_color = self.hover_color
        self.anim.stop()
        self.anim.setStartValue(self.current_margin)
        self.anim.setEndValue(4) # ★ 호버 시 좌우 마진을 4px로 줄여, 중앙에서 '좌우 양옆으로' 10px 두께까지 확장! (4 + 10 + 4 = 18px)
        self.anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.current_color = self.bg_color
        self.anim.stop()
        self.anim.setStartValue(self.current_margin)
        self.anim.setEndValue(7) # ★ 마우스 떼면 다시 좌우 마진을 7px로 늘려 중앙으로 쏙 축소!
        self.anim.start()
        super().leaveEvent(event)

    def update_margin(self, margin):
        self.current_margin = margin
        # ★ 핵심: margin 값을 좌우 매개변수에 똑같이 {margin}px로 주어 중심축(Center)을 완벽하게 고정합니다.
        # 애니메이션 프레임이 돌 때 좌우 여백이 동시에 깎이므로 원하는 대로 좌우 균등하게 벌어집니다.
        self.setStyleSheet(f"""
            QScrollBar:vertical {{ 
                background: transparent; 
                width: 18px; 
                margin: 6px 0px 6px 0px; 
            }}
            QScrollBar::handle:vertical {{
                background: {self.current_color};
                min-height: 30px;
                border-radius: 2px; 
                margin: 0px {margin}px 0px {margin}px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; border: none; background: none; }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}
        """)

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
            # ★ 핵심 1: 이미 화면 밖으로 밀려나서 닫히고 있는(Fade-out) 알림은 자리 계산에서 제외
            if getattr(t, 'is_closing', False):
                continue
                
            x = geom.right() - t.width() - margin_x if "right" in pos_setting else geom.left() + margin_x
            
            if "bottom" in pos_setting:
                target_y = current_y - t.height()
                # ★ 핵심 2: 알림이 모니터 위쪽 화면 밖으로 삐져나가려고 하면 강제로 스르륵 닫아버림
                if target_y < geom.top() + 10:
                    t.fade_and_close()
                    continue
                
                t.move(x, target_y)
                current_y -= (t.height() + 5)
            else:
                target_y = current_y
                # ★ 핵심 3: (상단 배치 시) 알림이 모니터 아래쪽 화면 밖으로 삐져나가려고 하면 강제 닫음
                if target_y + t.height() > geom.bottom() - 10:
                    t.fade_and_close()
                    continue
                
                t.move(x, target_y)
                current_y += (t.height() + 5)

    def remove(self, t):
        if t in self.toasts:
            self.toasts.remove(t)
            self.rearrange()
            
    def clear_all(self):
        for t in list(self.toasts):
            t.fade_and_close()

# ==========================================
# 리스트 아이템용 파동 애니메이션 (Ripple Dot)
# ==========================================
class RippleDot(QWidget):
    def __init__(self, hex_color, parent=None):
        super().__init__(parent)
        # ★ 수정됨: 파동이 잘리지 않도록 위젯 도화지 크기를 14x18 -> 24x24로 넉넉하게 확장
        self.setFixedSize(24, 24) 
        self.base_color = QColor(hex_color)
        self.progress = 0.0
        
        self.anim = QVariantAnimation(self)
        self.anim.setDuration(1500) 
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.setLoopCount(-1) 
        self.anim.valueChanged.connect(self._update_progress)
        self.anim.start()
        
    def _update_progress(self, val):
        self.progress = val
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing) 
        
        center = QPointF(self.width() / 2.0, self.height() / 2.0)
        base_radius = 4.0 # 고정 중앙 점 크기
        
        # ★ 수정됨: 리스트 파동이 훨씬 더 크고 시원하게 퍼지도록 수식 수정 (반경이 최대 +10.0 더 커짐)
        ripple_radius = base_radius + (10.0 * self.progress)
        alpha = int(255 * (1.0 - self.progress))
        ripple_color = QColor(self.base_color.red(), self.base_color.green(), self.base_color.blue(), alpha)
        
        painter.setBrush(QBrush(ripple_color))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(center, ripple_radius, ripple_radius)
        
        painter.setBrush(QBrush(self.base_color))
        painter.drawEllipse(center, base_radius, base_radius)

# ==========================================
# 완벽한 정원을 그리는 고정 점 (Static Dot)
# ==========================================
class StaticDot(QWidget):
    def __init__(self, hex_color, parent=None):
        super().__init__(parent)
        self.setFixedSize(24, 24) # 파동 위젯과 공간 비율을 맞추기 위해 똑같이 24로 확장
        self.base_color = QColor(hex_color)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing) 
        
        center = QPointF(self.width() / 2.0, self.height() / 2.0)
        base_radius = 4.0 
        
        painter.setBrush(QBrush(self.base_color))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(center, base_radius, base_radius)

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

        # ★ 추가됨: 모두 읽기 버튼
        self.read_all_btn = QPushButton("✔ 모두 읽기")
        self.read_all_btn.setFixedSize(80, 28)
        self.read_all_btn.setCursor(Qt.PointingHandCursor)
        # ★ 수정됨: Arial 폰트를 IBM Plex Sans KR 폰트로 교체 적용
        self.read_all_btn.setStyleSheet(modern_btn_style.replace("font-size: 16px;", "font-size: 12px;").replace("Arial", "'IBM Plex Sans KR'"))
        self.read_all_btn.clicked.connect(self.mark_all_read)

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
        header_layout.addWidget(self.read_all_btn) # ★ 추가됨
        header_layout.addWidget(self.refresh_btn)
        header_layout.addWidget(close_btn)

        self.list_widget = QListWidget()
        self.list_widget.setMouseTracking(True)
        self.list_widget.viewport().setMouseTracking(True)
        self.list_widget.setFocusPolicy(Qt.NoFocus)
        self.list_widget.setSelectionMode(QListWidget.NoSelection)
        self.list_widget.viewport().installEventFilter(self)
        self.list_widget.setWordWrap(True)
        # ★ 수정 1: 스크롤 방식을 '아이템 단위'에서 '픽셀 단위'로 변경하여 물 흐르듯 부드럽게 만듦
        self.list_widget.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.list_widget.verticalScrollBar().setSingleStep(15) # 마우스 휠 스크롤 속도 조절

        self.list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list_widget.itemDoubleClicked.connect(self.open_issue_editor)

        # 다크/라이트 모드에 맞춘 반투명 스크롤바 색상 변수 설정
        scroll_handle_bg = "rgba(0, 0, 0, 0.2)" if self.is_light else "rgba(255, 255, 255, 0.2)"
        scroll_handle_hover = "rgba(0, 0, 0, 0.4)" if self.is_light else "rgba(255, 255, 255, 0.4)"

        # ★ 수정 2: QListWidget 스크롤바(QScrollBar) 디자인 변경 (호버 시 넓어짐 효과)
        self.list_widget.setStyleSheet("""
            QListWidget { background-color: transparent; border: none; outline: none; }
            QListWidget::item { padding: 2px 0px; margin: 0px; background-color: transparent; border: none; }
        """)

        self.list_widget.setVerticalScrollBar(ModernScrollBar(self.is_light, self.list_widget))

        bg_layout.addLayout(header_layout)
        bg_layout.addWidget(self.list_widget)
        main_layout.addWidget(self.bg_widget)

        self.refresh_page()

        # ★ 추가됨: 애니메이션을 위한 초기 투명도 및 종료 플래그 설정
        self.setWindowOpacity(0.0)
        self._is_closing = False

    # ★ 추가됨: 모두 읽기 기능
    def mark_all_read(self):
        for p in self.problems_list:
            self.owner_window.unread_events.discard(str(p['eventid']))
        self.owner_window.save_state() # ★ 추가됨
        self._last_rendered_state = None # 강제 리렌더링
        self.refresh_page()
        self.owner_window.update() # 메인 원형 UI도 갱신

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
        
        is_unread = str(issue_data['eventid']) in self.owner_window.unread_events
        
        # ★ 분기문 교체 (QLabel 텍스트 방식 -> QPainter 그래픽 방식)
        if is_unread:
            dot_widget = RippleDot(self.hex_color) # 안 읽었으면 파동 원
        else:
            dot_widget = StaticDot(self.hex_color) # 읽었으면 완벽한 고정 원
            
        safe_title = issue_data['name'].replace('<', '&lt;').replace('>', '&gt;')
        title_lbl = QLabel(f"<span style='font-family: \"IBM Plex Sans KR\", sans-serif; color: {title_color}; font-size: 13px; font-weight: bold;'>{safe_title}</span>")
        title_lbl.setStyleSheet("background: transparent; border: none;")
        title_lbl.setWordWrap(True)
        
        header_layout.addWidget(dot_widget, 0, Qt.AlignTop)
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
        # ★ 추가됨: list_widget이 완전히 생성된 이후에만 이벤트 필터를 작동시키도록 방어 코드 추가
        if hasattr(self, 'list_widget') and self.list_widget is not None:
            if obj == self.list_widget.viewport() and event.type() == QEvent.Leave:
                self.list_widget.clearSelection()
                self.list_widget.setCurrentRow(-1)
                self.list_widget.viewport().update()
                
        return super().eventFilter(obj, event)

    def refresh_page(self):
        # 기존에 있던 self.list_widget.clear()는 아래로 이동합니다.
        
        total_count = len(self.problems_list)
        start = self.current_page * self.items_per_page
        end = start + self.items_per_page
        page_items = self.problems_list[start:end]

        self.title_lbl.setText(f"{self.title} {tr('lbl_list', '리스트')} ({total_count})")
        self.page_lbl.setText(f"{self.current_page + 1}/{self.total_pages}")
        
        self.prev_btn.setVisible(self.current_page > 0)
        self.next_btn.setVisible(self.current_page < self.total_pages - 1)
        self.page_lbl.setVisible(self.total_pages > 1)

        # ★ 추가됨: 안 읽은 알림이 없으면 '모두 읽기' 버튼 숨김
        has_unread = any(str(p['eventid']) in self.owner_window.unread_events for p in self.problems_list)
        self.read_all_btn.setVisible(has_unread)
        
        # ★ 핵심 방어 로직: 현재 페이지의 데이터가 100% 동일하다면 화면을 다시 그리지 않음
        # 이 코드를 통해 5초마다 리스트가 파괴/재생성되며 발생하는 
        # 마우스 호버(Hover) 풀림 및 더블클릭 씹힘 현상을 완벽하게 방지합니다.
        import json
        current_state_json = json.dumps(page_items, sort_keys=True)
        if getattr(self, '_last_rendered_state', None) == current_state_json:
            return  # 데이터 변경이 없으면 리스트를 지우지 않고 여기서 즉시 종료!
            
        self._last_rendered_state = current_state_json
        
        # 데이터가 바뀌었을 때만 리스트를 비우고 다시 그립니다.
        self.list_widget.clear()
        total_height = 52 + 28 # 헤더 높이 + 컨테이너 패딩
        
        if not page_items:
            item = QListWidgetItem()
            item.setFlags(Qt.NoItemFlags)
            item.setSizeHint(QSize(0, 60))
            self.list_widget.addItem(item)
            
            # ★ 수정됨: 이모지가 잘리지 않도록 넉넉한 패딩을 가진 QLabel로 교체
            empty_lbl = QLabel(tr("msg_no_issues", "✅ 현재 발생한 미해결 내역이 없습니다."))
            empty_lbl.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            text_color = "#4B5563" if self.is_light else "#A1A1AA"
            empty_lbl.setStyleSheet(f"color: {text_color}; font-size: 14px; font-family: 'IBM Plex Sans KR', sans-serif; padding: 10px 5px; background: transparent;")
            
            self.list_widget.setItemWidget(item, empty_lbl)
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
                
                calc_height = max(85, rect.height() + 85)
                
                item.setSizeHint(QSize(0, calc_height))
                self.list_widget.addItem(item)
                self.list_widget.setItemWidget(item, widget)
                total_height += calc_height

        # ★ 수정: 최대 높이를 제한하여 창이 작업 표시줄이나 모니터 아래로 뚫고 나가는 현상 완벽 방지
        screen = QApplication.screenAt(self.mapToGlobal(self.rect().center()))
        if not screen: 
            screen = QApplication.primaryScreen()
            
        screen_height = screen.availableGeometry().height() if screen else 1080
        
        # 최대 750px 또는 모니터 가용 높이의 80% 중 작은 값을 한계치로 설정
        max_height = min(750, int(screen_height * 0.8)) 
        final_height = min(max_height, max(150, total_height))
        
        self.resize(440, final_height)
        
        # 높이가 변하면서 창이 엉뚱한 위치에 걸칠 수 있으므로, 제자리로 안전하게 끌고 옴
        if self.owner_window:
            for circle in self.owner_window.circles:
                if getattr(circle, 'list_window', None) == self:
                    circle.update_list_position()
                    break

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

        # ★ 추가됨: 창 열기 전에 읽음 처리
        if str(issue_data["eventid"]) in self.owner_window.unread_events:
            self.owner_window.unread_events.discard(str(issue_data["eventid"]))
            self.owner_window.save_state() # ★ 추가됨
            self._last_rendered_state = None
            self.refresh_page()
            self.owner_window.update()

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

    def showEvent(self, event):
        super().showEvent(event)
        # 창이 열릴 때 0.2초(200ms) 동안 스르륵 나타나는 페이드인 효과
        self.show_anim = QVariantAnimation(self)
        self.show_anim.setDuration(200)
        self.show_anim.setStartValue(0.0)
        self.show_anim.setEndValue(1.0)
        self.show_anim.valueChanged.connect(self.setWindowOpacity)
        self.show_anim.start()
            
    def closeEvent(self, event):
        # 이미 닫히는 애니메이션이 진행 중이 아니라면
        if not getattr(self, '_is_closing', False):
            self._is_closing = True
            event.ignore()  # 즉시 꺼지는 것을 막음
            
            # 0.15초(150ms) 동안 스르륵 사라지는 페이드아웃 효과
            self.close_anim = QVariantAnimation(self)
            self.close_anim.setDuration(150)
            self.close_anim.setStartValue(self.windowOpacity())
            self.close_anim.setEndValue(0.0)
            self.close_anim.valueChanged.connect(self.setWindowOpacity)
            self.close_anim.finished.connect(self.close)  # 투명해지면 진짜로 창을 닫음
            self.close_anim.start()
            return
            
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
            
            /* ★ QTextBrowser 내부 흰색 영역과 스크롤바가 겹쳐서 생기는 바깥 라인 완벽 제거 */
            QTextBrowser {{
                border: 1px solid {border_color};
                border-radius: 6px;
                background-color: {pane_bg};
            }}
            
            /* 가로 스크롤바 깔끔하게 매칭 */
            QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 0px; }}
            QScrollBar::handle:horizontal {{ background: {scroll_bg}; min-width: 30px; border-radius: 2px; margin: 2px; }}
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
            
            # ★ 수정됨: 다국어(tr) 함수를 사용하여 언어 설정에 맞게 자동 변경되도록 처리
            add_text = tr("lbl_cannot_close", " (수동 클로즈 불가)")
            self.close_check.setText(self.close_check.text() + add_text)
            
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

        # (히스토리 탭 부분)
        self.history_browser = QTextBrowser()
        self.history_browser.setHtml(f"<p style='color: {dim_text}; margin: 10px;'>{tr('lbl_loading_data', '데이터를 불러오는 중입니다...')}</p>")
        
        # ★ 추가됨: 히스토리 창에 애니메이션 스크롤바 주입
        self.history_browser.setVerticalScrollBar(ModernScrollBar(self.is_light, self.history_browser))
        
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

        # (메시지 로그 탭 부분)
        self.log_browser = QTextBrowser()
        
        # ★ 추가됨: 메시지 로그 창에 애니메이션 스크롤바 주입
        self.log_browser.setVerticalScrollBar(ModernScrollBar(self.is_light, self.log_browser))
        
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
                        user_map[u["userid"]] = format_zabbix_user_name(u)
                
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

        self.hover_progress = 0.0
        self.hover_anim = QVariantAnimation(self)
        self.hover_anim.setDuration(150)
        self.hover_anim.valueChanged.connect(self._update_hover)

        self.click_scale = 1.0
        self.click_anim = QVariantAnimation(self)
        self.click_anim.setDuration(100)
        self.click_anim.valueChanged.connect(self._update_scale)

        self.is_highlighted = False
        self.highlight_type = "created" 
        
        self.highlight_timer = QTimer(self)
        self.highlight_timer.setSingleShot(True)
        self.highlight_timer.timeout.connect(self.clear_highlight)

        # ★ 기존의 딱딱한 깜빡임 타이머를 삭제하고, 부드럽게 숨쉬는(Pulse) 파동 애니메이션 추가
        self.blink_progress = 0.0
        self.blink_anim = QVariantAnimation(self)
        self.blink_anim.setDuration(1200) # 1.2초 동안 한 사이클 (부드러운 호흡 속도)
        self.blink_anim.setKeyValueAt(0.0, 0.0)
        self.blink_anim.setKeyValueAt(0.5, 1.0)
        self.blink_anim.setKeyValueAt(1.0, 0.0)
        self.blink_anim.setLoopCount(-1) # 무한 반복
        self.blink_anim.valueChanged.connect(self._update_blink_progress)

        # ==========================================
        # ★ 추가됨: 깜빡임이 끝날 때 뚝 끊기지 않게 스르륵 꺼지는 감쇠 애니메이션
        # ==========================================
        self.blink_stop_anim = QVariantAnimation(self)
        self.blink_stop_anim.setDuration(400) # 0.4초 동안 부드럽게 감쇠
        self.blink_stop_anim.valueChanged.connect(self._update_blink_progress)
        self.blink_stop_anim.finished.connect(self._on_blink_stop_finished)

        # ==========================================
        # ★ 추가됨: 우측 상단 '안 읽음(Unread)' 파동 뱃지 애니메이션
        # ==========================================
        self.unread_progress = 0.0
        self.unread_anim = QVariantAnimation(self)
        self.unread_anim.setDuration(1500)
        self.unread_anim.setStartValue(0.0)
        self.unread_anim.setEndValue(1.0)
        self.unread_anim.setLoopCount(-1)
        self.unread_anim.valueChanged.connect(self._update_unread_progress)
        self.unread_anim.start()
        
        # 새로고침 대기(로딩) 상태 변수 및 타이머
        self.is_waiting_for_data = False
        self.loading_angle = 0
        self.loading_timer = QTimer(self)
        self.loading_timer.timeout.connect(self._update_loading_angle)

    # ★ 누락되었던 파동 애니메이션 업데이트 함수 추가
    def _update_unread_progress(self, val):
        self.unread_progress = val
        self.update()

    def _update_loading_angle(self):
        self.loading_angle = (self.loading_angle + 20) % 360
        self.update()

    # ★ 추가됨: 감쇠 애니메이션이 끝나면 하이라이트 상태를 완전히 해제
    def _on_blink_stop_finished(self):
        self.is_highlighted = False
        self.blink_progress = 0.0
        self.update()

    def start_loading(self):
        self.is_waiting_for_data = True
        self.loading_timer.start(30)
        self.update()

    def stop_loading_and_show(self):
        if not self.is_waiting_for_data: return
        self.is_waiting_for_data = False
        self.loading_timer.stop()
        self.update()
        if not self.is_error_state:
            if not (getattr(self, 'list_window', None) and self.list_window.isVisible()):
                self.window().toggle_circle_list(self)

    # ★ 새롭게 추가된 블링크(호흡) 애니메이션 업데이트 함수
    def _update_blink_progress(self, val):
        self.blink_progress = val
        self.update()
        
    def _update_hover(self, val):
        self.hover_progress = val
        self.update()

    def _update_scale(self, val):
        self.click_scale = val
        self.update()
        
    def set_error_state(self, char):
        self.is_error_state = True
        self.error_char = char
        self.blink_anim.start() # 부드러운 깜빡임 시작
        self.update()

    def clear_error_state(self):
        self.is_error_state = False
        self.error_char = ""
        self.blink_anim.stop()
        self.blink_progress = 0.0
        self.update()
    
    def trigger_highlight(self, highlight_type):
        self.highlight_type = highlight_type
        self.is_highlighted = True
        self.blink_stop_anim.stop() # ★ 꺼지는 중이었다면 즉시 멈춤
        self.blink_anim.start()     # 부드러운 깜빡임 시작
        self.update()
        self.highlight_timer.start(3000)

    def clear_highlight(self):
        if self.is_error_state: return
        self.blink_anim.stop()
        
        # ★ 수정됨: 뚝 끊지 않고 현재 투명도에서 0.0까지 0.4초간 스르륵 빠지도록 설정
        self.blink_stop_anim.stop()
        self.blink_stop_anim.setStartValue(self.blink_progress)
        self.blink_stop_anim.setEndValue(0.0)
        self.blink_stop_anim.start()

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
        
        # 1. 클릭 애니메이션
        if self.click_scale != 1.0:
            painter.translate(self.width() / 2.0, self.height() / 2.0)
            painter.scale(self.click_scale, self.click_scale)
            painter.translate(-self.width() / 2.0, -self.height() / 2.0)
        
        theme = self.window().config.get("theme", "circle")
        is_light = self.window().config.get("color_mode", "dark") == "light"
        
        progress = max(0.0, min(1.0, (self.current_opacity - 0.3) / 0.7))
        base_bg = QColor(255, 255, 255, 240) if is_light else QColor(28, 28, 32, 230)

        # ★ 색상을 부드럽게 섞어주는 헬퍼 함수
        def blend(c1, c2, factor):
            return QColor(
                int(c1.red() + (c2.red() - c1.red()) * factor),
                int(c1.green() + (c2.green() - c1.green()) * factor),
                int(c1.blue() + (c2.blue() - c1.blue()) * factor),
                int(c1.alpha() + (c2.alpha() - c1.alpha()) * factor)
            )

        # ★ 추가됨: 배경이 진해질 때 글자가 잘 보이도록 대비색(흑/백)을 찾아주는 함수
        def get_contrast_color(c):
            lum = (0.299 * c.red() + 0.587 * c.green() + 0.114 * c.blue()) / 255
            return QColor(31, 41, 55) if lum > 0.55 else QColor(255, 255, 255)

        current_bg = base_bg 
        
        # ==========================================
        # ★ 수정됨: 평상시(기본) 색상을 미리 계산하여 애니메이션이 끝날 때 뚝 끊기지 않고 자연스럽게 돌아가게 함
        # ==========================================
        glow_color = self.circle_color # ★ 핵심 수정: 스피너가 참조할 수 있도록 기본 glow_color를 최상단에 미리 선언!
        
        active_border_alpha = 255 if is_light else 180
        current_border_alpha = int(active_border_alpha * (0.3 + 0.7 * progress))
        default_border = QColor(glow_color.red(), glow_color.green(), glow_color.blue(), current_border_alpha)
        
        active_text = QColor(31, 41, 55) if is_light else QColor(255, 255, 255)
        inactive_text = QColor(156, 163, 175) if is_light else QColor(113, 113, 122) 
        
        if self.alert_count == 0:
            default_text = blend(inactive_text, active_text, progress)
            dim_num = QColor(glow_color.red(), glow_color.green(), glow_color.blue(), 80)
            default_num = blend(dim_num, glow_color, progress)
        else:
            default_text = active_text
            default_num = glow_color

        # 색상 세팅 (부드러운 애니메이션 적용)
        if self.is_error_state:
            glow_color = QColor(231, 76, 60) # 에러일 땐 빨간색으로 변신
            base_border = QColor(0, 0, 0, 30) if is_light else QColor(255, 255, 255, 50)
            base_text = QColor(31, 41, 55) if is_light else QColor(255, 255, 255)
            
            glow_bg = QColor(glow_color.red(), glow_color.green(), glow_color.blue(), base_bg.alpha())
            current_bg = blend(base_bg, glow_bg, self.blink_progress * 0.8)
            
            contrast_text = get_contrast_color(glow_color)
            border_color = blend(base_border, glow_color, self.blink_progress)
            text_color = blend(base_text, contrast_text, self.blink_progress)
            num_color = text_color
            
        elif self.is_highlighted:
            if self.highlight_type == 'created':
                glow_color = self.circle_color # 발생일 땐 자기 자신 색상
            else:
                glow_color = QColor(16, 185, 129) if is_light else QColor(46, 204, 113) # 복구일 땐 초록색으로 변신
                
            glow_bg = QColor(glow_color.red(), glow_color.green(), glow_color.blue(), base_bg.alpha())
            current_bg = blend(base_bg, glow_bg, self.blink_progress * 0.75)
            
            contrast_text = get_contrast_color(glow_color)
            
            border_color = blend(default_border, glow_color, self.blink_progress)
            text_color = blend(default_text, contrast_text, self.blink_progress)
            num_color = blend(default_num, contrast_text, self.blink_progress)
            
        else:
            border_color = default_border
            text_color = default_text
            num_color = default_num

        # 2. 배경 및 테두리 그리기
        painter.setBrush(QBrush(current_bg)) # ★ base_bg에서 current_bg로 변경!
        pen_width = 3 if self.is_highlighted or self.is_error_state else 2
        painter.setPen(QPen(border_color, pen_width))
        
        rect = self.rect().adjusted(2, 2, -2, -2)
        if "rectangle" in theme:
            painter.drawRoundedRect(rect, 12, 12)
        else:
            painter.drawEllipse(rect)

        # 3. 호버 오버레이 효과
        if self.hover_progress > 0:
            if is_light:
                hover_alpha = int(25 * self.hover_progress)
                painter.setBrush(QBrush(QColor(0, 0, 0, hover_alpha)))
            else:
                hover_alpha = int(40 * self.hover_progress)
                painter.setBrush(QBrush(QColor(255, 255, 255, hover_alpha)))
                
            painter.setPen(Qt.NoPen)
            if "rectangle" in theme:
                painter.drawRoundedRect(rect, 12, 12)
            else:
                painter.drawEllipse(rect)

        # 4. 데이터 갱신 대기 중(로딩) 스피너 그리기
        if getattr(self, 'is_waiting_for_data', False):
            painter.setBrush(QBrush(QColor(0, 0, 0, 140 if is_light else 180)))
            painter.setPen(Qt.NoPen)
            if "rectangle" in theme:
                painter.drawRoundedRect(rect, 12, 12)
            else:
                painter.drawEllipse(rect)
                
            spin_pen = QPen(glow_color, max(3, int(self.width() * 0.06)))
            spin_pen.setCapStyle(Qt.RoundCap)
            painter.setPen(spin_pen)
            
            margin = int(self.width() * 0.25)
            spinner_rect = rect.adjusted(margin, margin, -margin, -margin)
            
            start_angle = -self.loading_angle * 16
            span_angle = 120 * 16 # 120도 길이의 꼬리
            painter.drawArc(spinner_rect, start_angle, span_angle)

        # 5. 에러 상태일 경우 글자 렌더링하고 즉시 종료
        if self.is_error_state:
            painter.setPen(text_color)
            font = QFont("IBM Plex Sans KR") 
            font.setPixelSize(int(self.width() * 0.4)) 
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(0, 0, self.width(), self.height(), Qt.AlignCenter, self.error_char)
            return

        # 6. 정상 상태일 경우 심각도 이름 렌더링
        painter.setPen(text_color)
        font = QFont("IBM Plex Sans KR") 
        font.setBold(True) 
        
        pixel_size = int(self.width() * 0.24)
        font.setPixelSize(pixel_size)
        fm = QFontMetrics(font)
        
        max_text_width = self.width() - 20
        while fm.boundingRect(self.severity_name).width() > max_text_width and pixel_size > 8:
            pixel_size -= 1
            font.setPixelSize(pixel_size)
            fm = QFontMetrics(font)

        painter.setFont(font)
        painter.drawText(0, int(self.height() * 0.15), self.width(), int(self.height() * 0.35), Qt.AlignCenter, self.severity_name)

        # 7. 숫자 렌더링
        count_str = str(self.alert_count)
        num_pixel_size = int(self.width() * 0.34)
        font.setPixelSize(num_pixel_size)
        fm = QFontMetrics(font)
        
        max_num_width = self.width() - 24
        while fm.boundingRect(count_str).width() > max_num_width and num_pixel_size > 8:
            num_pixel_size -= 1
            font.setPixelSize(num_pixel_size)
            fm = QFontMetrics(font)

        painter.setFont(font)
        painter.setPen(num_color)
        painter.drawText(0, int(self.height() * 0.45), self.width(), int(self.height() * 0.45), Qt.AlignCenter, count_str)

        # ==========================================
        # ★ 수정됨: 안 읽은 이벤트가 있으면 우측 상단(또는 정중앙)에 파동 치는 미니 원 그리기
        # ==========================================
        has_unread = any(str(p['eventid']) in self.window().unread_events for p in self.problems)
        if has_unread:
            if "rectangle" in theme:
                # ★ 수정됨: 고정 픽셀(14px) 대신 위젯 넓이의 15% 비율로 동적 계산하여 쏠림 현상 원천 차단
                offset = self.width() * 0.15 
                badge_center = QPointF(self.width() - offset, offset)
            else:
                # 원형 모드: X는 정중앙(r), Y는 중심에서 위쪽 25% (r * 0.25)
                r = self.width() / 2.0
                badge_center = QPointF(r, r * 0.25)

            badge_color = QColor(231, 76, 60) # 빨간색
            
            # 파동 그리기
            ripple_radius = 4.0 + (8.0 * self.unread_progress)
            alpha = int(255 * (1.0 - self.unread_progress))
            painter.setBrush(QBrush(QColor(badge_color.red(), badge_color.green(), badge_color.blue(), alpha)))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(badge_center, ripple_radius, ripple_radius)
            
            # 고정된 중앙 점 그리기
            painter.setBrush(QBrush(badge_color))
            painter.drawEllipse(badge_center, 4.0, 4.0)
        
    def enterEvent(self, event):
        if self.is_error_state: return 
        self.opacity_anim.stop()
        self.opacity_anim.setStartValue(self.current_opacity)
        self.opacity_anim.setEndValue(1.0) 
        self.opacity_anim.start()

        self.hover_anim.stop()
        self.hover_anim.setStartValue(self.hover_progress)
        self.hover_anim.setEndValue(1.0)
        self.hover_anim.start()

    def leaveEvent(self, event):
        if self.is_error_state: return
        self.opacity_anim.stop()
        self.opacity_anim.setStartValue(self.current_opacity)
        target_opacity = 1.0 if self.is_first_load else (0.3 if self.alert_count == 0 else 1.0)
        self.opacity_anim.setEndValue(target_opacity)
        self.opacity_anim.start()

        self.hover_anim.stop()
        self.hover_anim.setStartValue(self.hover_progress)
        self.hover_anim.setEndValue(0.0)
        self.hover_anim.start()

    def contextMenuEvent(self, event):
        self.window().main_menu.exec_(event.globalPos())

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._is_dragging = False
            self._drag_start_pos = event.globalPos() - self.window().pos()
            self._click_start_pos = event.globalPos() 
            
            self.click_anim.stop()
            self.click_anim.setStartValue(self.click_scale)
            self.click_anim.setEndValue(0.92) 
            self.click_anim.start()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            if not self._is_dragging:
                if (event.globalPos() - getattr(self, '_click_start_pos', event.globalPos())).manhattanLength() < 5:
                    return
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
            
            self.window().move(nx, ny)
            self.update_list_position()
            
            if hasattr(self.window(), 'circles'):
                for circle in self.window().circles:
                    if circle != self and getattr(circle, 'list_window', None) and circle.list_window.isVisible():
                        circle.update_list_position()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.click_anim.stop()
            self.click_anim.setStartValue(self.click_scale)
            self.click_anim.setEndValue(1.0)
            self.click_anim.start()
            
            if self.is_error_state: return 
            if not self._is_dragging:
                if not self.window().is_resize_mode:
                    if getattr(self, 'list_window', None) and self.list_window.isVisible():
                        self.window().toggle_circle_list(self)
                    elif getattr(self.window(), 'is_fetching', False):
                        self.start_loading()
                    else:
                        self.window().toggle_circle_list(self)
            else:
                self.window().save_current_settings()

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
        self.main_widget = main_widget  
        self.config = self.main_widget.config
        self.is_light = self.config.get("color_mode", "dark") == "light"
        
        max_count = self.config.get('history_max_count', 100)
        self.setWindowTitle(f"{tr('title_history', '최근 알림 히스토리')} (Max {max_count})")
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint) 
        self.resize(580, 480)
        
        # 🎨 모드에 따른 동적 색상 할당
        bg_color = "#F9FAFB" if self.is_light else "#1C1C20"
        text_color = "#111827" if self.is_light else "#F4F4F5"
        pane_bg = "#FFFFFF" if self.is_light else "#2A2A30"
        border_color = "#D1D5DB" if self.is_light else "#3F3F46"
        input_bg = "#FFFFFF" if self.is_light else "#18181B"
        
        self.setStyleSheet(f"""
            QDialog {{ background-color: {bg_color}; font-family: 'IBM Plex Sans KR', sans-serif; color: {text_color}; }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # 상단 레이아웃 (제목 & 필터)
        header_layout = QHBoxLayout()
        header_lbl = QLabel(tr("title_realtime_history", "🕒 실시간 알림 내역"))
        header_lbl.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {text_color}; font-family: 'IBM Plex Sans KR', sans-serif;")
        header_layout.addWidget(header_lbl)
        
        header_layout.addStretch()
        
        # 모던 콤보박스 디자인
        self.filter_combo = QComboBox()
        self.filter_combo.addItems([tr("filter_all", "전체보기"), tr("sev_disaster", "심각"), tr("sev_high", "중증"), tr("sev_average", "경미"), tr("sev_warning", "경고"), tr("sev_info", "정보"), tr("sev_not_cls", "미정"), tr("sev_system", "기타 (시스템)")])
        self.filter_combo.setCursor(Qt.PointingHandCursor)
        
        arrow_url = get_arrow_path()
        self.filter_combo.setStyleSheet(f"""
            QComboBox {{
                font-family: 'IBM Plex Sans KR', sans-serif; 
                padding: 6px 12px; 
                font-size: 13px; 
                background-color: {input_bg};
                color: {text_color};
                border: 1px solid {border_color};
                border-radius: 6px;
            }}
            QComboBox::drop-down {{ subcontrol-origin: padding; subcontrol-position: top right; width: 24px; border-left-width: 0px; }}
            QComboBox::down-arrow {{ image: url('{arrow_url}'); width: 16px; height: 16px; }}
            QComboBox QAbstractItemView {{
                background-color: {pane_bg}; color: {text_color}; selection-background-color: {border_color}; selection-color: {text_color}; outline: none; border: 1px solid {border_color}; border-radius: 6px; padding: 4px;
            }}
        """)
        self.filter_combo.currentIndexChanged.connect(self.update_view)
        header_layout.addWidget(self.filter_combo)
        
        layout.addLayout(header_layout)
        
        # 모던 브라우저 패널
        self.browser = QTextBrowser()
        self.browser.setStyleSheet(f"""
            QTextBrowser {{
                background-color: {pane_bg}; 
                border: 1px solid {border_color}; 
                border-radius: 8px;
                padding: 8px 14px 8px 8px;
                font-family: 'IBM Plex Sans KR', sans-serif; 
                font-size: 13px;
            }}
        """)
        # ★ 우리가 만든 애니메이션 스크롤바 장착!
        self.browser.setVerticalScrollBar(ModernScrollBar(self.is_light, self.browser))
        layout.addWidget(self.browser)
        
        # 하단 닫기 버튼
        close_btn = QPushButton(tr("btn_close", "닫기"))
        close_btn.setCursor(Qt.PointingHandCursor)
        can_bg = "#EF4444" if self.is_light else "#DC2626"
        can_hover = "#DC2626" if self.is_light else "#B91C1C"
        close_btn.setStyleSheet(f"""
            QPushButton {{ padding: 8px 24px; background-color: {can_bg}; color: white; border: none; border-radius: 6px; font-weight: bold; font-family: 'IBM Plex Sans KR', sans-serif; }} 
            QPushButton:hover {{ background-color: {can_hover}; }}
        """)
        close_btn.clicked.connect(self.close)
        
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 8, 0, 0)
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)
        
        # 자동 새로고침 타이머
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
            if current_len != self.last_history_len or getattr(self, 'last_top_time', '') != top_item_time:
                self.update_view()
                self.last_top_time = top_item_time
        
    def update_view(self):
        self.last_history_len = len(self.main_widget.alert_history)
        history_data = self.main_widget.alert_history
        filter_text = self.filter_combo.currentText()
        
        # ★ 다크/라이트 모드에 맞춰 HTML 텍스트 및 점선 색상 동적 변경
        time_c = "#7F8C8D" if self.is_light else "#9CA3AF"
        msg_c = "#2C3E50" if self.is_light else "#E4E4E7"
        line_c = "#E5E7EB" if self.is_light else "#3F3F46"
        
        if not history_data:
            self.browser.setHtml(f"<p style='color: {time_c}; padding: 10px;'>{tr('msg_no_recent_alerts', '최근 발생한 알림이 없습니다.')}</p>")
            return
            
        color_map = {
            "심각": "#E74C3C", 
            "중증": "#E67E22", 
            "경미": "#F39C12", 
            "경고": "#F1C40F", 
            "정보": "#3498DB", 
            "미정": "#95A5A6", 
            "🚨 시스템": "#E74C3C",
            "✅ 시스템": "#2ECC71"
        }
            
        html = "<div style='padding: 5px;'>"
        match_count = 0
        for item in history_data:
            lvl = item['level']
            
            if filter_text != "전체보기":
                if filter_text == "기타 (시스템)":
                    if lvl not in ["🚨 시스템", "✅ 시스템"]: continue
                else:
                    if lvl != filter_text: continue
                    
            color = color_map.get(lvl, msg_c)
            
            html += f"<div style='margin-bottom: 12px;'>"
            html += f"<span style='color: {time_c}; font-size: 12px;'>[{item['time']}]</span> "
            html += f"<strong style='color: {color};'>[{lvl}]</strong><br> "
            msg_html = item['msg'].replace('\n', '<br>')
            html += f"<span style='color: {msg_c}; font-size: 13px; line-height: 1.4;'>{msg_html}</span>"
            html += f"</div><hr style='border: 0; border-top: 1px dashed {line_c};'>"
            match_count += 1
            
        html += "</div>"
        
        if match_count == 0:
            # ★ 수정됨: 미리 정의된 다국어 키(msg_no_matching_alerts)를 불러오고 format으로 필터명 삽입
            msg = tr("msg_no_matching_alerts", "선택한 조건({filter})에 해당하는 알림이 없습니다.").format(filter=filter_text)
            html = f"<p style='color: {time_c}; padding: 10px;'>{msg}</p>"
            
        self.browser.setHtml(html)

# ==========================================
# ★ 다크/라이트 모드 지원 커스텀 숫자 입력 창
# ==========================================
class CustomInputDialog(QDialog):
    def __init__(self, title, message, default_val, min_val, max_val, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.is_light = self.config.get("color_mode", "dark") == "light"
        
        self.setWindowTitle(title)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.resize(340, 160)
        
        # 🎨 모드에 따른 동적 색상 할당
        bg_color = "#F9FAFB" if self.is_light else "#1C1C20"
        text_color = "#111827" if self.is_light else "#F4F4F5"
        input_bg = "#FFFFFF" if self.is_light else "#18181B"
        border_color = "#D1D5DB" if self.is_light else "#3F3F46"
        sel_color = "#3B82F6" if self.is_light else "#60A5FA"
        
        # 버튼 호버 및 화살표 색상
        btn_hover = "rgba(0, 0, 0, 0.05)" if self.is_light else "rgba(255, 255, 255, 0.05)"
        arrow_color = "#6B7280" if self.is_light else "#A1A1AA"
        
        # ★ 해결: 1. 위쪽 화살표 이미지 동적 생성
        up_path = os.path.join(CONFIG_DIR, f"spin_up_{'l' if self.is_light else 'd'}.png").replace("\\", "/")
        if not os.path.exists(up_path):
            pix = QPixmap(16, 16)
            pix.fill(Qt.transparent)
            p = QPainter(pix)
            p.setRenderHint(QPainter.Antialiasing)
            p.setBrush(QColor(arrow_color))
            p.setPen(Qt.NoPen)
            p.drawPolygon(QPolygonF([QPointF(2, 11), QPointF(14, 11), QPointF(8, 5)])) # ▲ 모양
            p.end()
            pix.save(up_path, "PNG")
            
        # ★ 해결: 2. 아래쪽 화살표 이미지 동적 생성
        down_path = os.path.join(CONFIG_DIR, f"spin_down_{'l' if self.is_light else 'd'}.png").replace("\\", "/")
        if not os.path.exists(down_path):
            pix = QPixmap(16, 16)
            pix.fill(Qt.transparent)
            p = QPainter(pix)
            p.setRenderHint(QPainter.Antialiasing)
            p.setBrush(QColor(arrow_color))
            p.setPen(Qt.NoPen)
            p.drawPolygon(QPolygonF([QPointF(2, 5), QPointF(14, 5), QPointF(8, 11)])) # ▼ 모양
            p.end()
            pix.save(down_path, "PNG")
            
        # ★ 해결: 3. QSpinBox CSS 화살표 이미지 주입 및 글자 겹침 방지 여백(padding-right: 30px) 설정
        self.setStyleSheet(f"""
            QDialog {{ background-color: {bg_color}; font-family: 'IBM Plex Sans KR', sans-serif; color: {text_color}; }}
            QLabel {{ color: {text_color}; font-size: 13px; }}
            QSpinBox {{ 
                background-color: {input_bg}; color: {text_color}; 
                border: 1px solid {border_color}; border-radius: 6px; 
                padding: 6px 30px 6px 12px; font-size: 14px;
            }}
            QSpinBox:focus {{ border: 1px solid {sel_color}; }}
            QSpinBox::up-button {{
                subcontrol-origin: border; subcontrol-position: top right;
                width: 24px; border-left: 1px solid {border_color}; border-bottom: 1px solid {border_color};
                border-top-right-radius: 6px; background: transparent;
            }}
            QSpinBox::down-button {{
                subcontrol-origin: border; subcontrol-position: bottom right;
                width: 24px; border-left: 1px solid {border_color};
                border-bottom-right-radius: 6px; background: transparent;
            }}
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {{ background-color: {btn_hover}; }}
            QSpinBox::up-arrow {{ image: url('{up_path}'); width: 10px; height: 10px; }}
            QSpinBox::down-arrow {{ image: url('{down_path}'); width: 10px; height: 10px; }}
            QSpinBox::up-arrow:off, QSpinBox::down-arrow:off {{ opacity: 0.3; }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        lbl = QLabel(message)
        lbl.setWordWrap(True)
        layout.addWidget(lbl)
        
        self.spin_box = QSpinBox()
        self.spin_box.setRange(min_val, max_val)
        self.spin_box.setValue(default_val)
        layout.addWidget(self.spin_box)
        
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 10, 0, 0)
        btn_layout.addStretch()
        
        # 모던 확인/취소 버튼
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
        layout.addLayout(btn_layout)
        
    def get_value(self):
        return self.spin_box.value()

class ZabbixDesktopWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.config = load_config()
        self.unread_events = set() 
        self.alert_history = []
        self.load_state() # ★ 추가됨: 프로그램 시작 시 디스크에서 상태 불러오기
        
        apply_debug_level(self.config.get("debug_mode", False))
        self.toast_manager = ToastManager(self, self.config)
        self.is_resize_mode = False
        self.in_error_state = False
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

    # ==========================================
    # ★ 추가됨: 상태(히스토리, 안 읽음 뱃지) 저장 및 로드 로직
    # ==========================================
    def load_state(self):
        if not self.config.get("save_history_state", True):
            return
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.alert_history = data.get("alert_history", [])
                    self.unread_events = set(data.get("unread_events", []))
            except Exception as e:
                logger.error(f"상태 로드 실패: {e}")

    def save_state(self):
        if not self.config.get("save_history_state", True):
            return
        try:
            with open(STATE_FILE, 'w', encoding='utf-8') as f:
                json.dump({
                    "alert_history": self.alert_history,
                    "unread_events": list(self.unread_events) # set은 json 저장이 안되므로 list로 변환
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"상태 저장 실패: {e}")

    def toggle_save_state(self):
        enable = self.act_save_state.isChecked()
        self.config["save_history_state"] = enable
        self.save_current_settings()
        if enable:
            self.save_state()
        else:
            if os.path.exists(STATE_FILE):
                os.remove(STATE_FILE) # 기능 끄면 파일 삭제

    def initUI(self):
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        flags = Qt.FramelessWindowHint | Qt.Tool
        if self.config.get("always_on_top", False): flags |= Qt.WindowStaysOnTopHint
        else: flags |= Qt.WindowStaysOnBottomHint
        self.setWindowFlags(flags)
        
        self.main_layout = QGridLayout()
        # ★ 원형 테마일 때의 간격을 15에서 6으로 좁혀서 오밀조밀하게 배치합니다.
        self.main_layout.setSpacing(0 if "rectangle" in self.config.get("theme", "") else 6)
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
        
        # ★ 비활성화(Gray out) 전용 폰트 색상 및 호버 배경색 설정
        disabled_color = "#9CA3AF" if is_light else "#52525B"
        disabled_hover_bg = "rgba(0, 0, 0, 0.06)" if is_light else "rgba(255, 255, 255, 0.06)"
        
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
            
            /* ★ 변경: '활성화 상태(!disabled)'이면서 '호버 상태(selected)'일 때만 파란색 하이라이트 적용 */
            QMenu::item:selected:!disabled {{ 
                background-color: {sel_bg}; 
                color: white; 
                border-radius: 4px;
            }} 
            
            /* ★ 추가: 비활성화 항목 평상시 상태 (글자색 흐리게) */
            QMenu::item:disabled {{
                color: {disabled_color};
                background-color: transparent;
            }}
            
            /* ★ 추가: 비활성화 항목에 마우스를 올렸을 때 (파란색 원천 차단, 연한 음영만 살짝) */
            QMenu::item:selected:disabled {{
                background-color: {disabled_hover_bg};
                color: {disabled_color};
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
        # 1. 그리드 레이아웃이 가지고 있는 '유령 칸'을 초기화하기 위해 기존 레이아웃 완벽 파괴
        if self.layout() is not None:
            old_layout = self.layout()
            for circle in self.circles:
                old_layout.removeWidget(circle)
                circle.setParent(self) # 위젯이 날아가지 않도록 메인 창에 단단히 묶어둠
            QWidget().setLayout(old_layout) # 더미 위젯에 씌워서 메모리에서 완전히 날려버림(Garbage Collect)
            
        # 2. 깨끗한 새 레이아웃 생성
        self.main_layout = QGridLayout()
        theme = self.config.get("theme", "circle")
        self.main_layout.setSpacing(0 if "rectangle" in theme else 6)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.setLayout(self.main_layout)
        
        # 3. 새로운 테마와 방향에 맞게 알림원 재배치
        direction = self.config.get("layout_direction", "vertical")
        
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
                
        # 4. OS에게 "이전의 넓었던 창 크기를 잊고 내부 알림원에 딱 맞게 강제로 줄여!"라고 명령
        self.resize(1, 1)
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

        # ★ 추가됨: 상태 기억하기 스위치
        self.act_save_state = QAction(tr("menu_save_state", "상태 기억하기 (히스토리/안 읽음)"), self.main_menu, checkable=True)
        self.act_save_state.triggered.connect(self.toggle_save_state)
        self.main_menu.addAction(self.act_save_state)
        
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

        # ★ 알림 동작 설정 서브메뉴 생성
        noti_settings_menu = self.main_menu.addMenu(tr("menu_noti_settings", "🔔 알림 동작 설정"))

        # 1. 업데이트 알림 On/Off 스위치 (독립적)
        self.act_noti_update = QAction(tr("menu_noti_update", "업데이트 알림 표시 (메시지/심각도 변경)"), noti_settings_menu, checkable=True)
        self.act_noti_update.triggered.connect(self.toggle_noti_update)
        noti_settings_menu.addAction(self.act_noti_update)
        
        noti_settings_menu.addSeparator()

        # 2. 알림 스타일 선택 (2개 중 1개만 선택되도록 구성)
        self.act_custom_noti_style = QAction(tr("menu_use_custom_noti", "자체 UI 알림 사용"), noti_settings_menu, checkable=True)
        self.act_win_noti = QAction(tr("menu_use_win_noti", "Windows 기본 알림 사용"), noti_settings_menu, checkable=True)

        self.act_custom_noti_style.triggered.connect(lambda: self.set_noti_style(False))
        self.act_win_noti.triggered.connect(lambda: self.set_noti_style(True))

        noti_settings_menu.addAction(self.act_custom_noti_style)
        noti_settings_menu.addAction(self.act_win_noti)
        
        self.main_menu.addSeparator()

        # ★ 수정됨: 지역 변수를 self.noti_menu 로 변경
        self.noti_menu = self.main_menu.addMenu(tr("menu_noti_duration", "알림 유지 시간"))
        self.dict_noti = {}
        noti_options = {0: tr("noti_off", "알림 끄기"), 3: tr("noti_3s", "3초"), 5: tr("noti_5s", "5초"), 7: tr("noti_7s", "7초 (권장)"), 10: tr("noti_10s", "10초"), 15: tr("noti_15s", "15초"), 30: tr("noti_30s", "30초"), -1: tr("noti_manual", "수동 종료 시까지")}
        for secs, label in noti_options.items():
            act = QAction(label, self.noti_menu, checkable=True)
            act.triggered.connect(lambda checked, s=secs: self.set_noti_duration(s))
            self.noti_menu.addAction(act)
            self.dict_noti[secs] = act

        custom_str = tr("menu_custom", "직접 입력...")

        # ★ 추가됨: 알림 유지 시간 직접 입력
        self.noti_menu.addSeparator()
        self.act_custom_noti = QAction(custom_str, self.noti_menu, checkable=True)
        self.act_custom_noti.triggered.connect(self.prompt_custom_noti)
        self.noti_menu.addAction(self.act_custom_noti)

        # ★ 수정됨: 지역 변수를 self.pos_menu 로 변경
        self.pos_menu = self.main_menu.addMenu(tr("menu_noti_pos", "알림 위치"))

        self.dict_pos = {}
        for key, label_key, def_label in [("bottom_right", "pos_br", "우측 하단"), ("bottom_left", "pos_bl", "좌측 하단"), ("top_right", "pos_tr", "우측 상단"), ("top_left", "pos_tl", "좌측 상단")]:
            act = QAction(tr(label_key, def_label), self.pos_menu, checkable=True)
            act.triggered.connect(lambda checked, k=key: self.set_noti_position(k))
            self.pos_menu.addAction(act)
            self.dict_pos[key] = act

        refresh_menu = self.main_menu.addMenu(tr("menu_refresh_int", "새로고침 주기"))
        self.dict_ref = {}
        ref_options = {3: tr("ref_3s", "3초 (매우 빠름)"), 5: tr("ref_5s", "5초 (권장)"), 10: tr("ref_10s", "10초"), 30: tr("ref_30s", "30초")}
        for secs, label in ref_options.items():
            act = QAction(label, refresh_menu, checkable=True)
            act.triggered.connect(lambda checked, s=secs: self.set_refresh_interval(s))
            refresh_menu.addAction(act)
            self.dict_ref[secs] = act

        refresh_menu.addSeparator()
        self.act_custom_ref = QAction(custom_str, refresh_menu, checkable=True)
        self.act_custom_ref.triggered.connect(self.prompt_custom_ref)
        refresh_menu.addAction(self.act_custom_ref)

        page_menu = self.main_menu.addMenu(tr("menu_items_page", "페이지당 표시 개수"))
        self.dict_page = {}
        for cnt in [3, 5, 7, 10, 15]:
            act = QAction(tr("item_count", "{cnt}개").format(cnt=cnt), page_menu, checkable=True)
            act.triggered.connect(lambda checked, c=cnt: self.set_items_per_page(c))
            page_menu.addAction(act)
            self.dict_page[cnt] = act

        # ★ 추가됨: 페이지당 개수 직접 입력
        page_menu.addSeparator()
        self.act_custom_page = QAction(custom_str, page_menu, checkable=True)
        self.act_custom_page.triggered.connect(self.prompt_custom_page)
        page_menu.addAction(self.act_custom_page)
            
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
        self.save_state() # ★ 추가됨

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
        self.act_save_state.setChecked(self.config.get("save_history_state", True)) # ★ 추가됨
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
        
        # ★ 알림 스타일 2중 1개 체크 동기화 로직
        use_win = self.config.get("use_windows_noti", False)
        self.act_custom_noti_style.setChecked(not use_win)
        self.act_win_noti.setChecked(use_win)
        
        # ==========================================
        # ★ 추가됨: Windows 알림 사용 시 시간/위치 메뉴 비활성화
        # ==========================================
        self.noti_menu.setEnabled(not use_win)
        self.pos_menu.setEnabled(not use_win)

        # ★ 직접 입력된 값이면 '직접 입력...'에 체크 및 설정된 값을 괄호로 보여줌 (다국어 연동)

        # ★ 직접 입력된 값이면 '직접 입력...'에 체크 및 설정된 값을 괄호로 보여줌 (다국어 연동)
        curr_noti = self.config.get("noti_duration", 7)
        is_cust_noti = curr_noti not in self.dict_noti
        self.act_custom_noti.setChecked(is_cust_noti)
        self.act_custom_noti.setText(tr("custom_sec_format", "직접 입력... ({val}초)").format(val=curr_noti) if is_cust_noti else tr("menu_custom", "직접 입력..."))
        
        curr_ref = self.config.get("refresh_interval", 5)
        is_cust_ref = curr_ref not in self.dict_ref
        self.act_custom_ref.setChecked(is_cust_ref)
        self.act_custom_ref.setText(tr("custom_sec_format", "직접 입력... ({val}초)").format(val=curr_ref) if is_cust_ref else tr("menu_custom", "직접 입력..."))
        
        curr_page = self.config.get("items_per_page", 5)
        is_cust_page = curr_page not in self.dict_page
        self.act_custom_page.setChecked(is_cust_page)
        self.act_custom_page.setText(tr("custom_item_format", "직접 입력... ({val}개)").format(val=curr_page) if is_cust_page else tr("menu_custom", "직접 입력..."))

    def prompt_custom_noti(self):
        title = tr("title_custom_noti", "알림 유지 시간")
        msg = tr("msg_custom_noti", "알림 유지 시간을 초 단위로 입력하세요.\n(0: 끄기, -1: 수동 종료)")
        dlg = CustomInputDialog(title, msg, self.config.get("noti_duration", 7), -1, 86400, self.config, self)
        if dlg.exec_() == QDialog.Accepted:
            self.set_noti_duration(dlg.get_value())

    def prompt_custom_ref(self):
        title = tr("title_custom_ref", "새로고침 주기")
        msg = tr("msg_custom_ref", "새로고침 주기를 초 단위로 입력하세요.\n(최소 1초 이상)")
        dlg = CustomInputDialog(title, msg, self.config.get("refresh_interval", 5), 1, 86400, self.config, self)
        if dlg.exec_() == QDialog.Accepted:
            self.set_refresh_interval(dlg.get_value())

    def prompt_custom_page(self):
        title = tr("title_custom_page", "페이지당 표시 개수")
        msg = tr("msg_custom_page", "리스트에 한 번에 표시할 알림 개수를 입력하세요.\n(최소 1개 이상)")
        dlg = CustomInputDialog(title, msg, self.config.get("items_per_page", 5), 1, 1000, self.config, self)
        if dlg.exec_() == QDialog.Accepted:
            self.set_items_per_page(dlg.get_value())

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
        
        # apply_layout_direction 안에서 레이아웃 파괴/재생성 및 간격 조절을 모두 수행함
        self.apply_layout_direction()
        
        for circle in self.circles: 
            circle.update()

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
        
        # ★ 추가됨 1: 통신 시작할 때 플래그 켜기
        self.is_fetching = True
        
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
                self.show_notification("시스템 복구", "✅ Zabbix 서버 연결이 복구되었습니다.", "✅ Zabbix 서버 연결이 복구되었습니다.", "resolved", self.config.get("noti_duration", 7))
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

        # ==========================================
        # ★ 추가됨: 이미 복구되어 사라진 이벤트 ID는 '안 읽음(unread)' 목록에서도 자동 청소
        # (현재 활성화된 current_problems_set과 교집합만 남김)
        # ==========================================
        self.unread_events.intersection_update(current_problems_set)

        # 3. 발생, 복구, 업데이트 알림 팝업 띄우기 & 히스토리에 기록하기
        if getattr(self, '_first_load_done', False):            
            # [🚨 장애 발생 팝업 처리]
            for s_name, p in new_problems:
                self.unread_events.add(str(p['eventid'])) # ★ 추가됨: 안 읽음 처리
                safe_title = p['name'].replace('<', '&lt;').replace('>', '&gt;')
                content = p.get("opdata", "").strip()
                
                if content:
                    safe_content = content.replace('<', '&lt;').replace('>', '&gt;').replace('\n', '<br>')
                    history_msg = f"{safe_title}<br>💡 {safe_content}"
                    toast_msg = f"<span style='font-family: \"IBM Plex Sans KR\", sans-serif; font-size: 13px; font-weight: bold;'>[{s_name}] {safe_title}</span><br><span style='font-family: \"IBM Plex Sans KR\", sans-serif; color: #BDC3C7; font-size: 11px; font-weight: normal;'>💡 {safe_content}</span>"
                    plain_msg = f"💡 {content}" # ★ 추가됨
                else:
                    history_msg = safe_title
                    toast_msg = f"<span style='font-family: \"IBM Plex Sans KR\", sans-serif; font-size: 13px; font-weight: bold;'>[{s_name}] {safe_title}</span>"
                    plain_msg = "발생된 장애 메시지가 없습니다." # ★ 추가됨

                # 수정 후 (깔끔!)
                self.add_history_log(s_name, history_msg) 
                self.show_notification(f"[{s_name}] {p['name']}", plain_msg, toast_msg, 'created', self.config.get("noti_duration", 7))
                    
            # ★ [🔄 장애 업데이트 팝업 처리]
            if self.config.get("noti_on_update", True):
                for s_name, p, old_s_name, is_new_msg in updated_problems:
                    self.unread_events.add(str(p['eventid'])) # ★ 추가됨: 안 읽음 처리
                    safe_title = p['name'].replace('<', '&lt;').replace('>', '&gt;')
                    
                    update_details = []
                    if s_name != old_s_name:
                        update_details.append(tr("lbl_sev_changed", "심각도 변경({old}➔{new})").format(old=old_s_name, new=s_name))
                    if is_new_msg:
                        update_details.append(tr("lbl_msg_added", "메시지 추가"))
                        
                    detail_str = ", ".join(update_details)
                    
                    toast_msg = f"<span style='font-family: \"IBM Plex Sans KR\", sans-serif; font-size: 13px; font-weight: bold;'>[{tr('lbl_updated', '업데이트')}: {s_name}] {safe_title}</span><br><span style='font-family: \"IBM Plex Sans KR\", sans-serif; color: #F39C12; font-size: 11px; font-weight: bold;'>💡 {detail_str}</span>"
                    
                    # 수정 후 (깔끔!)
                    self.add_history_log(s_name, f"({tr('lbl_updated', '업데이트')}: {detail_str}) {safe_title}") 
                    self.show_notification(f"[{tr('lbl_updated', '업데이트')}: {s_name}] {p['name']}", f"💡 {detail_str}", toast_msg, 'updated', self.config.get("noti_duration", 7))

            # ★ [✅ 장애 복구 팝업 처리]
            for s_name, p in resolved_problems:
                safe_title = p['name'].replace('<', '&lt;').replace('>', '&gt;')
                toast_msg = f"<span style='font-family: \"IBM Plex Sans KR\", sans-serif; font-size: 13px; font-weight: bold;'>[{tr('lbl_resolved', '복구')}] {safe_title}</span>"
                
                # 수정 후 (깔끔!)
                self.add_history_log("✅ 시스템", f"[{s_name}] 복구됨: {safe_title}") 
                self.show_notification(f"[{tr('lbl_resolved', '복구')}] {p['name']}", "장애가 정상적으로 복구되었습니다.", toast_msg, 'resolved', self.config.get("noti_duration", 7))
                
        self._first_load_done = True

        # 4. 열려있는 리스트 창 새로고침
        for circle in self.circles:
            if getattr(circle, 'list_window', None) and circle.list_window.isVisible():
                circle.list_window.problems_list = circle.problems
                circle.list_window.total_pages = max(1, (len(circle.list_window.problems_list) + circle.list_window.items_per_page - 1) // circle.list_window.items_per_page)
                if circle.list_window.current_page >= circle.list_window.total_pages:
                    circle.list_window.current_page = max(0, circle.list_window.total_pages - 1)
                circle.list_window.set_refreshing_state(False)

        # ★ 추가됨 2: 통신 끝나면 플래그 끄고, 기다리던 원의 리스트 창 열어주기
        self.is_fetching = False
        for circle in self.circles:
            if getattr(circle, 'is_waiting_for_data', False):
                circle.stop_loading_and_show()
        self.save_state() # ★ 추가됨

    def on_api_error(self, error_msg):
        for circle in self.circles:
            if getattr(circle, 'list_window', None) and circle.list_window.isVisible():
                circle.list_window.set_refreshing_state(False)
                circle.list_window.title_lbl.setText(tr("msg_update_failed_title", "❌ 업데이트 실패"))

        if not self.in_error_state:
            self.in_error_state = True
            logger.error(tr_log(f"[API 상태] Zabbix 서버 연결 끊김: {error_msg}", f"[API Status] Zabbix server connection lost: {error_msg}"))
            self.add_history_log("🚨 시스템", f"서버 연결 끊김 ({error_msg})")
            
            # ★ 수정됨: 분기 래퍼 함수만 남기고 지저분한 중복 조건문 싹 청소
            self.show_notification("🚨 서버 연결 오류", error_msg, f"🚨 연결 오류: {error_msg}", 'error', self.config.get("noti_duration", 7))
            
            for i, char in enumerate(["E", "R", "R", "O", "R", "!"]):
                self.circles[i].set_error_state(char)
                
        # ★ 추가됨 3: 통신 에러가 났을 때도 무한 로딩에 빠지지 않게 플래그 끄고 락 해제
        self.is_fetching = False
        for circle in self.circles:
            if getattr(circle, 'is_waiting_for_data', False):
                circle.stop_loading_and_show()

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

    # ★ 추가됨: Windows / 자체 알림을 분기 처리하는 래퍼 함수
    def show_notification(self, plain_title, plain_msg, html_msg, noti_type, duration):
        if duration == 0: return
        
        # 설정에 따라 Windows 기본 알림 사용 시
        if self.config.get("use_windows_noti", False) and getattr(self, 'tray', None):
            icon_map = {
                'created': QSystemTrayIcon.Warning,
                'updated': QSystemTrayIcon.Information,
                'resolved': QSystemTrayIcon.Information,
                'error': QSystemTrayIcon.Critical
            }
            self.tray.showMessage(plain_title, plain_msg, icon_map.get(noti_type, QSystemTrayIcon.Information), duration * 1000)
        # 설정이 꺼져있으면 자체 커스텀 알림(Toast) 사용
        else:
            self.toast_manager.show(html_msg, noti_type, duration)

    # ★ 2중 1개 선택 시 설정을 저장하는 함수
    def set_noti_style(self, use_windows):
        logger.debug(tr_log(f"[UI 액션] 알림 스타일 변경 (Windows 사용: {use_windows})", f"[UI Action] Noti style changed (Use Windows: {use_windows})"))
        self.config["use_windows_noti"] = use_windows
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
            self.unsetCursor() # ★ 추가됨: 크기 조절 모드가 끝날 때 갇혀있는 마우스 커서 강제 초기화!
            
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
            # ★ 추가됨: 마우스 드래그 중이 아닐 때만 위치에 따라 커서 변경 (드래그 중에 커서 연산이 꼬이는 것 방지)
            if not getattr(self, '_resize_corner', None) and not getattr(self, '_is_moving', False):
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

    def leaveEvent(self, event):
        # ★ 추가됨: 마우스가 창 밖으로 휙 나갈 때 커서가 안 돌아오는 증상 완벽 해결
        if not getattr(self, '_resize_corner', None) and not getattr(self, '_is_moving', False):
            self.unsetCursor()
        super().leaveEvent(event)

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