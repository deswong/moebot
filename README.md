# MoeBot MQTT Bridge

This project provides a reliable Python-based MQTT bridge for MoeBot robotic mowers. It allows you to integrate your mower with home automation systems like Home Assistant, OpenHAB, or any MQTT-capable platform.

It is designed to be lightweight, robust, and run entirely locally without relying on external cloud services for operation.

> **Note**: While this bridge operates locally, you **must** initially set up a Tuya Cloud account to obtain your unique **Device ID** and **Local Key**. Once these credentials are obtained, the cloud connection is no longer needed for daily operation.

## Features

- **Local Operation**: Does not require constant internet access or cloud polling.
- **Robust Connection**: Automatically handles Tuya protocol version negotiation (3.3/3.4).
- **Extended Data**: Retrieves detailed status including:
    - Battery & State (Mowing, Charging, etc.)
    - Machine Errors (decoded messages)
    - Device Password/PIN
    - Zone Configuration
- **MQTT Control**: Full control via MQTT commands (Start, Stop, Pause, Dock, Configuration).
- **Memory Efficient**: Lazy loads dependencies to minimize footprint.

## Installation

### Option 1: Modern Setup (using `uv`) - Recommended

This project uses `uv` for fast dependency management.

1.  **Install `uv`** (if not installed):
    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```

2.  **Run with `uv`**:
    You don't need to manually create a virtual environment. `uv` handles it by reading the dependencies directly from `main.py`.
    ```bash
    uv run main.py
    ```
    This will automatically install dependencies and run the script.

### Option 2: Traditional Setup (pip)

1.  **Create a Virtual Environment**:
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # on Linux/Mac
    # venv\Scripts\activate  # on Windows
    ```

2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

## Finding Device Details (Device ID & Local Key)

To use this bridge, you need your unique **Device ID** and **Local Key**. The easiest way to get these is using the `tinytuya` wizard included with this project's dependencies.

