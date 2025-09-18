from typing import List, Dict, Optional

try:
    from core.fireworks_api_client import generate_response
except Exception:
    def generate_response(messages, stream=False, temperature=0.0):
        if stream:
            yield ""
        return ["english"]


TOP_LANGUAGES = [
    "english", "chinese", "hindi", "spanish", "french",
    "arabic", "bengali", "portuguese", "russian", "urdu"
]

def _normalize_lang_name(name: str) -> str:
    n = (name or "").strip().lower()
    alias_map = {
        "indo": "indonesian", "bahasa": "indonesian", "bahasa indonesia": "indonesian",
        "zh": "chinese", "mandarin": "chinese", "zh-cn": "chinese", "zh-hans": "chinese",
        "es": "spanish", "español": "spanish",
        "fr": "french", "français": "french",
        "pt": "portuguese", "português": "portuguese",
        "ar": "arabic",
        "bn": "bengali", "bangla": "bengali",
        "ru": "russian",
        "hi": "hindi",
        "ur": "urdu"
    }
    if n in alias_map:
        return alias_map[n]
    return n


def detect_target_language_from_messages(messages: Optional[List[Dict]]) -> str:
    try:
        if not messages:
            return "english"
        recent = "\n".join([f"{m.get('role')}: {m.get('content','')}" for m in messages[-6:]])
        allowed = TOP_LANGUAGES + ["indonesian"]
        choices_str = ", ".join(allowed)
        prompt = (
            "From the conversation below, choose the best reply language.\n"
            f"Respond with ONE lowercase word from this list only: {choices_str}.\n\n"
            f"Conversation:\n{recent}\n\nLanguage:"
        )
        msgs = [{"role": "user", "content": prompt}]
        result = generate_response(msgs, stream=False, temperature=0.0)
        lang = _normalize_lang_name("".join(result).strip())
        if lang not in allowed:
            for a in allowed:
                if a in lang:
                    return a
            return "english"
        return lang
    except Exception:
        try:
            text = " ".join([(messages or [])[-1].get('content','')]).lower()
            if "bahasa indonesia" in text or "gunakan bahasa indonesia" in text:
                return "indonesian"
            if any(k in text for k in ["español", "spanish"]):
                return "spanish"
            if any(k in text for k in ["français", "french"]):
                return "french"
            if any(k in text for k in ["português", "portuguese"]):
                return "portuguese"
            if any(k in text for k in ["русский", "russian"]):
                return "russian"
            if any(k in text for k in ["हिंदी", "hindi"]):
                return "hindi"
            if any(k in text for k in ["العربية", "arabic"]):
                return "arabic"
            if any(k in text for k in ["বাংলা", "bengali", "bangla"]):
                return "bengali"
            if any(k in text for k in ["中文", "汉语", "mandarin", "chinese", "zh-cn"]):
                return "chinese"
            if any(k in text for k in ["اردو", "urdu"]):
                return "urdu"
        except Exception:
            pass
        return "english"


def detect_target_language_from_text(text: str) -> str:
    try:
        snippet = (text or "").strip()
        if not snippet:
            return "english"
        allowed = TOP_LANGUAGES + ["indonesian"]
        choices_str = ", ".join(allowed)
        prompt = (
            "From the context below, choose the best reply language.\n"
            f"Respond with ONE lowercase word from this list only: {choices_str}.\n\n"
            f"Context:\n{snippet[:2000]}\n\nLanguage:"
        )
        msgs = [{"role": "user", "content": prompt}]
        result = generate_response(msgs, stream=False, temperature=0.0)
        lang = _normalize_lang_name("".join(result).strip())
        if lang not in allowed:
            for a in allowed:
                if a in lang:
                    return a
            return "english"
        return lang
    except Exception:
        lower = (text or "").lower()
        if any(k in lower for k in ["bahasa indonesia", "gunakan bahasa indonesia"]):
            return "indonesian"
        if any(k in lower for k in ["español", "spanish"]):
            return "spanish"
        if any(k in lower for k in ["français", "french"]):
            return "french"
        if any(k in lower for k in ["português", "portuguese"]):
            return "portuguese"
        if any(k in lower for k in ["русский", "russian"]):
            return "russian"
        if any(k in lower for k in ["हिंदी", "hindi"]):
            return "hindi"
        if any(k in lower for k in ["العربية", "arabic"]):
            return "arabic"
        if any(k in lower for k in ["বাংলা", "bengali", "bangla"]):
            return "bengali"
        if any(k in lower for k in ["中文", "汉语", "mandarin", "chinese", "zh-cn"]):
            return "chinese"
        if any(k in lower for k in ["اردو", "urdu"]):
            return "urdu"
        return "english"


