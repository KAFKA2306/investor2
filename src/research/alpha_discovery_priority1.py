from __future__ import annotations

import re
import time
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np

from src.research.alphacrafter_frontier import (
    as_dict,
    daily_rank_ic,
    evaluate_weights,
    make_weight_path,
    orient_factor_on_train,
    semantic_group,
)

ARMS = ("baseline", "ast_originality", "semantic_schema")


@dataclass(frozen=True)
class CandidateSpec:
    candidate_id: str
    operation: str
    left: str
    right: str | None = None
    sign: int = 1

    def expression(self) -> str:
        prefix = "-" if self.sign < 0 else ""
        if self.operation == "single":
            return f"{prefix}{self.left}"
        if self.right is None:
            raise ValueError(f"{self.operation} requires a right operand")
        if self.operation == "blend":
            return f"{prefix}0.5*({self.left}+{self.right})"
        if self.operation == "spread":
            return f"{prefix}({self.left}-{self.right})"
        raise ValueError(f"unsupported operation: {self.operation}")


def _horizon(feature_name: str) -> int:
    match = re.search(r"_(\d+)$", feature_name)
    return int(match.group(1)) if match else 1


def _semantic_atom(feature_name: str) -> str:
    return f"{semantic_group(feature_name)}@{_horizon(feature_name)}"


def ast_fingerprint(candidate: CandidateSpec) -> str:
    if candidate.operation == "single":
        return f"single:{candidate.left}"
    if candidate.right is None:
        raise ValueError(f"{candidate.operation} requires a right operand")
    operands = sorted((candidate.left, candidate.right))
    # Candidate sign and operand reversal are intentionally ignored. Sign is
    # trained on the frozen train split, so these forms are equivalent for this
    # ablation and should consume one structural identity.
    return f"{candidate.operation}:{operands[0]}:{operands[1]}"


def semantic_signature(candidate: CandidateSpec) -> str:
    if candidate.operation == "single":
        return f"single:{_semantic_atom(candidate.left)}"
    if candidate.right is None:
        raise ValueError(f"{candidate.operation} requires a right operand")
    operands = sorted(
        (_semantic_atom(candidate.left), _semantic_atom(candidate.right))
    )
    return f"{candidate.operation}:{operands[0]}:{operands[1]}"


def build_candidate_pool(feature_names: list[str]) -> list[CandidateSpec]:
    if len(feature_names) < 2:
        raise ValueError("at least two source features are required")
    pool: list[CandidateSpec] = []
    for index, name in enumerate(feature_names):
        pool.append(CandidateSpec(f"single-pos-{index:02d}", "single", name, sign=1))
    for index, name in enumerate(feature_names):
        pool.append(CandidateSpec(f"single-neg-{index:02d}", "single", name, sign=-1))
    pair_index = 0
    for left_index, left in enumerate(feature_names):
        for right in feature_names[left_index + 1 :]:
            pool.extend(
                [
                    CandidateSpec(
                        f"pair-{pair_index:03d}-blend-fwd", "blend", left, right
                    ),
                    CandidateSpec(
                        f"pair-{pair_index:03d}-blend-rev", "blend", right, left
                    ),
                    CandidateSpec(
                        f"pair-{pair_index:03d}-spread-fwd", "spread", left, right
                    ),
                    CandidateSpec(
                        f"pair-{pair_index:03d}-spread-rev", "spread", right, left
                    ),
                ]
            )
            pair_index += 1
    return pool


def candidate_dict(candidate: CandidateSpec) -> dict[str, Any]:
    payload: dict[str, Any] = asdict(candidate)
    payload["expression"] = candidate.expression()
    payload["ast_fingerprint"] = ast_fingerprint(candidate)
    payload["semantic_signature"] = semantic_signature(candidate)
    return payload


def select_candidates(
    pool: list[CandidateSpec], *, arm: str, evaluator_budget: int
) -> tuple[list[CandidateSpec], list[dict[str, Any]]]:
    if arm not in ARMS:
        raise ValueError(f"unknown arm: {arm}")
    if evaluator_budget < 1:
        raise ValueError("evaluator_budget must be positive")
    selected: list[CandidateSpec] = []
    scan: list[dict[str, Any]] = []
    seen_ast: set[str] = set()
    seen_semantic: set[str] = set()
    for candidate in pool:
        ast_key = ast_fingerprint(candidate)
        semantic_key = semantic_signature(candidate)
        reject_reason: str | None = None
        if arm == "ast_originality" and ast_key in seen_ast:
            reject_reason = "duplicate_ast"
        elif arm == "semantic_schema" and semantic_key in seen_semantic:
            reject_reason = "duplicate_semantic_schema"

        accepted = reject_reason is None
        row = candidate_dict(candidate)
        row.update(
            {
                "scan_index": len(scan),
                "accepted_for_validation": accepted,
                "reject_reason": reject_reason,
            }
        )
        scan.append(row)
        if not accepted:
            continue

        selected.append(candidate)
        seen_ast.add(ast_key)
        seen_semantic.add(semantic_key)
        if len(selected) == evaluator_budget:
            break

    if len(selected) != evaluator_budget:
        raise RuntimeError(
            f"candidate pool exhausted for {arm}: selected {len(selected)} of required {evaluator_budget}"
        )
    return selected, scan


