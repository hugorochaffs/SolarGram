# APsystems Local Monitoring & Telegram Daily Reports

This project performs local polling (via raw TCP socket on port 8899) of your **APsystems ECU** unit (ECU-R, ECU-R-PRO, ECU-B, or ECU-C) without relying on APsystems cloud services or heavy frameworks like Home Assistant.

The system runs in the background, monitoring your solar installation, tracking daily generation peaks (for the whole system, each microinverter, and each PV module), and sending a **comprehensive daily report via Telegram at 18:00**. If communication with the ECU fails, an immediate alert is dispatched to Telegram.

---

## 📋 Features

* **Real-Time Monitoring:** Direct local reading from the ECU via TCP socket protocol.
* **Peak Tracking:** Records daily peak power achieved by the system overall, each microinverter, and each individual PV module.
* **Telegram Daily Report (18:00):**
* Daily energy generation (`kWh`)
* Total lifetime energy generation (`kWh`)
* System daily peak power (`W` and timestamp)
* Count of online/offline microinverters
* Detailed status per microinverter (Frequency `Hz`, Temperature `°C`, Signal level, Current Power, and Daily Peak)
* Detailed status per PV module/channel (Current Power `W`, Voltage `V`, and Daily Peak)


* **Failure & Recovery Alerts:** Immediate notifications if the ECU becomes unreachable, with follow-ups upon reconnection.
* **Zero Heavy Dependencies:** Written in pure Python 3 using standard library packages only.

---

## 🛠️ Project Structure

* `main.py`: Entry point for the daemon process and CLI argument parsing.
* `ecu_client.py`: TCP socket handler and binary protocol decoder for the ECU.
* `stats_tracker.py`: Tracks and persists daily power peaks to `daily_stats.json`.
* `telegram_notifier.py`: HTML formatting and HTTP delivery via the Telegram Bot API.
* `.env`: Environment file for local credentials and operational parameters.
* `.env.example`: Template for configuration settings.
* `apsystems-monitor.service`: `systemd` service unit file for Linux installation.

---

## ⚙️ Configuration (`.env`)

Copy `.env.example` to `.env` and fill in your details:

```env
# ==========================================
# APsystems ECU Settings
# ==========================================
ECU_IP=192.168.xx.xx
ECU_PORT=8899
ECU_ID=xxxxxxxxx
POLL_INTERVAL_SECONDS=120
REPORT_TIME=18:00

# ==========================================
# Telegram Bot Settings
# ==========================================
TELEGRAM_BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRstuVWXyz
TELEGRAM_CHAT_ID=12345678
TELEGRAM_ALERT_ON_FAILURE=true
ALERT_COOLDOWN_MINUTES=60

```

### Obtaining your Telegram Token & Chat ID:

1. **Bot Token:** Message [@BotFather](https://t.me/BotFather) on Telegram. Run `/newbot`, set a name and username, and copy the issued token.
2. **Chat ID:** Open a chat with your newly created bot, press `Start`, and send a message. Then query [@userinfobot](https://t.me/userinfobot) or [@raw_data_bot](https://t.me/raw_data_bot) to retrieve your numeric Chat ID.

---

## 🧪 Manual Testing

You can run standalone diagnostics using CLI flags in `main.py`:

1. **Test communication with local ECU:**
```bash
python3 main.py --test-ecu

```


2. **Test Telegram bot integration:**
```bash
python3 main.py --test-telegram

```


3. **Generate and send Daily Report immediately (bypassing 18:00 schedule):**
```bash
python3 main.py --test-report

```



---

## 📦 Service Installation (`systemd` on Linux)

To run the script persistently in the background and start automatically on boot:

1. **Copy unit file to systemd directory:**
```bash
sudo cp apsystems-monitor.service /etc/systemd/system/

```


2. **Reload systemd manager configuration:**
```bash
sudo systemctl daemon-reload

```


3. **Enable service to launch on boot:**
```bash
sudo systemctl enable apsystems-monitor.service

```


4. **Start service immediately:**
```bash
sudo systemctl start apsystems-monitor.service

```


5. **Verify service status:**
```bash
sudo systemctl status apsystems-monitor.service

```


6. **View live operational logs:**
```bash
journalctl -u apsystems-monitor.service -f

```



---

## 📝 Sample Telegram Daily Report

```html
☀️ DAILY SOLAR GENERATION REPORT
📅 Date: 08/12/2026 at 18:00
📍 ECU ID: xxxxxxxx

📊 OVERALL GENERATION SUMMARY:
• ⚡ Generation Today: 34.13 kWh
• 📈 Lifetime Total: 3,921.76 kWh
• 🔥 System Peak: 3,250 W (at 12:42:10)
• 🔌 Inverter Status: 5 / 8 Online

🛠️ MICROINVERTER & MODULE DETAILS:

🟢 Microinverter xxxxxxxx
  • Signal: 1/5 | Freq: 60.0 Hz | Temp: 36°C
  • Power Output: 35 W | Today's Peak: 540 W (12:40:15)
  • PV Modules (Channels):
    ▫️ Module 1: 18 W @ 206 V | Peak: 275 W
    ▫️ Module 2: 17 W @ 206 V | Peak: 265 W

🟢 Microinverter xxxxxxxxx
  • Signal: 3/5 | Freq: 60.1 Hz | Temp: 36°C
  • Power Output: 50 W | Today's Peak: 1180 W (12:42:10)
  • PV Modules (Channels):
    ▫️ Module 1: 13 W @ 204 V | Peak: 295 W
    ▫️ Module 2: 12 W @ 204 V | Peak: 295 W
    ▫️ Module 3: 12 W @ 204 V | Peak: 295 W
    ▫️ Module 4: 13 W @ 204 V | Peak: 295 W

🔴 Microinverter xxxxxxxxx
  • Status: ⚠️ Offline / No communication signal with ECU

```
