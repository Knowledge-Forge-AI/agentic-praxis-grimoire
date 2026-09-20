"""Pure built-in operational metadata classification; no Git dependencies."""

# Built-in untracked operational metadata roots.
# Tracked paths under these roots remain product.
OPERATIONAL_METADATA_ROOTS: tuple[str, ...] = (
    ".serena",
    ".pytest_cache",
    ".claude/.cc-writes",
    ".scratch",
)


def is_metadata_pattern(path: str) -> bool:
    """Return whether a relative path matches known operational metadata roots.

    Ambiguous root 'result' is explicitly product by default.
    """
    norm = path.replace("\\", "/").strip("/")
    for root in OPERATIONAL_METADATA_ROOTS:
        if norm == root or norm.startswith(f"{root}/"):
            return True
    return False


def classify_path(path: str, is_tracked: bool) -> str:
    """Classify a path as product or operational metadata.

    Tracked paths are product by default even when their name resembles metadata.
    """
    if is_tracked:
        return "product"
    if is_metadata_pattern(path):
        return "operational_metadata"
    return "product"

