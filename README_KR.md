# Zabbix Overlay Widget

Zabbix 서버의 장애(Problem) 상태를 실시간으로 모니터링하고, 바탕화면에 직관적인 플로팅(Floating) UI로 띄워주는 데스크톱 위젯입니다. 시스템 상태를 브라우저 없이도 바탕화면에서 즉각적으로 파악하고 대처할 수 있도록 설계되었습니다.

> **Note**: 본 프로젝트의 코드 일부와 이 문서는 구글의 AI 모델인 **Gemini**의 도움을 받아 작성 및 구조화되었습니다.

## 주요 기능 상세
* **실시간 모니터링 UI**: Zabbix API와 주기적으로 통신하여 장애 상태(Disaster, High, Average, Warning, Info, Not classified)를 심각도별로 색상화하여 보여줍니다.
* **플로팅 오버레이 (Floating Overlay)**: 
  * 화면의 원하는 위치에 자유롭게 드래그하여 배치할 수 있습니다.
  * '항상 위 표시(Always on Top)' 모드를 지원하여 다른 작업 중에도 모니터링이 가능합니다.
  * 바탕화면과 자연스럽게 어우러지는 반투명 백그라운드 디자인을 채택했습니다.
* **인터랙티브 알림 (Toast Notification)**: 
  * 신규 장애 발생, 심각도 변경, 복구 완료, 사용자 코멘트(Ack) 추가 시 화면 구석에 애니메이션 토스트 알림을 띄웁니다.
  * 알림 유지 시간 및 위치(우측 하단, 좌측 상단 등)를 커스터마이징할 수 있습니다.
* **즉각적인 장애 조치 (Issue Action)**: 
  * 위젯의 아이콘을 더블클릭하여 바로 Zabbix 서버에 인지(Acknowledge) 상태를 전송하거나, 코멘트를 남기거나, 수동으로 장애를 닫을(Close) 수 있습니다.
* **고급 히스토리 및 로그 뷰어**: 
  * 필터링이 가능한 장애 히스토리 창과, 다른 담당자들이 남긴 조치 이력(메시지 로그)을 실시간으로 확인할 수 있습니다.
* **디자인 및 레이아웃 커스터마이징**: 
  * 위젯의 크기 조절, 원형/사각형 테마 변경, 1줄/2줄 가로세로 배치 변경을 지원합니다.
* **다국어 지원 (i18n)**: 한국어(ko) 및 영어(en)를 지원하며, JSON 기반으로 동적 번역됩니다.

## 기술 스택 및 환경 (Tech Stack & Environment)

* **빌드 환경**: Python 3.12
* **UI 프레임워크**: PyQt5
* **사용된 주요 모듈 (Imports)**:
  * `PyQt5 (QtWidgets, QtCore, QtGui)`: GUI 구성, 시스템 트레이 아이콘, 애니메이션, 스레딩 (QThread, QTimer), 그래픽 렌더링.
  * `requests`, `urllib3`: Zabbix JSON-RPC API 통신 및 HTTPS 인증서 경고 처리.
  * `json`: 설정 파일(config) 및 다국어 언어 파일 파싱/저장.
  * `os`, `sys`: 파일 경로 탐색, 실행 환경(PyInstaller frozen 여부) 확인.
  * `winreg`, `ctypes`: Windows 레지스트리 제어(부팅 시 자동실행 등록) 및 Z-Order 최상단 고정 제어.
  * `logging`, `traceback`: 디버그 모드 및 예외 처리 로깅(RotatingFileHandler 사용).
  * `hashlib`: 실행 파일의 버전을 구분하기 위한 MD5 해시 생성.
  * `math`, `random`, `datetime`: 토스트 알림창의 버블 애니메이션 수학 계산 및 타임스탬프 변환.

## 설치 및 실행 방법

### 1. 저장소 클론 및 패키지 설치
git clone https://github.com/사용자이름/zabbix-overlay-widget.git
cd zabbix-overlay-widget

# 필수 외부 라이브러리 설치
pip install PyQt5 requests urllib3

### 2. 소스 코드 실행
# Python 3.12 환경에서 실행을 권장합니다.
python zabbix_overlay.py

### 3. Zabbix 환경 설정 (`config/zabbix_overlay_config.json`)
최초 실행 시 `config` 폴더와 기본 설정 파일이 자동 생성된 후 프로그램이 종료됩니다. 생성된 파일을 열어 아래 정보를 수정해 주세요.
* `zabbix_url`: `https://[Zabbix-IP-또는-도메인]/api_jsonrpc.php`
* `zabbix_api_token`: 보안을 위해 Zabbix에서 발급한 API Token 사용을 권장합니다.
* `zabbix_user` / `zabbix_password`: API Token이 없을 경우 사용하는 Zabbix 계정 정보.

## 실행 파일(exe) 빌드 방법 (Windows)
Python이 설치되지 않은 환경에서도 실행할 수 있도록 단일 실행 파일(`.exe`)로 빌드하는 방법입니다. **Python 3.12** 환경에서 테스트되었습니다.

# PyInstaller 설치
pip install pyinstaller

# 아이콘을 포함하여 콘솔창이 뜨지 않는(-w) 단일 파일(-F)로 빌드
pyinstaller -w -F --icon=zabbix_icon.ico zabbix_overlay.py

빌드가 완료되면 `dist` 폴더 안에 `zabbix_overlay.exe` 파일이 생성됩니다.

## 라이선스
This project is licensed under the MIT License.
