import json
import os
from typing import Dict


class LocalizationManager:
    """
    Singleton localization manager that loads JSON translation files.
    Falls back to English, then to the key itself, when a translation is missing.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._locale = "en"
        self._translations: Dict[str, Dict[str, str]] = {}
        self._load_locale("en")
        self._load_locale("ru")

    def _load_locale(self, locale: str):
        """Load translation file for the given locale."""
        path = os.path.join(os.path.dirname(__file__), f"{locale}.json")
        try:
            with open(path, "r", encoding="utf-8") as f:
                self._translations[locale] = json.load(f)
        except Exception as e:
            print(f"Failed to load locale {locale}: {e}")
            self._translations[locale] = {}

    def set_locale(self, locale: str):
        """Switch the active locale (must be a loaded locale key)."""
        if locale in self._translations:
            self._locale = locale

    def get(self, key: str) -> str:
        """
        Return the translation for key in the active locale.
        Falls back to English, then returns the key itself if no translation found.
        """
        result = self._translations.get(self._locale, {}).get(key)
        if result is None:
            result = self._translations.get("en", {}).get(key, key)
        return result

    def get_locale(self) -> str:
        """Return the currently active locale code."""
        return self._locale


# Global singleton — import this everywhere: from localization import loc
loc = LocalizationManager()
