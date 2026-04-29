# Zabbix Overlay Widget

A powerful desktop widget that monitors real-time Zabbix problems and displays them in an intuitive, floating UI right on your desktop. It is designed to help you quickly assess and respond to system alerts without needing to keep a web browser open.

> **Note**: The code structuring and documentation for this project were assisted by **Gemini**, Google's AI model.

## Detailed Features
* **Real-Time Monitoring UI**: Communicates periodically with the Zabbix API to display active problems grouped by severity (Disaster, High, Average, Warning, Info, Not classified) using distinct colors.
* **Floating Overlay**: 
  * Freely draggable to any position on your screen.
  * Supports an 'Always on Top' mode so you never miss an alert while working.
  * Features a translucent background that blends seamlessly with your desktop.
* **Interactive Toast Notifications**: 
  * Displays animated toast pop-ups in the corner of your screen for new alerts, severity changes, resolved issues, and new user acknowledgments.
  * Customizable duration and screen position (e.g., Bottom Right, Top Left).
* **Quick Issue Action**: 
  * Double-click on any severity icon to directly Acknowledge problems, leave comments, or manually Close them via the Zabbix API.
* **Advanced History & Log Viewer**: 
  * Check past alert histories with filtering options and read operational message logs left by other team members in real-time.
* **UI Customization**: 
  * Resize the widget freely, switch between circle/rectangle themes, and change layout orientations (horizontal/vertical, 1 or 2 rows).
* **Multi-language (i18n)**: Fully supports English (en) and Korean (ko) via dynamic JSON-based translations.

## Tech Stack & Environment

* **Build Environment**: Python 3.12
* **UI Framework**: PyQt5
* **Key Imported Modules**:
  * `PyQt5 (QtWidgets, QtCore, QtGui)`: Used for GUI construction, system tray icons, animations, multithreading (QThread), and graphics rendering.
  * `requests`, `urllib3`: For handling Zabbix JSON-RPC API communication and suppressing insecure HTTPS warnings.
  * `json`: For parsing and saving configuration files and translation data.
  * `os`, `sys`: For file path resolution and handling PyInstaller frozen states.
  * `winreg`, `ctypes`: For Windows registry manipulation (Run on Startup) and strict window Z-Order control.
  * `logging`, `traceback`: For debug mode logging with `RotatingFileHandler` and exception catching.
  * `hashlib`: Generates an MD5 hash of the executable to distinguish builds.
  * `math`, `random`, `datetime`: For calculating the toast notification bubble animations and handling timestamps.

## Installation & Usage

### 1. Clone the repository and install dependencies
git clone https://github.com/YourUsername/zabbix-overlay-widget.git
cd zabbix-overlay-widget

# Install required external libraries
pip install PyQt5 requests urllib3

### 2. Run the application
# Recommended to run in a Python 3.12 environment
python zabbix_overlay.py

### 3. Zabbix Configuration (`config/zabbix_overlay_config.json`)
Upon the first launch, the program will generate a default configuration file and exit. Open the generated file in the `config` folder and update your details:
* `zabbix_url`: `https://[Your-Zabbix-IP-or-Domain]/api_jsonrpc.php`
* `zabbix_api_token`: (Highly Recommended) API token generated from Zabbix.
* `zabbix_user` / `zabbix_password`: Your Zabbix credentials if you are not using an API token.

## Building the Executable (Windows)
You can compile the script into a standalone `.exe` file so it can run on systems without Python installed. Tested with **Python 3.12**.

# Install PyInstaller
pip install pyinstaller

# Build a standalone executable (-F) without a console window (-w), including the icon
pyinstaller -w -F --icon=zabbix_icon.ico zabbix_overlay.py

Once completed, you will find the `zabbix_overlay.exe` inside the `dist` folder.

## License
This project is licensed under the MIT License.
