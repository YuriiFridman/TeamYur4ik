import os
import logging

logger = logging.getLogger(__name__)

# Server network configuration
HOST = os.getenv("HOST", "0.0.0.0")
WS_PORT = int(os.getenv("WS_PORT", "8765"))
VOICE_PORT = int(os.getenv("VOICE_PORT", "9000"))

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "teamyur4ik.db")

# Security — warn loudly when insecure defaults are used so operators
# notice immediately that they must set these values in production.
_DEFAULT_SECRET = "change-this-secret-key-in-production"
SECRET_KEY = os.getenv("SECRET_KEY", _DEFAULT_SECRET)
if SECRET_KEY == _DEFAULT_SECRET:
    logger.warning(
        "SECRET_KEY is using the insecure default value. "
        "Set the SECRET_KEY environment variable before deploying to production."
    )

JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24

_DEFAULT_AES = b"TeamYur4ikKey256"[:16].ljust(32, b"0")
_aes_env = os.getenv("AES_KEY", "").encode()
AES_KEY: bytes = _aes_env.ljust(32, b"0")[:32] if _aes_env else _DEFAULT_AES
if AES_KEY == _DEFAULT_AES:
    logger.warning(
        "AES_KEY is using the insecure default value. "
        "Set the AES_KEY environment variable (32-byte hex or ASCII) before deploying to production."
    )

# Channel limits
MAX_CHANNELS = 50
MAX_USERS_PER_CHANNEL = 100

# Voice settings
VOICE_SAMPLE_RATE = 48000
VOICE_CHANNELS = 1
VOICE_FRAME_DURATION = 20  # ms
