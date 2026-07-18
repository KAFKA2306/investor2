import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_paper_catalog.py"
SPEC = importlib.util.spec_from_file_location("validate_paper_catalog", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_2010s_paper_catalog_is_structurally_valid() -> None:
    catalog = ROOT / "docs" / "research" / "2010s_paper_catalog.json"
    assert MODULE.validate_catalog(catalog) == []
