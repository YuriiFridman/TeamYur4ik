import os

# Server network configuration
HOST = os.getenv("HOST", "0.0.0.0")
WS_PORT = int(os.getenv("WS_PORT", "8765"))
VOICE_PORT = int(os.getenv("VOICE_PORT", "9000"))

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "teamyur4ik.db")

# Security
SECRET_KEY = os.getenv("SECRET_KEY", "change-this-secret-key-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24
AES_KEY = os.getenv("AES_KEY", "").encode() or b"TeamYur4ikKey256"[:32].ljust(32, b'0')

# Channel limits
MAX_CHANNELS = 50
MAX_USERS_PER_CHANNEL = 100

# Voice settings
VOICE_SAMPLE_RATE = 48000
VOICE_CHANNELS = 1
VOICE_FRAME_DURATION = 20  # ms
