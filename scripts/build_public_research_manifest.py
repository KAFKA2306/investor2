#!/usr/bin/env python3
"""Project internal research evidence into small public-safe contracts."""

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
EMPIRICAL_2019_VERIFIER = ROOT / "scripts" / "verify_2019_arxiv_empirical.py"
EMPIRICAL_2019_REGISTRY = ROOT / "docs" / "research" / "2019_arxiv_finance_registry.json"
EMPIRICAL_VERDICTS = {"REPRODUCED", "FAILED", "BLOCKED"}

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
        "2019年 arXiv 論文の実証再現索引",
        "https://github.com/KAFKA2306/investor2/blob/main/docs/research/2019_arxiv_finance_registry.json",
        "2019年のpaper-specific runについて、方法契約と実証判定を分離して管理する正準索引です。",
    ),
    (
        "2019年論文の実証証拠チェック",
        "https://github.com/KAFKA2306/investor2/blob/main/scripts/verify_2019_arxiv_empirical.py",
        "run manifest・report・traceとSHA-256を検証し、BLOCKEDを成功や失敗と混同しないためのコードです。",
    ),
    (
        "2021年 arXiv 論文の再現索引",
        "https://github.com/KAFKA2306/investor2/blob/main/docs/research/2021_arxiv_finance_registry.json",
        "論文の一次URL、実装段階、再現用データの永続化状態を管理する正準索引です。",
    ),
    (
        "2021年論文の方法チェック",
        "https://github.com/KAFKA2306/investor2/blob/main/scripts/verify_2021_arxiv_methods.py",
        "論文から切り出した最小の方法契約を、決定論的に検証するコードです。",
    ),
    (
        "論文再現データの保存ルール",
        "https://github.com/KAFKA2306/investor2/blob/main/docs/specs/paper_reproduction_store.md",
        "GitHubの索引とHugging Faceの大容量artifactをどう分離するかを定めた契約です。",
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
    "paper_reproduction_2021",
    "canonical_storage",
    "materialized_artifacts",
    "method_observed",
    "gates",
    "scope_note",
    "original_verdict",
    "reproduction_verdict",
    "unreproduced_evidence",
}


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_internal_builder():
    return _load_module(INTERNAL_BUILDER, "internal_research_manifest_builder")


def load_2019_verifier():
    return _load_module(EMPIRICAL_2019_VERIFIER, "empirical_2019_verifier")


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


def paper_stage_label(paper: dict[str, Any]) -> str:
    empirical = paper["empirical_reproduction_state"]
    verdict = paper.get("empirical_verdict")
    if empirical == "EMPIRICALLY_RUN":
        if verdict == "REPRODUCED":
            return "実証再現を実行し、事前条件内で再現"
        if verdict == "FAILED":
            return "実証再現を実行したが、事前条件を満たさず"
        if verdict == "BLOCKED":
            return "実証再現protocolを実行したが、証拠gateで停止"
        raise ValueError(f"EMPIRICALLY_RUN paper lacks final verdict: {paper['id']}")
    if empirical != "NOT_RUN":
        raise ValueError(f"unknown empirical state: {paper['id']}")
    if paper["artifact_state"] == "MATERIALIZED":
        return "再現用データを保存済み・実証再現は未実施"
    if paper["method_contract_state"] == "PASS":
        return "方法の最小実装まで完了・実証再現は未実施"
    return "方法実装の確認が必要・実証再現は未実施"


def project_paper(paper: dict[str, Any]) -> dict[str, Any]:
    evidence = None
    if paper["empirical_reproduction_state"] == "EMPIRICALLY_RUN":
        evidence = {
            "path": paper["empirical_evidence_manifest"],
            "sha256": paper["empirical_evidence_manifest_sha256"],
        }
    return {
        "id": paper["id"],
        "arxiv_id": paper["arxiv_id"],
        "title": paper["title"],
        "authors": list(paper["authors"]),
        "first_submitted": paper["first_submitted"],
        "category": paper["primary_category"],
        "source_url": paper["source_url"],
        "claim": paper["paper_claim"],
        "implemented": paper["implementation_scope"],
        "method_state": paper["method_contract_state"],
        "artifact_state": paper["artifact_state"],
        "empirical_state": paper["empirical_reproduction_state"],
        "empirical_verdict": paper.get("empirical_verdict"),
        "empirical_evidence": evidence,
        "stage_label": paper_stage_label(paper),
        "missing_evidence": paper["unreproduced_evidence"],
    }


