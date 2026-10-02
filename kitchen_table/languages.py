"""Languages the reader can choose. `speech` is the BCP-47 tag used for read-aloud."""

LANGUAGES = {
    "en": {"name": "English", "native": "English", "speech": "en-US"},
    "es": {"name": "Spanish", "native": "Español", "speech": "es-US"},
    "ru": {"name": "Russian", "native": "Русский", "speech": "ru-RU"},
    "uk": {"name": "Ukrainian", "native": "Українська", "speech": "uk-UA"},
    "zh": {"name": "Simplified Chinese", "native": "简体中文", "speech": "zh-CN"},
    "vi": {"name": "Vietnamese", "native": "Tiếng Việt", "speech": "vi-VN"},
    "tl": {"name": "Tagalog", "native": "Tagalog", "speech": "fil-PH"},
    "ko": {"name": "Korean", "native": "한국어", "speech": "ko-KR"},
    "ar": {"name": "Arabic", "native": "العربية", "speech": "ar-SA", "rtl": True},
    "fa": {"name": "Persian", "native": "فارسی", "speech": "fa-IR", "rtl": True},
    "pt": {"name": "Portuguese", "native": "Português", "speech": "pt-BR"},
    "pl": {"name": "Polish", "native": "Polski", "speech": "pl-PL"},
    "hi": {"name": "Hindi", "native": "हिन्दी", "speech": "hi-IN"},
    "fr": {"name": "French", "native": "Français", "speech": "fr-FR"},
    "ht": {"name": "Haitian Creole", "native": "Kreyòl ayisyen", "speech": "fr-HT"},
    "de": {"name": "German", "native": "Deutsch", "speech": "de-DE"},
    "it": {"name": "Italian", "native": "Italiano", "speech": "it-IT"},
    "ja": {"name": "Japanese", "native": "日本語", "speech": "ja-JP"},
}


def name(code: str) -> str:
    return LANGUAGES.get(code, LANGUAGES["en"])["name"]
