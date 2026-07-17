from pathlib import Path
import importlib.util
import sys


MODULE_PATH = Path(__file__).parents[1] / "scripts" / "verify_post_publication_momentum.py"
SPEC = importlib.util.spec_from_file_location("verify_post_publication_momentum", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_frozen_oos_result() -> None:
    data_path = Path(__file__).parents[1] / "docs" / "research" / "data" / "ff_momentum_1994_2017.csv"
    report = MODULE.build_report(MODULE.load_returns(data_path))
    full = report["gross_results"]["post_publication_1994_2017"]
    late = report["gross_results"]["late_holdout_2006_2017"]

    assert full["months"] == 288
    assert abs(full["annualized_arithmetic_mean"] - 0.0494375) < 1e-12
    assert abs(full["annualized_sharpe_zero_rf"] - 0.28545290355718356) < 1e-12
    assert abs(full["max_drawdown"] - (-0.5742421471511056)) < 1e-12
    assert late["months"] == 144
    assert abs(late["annualized_arithmetic_mean"] - (-0.00225)) < 1e-12
    assert report["verdict"].startswith("not_confirmed")