1.  **Register on Tuya IoT Platform**:
    - Go to [iot.tuya.com](https://iot.tuya.com/) and create a free account.
    - Create a "Cloud Development" project (select "Smart Home" type).
    - Link your "Tuya Smart" or "Smart Life" App account to this project (Devices -> Link Tuya App Account).
    - **Note**: Ensure your data center region matches your location.

2.  **Run the Wizard**:
    From your project folder (with virtual environment active), run:
    ```bash
    python3 -m tinytuya wizard
    ```

3.  **Follow the Prompts**:
    - It will ask for your **API Key** and **API Secret** (found in your Tuya IoT Project Overview).
    - It will scan your linked account and list all devices.
    - Look for your mower in the list. Note down the `id` (Device ID) and `key` (Local Key).
    - **Important**: The `key` is the **Local Key**, not the `uuid` or `product_key`.

## Configuration

Once you have your credentials, you need to update the configuration in `main.py`:

1.  Open `main.py` in a text editor.
2.  Locate the **Configuration** section at the top.
3.  Replace the placeholders with your actual details:

```python
# MoeBot Configuration
DEVICE_ID = "YOUR_DEVICE_ID"          # e.g., "bf9744..."
DEVICE_IP = "YOUR_DEVICE_IP"          # e.g., "192.168.1.100"
LOCAL_KEY = "YOUR_LOCAL_KEY"          # e.g., "e2_y!..."

# MQTT Configuration
MQTT_HOST = "YOUR_MQTT_BROKER_IP"     # e.g., "192.168.1.50"
MQTT_PORT = 1883
MQTT_USERNAME = "YOUR_MQTT_USERNAME"  # Optional
MQTT_PASSWORD = "YOUR_MQTT_PASSWORD"  # Optional
MQTT_TOPIC = "moebot"
```

## Usage

### 1. Simple Status Query (CLI)
Run the script without arguments to perform a single poll of the device status. This is useful for testing connectivity.

```bash
python3 main.py
```

### 2. Live Listener
To watch for real-time updates from the device in your console:

```bash
python3 main.py listen
```

### 3. MQTT Bridge (Daemon Mode)
To start the MQTT bridge, which connects to the broker and listens for commands:

```bash
python3 main.py mqtt
```

## MQTT Commands & Topics

**Base Topic**: `moebot` (configurable)

### Status Topics (`moebot/stats/...`)
- `state`: Current machine state (e.g., MOWING, CHARGING, STANDBY)
- `battery`: Battery percentage
- `machine_errors`: Comma-separated list of active errors (or "None")
- `device_password`: Current PIN
- `mow_time`: Scheduled mow duration
- `online`: generic online/offline boolean
- `zoneX_distance` / `zoneX_ratio`: Zone configuration

### Command Topics (`moebot/cmnd/...`)
Send a payload to these topics to control the mower:

- `start`: Start mowing (Payload: `spiral` for spiral cut, or empty for normal)
- `pause`: Pause operation
- `dock`: Return to station
- `cancel`: Cancel current operation
- `mow_in_rain`: Enable (`true`/`on`) or disable (`false`/`off`) rain mode
- `mow_time`: Set duration in hours (e.g., `4`)
- `poll`: Force a status refresh

## Running as a Service

To keep the bridge running in the background, you should set it up as a system service.

### Linux (systemd)

1.  Edit the `moebot.service` file below, updating the paths to match your installation:

    ```ini
    [Unit]
    Description=MoeBot MQTT Bridge
    After=network.target

    [Service]
    Type=simple
    User=your_user
    WorkingDirectory=/path/to/moebot-mqtt
    # Option 1: Using pip/venv
    ExecStart=/path/to/moebot-mqtt/venv/bin/python3 main.py mqtt
    # Option 2: Using uv (path to .venv created by 'uv sync' or 'uv run')
    # ExecStart=/path/to/moebot-mqtt/.venv/bin/python3 main.py mqtt
    Restart=always
    RestartSec=10

    [Install]
    WantedBy=multi-user.target
    ```

2.  Copy to systemd directory:
    ```bash
    sudo nano /etc/systemd/system/moebot.service
    # Paste content, save and exit
    ```

3.  Enable and start:
    ```bash
    sudo systemctl daemon-reload
    sudo systemctl enable moebot.service
    sudo systemctl start moebot.service
    ```

4.  Check status:
    ```bash
    sudo systemctl status moebot.service
    ```

### Windows

For Windows, you can use the **NSSM (Non-Sucking Service Manager)** or Task Scheduler.

#### Option A: Task Scheduler (Simpler)
1.  Open **Task Scheduler**.
2.  Create a **Basic Task** -> "Start MoeBot Bridge".
3.  Trigger: **When the computer starts**.
4.  Action: **Start a program**.
    - Program/script: `path\to\venv\Scripts\python.exe`
    - Add arguments: `main.py mqtt`
    - Start in: `path\to\moebot-mqtt`
5.  Check "Run whether user is logged on or not" in properties.

#### Option B: NSSM (Robust)
1.  Download and extract [NSSM](https://nssm.cc/).
2.  Open Command Prompt as Administrator.
3.  Run: `nssm install MoeBotMQTT`
4.  In the GUI:
    - **Path**: `C:\path\to\moebot-mqtt\venv\Scripts\python.exe`
    - **Startup directory**: `C:\path\to\moebot-mqtt`
    - **Arguments**: `main.py mqtt`
5.  Click **Install service**.
6.  Start it: `nssm start MoeBotMQTT`

## Troubleshooting

- **Error: Network Error / Unable to Connect (901/905)**:
    - Ensure the device IP is correct.
    - Ensure the device is on the same 2.4GHz WiFi network.
    - Check if the Local Key has expired (re-generate via Tuya developer portal if needed).

- **No Logs Available**:
    - This client relies on local data. If the device does not expose logs (DPS 111/112) locally, they will not appear in MQTT. Only Cloud-based Tuya APIs can see that historical data if the local protocol drops it.

- **Dependencies Missing**:
    - Ensure you activated the virtual environment before running (`source venv/bin/activate`).
