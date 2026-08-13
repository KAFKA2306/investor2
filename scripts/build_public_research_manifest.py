#!/usr/bin/env python3
"""Project the internal research evidence manifest into a small public-safe contract.

The public dashboard must never depend on internal audit/governance fields.  This
module is the explicit boundary: internal evidence can grow freely while the
public JSON stays stable, understandable, and intentionally small.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
INTERNAL_BUILDER = ROOT / "scripts" / "build_research_verification_manifest.py"

PUBLIC_QUESTIONS = {
    "jegadeesh_titman_1993_momentum": "最近上がった株は、その後もしばらく上がりやすい？",
    "banz_1981_size_late_oos_proxy": "小さい会社の株は、大きい会社の株より上がりやすい？",
    "fama_french_1992_size_proxy": "会社の大きさだけで、その後の株価差を説明できる？",
    "fama_french_1992_value_proxy": "割安な株は、割高な株より上がりやすい？",
    "fama_french_1993_smb": "小型株が有利という傾向は、論文発表後も続いた？",
    "fama_french_1993_hml": "割安株が有利という傾向は、論文発表後も続いた？",
    "fama_french_2015_rmw": "利益率の高い会社は、低い会社より上がりやすい？",
    "fama_french_2015_cma": "投資を抑える会社は、積極投資する会社より上がりやすい？",
}

METHOD_NOTES = {
    "Sullivan, Timmermann & White (1999)": "たくさんのルールを試すほど、偶然の当たりが増える問題を扱う研究。",
    "Harvey, Liu & Zhu (2016)": "多数の投資アイデアを試すとき、合格ラインを厳しくする考え方。",
    "Hansen (2005), A Test for Superior Predictive Ability": "多くの候補の中に、本当に優れた方法があるかを調べる研究。",
    "Bailey et al., Probability of Backtest Overfitting": "過去データで、たまたま良かった案を選んでしまう危険を扱う研究。",
    "Japan Exchange Group: Short Selling Restrictions": "日本株を実際に空売りするときのルールを確認する一次資料。",
}

REPOSITORY_SOURCES = (
    (
        "検証に使った論文とデータの一覧",
        "https://github.com/KAFKA2306/investor2/blob/main/docs/research/paper_factor_registry.json",
        "どの研究を、どのデータで確かめたかを確認できます。",
    ),
    (
        "モメンタムの検証結果",
        "https://github.com/KAFKA2306/investor2/blob/main/docs/research/post_publication_momentum_oos.json",
        "『最近上がった株は上がり続けるか』の計算結果です。",
    ),
    (
        "同じ検証を繰り返した結果",
        "https://github.com/KAFKA2306/investor2/blob/main/docs/research/2010s_paper_validation_repeated.json",
        "乱数を変えても結論が変わらないかを確認した記録です。",
    ),
    (
        "公開結果を組み立てるコード",
        "https://github.com/KAFKA2306/investor2/blob/main/scripts/build_public_research_manifest.py",
        "このページに出す情報を、内部データから自動生成するコードです。",
    ),
)

FORBIDDEN_PUBLIC_KEYS = {
    "external_claims",
    "locked_protocol",
    "interpretation",
    "repository_results",
    "gates",
    "scope_note",
    "original_verdict",
}


def load_internal_builder():
    spec = importlib.util.spec_from_file_location("internal_research_manifest_builder", INTERNAL_BUILDER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {INTERNAL_BUILDER}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def human_reason(record: dict[str, Any]) -> str:
    gates = record.get("gates", {})
    reasons: list[str] = []
    if gates.get("t_stat_ge_3") != "PASS":
        reasons.append("偶然ではないと言い切るには、統計的な強さが足りません")
    if gates.get("block_bootstrap_lower_gt_0") != "PASS":
        reasons.append("データの切り方を変えると、結果が安定しない可能性があります")
    if gates.get("late_period_mean_gt_0") != "PASS":
        reasons.append("検証期間の後半では、同じ効果が続いていません")
    if gates.get("after_25bps_monthly_haircut_gt_0") != "PASS":
        reasons.append("簡単な取引コストを差し引くと、利益が残りません")
    if gates.get("point_in_time_security_level_rebuild") != "PASS":
        reasons.append("当時の個別銘柄を、その時点で分かっていた情報だけでまだ再現していません")
    if gates.get("tradability_and_borrowability") != "PASS":
        reasons.append("その時点で本当に売買できたかを、まだ確認していません")
    if not reasons:
        return "公開している確認項目はすべて通過しています。"
    return "。".join(reasons) + "。"


def project_result(record: dict[str, Any]) -> dict[str, Any]:
    confirmed = record["dashboard_verdict"] == "CONFIRMED"
    return {
        "id": record["id"],
        "question": PUBLIC_QUESTIONS.get(record["id"], record["paper"]),
        "paper": record["paper"],
        "period": record["window"],
        "months": record["months"],
        "annualized_mean": record["annualized_mean"],
        "late_period_mean": record["late_period_mean"],
        "cost_25bps_annualized_mean": record["cost_25bps_annualized_mean"],
        "sharpe": record["sharpe"],
        "newey_west_t": record["newey_west_t"],
        "verdict": record["dashboard_verdict"],
        "verdict_label": (
            "投資に使える可能性を確認" if confirmed else "まだ投資に使えるとは確認できない"
        ),
        "why": human_reason(record),
    }


def build_public_manifest(internal: dict[str, Any]) -> dict[str, Any]:
    summary = internal["summary"]
    method_sources = [
        {
            "label": source["label"],
            "url": source["url"],
            "note": METHOD_NOTES.get(source["label"], "検証方法の根拠となる一次資料です。"),
            "kind": "検証方法の根拠",
        }
        for source in internal["primary_method_sources"]
    ]
    repository_sources = [
        {"label": label, "url": url, "note": note, "kind": "再現できる記録"}
        for label, url, note in REPOSITORY_SOURCES
    ]
    return {
        "schema_version": 1,
        "build": dict(internal["build"]),
        "summary": {
            "tested_hypotheses": summary["tested_hypotheses"],
            "confirmed": summary["confirmed"],
            "not_confirmed": summary["not_confirmed"],
            "latest_factor_data_end": summary["latest_factor_data_end"],
            "latest_momentum_data_end": summary["latest_momentum_data_end"],
        },
        "results": [project_result(record) for record in internal["repository_results"]],
        "repeat_check": {
            "study_count": internal["repeated_validation"]["study_count"],
            "repetitions": internal["repeated_validation"]["repetitions"],
            "same_conclusion_each_time": internal["repeated_validation"]["all_verdicts_stable"],
        },
        "sources": repository_sources + method_sources,
    }


def walk_keys(value: Any):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from walk_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_keys(child)


def validate_public_manifest(data: dict[str, Any], expected_revision: str | None = None) -> None:
    if data.get("schema_version") != 1:
        raise ValueError("unsupported public schema_version")
    keys = set(walk_keys(data))
    leaked = sorted(keys & FORBIDDEN_PUBLIC_KEYS)
    if leaked:
        raise ValueError(f"internal-only fields leaked into public manifest: {leaked}")

    results = data.get("results")
    summary = data.get("summary")
    if not isinstance(results, list) or not isinstance(summary, dict):
        raise ValueError("public results and summary are required")
    ids = [item.get("id") for item in results]
    if any(not isinstance(item_id, str) or not item_id for item_id in ids):
        raise ValueError("every public result requires an id")
    if len(ids) != len(set(ids)):
        raise ValueError("public result ids must be unique")
    for item in results:
        for field in ("question", "paper", "period", "verdict", "verdict_label", "why"):
            if not isinstance(item.get(field), str) or not item[field].strip():
                raise ValueError(f"public result {item['id']} missing {field}")
    confirmed = sum(item["verdict"] == "CONFIRMED" for item in results)
    not_confirmed = sum(item["verdict"] == "NOT_CONFIRMED" for item in results)
    if summary.get("tested_hypotheses") != len(results):
        raise ValueError("public tested_hypotheses does not match results")
    if summary.get("confirmed") != confirmed or summary.get("not_confirmed") != not_confirmed:
        raise ValueError("public verdict summary does not match results")

    sources = data.get("sources")
    if not isinstance(sources, list) or not sources:
        raise ValueError("public sources are required")
    for source in sources:
        if not all(isinstance(source.get(key), str) and source[key].strip() for key in ("label", "url", "note", "kind")):
            raise ValueError("every public source requires label, url, note, and kind")

    build = data.get("build", {})
    revision = build.get("code_sha")
    if not isinstance(revision, str) or not re.fullmatch(r"[0-9a-f]{40}|LOCAL_WORKTREE", revision):
        raise ValueError("public build.code_sha must be a commit SHA or LOCAL_WORKTREE")
    if expected_revision and revision != expected_revision:
        raise ValueError(f"public revision {revision} does not match expected {expected_revision}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-revision")
    args = parser.parse_args()

    builder = load_internal_builder()
    internal = builder.build_manifest()
    builder.validate_manifest(internal)
    public = build_public_manifest(internal)
    validate_public_manifest(public, expected_revision=args.expected_revision)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(public, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
