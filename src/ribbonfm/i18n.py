"""gettext based internationalisation.

Every user-visible string should be wrapped in ``_`` so that translations can be
picked up. The default language is detected from the environment and may be
changed at runtime by calling :func:`set_language`.

The compiled ``.mo`` files are searched in the standard GNU directories and in
the bundled ``locale`` directory shipped with the application.
"""

from __future__ import annotations

import gettext
import locale
import os
import sys
from pathlib import Path
from typing import Callable, Optional

from . import config

_available: dict[str, Path] = {}
_current: Optional[str] = None
_translations: dict[str, gettext.NullTranslations] = {}


def _locale_dir() -> Optional[Path]:
    """Look for a directory that contains ``<lang>/LC_MESSAGES/<domain>.mo``."""
    candidates = (
        config.resources_dir() / "locale",
        config.resources_dir().parent / "locale",
        Path(__file__).resolve().parent.parent / "locale",
    )
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    return None


def _discover() -> None:
    """Scan the locale directory for available translations."""
    _available.clear()
    base = _locale_dir()
    if not base:
        return
    for lang_dir in base.iterdir():
        mo = lang_dir / "LC_MESSAGES" / f"{config.APP_GETTEXT_DOMAIN}.mo"
        if mo.is_file():
            _available[lang_dir.name] = base


_ = gettext.gettext


def available_languages() -> dict[str, Path]:
    """Return ``{language_code: locale_dir}`` of installed translations."""
    if not _available:
        _discover()
    return dict(_available)


def current_language() -> Optional[str]:
    """Return the active language code (``None`` means system default)."""
    return _current


def _make_translator(lang: str) -> Callable[[str], str]:
    base = _available.get(lang)
    if base:
        try:
            tr = gettext.translation(
                config.APP_GETTEXT_DOMAIN,
                localedir=str(base),
                languages=[lang],
                fallback=True,
            )
            _translations[lang] = tr
            return tr.gettext
        except Exception:  # pragma: no cover - defensive
            return gettext.gettext
    return gettext.gettext


def _candidates(lang: str) -> list[str]:
    """Expand a language code to plausible codes/directory names.

    Handles both ``zh-CN`` (BCP-47) and ``zh_CN`` (glibc/gettext) styles so a
    translation shipped as ``locale/zh_CN/`` is found for a ``zh-CN`` locale.
    """
    result = []
    for code in (lang, lang.replace("-", "_"), lang.split("-")[0],
                 lang.split("_")[0]):
        if code and code not in result:
            result.append(code)
    return result


def _install_system() -> str:
    """Bind the whole process to the system locale (default behaviour)."""
    try:
        locale.setlocale(locale.LC_ALL, "")
        raw = locale.getlocale()[0] or locale.getpreferredencoding(False) or ""
        lang = locale.normalize(raw) if raw else ""
        if "." in lang:
            lang = lang.split(".")[0]
        lang = lang.replace("-", "_")
    except (locale.Error, TypeError, ValueError):
        lang = os_lang()
    gettext.bindtextdomain(config.APP_GETTEXT_DOMAIN)
    gettext.textdomain(config.APP_GETTEXT_DOMAIN)
    return lang


def os_lang() -> str:
    """Best effort host language detection.

    On Windows the ``locale``/``LANG`` signals are unreliable, so prefer the
    user's display language (``GetUserDefaultUILanguage``) mapped to a gettext
    code (e.g. ``zh_CN``).
    """
    win = _windows_lang()
    if win:
        return win
    for var in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        val = os.environ.get(var)
        if val:
            return val.split(":")[0].split(".")[0].replace("_", "-")
    return "en"


def _windows_lang() -> Optional[str]:
    """Return a gettext language code from the Windows UI language, or ``None``."""
    if not sys.platform.startswith("win"):
        return None
    lcids = ()
    try:
        import ctypes
        k32 = ctypes.windll.kernel32
        # User display language, then system default UI language.
        for fn in (k32.GetUserDefaultUILanguage, k32.GetSystemDefaultUILanguage):
            try:
                langid = fn()
                lcids += (int(langid),)
            except Exception:
                continue
    except Exception:
        return None
    for langid in lcids:
        for lcid in (langid, langid & 0x03FF):  # primary-language sub-id
            mapped = locale.windows_locale.get(lcid)
            if mapped:
                return mapped.replace("-", "_")
    return None


def _first_available() -> Optional[str]:
    """Return a bundled language to fall back to; prefer English, else any."""
    for pref in ("en", "en_US", "en_GB"):
        if pref in _available:
            return pref
    return next(iter(_available), None)


def init(language: Optional[str] = None) -> Callable[[str], str]:
    """Initialise gettext and return the ``_`` function.

    Args:
        language: explicit language code, or ``None`` to use the system locale.

    Resolves the language in this order: explicit ``language``, the detected
    system language, then a fallback to any bundled catalog. If no catalog is
    bundled at all it falls back to :func:`gettext.gettext` (English msgids).
    """
    global _, _current
    _discover()
    if language:
        for candidate in _candidates(language):
            if candidate in _available:
                return _activate(candidate)
    _current = None
    lang = _install_system()
    for candidate in _candidates(lang):
        if candidate in _available:
            return _activate(candidate)
    # Never show raw keys when a catalog exists: use the first available one.
    first = _first_available()
    if first is not None:
        return _activate(first)
    _ = gettext.gettext
    return _


def _activate(lang: str) -> Callable[[str], str]:
    global _, _current
    _current = lang
    _ = _make_translator(lang)
    return _


def set_language(language: str) -> Callable[[str], str]:
    """Switch the active translation at runtime.

    Only affects newly translated strings; existing widgets need to be re-rendered
    which is why :func:`ribbonfm.app.reload_language` asks for a restart.
    Args:
        language: a language code such as ``zh-CN``.
    """
    global _, _current
    for candidate in _candidates(language):
        if candidate in available_languages():
            _current = candidate
            _ = _make_translator(candidate)
            return _
    # Unknown code -> fall back to system default behaviour.
    _current = None
    _ = init(None)
    return _