def materialize_candidate(
    candidate: CandidateSpec, features: dict[str, np.ndarray]
) -> np.ndarray:
    if candidate.left not in features:
        raise KeyError(candidate.left)
    left = np.asarray(features[candidate.left], dtype=np.float64)
    if candidate.operation == "single":
        return float(candidate.sign) * left
    if candidate.right is None or candidate.right not in features:
        raise KeyError(candidate.right)
    right = np.asarray(features[candidate.right], dtype=np.float64)
    if left.shape != right.shape:
        raise ValueError("candidate operands must have the same shape")
    if candidate.operation == "blend":
        value = 0.5 * (left + right)
    elif candidate.operation == "spread":
        value = left - right
    else:
        raise ValueError(f"unsupported operation: {candidate.operation}")
    return float(candidate.sign) * value


def _mean_rank_ic(
    factor: np.ndarray, returns: np.ndarray, start: int, end: int
) -> float:
    series = daily_rank_ic(factor, returns, 1)[start:end]
    observed = series[np.isfinite(series)]
    return float(observed.mean()) if observed.size else 0.0


def _duplicates(values: list[str]) -> int:
    return len(values) - len(set(values))


def evaluate_arm(
    *,
    arm: str,
    pool: list[CandidateSpec],
    features: dict[str, np.ndarray],
    returns: np.ndarray,
    benchmark: np.ndarray,
    train: tuple[int, int],
    validation: tuple[int, int],
    oos: tuple[int, int],
    evaluator_budget: int,
    finalists: int,
    n_long: int,
    n_short: int,
    beta: float,
    gamma: float,
    transaction_cost_bps: float,
    borrow_fee_bps: float,
) -> dict[str, Any]:
    started = time.perf_counter()
    selected, scan = select_candidates(
        pool, arm=arm, evaluator_budget=evaluator_budget
    )
    if finalists < 1 or finalists > evaluator_budget:
        raise ValueError("finalists must be between 1 and evaluator_budget")

    train_start, train_end = train
    validation_start, validation_end = validation
    oos_start, oos_end = oos
    validation_rows: list[dict[str, Any]] = []
    oriented_by_id: dict[str, np.ndarray] = {}
    for candidate in selected:
        raw = materialize_candidate(candidate, features)
        oriented, direction = orient_factor_on_train(
            raw, returns, train_start, train_end
        )
        oriented_by_id[candidate.candidate_id] = oriented
        row = candidate_dict(candidate)
        row.update(
            {
                "train_orientation": int(direction),
                "validation_mean_rank_ic": _mean_rank_ic(
                    oriented, returns, validation_start, validation_end
                ),
            }
        )
        validation_rows.append(row)

    ranked = sorted(
        validation_rows,
        key=lambda row: (
            -float(row["validation_mean_rank_ic"]),
            str(row["candidate_id"]),
        ),
    )
    finalist_rows = ranked[:finalists]
    oos_rows: list[dict[str, Any]] = []
    for finalist in finalist_rows:
        candidate_id = str(finalist["candidate_id"])
        factor = oriented_by_id[candidate_id]
        weights = make_weight_path(
            factor,
            n_long=n_long,
            n_short=n_short,
            beta=beta,
            gamma=gamma,
        )
        portfolio_metrics, _ = evaluate_weights(
            weights,
            returns,
            benchmark,
            oos_start,
            oos_end,
            transaction_cost_bps_per_side=transaction_cost_bps,
            borrow_fee_bps_per_year=borrow_fee_bps,
        )
        oos_rank_ic = _mean_rank_ic(factor, returns, oos_start, oos_end)
        survivor = bool(
            oos_rank_ic > 0.0
            and portfolio_metrics.cumulative_return > 0.0
            and portfolio_metrics.annualized_sharpe > 0.0
        )
        row = dict(finalist)
        row.update(
            {
                "oos_mean_rank_ic": oos_rank_ic,
                "oos_portfolio": as_dict(portfolio_metrics),
                "survivor": survivor,
            }
        )
        oos_rows.append(row)

    survivor_ast = {
        str(row["ast_fingerprint"])
        for row in oos_rows
        if bool(row["survivor"])
    }
    unique_survivors = len(survivor_ast)
    evaluated_ast = [ast_fingerprint(candidate) for candidate in selected]
    evaluated_semantic = [semantic_signature(candidate) for candidate in selected]
    rejected = sum(
        1 for row in scan if not bool(row["accepted_for_validation"])
    )
    finalist_sharpes = [
        float(row["oos_portfolio"]["annualized_sharpe"]) for row in oos_rows
    ]
    elapsed = time.perf_counter() - started

    return {
        "arm": arm,
        "validation_evaluator_calls": len(selected),
        "scanned_candidates": len(scan),
        "prefilter_rejections": rejected,
        "prefilter_rejection_rate": rejected / len(scan) if scan else 0.0,
        "unique_structural_candidates_evaluated": len(set(evaluated_ast)),
        "structural_duplicate_evaluations": _duplicates(evaluated_ast),
        "unique_semantic_schemas_evaluated": len(set(evaluated_semantic)),
        "semantic_duplicate_evaluations": _duplicates(evaluated_semantic),
        "finalist_count": len(oos_rows),
        "unique_oos_survivors": unique_survivors,
        "survivors_per_validation_call": unique_survivors / len(selected),
        "validation_calls_per_unique_survivor": (
            len(selected) / unique_survivors if unique_survivors else None
        ),
        "median_finalist_oos_sharpe": (
            float(np.median(finalist_sharpes)) if finalist_sharpes else 0.0
        ),
        "best_finalist_oos_sharpe": (
            max(finalist_sharpes) if finalist_sharpes else 0.0
        ),
        "wall_clock_seconds": elapsed,
        "scan": scan,
        "validation": validation_rows,
        "oos_finalists": oos_rows,
    }


