from typing import Final


# Raw sources required to calculate and release PSI Final.
REQUIRED_SOURCES: Final[tuple[str, ...]] = (
    "product",
    "purchase",
    "revenue",
    "inventory",
    "crm",
    "target",
)

# Reviewed registers may be uploaded for transparency and included in the
# workbook, but they do not generate new mismatches or block a release.
OPTIONAL_SOURCES: Final[tuple[str, ...]] = ("preorder",)
UPLOAD_SOURCES: Final[tuple[str, ...]] = REQUIRED_SOURCES + OPTIONAL_SOURCES
