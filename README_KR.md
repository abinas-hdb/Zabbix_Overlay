# Zabbix Overlay Widget

> **Read this in other languages:** [English](README.md)

데스크탑 화면 위에 직관적인 플로팅 UI로 Zabbix 장애(Problem) 상황을 실시간으로 모니터링하고 띄워주는 강력한 위젯입니다. 웹 브라우저를 계속 띄워둘 필요 없이, 데스크탑 환경에서 시스템 경고를 빠르게 파악하고 즉각적으로 조치할 수 있도록 설계되었습니다.

> **참고**: 이 프로젝트의 코드 구조화 및 문서는 구글의 AI 모델인 **Gemini**의 도움을 받아 작성되었습니다.

## 상세 기능
* **실시간 모니터링 UI**: Zabbix API와 주기적으로 통신하여 현재 발생한 장애를 심각도(Disaster, High, Average, Warning, Info, Not classified)별 고유 색상으로 표시합니다. 새로운 알림이 도착하면 위젯 배경 전체가 해당 심각도의 색상으로 부드럽게 점멸하는 **파동(숨쉬기) 애니메이션**을 제공합니다.
* **스마트 안 읽음(Unread) 추적 시스템**: 
  * 새로운 장애가 발생하거나 업데이트되면 메인 위젯에 눈에 띄는 붉은색 '파동' 뱃지가 표시됩니다.
  * 리스트 화면 내에서도 안 읽은 항목은 지속적인 파동 애니메이션으로 강조됩니다.
  * 직관적인 "**✔ 모두 읽기**" 버튼을 통해 알림 상태를 즉시 초기화할 수 있습니다.
* **유연한 알림 시스템**: 
  * 화려한 애니메이션이 적용된 **자체 UI 팝업 알림**과 **Windows 기본 알림** 중 원하는 스타일을 선택할 수 있습니다.
  * Windows 알림 사용 시 OS의 '알림 센터(Action Center)'와 완벽하게 연동되어, 팝업이 사라진 후에도 알림 히스토리가 보존됩니다.
* **플로팅 오버레이**: 
  * 화면 어디로든 자유롭게 드래그하여 배치할 수 있습니다.
  * '항상 위 표시(Always on Top)' 모드를 지원하여 다른 작업 중에도 중요한 알림을 놓치지 않습니다.
* **빠른 장애 조치**: 
  * 심각도 아이콘을 더블 클릭하여 장애 상세 정보를 확인하고, 인지(Acknowledge) 처리, 코멘트 작성, 심각도 변경 또는 수동 클로즈(Close)를 Zabbix API를 통해 직접 수행할 수 있습니다.
* **고급 히스토리 및 로그 뷰어**: 
  * 필터링 기능을 통해 과거 알림 히스토리를 조회하고, 다른 팀원들이 남긴 운영 메시지 로그를 실시간으로 확인할 수 있습니다.
* **UI 커스터마이징**: 
  * **다크 모드(Dark Mode)**와 **라이트 모드(Light Mode)** 간의 매끄러운 전환을 지원합니다.
  * 위젯 크기를 자유롭게 조절할 수 있으며, 원형/사각형 테마 및 가로/세로(1줄 또는 2줄) 방향 등 다양한 레이아웃 설정이 가능합니다.
* **사용자 친화적 설정 (i18n)**: 
  * 프로그램 최초 실행 시 **초기 언어 선택 다이얼로그**가 자동으로 팝업됩니다. 동적 JSON 파일을 통해 한국어(ko)와 영어(en)를 완벽하게 지원합니다.
  * 중복 실행 방지 기능이 탑재되어 시스템 안정성을 보장합니다.

## 기술 스택 및 환경

