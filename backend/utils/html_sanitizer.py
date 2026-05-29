"""HTML sanitizer for TipTap scene editor input.

Allow-list approach: keeps the safe subset our reader UI renders and
strips anything else (scripts, styles, inline event handlers, javascript
URLs, inline style, arbitrary classes). Behaviour is preserved verbatim
from the legacy ``sanitize_scene_html`` implementation that lived in
``server.py`` before the Media Routes Split.
"""
from __future__ import annotations

import re


_ALLOWED_TAGS = {"p", "br", "ul", "li", "strong", "em", "span"}
_ALLOWED_CLASSES = {
    "text-left",
    "text-center",
    "text-right",
    "font-size-s",
    "font-size-m",
    "font-size-l",
}


def sanitize_scene_html(html: str) -> str:
    """Sanitize HTML coming from the TipTap editor.

    Allowed tags: ``p, br, ul, li, strong, em, span`` (with restricted
    class attribute). Strips scripts, styles, inline event handlers,
    ``javascript:`` URLs, inline ``style`` attributes and any class not
    in the allow-list. Disallowed tags are removed but their text content
    is preserved.
    """
    if not html:
        return ""

    # Drop <script> / <style> blocks entirely (incl. their content).
    html = re.sub(
        r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE
    )
    html = re.sub(
        r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE
    )

    # Strip inline event handlers (onclick, onmouseover, …).
    html = re.sub(
        r"\s+on\w+\s*=\s*[\"'][^\"']*[\"']", "", html, flags=re.IGNORECASE
    )

    # Strip javascript: URLs in href.
    html = re.sub(
        r"href\s*=\s*[\"']javascript:[^\"']*[\"']", "", html, flags=re.IGNORECASE
    )

    # Strip inline style attribute (no colors / fonts allowed).
    html = re.sub(
        r"\s+style\s*=\s*[\"'][^\"']*[\"']", "", html, flags=re.IGNORECASE
    )

    # Clean class attribute: only keep allow-listed classes.
    def _clean_class(match: re.Match) -> str:
        classes = match.group(1).split()
        kept = [c for c in classes if c in _ALLOWED_CLASSES]
        if kept:
            return f' class="{" ".join(kept)}"'
        return ""

    html = re.sub(
        r"\s+class\s*=\s*[\"']([^\"']*)[\"']",
        _clean_class,
        html,
        flags=re.IGNORECASE,
    )

    # Drop disallowed tags but keep their inner text.
    disallowed_pattern = (
        r"</?(?!(?:" + "|".join(_ALLOWED_TAGS) + r")\b)[a-z][^>]*>"
    )
    html = re.sub(disallowed_pattern, "", html, flags=re.IGNORECASE)

    return html.strip()
