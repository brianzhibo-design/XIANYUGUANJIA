"""Auto-update configuration for GitHub private releases."""

import os

GITHUB_OWNER = os.getenv("GITHUB_UPDATE_OWNER", "brianzhibo-design")
GITHUB_REPO = os.getenv("GITHUB_UPDATE_REPO", "XIANYUGUANJIA")
GITHUB_TOKEN = os.getenv("GITHUB_UPDATE_TOKEN", "")
UPDATE_ASSET_SUFFIX = "-update.tar.gz"
CHECKSUM_ASSET_SUFFIX = "-checksums.txt"