def build_public_manifest(internal: dict[str, Any]) -> dict[str, Any]:
    summary = internal["summary"]
    paper_internal = internal["paper_reproduction_2021"]
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
    paper_summary_keys = (
        "indexed",
        "method_contract_pass",
        "materialized",
        "empirically_run",
        "empirically_reproduced",
        "empirically_failed",
        "empirically_blocked",
        "empirically_not_run",
    )
    return {
        "schema_version": 2,
        "build": dict(internal["build"]),
        "summary": {
            "tested_hypotheses": summary["tested_hypotheses"],
            "confirmed": summary["confirmed"],
            "not_confirmed": summary["not_confirmed"],
            "latest_factor_data_end": summary["latest_factor_data_end"],
            "latest_momentum_data_end": summary["latest_momentum_data_end"],
            **{f"papers_2021_{key}": summary[f"papers_2021_{key}"] for key in paper_summary_keys},
        },
        "results": [project_result(record) for record in internal["repository_results"]],
        "paper_reproduction": {
            "summary": dict(paper_internal["summary"]),
            "papers": [project_paper(paper) for paper in paper_internal["papers"]],
        },
        "repeat_check": {
            "study_count": internal["repeated_validation"]["study_count"],
            "repetitions": internal["repeated_validation"]["repetitions"],
            "same_conclusion_each_time": internal["repeated_validation"]["all_verdicts_stable"],
        },
        "sources": repository_sources + method_sources,
    }


def _safe_repo_path(value: str) -> Path:
    path = (ROOT / value).resolve()
    path.relative_to(ROOT.resolve())
    return path


