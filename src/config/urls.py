"""
CivitAI host configuration
"""

import re

# Host used for all API requests and downloads
CIVITAI_HOST = "https://civitai.red"
CIVITAI_API_BASE = f"{CIVITAI_HOST}/api/v1"

# Hosts accepted in user-supplied links (all serve the same models)
CIVITAI_HOST_PATTERN = r'https?://(?:www\.)?civitai\.(?:com|red|green)'

_HOST_RE = re.compile(rf'^{CIVITAI_HOST_PATTERN}(?=/|$)')


def download_url_for(version_id) -> str:
    """Build the download URL for a model version"""
    return f"{CIVITAI_HOST}/api/download/models/{version_id}"


def to_civitai_host(url: str) -> str:
    """Rewrite a link on any CivitAI host to use CIVITAI_HOST"""
    return _HOST_RE.sub(CIVITAI_HOST, url.strip(), count=1)
