"""Auto-update configuration for GitHub private releases."""

import os

GITHUB_OWNER = os.getenv("GITHUB_UPDATE_OWNER", "brianzhibo-design")
GITHUB_REPO = os.getenv("GITHUB_UPDATE_REPO", "XIANYUGUANJIA")
GITHUB_TOKEN = os.getenv(
    "GITHUB_UPDATE_TOKEN",
    "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",
)
UPDATE_ASSET_SUFFIX = "-update.tar.gz"