* **빌드 환경**: Python 3.12+
* **UI 프레임워크**: PyQt5
* **주요 사용 모듈**:
  * `PyQt5 (QtWidgets, QtCore, QtGui)`: GUI 구성, 시스템 트레이 아이콘, 부드러운 속성 애니메이션(`QVariantAnimation`), 멀티스레딩(`QThread`) 및 중복 실행 방지(`QSharedMemory`)에 사용됩니다.
  * `requests`, `urllib3`: Zabbix JSON-RPC API 통신 처리 및 안전하지 않은 HTTPS 경고 무시에 사용됩니다.
  * `json`: 환경 설정 파일 및 다국어 번역 데이터의 파싱 및 저장에 사용됩니다.
  * `os`, `sys`: 파일 경로 탐색 및 PyInstaller 패키징 상태 관리에 사용됩니다.
  * `winreg`, `ctypes`: Windows 레지스트리 조작(부팅 시 자동실행), 강력한 창 Z-Order 제어 및 Windows 알림 센터 App ID 등록에 사용됩니다.
  * `logging`: `RotatingFileHandler`를 이용한 디버그 모드 로그 기록에 사용됩니다.
  * `hashlib`: 실행 파일의 MD5 해시를 생성하여 빌드 버전을 식별하는 데 사용됩니다.

## 설치 및 사용 방법

### 1. 저장소 클론 및 종속성 설치
```bash
git clone [https://github.com/YourUsername/zabbix-overlay-widget.git](https://github.com/YourUsername/zabbix-overlay-widget.git)
cd zabbix-overlay-widget

# 필수 외부 라이브러리 설치
pip install PyQt5 requests urllib3
```

### 2. 프로그램 실행
```bash
# Python 3.12 환경에서의 실행을 권장합니다.
python zabbix_overlay.py
```

### 3. Zabbix 설정 (`config/zabbix_overlay_config.json`)
최초 실행 시 언어 선택 창이 나타나며, 언어를 선택하면 기본 설정 파일이 생성된 후 프로그램이 종료됩니다. `config` 폴더에 생성된 파일을 열어 실제 서버 정보로 업데이트해 주세요:
* `zabbix_url`: `https://[자신의-Zabbix-IP-또는-도메인]/api_jsonrpc.php`
* `zabbix_api_token`: (권장) Zabbix에서 발급받은 API 토큰을 입력합니다.
* `zabbix_user` / `zabbix_password`: API 토큰을 사용하지 않는 경우 Zabbix 로그인 계정 정보를 입력합니다.

## 실행 파일 빌드 (Windows)
Python이 설치되지 않은 PC에서도 실행할 수 있도록 단일 `.exe` 파일로 컴파일할 수 있습니다. 아래 빌드 명령어에는 필수 폰트와 아이콘 리소스 포함 옵션이 적용되어 있습니다.

```bash
# PyInstaller 설치
pip install pyinstaller

# 콘솔 창 없이 단일 실행 파일로 빌드 (리소스 포함)
pyinstaller --noconsole --onefile --add-data "IBMPlexSansKR-Regular.ttf;." --add-data "zabbix_icon.ico;." --icon "zabbix_icon.ico" zabbix_overlay.py
```

빌드가 완료되면 `dist` 폴더 안에 `zabbix_overlay.exe` 파일이 생성됩니다.

## 알려진 문제 및 해결 방법

**백신 프로그램 오탐(False Positive) 현상 (Windows)**
이 프로젝트를 PyInstaller를 사용하여 독립 실행형 `.exe` 파일로 컴파일하여 실행할 경우, Windows Defender를 비롯한 일부 백신 프로그램에서 이를 바이러스나 악성코드로 오진하여 차단할 수 있습니다. 이는 PyInstaller로 패키징된 파일에서 매우 흔하게 발생하는 **오탐(False Positive)** 현상이며, 주된 이유는 다음과 같습니다:
* 유료 디지털 서명(Code Signing 인증서)이 포함되어 있지 않음
* OS 레벨의 시스템 기능(창 항상 위 겹침, 시스템 트레이, 알림 센터 연동, 부팅 시 자동실행 레지스트리 등)을 깊숙이 제어함
* 백그라운드에서 Zabbix 서버와 지속적인 HTTPS API 통신을 수행함

**해결 방법:**
본 프로그램의 소스 코드는 100% 공개되어 있으며 어떠한 악의적인 코드도 포함되어 있지 않으니 안심하셔도 됩니다. 프로그램을 차단 없이 원활하게 실행하시려면, 사용 중인 백신 프로그램(Windows Defender, V3, 알약 등)의 **검사 예외(제외) 항목**에 `zabbix_overlay.exe` 파일 또는 해당 파일이 있는 폴더 전체를 추가해 주시기 바랍니다.

## 라이선스
이 프로젝트는 MIT 라이선스(MIT License)에 따라 배포됩니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.
