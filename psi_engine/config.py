from __future__ import annotations

OFFICIAL_SOURCES = ("product", "purchase", "crm", "target", "revenue", "inventory")
CONTROL_INPUTS = ("manual_check",)
REQUIRED_SOURCES = OFFICIAL_SOURCES + CONTROL_INPUTS
SOURCE_OWNERS = {
    "product": "purchase", "purchase": "purchase", "crm": "sale", "target": "sale",
    "revenue": "accounting", "inventory": "accounting", "manual_check": "accounting",
}
SOURCE_LABELS = {
    "product": "Product", "purchase": "Purchase / Loading List", "crm": "CRM Sale",
    "target": "Target", "revenue": "Revenue", "inventory": "Inventory",
    "manual_check": "Manual Check (approved controls)",
}
LOGIN_EMAILS = {key: f"{key}@psi.nanohome.local" for key in ("purchase", "sale", "accounting", "tech")}

def may_upload(team: str, source: str) -> bool:
    return team == "tech" or SOURCE_OWNERS.get(source) == team
