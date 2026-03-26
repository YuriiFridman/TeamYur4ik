```
 _______ _______ _______ _______ ___ ___  __ __  ____    ___ ____  __ __
|       |       |   _   |   |   |   |   ||  |  ||    \  /  _]    ||  |  |
|_     _|    ___|  |_|  |       |   |   ||  |  ||  D  )/  [_ |  | |  |  |
  |   | |   |___  |   | |       |\     / |  |  ||    /|    _]|  | |  |  |
  |   | |    ___|  \_/  |   |   | |   |  |  :  ||    \|   [_ |  | |  :  |
  |   | |   |___|       |       | |   |  |     ||  .  \     ||  |  \   /
  |___| |_______|_______|_______|_|___|   \__,_||__|\_|\_____|____|  \_/

           TeamSpeak-inspired voice & text chat — built with Python
```

# TeamYur4ik

A full-featured, **TeamSpeak-like** desktop voice and text chat application written entirely in Python.
Real-time voice chat, servers, channels, roles, moderation, and a polished Discord-style UI.

---

## ✨ Features

| Feature | Detail |
|---|---|
| 🎙️ Real-time voice chat | Opus-encoded audio over UDP with auto-relay |
| 💬 Text chat | Persistent message history per channel |
| 🏠 Servers & channels | Create unlimited servers; text and voice channels |
| 👥 User roles | Admin / Moderator / Member with permission enforcement |
| 🔨 Moderation | Kick, ban, mute users; ban management panel |
| 🖥️ Admin panel | GUI panel to manage channels, users, and bans |
| 🌍 Cross-platform | Windows, Linux, macOS |
| 🌑 Dark & light themes | Discord-inspired dark theme + clean light theme |
| 🌐 EN / RU localization | Switch language at runtime |
| 📦 PyInstaller build | Single-file `.exe` / binary for distribution |

---

## 🏗️ Architecture

### Backend (`server/`)
- **`server.py`** – asyncio WebSocket server; handles all client commands
- **`voice_relay.py`** – asyncio UDP relay; broadcasts Opus frames to channel peers
- **`database.py`** – SQLite with parameterised queries; bcrypt password hashing
- **`auth.py`** – JWT token creation and verification (PyJWT)
- **`config.py`** – All configuration via environment variables

### Client (`client/`)
- **`ui/main_window.py`** – 3-panel PyQt6 layout (server list · channels+users · chat)
- **`ui/login_window.py`** – Login / register with background worker thread
- **`ui/settings_dialog.py`** – Audio, theme, language, PTT key settings
- **`ui/admin_panel.py`** – Channel/user/ban management dialog
- **`network/client.py`** – WebSocket (text) + UDP (voice) with auto-reconnect
- **`audio/audio_manager.py`** – PyAudio capture/playback; Opus codec; VAD & PTT
- **`localization/`** – JSON translation files, singleton `loc` manager

---

## 🚀 Quick Start

### Run the server

```bash
git clone https://github.com/YOUR_USER/TeamYur4ik.git
cd TeamYur4ik/server

pip install -r requirements.txt
python server.py
```

The server listens on:
- WebSocket : `ws://0.0.0.0:8765`
- Voice UDP : `0.0.0.0:9000`

### Run the client

```bash
cd TeamYur4ik/client

pip install -r requirements.txt
python main.py
```

Enter your server address (e.g. `localhost`), port `8765`, voice port `9000`, then register
an account and log in.

---

## 📦 Build standalone executable

```bash
cd TeamYur4ik/build

# Linux / macOS
bash build.sh

# Windows
build.bat
```

The output binary is in `build/dist/TeamYur4ik`.

---

## ☁️ Deploy on Railway.app

1. Create a free account at [railway.app](https://railway.app)
2. Click **New Project → Deploy from GitHub repo**
3. Select this repository
4. Set the **Root Directory** to `server`
5. Add the environment variables listed in the table below
6. Railway will detect `railway.json` and run `python server.py` automatically
7. Copy the generated public URL and use it as the server address in the client

---

## ⚙️ Environment variables

| Variable | Default | Description |
|---|---|---|
| `HOST` | `0.0.0.0` | Bind address for WebSocket and UDP |
| `WS_PORT` | `8765` | WebSocket port |
| `VOICE_PORT` | `9000` | UDP voice relay port |
| `DATABASE_URL` | `teamyur4ik.db` | Path to SQLite database file |
| `SECRET_KEY` | *(insecure default)* | JWT signing secret — **change in production** |
| `AES_KEY` | *(insecure default)* | AES encryption key (32 bytes) |

---

## 🛠️ Development setup

```bash
# Create a virtual environment
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# Install all dependencies
pip install -r server/requirements.txt
pip install -r client/requirements.txt

# Run server
cd server && python server.py

# Run client (in a separate terminal)
cd client && python main.py
```

### Project structure

```
TeamYur4ik/
├── server/
│   ├── server.py          # WebSocket server
│   ├── voice_relay.py     # UDP voice relay
│   ├── database.py        # SQLite ORM-free helpers
│   ├── auth.py            # JWT helpers
│   ├── config.py          # Configuration
│   ├── requirements.txt
│   ├── Procfile           # Heroku/Railway
│   └── railway.json
├── client/
│   ├── main.py            # Entry point
│   ├── audio/
│   │   └── audio_manager.py
│   ├── network/
│   │   └── client.py
│   ├── ui/
│   │   ├── main_window.py
│   │   ├── login_window.py
│   │   ├── settings_dialog.py
│   │   ├── admin_panel.py
│   │   └── styles.py
│   ├── localization/
│   │   ├── en.json
│   │   └── ru.json
│   └── requirements.txt
└── build/
    ├── TeamYur4ik.spec
    ├── build.sh
    └── build.bat
```

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.
