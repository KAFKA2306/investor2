from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from src.io.input_ledger.validators.edinetdb import audit_edinetdb_annual_financials

Validator = Callable[[Mapping[str, Any], Mapping[str, Any], Path], dict[str, Any]]

VALIDATORS: dict[str, Validator] = {
    "edinetdb_mcp_projection": audit_edinetdb_annual_financials,
}
