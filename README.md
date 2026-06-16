# Zabbix Overlay Widget

> **Read this in other languages:** [한국어 (Korean)](README_KR.md)

A powerful desktop widget that monitors real-time Zabbix problems and displays them in an intuitive, floating UI right on your desktop. It is designed to help you quickly assess and respond to system alerts without needing to keep a web browser open.

> **Note**: The code structuring and documentation for this project were assisted by **Gemini**, Google's AI model.

## Detailed Features
* **Real-Time Monitoring UI**: Communicates periodically with the Zabbix API to display active problems grouped by severity (Disaster, High, Average, Warning, Info, Not classified). Features a smooth **pulse (breathing) animation** that fills the widget background with the specific severity color when new alerts arrive.
* **Smart Unread Tracking System**: 
  * Newly created or updated alerts trigger a striking red "ripple" badge on the main widget.
  * Inside the list view, unread items display continuous ripple animations. 
  * Features a convenient "**✔ Mark all as read**" button to clear notifications instantly.
* **Versatile Notifications**: 
  * Choose between beautifully animated **Custom UI Toast pop-ups** or **Windows Native Notifications**.
  * Windows notifications are fully integrated with the OS Action Center, preserving your alert history even after the pop-up fades.
* **Floating Overlay**: 
  * Freely draggable to any position on your screen.
  * Supports an 'Always on Top' mode so you never miss an alert while working.
* **Quick Issue Action**: 
  * Double-click on any severity icon to view details, Acknowledge problems, leave comments, change severities, or manually Close them via the Zabbix API.
* **Advanced History & Log Viewer**: 
  * Check past alert histories with filtering options and read operational message logs left by other team members.
* **UI Customization**: 
  * Supports seamless switching between **Dark Mode** and **Light Mode**.
  * Resize the widget freely, switch between circle/rectangle themes, and change layout orientations (horizontal/vertical, 1 or 2 rows).
* **User-Friendly Setup (i18n)**: 
  * Automatically prompts an **Initial Language Selection Dialog** on the very first run. Fully supports English (en) and Korean (ko) via dynamic JSON-based translations.
  * Prevents duplicate execution to ensure system stability.

## Tech Stack & Environment

* **Build Environment**: Python 3.12+
* **UI Framework**: PyQt5
* **Key Imported Modules**:
  * `PyQt5 (QtWidgets, QtCore, QtGui)`: Used for GUI construction, system tray icons, smooth property animations (`QVariantAnimation`), multithreading (`QThread`), and duplicate execution prevention (`QSharedMemory`).
  * `requests`, `urllib3`: For handling Zabbix JSON-RPC API communication and suppressing insecure HTTPS warnings.
  * `json`: For parsing and saving configuration files and translation data.
  * `os`, `sys`: For file path resolution and handling PyInstaller frozen states.
  * `winreg`, `ctypes`: For Windows registry manipulation (Run on Startup), strict window Z-Order control, and Windows Action Center App ID registration.
  * `logging`: For debug mode logging with `RotatingFileHandler`.
  * `hashlib`: Generates an MD5 hash of the executable to distinguish builds.

## Installation & Usage

### 1. Clone the repository and install dependencies
```bash
git clone [https://github.com/YourUsername/zabbix-overlay-widget.git](https://github.com/YourUsername/zabbix-overlay-widget.git)
cd zabbix-overlay-widget

# Install required external libraries
pip install PyQt5 requests urllib3
```

### 2. Run the application
```bash
# Recommended to run in a Python 3.12 environment
python zabbix_overlay.py
```

### 3. Zabbix Configuration (`config/zabbix_overlay_config.json`)
Upon the first launch, the program will prompt you to select a language, generate a default configuration file, and exit. Open the generated file in the `config` folder and update your details:
* `zabbix_url`: `https://[Your-Zabbix-IP-or-Domain]/api_jsonrpc.php`
* `zabbix_api_token`: (Highly Recommended) API token generated from Zabbix.
* `zabbix_user` / `zabbix_password`: Your Zabbix credentials if you are not using an API token.

## Building the Executable (Windows)
You can compile the script into a standalone `.exe` file so it can run on systems without Python installed. The build command includes the necessary font and icon assets.

```bash
# Install PyInstaller
pip install pyinstaller

# Build a standalone executable without a console window, including resources
pyinstaller --noconsole --onefile --add-data "IBMPlexSansKR-Regular.ttf;." --add-data "zabbix_icon.ico;." --icon "zabbix_icon.ico" zabbix_overlay.py
```

Once completed, you will find the `zabbix_overlay.exe` inside the `dist` folder.

## Known Issues & Troubleshooting

**Antivirus False Positives (Windows)**
If you compile this project into a standalone `.exe` using PyInstaller, some antivirus software (like Windows Defender) may flag it as a virus or malware. This is a common **false positive** issue with PyInstaller bundles, primarily because:
* It lacks a paid Digital Signature (Code Signing Certificate).
* It interacts with OS-level APIs (Window Z-order, System Tray, Action Center, Registry for Auto-start).
* It performs background HTTPS requests to the Zabbix server.

**Resolution:**
Rest assured, the source code is completely open, transparent, and safe. To run the executable without issues, simply add the `zabbix_overlay.exe` file or its containing folder to your antivirus software's **Exclusion List (Whitelist)**.

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