def project_2019_paper(paper: dict[str, Any]) -> dict[str, Any]:
    manifest_path = _safe_repo_path(paper["evidence_manifest"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    report_path = _safe_repo_path(manifest["artifacts"]["report"]["path"])
    report = json.loads(report_path.read_text(encoding="utf-8"))
    return {
        "id": paper["id"],
        "arxiv_id": paper["arxiv_id"],
        "title": paper["title"],
        "source_url": paper["source_url"],
        "source_pdf_url": paper["source_pdf_url"],
        "source_version": paper["source_version"],
        "source_pdf_sha256": report["source_pdf"]["sha256"],
        "method_state": paper["method_contract_state"],
        "data_state": paper["data_contract_state"],
        "split_state": paper["split_contract_state"],
        "empirical_state": paper["empirical_reproduction_state"],
        "empirical_verdict": paper["empirical_verdict"],
        "stage_reached": paper["stage_reached"],
        "training_attempted": report["training_attempted"],
        "training_executed": report["training_executed"],
        "evaluation_executed": report["evaluation_executed"],
        "paper_target": paper["paper_target"],
        "observed_metrics": paper["observed_metrics"],
        "reason_codes": list(paper["reason_codes"]),
        "evidence": {
            "manifest_path": paper["evidence_manifest"],
            "manifest_sha256": paper["evidence_manifest_sha256"],
        },
    }


def build_public_2019_manifest(*, code_sha: str) -> dict[str, Any]:
    verifier = load_2019_verifier()
    internal = verifier.build_report(EMPIRICAL_2019_REGISTRY)
    papers = [project_2019_paper(paper) for paper in internal["papers"]]
    summary = {
        **internal["summary"],
        "method_contract_pass": sum(paper["method_state"] == "PASS" for paper in papers),
    }
    return {
        "schema_version": 1,
        "build": {"code_sha": code_sha},
        "summary": summary,
        "papers": papers,
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
    if data.get("schema_version") != 2:
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

    paper_queue = data.get("paper_reproduction")
    if not isinstance(paper_queue, dict):
        raise ValueError("public paper_reproduction is required")
    papers = paper_queue.get("papers")
    paper_summary = paper_queue.get("summary")
    if not isinstance(papers, list) or not isinstance(paper_summary, dict):
        raise ValueError("public paper records and summary are required")
    paper_ids = [paper.get("id") for paper in papers]
    if any(not isinstance(paper_id, str) or not paper_id for paper_id in paper_ids) or len(paper_ids) != len(set(paper_ids)):
        raise ValueError("public paper ids must be unique non-empty strings")
    expected_paper = {
        "indexed": len(papers),
        "method_contract_pass": sum(paper.get("method_state") == "PASS" for paper in papers),
        "materialized": sum(paper.get("artifact_state") == "MATERIALIZED" for paper in papers),
        "empirically_run": sum(paper.get("empirical_state") == "EMPIRICALLY_RUN" for paper in papers),
        "empirically_reproduced": sum(paper.get("empirical_verdict") == "REPRODUCED" for paper in papers),
        "empirically_failed": sum(paper.get("empirical_verdict") == "FAILED" for paper in papers),
        "empirically_blocked": sum(paper.get("empirical_verdict") == "BLOCKED" for paper in papers),
        "empirically_not_run": sum(paper.get("empirical_state") == "NOT_RUN" for paper in papers),
    }
    if paper_summary != expected_paper:
        raise ValueError("public paper summary does not match records")
    for key, value in expected_paper.items():
        if summary.get(f"papers_2021_{key}") != value:
            raise ValueError(f"public papers_2021_{key} does not match paper records")
    for paper in papers:
        for field in ("arxiv_id", "title", "first_submitted", "category", "source_url", "claim", "implemented", "method_state", "artifact_state", "empirical_state", "stage_label", "missing_evidence"):
            if not isinstance(paper.get(field), str) or not paper[field].strip():
                raise ValueError(f"public paper {paper['id']} missing {field}")
        state = paper["empirical_state"]
        verdict = paper.get("empirical_verdict")
        evidence = paper.get("empirical_evidence")
        if state == "NOT_RUN":
            if verdict is not None or evidence is not None:
                raise ValueError(f"NOT_RUN public paper carries empirical result/evidence: {paper['id']}")
            if "実証再現は未実施" not in paper["stage_label"]:
                raise ValueError(f"unrun public paper is not clearly labeled: {paper['id']}")
        elif state == "EMPIRICALLY_RUN":
            if verdict not in EMPIRICAL_VERDICTS:
                raise ValueError(f"empirically run public paper lacks verdict: {paper['id']}")
            if not isinstance(evidence, dict):
                raise ValueError(f"empirically run public paper lacks evidence ref: {paper['id']}")
            if not isinstance(evidence.get("path"), str) or not evidence["path"].strip():
                raise ValueError(f"empirical evidence path missing: {paper['id']}")
            if not isinstance(evidence.get("sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", evidence["sha256"]):
                raise ValueError(f"empirical evidence SHA-256 missing: {paper['id']}")
        else:
            raise ValueError(f"unknown public empirical state: {paper['id']}")

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


def validate_public_2019_manifest(data: dict[str, Any], expected_revision: str | None = None) -> None:
    if data.get("schema_version") != 1:
        raise ValueError("unsupported 2019 public schema_version")
    build = data.get("build", {})
    revision = build.get("code_sha")
    if not isinstance(revision, str) or not re.fullmatch(r"[0-9a-f]{40}|LOCAL_WORKTREE", revision):
        raise ValueError("2019 public build.code_sha must be a commit SHA or LOCAL_WORKTREE")
    if expected_revision and revision != expected_revision:
        raise ValueError(f"2019 public revision {revision} does not match expected {expected_revision}")
    papers = data.get("papers")
    summary = data.get("summary")
    if not isinstance(papers, list) or not isinstance(summary, dict) or not papers:
        raise ValueError("2019 public paper records and summary are required")
    if summary.get("indexed") != len(papers):
        raise ValueError("2019 indexed count mismatch")
    expected_run = sum(paper.get("empirical_state") == "EMPIRICALLY_RUN" for paper in papers)
    expected_blocked = sum(paper.get("empirical_verdict") == "BLOCKED" for paper in papers)
    if summary.get("empirically_run") != expected_run or summary.get("blocked") != expected_blocked:
        raise ValueError("2019 empirical summary mismatch")
    if summary.get("method_contract_pass") != sum(paper.get("method_state") == "PASS" for paper in papers):
        raise ValueError("2019 method summary mismatch")
    for paper in papers:
        for field in ("id", "arxiv_id", "title", "source_url", "source_pdf_url", "source_version", "source_pdf_sha256", "method_state", "data_state", "split_state", "empirical_state", "empirical_verdict", "stage_reached"):
            if not isinstance(paper.get(field), str) or not paper[field].strip():
                raise ValueError(f"2019 public paper missing {field}: {paper.get('id')}")
        if not re.fullmatch(r"[0-9a-f]{64}", paper["source_pdf_sha256"]):
            raise ValueError(f"2019 source PDF SHA invalid: {paper['id']}")
        if paper["empirical_state"] != "EMPIRICALLY_RUN" or paper["empirical_verdict"] not in EMPIRICAL_VERDICTS:
            raise ValueError(f"2019 terminal paper lacks empirical verdict: {paper['id']}")
        if paper["empirical_verdict"] == "BLOCKED":
            if paper["training_executed"] or paper["evaluation_executed"] or paper["observed_metrics"] is not None:
                raise ValueError(f"BLOCKED paper cannot claim model metrics: {paper['id']}")
        evidence = paper.get("evidence")
        if not isinstance(evidence, dict) or not re.fullmatch(r"[0-9a-f]{64}", str(evidence.get("manifest_sha256", ""))):
            raise ValueError(f"2019 evidence SHA missing: {paper['id']}")


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

    public_2019 = build_public_2019_manifest(code_sha=public["build"]["code_sha"])
    validate_public_2019_manifest(public_2019, expected_revision=args.expected_revision)
    output_2019 = args.output.parent / "research_2019_public_manifest.json"
    output_2019.write_text(
        json.dumps(public_2019, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