def run_ablation(
    *,
    feature_names: list[str],
    feature_tensor: np.ndarray,
    returns: np.ndarray,
    benchmark: np.ndarray,
    train: tuple[int, int],
    validation: tuple[int, int],
    oos: tuple[int, int],
    evaluator_budget: int = 24,
    finalists: int = 8,
    n_long: int = 32,
    n_short: int = 32,
    beta: float = 1.0,
    gamma: float = 0.0,
    transaction_cost_bps: float = 15.0,
    borrow_fee_bps: float = 30.0,
) -> dict[str, Any]:
    values = np.asarray(feature_tensor, dtype=np.float64)
    ret = np.asarray(returns, dtype=np.float64)
    bench = np.asarray(benchmark, dtype=np.float64)
    if values.ndim != 3:
        raise ValueError("feature_tensor must have shape [T,N,F]")
    if values.shape[:2] != ret.shape:
        raise ValueError("feature_tensor and returns must align on [T,N]")
    if values.shape[2] != len(feature_names):
        raise ValueError("feature_names do not match feature_tensor")
    if bench.shape != (values.shape[0],):
        raise ValueError("benchmark must have shape [T]")
    if n_long + n_short > values.shape[1]:
        raise ValueError("portfolio long/short counts exceed asset count")

    feature_map = {
        name: values[:, :, index] for index, name in enumerate(feature_names)
    }
    pool = build_candidate_pool(feature_names)
    arms = {
        arm: evaluate_arm(
            arm=arm,
            pool=pool,
            features=feature_map,
            returns=ret,
            benchmark=bench,
            train=train,
            validation=validation,
            oos=oos,
            evaluator_budget=evaluator_budget,
            finalists=finalists,
            n_long=n_long,
            n_short=n_short,
            beta=beta,
            gamma=gamma,
            transaction_cost_bps=transaction_cost_bps,
            borrow_fee_bps=borrow_fee_bps,
        )
        for arm in ARMS
    }
    baseline = int(arms["baseline"]["unique_oos_survivors"])
    verdicts: dict[str, str] = {"baseline": "REFERENCE"}
    for arm in ARMS[1:]:
        value = int(arms[arm]["unique_oos_survivors"])
        verdicts[arm] = (
            "IMPROVES_PRIMARY"
            if value > baseline
            else "WORSE_PRIMARY"
            if value < baseline
            else "TIE_PRIMARY"
        )
    best_value = max(
        int(payload["unique_oos_survivors"]) for payload in arms.values()
    )
    winners = [
        arm
        for arm, payload in arms.items()
        if int(payload["unique_oos_survivors"]) == best_value
    ]
    return {
        "candidate_pool_size": len(pool),
        "candidate_pool_preview": [
            candidate_dict(candidate) for candidate in pool[:20]
        ],
        "arms": arms,
        "mechanism_verdict_vs_baseline": verdicts,
        "winner_by_primary": winners,
        "best_primary_value": best_value,
    }
