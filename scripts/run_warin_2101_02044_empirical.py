#!/usr/bin/env python3
"""Run an independent empirical reproduction of Warin (arXiv:2101.02044v4).

Scope is deliberately narrow and locked before execution: Section 3.2, Table 1,
point-by-point direct formulation (11), beta=2.0, dimension four.  The paper's
synthetic Black-Scholes inputs, network shape, optimizer schedule, 15,000
iterations, batch size 300, N=104 and 100,000-path evaluation are used.

The author implementation, TensorFlow version and random seed are not published.
This script therefore records those limitations while performing an independent
implementation.  A verdict is based only on the predeclared metric tolerances in
the protocol JSON; it never upgrades a method-contract check into empirical
reproduction.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import sys
import urllib.request
from pathlib import Path
from typing import Any

import numpy as np
import tensorflow as tf

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROTOCOL = ROOT / "docs/research/protocols/warin_2101_02044_v4_beta2.json"
SCHEMA_VERSION = "investor2.warin-2101.02044-empirical.v1"


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode(
        "utf-8"
    )


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def download_sha256(url: str) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "KAFKA2306-investor2-warin-reproduction/1.0"},
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        payload = response.read()
        content_type = response.headers.get("Content-Type")
        final_url = response.geturl()
    if not payload.startswith(b"%PDF"):
        raise ValueError("arXiv source response is not a PDF")
    return {
        "requested_url": url,
        "final_url": final_url,
        "sha256": sha256_bytes(payload),
        "size_bytes": len(payload),
        "content_type": content_type,
        "stored_in_repository": False,
        "storage_reason": "arXiv license grants distribution rights to arXiv; third-party redistribution permission was not established",
    }


def analytical_moments(protocol: dict[str, Any]) -> dict[str, float]:
    model = protocol["market_model"]
    beta = float(protocol["reproduction_scope"]["beta"])
    mu = np.asarray(model["mu"], dtype=np.float64)
    vol = np.asarray(model["sigma_diagonal"], dtype=np.float64)
    rho = np.asarray(model["correlation"], dtype=np.float64)
    covariance = np.diag(vol) @ rho @ np.diag(vol)
    r_value = float(mu @ np.linalg.solve(covariance, mu))
    growth = math.exp(r_value * float(model["horizon_years"])) - 1.0
    x0 = float(model["initial_wealth"])
    return {
        "R": r_value,
        "mean": x0 + growth / (2.0 * beta),
        "variance": growth / (4.0 * beta * beta),
    }


def build_model(width: int, output_dimension: int) -> tf.keras.Model:
    return tf.keras.Sequential(
        [
            tf.keras.layers.Input(shape=(2,), dtype=tf.float32),
            tf.keras.layers.Dense(width, activation="tanh"),
            tf.keras.layers.Dense(width, activation="tanh"),
            tf.keras.layers.Dense(width, activation="tanh"),
            tf.keras.layers.Dense(output_dimension, activation=None),
        ],
        name="warin_point_by_point_direct",
    )


def model_state(model: tf.keras.Model) -> dict[str, Any]:
    layers: list[dict[str, Any]] = []
    for layer in model.layers:
        weights = layer.get_weights()
        if not weights:
            continue
        layers.append(
            {
                "name": layer.name,
                "class": layer.__class__.__name__,
                "arrays": [array.tolist() for array in weights],
                "shapes": [list(array.shape) for array in weights],
            }
        )
    return {"format": "canonical-json-keras-weights-v1", "layers": layers}


def prepare_tensors(protocol: dict[str, Any]) -> dict[str, tf.Tensor | int | float]:
    market = protocol["market_model"]
    mu = tf.constant(market["mu"], dtype=tf.float32)
    vol = tf.constant(market["sigma_diagonal"], dtype=tf.float32)
    rho = tf.constant(market["correlation"], dtype=tf.float32)
    chol = tf.linalg.cholesky(rho)
    n_steps = int(market["rebalancing_steps"])
    horizon = float(market["horizon_years"])
    dt = horizon / n_steps
    return {
        "mu": mu,
        "vol": vol,
        "chol": chol,
        "n_steps": n_steps,
        "dt": dt,
        "sqrt_dt": math.sqrt(dt),
        "initial_wealth": float(market["initial_wealth"]),
    }


def run(protocol: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    lock = protocol["implementation_lock"]
    network = protocol["network"]
    evaluation = protocol["evaluation"]
    scope = protocol["reproduction_scope"]
    target = scope["target"]
    tolerance = scope["predeclared_comparison_tolerance"]
    seed = int(lock["seed"])
    iterations = int(network["gradient_iterations"])
    batch_size = int(network["batch_size"])
    beta = float(scope["beta"])
    eval_count = int(evaluation["simulation_count"])

    if tf.__version__ != str(lock["tensorflow"]):
        raise ValueError(f"TensorFlow version {tf.__version__} != locked {lock['tensorflow']}")
    if iterations != 15000 or batch_size != 300 or eval_count != 100000:
        raise ValueError("canonical Warin run must retain the paper's documented iteration/batch/evaluation counts")

    os.environ.setdefault("TF_DETERMINISTIC_OPS", "1")
    tf.keras.utils.set_random_seed(seed)
    try:
        tf.config.experimental.enable_op_determinism()
    except Exception:
        pass
    tf.config.threading.set_inter_op_parallelism_threads(0)
    tf.config.threading.set_intra_op_parallelism_threads(0)

    tensors = prepare_tensors(protocol)
    mu = tensors["mu"]
    vol = tensors["vol"]
    chol = tensors["chol"]
    n_steps = int(tensors["n_steps"])
    dt = float(tensors["dt"])
    sqrt_dt = float(tensors["sqrt_dt"])
    initial_wealth = float(tensors["initial_wealth"])
    dimension = len(protocol["market_model"]["mu"])

    model = build_model(int(network["hidden_width"]), dimension)
    # Materialize variables before optimizer creation and state hashing.
    model(tf.zeros((1, 2), dtype=tf.float32), training=False)
    optimizer = tf.keras.optimizers.Adam(learning_rate=float(network["learning_rate_initial"]))

    seed0 = tf.constant(seed, dtype=tf.int32)
    n_steps_t = tf.constant(n_steps, dtype=tf.int32)
    dt_t = tf.constant(dt, dtype=tf.float32)
    sqrt_dt_t = tf.constant(sqrt_dt, dtype=tf.float32)
    drift = (mu - 0.5 * tf.square(vol)) * dt_t

    @tf.function(reduce_retracing=True)
    def terminal_wealth(training_step: tf.Tensor, sample_count: tf.Tensor, training: bool) -> tf.Tensor:
        wealth = tf.fill([sample_count], tf.constant(initial_wealth, dtype=tf.float32))
        i0 = tf.constant(0, dtype=tf.int32)

        def cond(i: tf.Tensor, current: tf.Tensor) -> tf.Tensor:
            del current
            return i < n_steps_t

        def body(i: tf.Tensor, current: tf.Tensor) -> tuple[tf.Tensor, tf.Tensor]:
            t_value = tf.cast(i, tf.float32) / tf.cast(n_steps_t, tf.float32)
            inputs = tf.stack([tf.fill([sample_count], t_value), current], axis=1)
            weights = model(inputs, training=training)
            stateless_seed = tf.stack(
                [seed0 + training_step * tf.constant(7919, tf.int32), i + training_step * n_steps_t]
            )
            z = tf.random.stateless_normal([sample_count, dimension], seed=stateless_seed, dtype=tf.float32)
            dw = tf.matmul(z, chol, transpose_b=True) * sqrt_dt_t
            simple_returns = tf.exp(drift + vol * dw) - 1.0
            next_wealth = current * (1.0 + tf.reduce_sum(weights * simple_returns, axis=1))
            return i + 1, next_wealth

        _, wealth = tf.while_loop(
            cond,
            body,
            (i0, wealth),
            parallel_iterations=1,
            maximum_iterations=n_steps,
        )
        return wealth

    @tf.function(reduce_retracing=True)
    def train_step(step: tf.Tensor) -> tuple[tf.Tensor, tf.Tensor, tf.Tensor]:
        with tf.GradientTape() as tape:
            wealth = terminal_wealth(step, tf.constant(batch_size, tf.int32), True)
            mean = tf.reduce_mean(wealth)
            variance = tf.reduce_mean(tf.square(wealth - mean))
            loss = -mean + tf.constant(beta, tf.float32) * variance
        gradients = tape.gradient(loss, model.trainable_variables)
        if any(gradient is None for gradient in gradients):
            raise RuntimeError("missing gradient in Warin training step")
        optimizer.apply_gradients(zip(gradients, model.trainable_variables))
        return loss, mean, variance

    trace: list[dict[str, Any]] = []
    initial_lr = float(network["learning_rate_initial"])
    final_lr = float(network["learning_rate_final"])
    for iteration in range(iterations):
        fraction = iteration / max(1, iterations - 1)
        learning_rate = initial_lr + (final_lr - initial_lr) * fraction
        optimizer.learning_rate.assign(learning_rate)
        loss, mean, variance = train_step(tf.constant(iteration + 1, tf.int32))
        if not all(math.isfinite(float(value.numpy())) for value in (loss, mean, variance)):
            raise FloatingPointError(f"non-finite training metric at iteration {iteration + 1}")
        if iteration == 0 or (iteration + 1) % 100 == 0 or iteration + 1 == iterations:
            trace.append(
                {
                    "iteration": iteration + 1,
                    "learning_rate": learning_rate,
                    "loss": float(loss.numpy()),
                    "batch_mean": float(mean.numpy()),
                    "batch_variance": float(variance.numpy()),
                }
            )

    # Independent evaluation stream: use step identifiers disjoint from training.
    eval_chunk = 5000
    total_sum = 0.0
    total_sumsq = 0.0
    total_n = 0
    for chunk_index, start in enumerate(range(0, eval_count, eval_chunk)):
        count = min(eval_chunk, eval_count - start)
        wealth = terminal_wealth(
            tf.constant(1_000_000 + chunk_index, tf.int32),
            tf.constant(count, tf.int32),
            False,
        ).numpy().astype(np.float64, copy=False)
        if not np.isfinite(wealth).all():
            raise FloatingPointError("non-finite terminal wealth in evaluation")
        total_sum += float(wealth.sum(dtype=np.float64))
        total_sumsq += float(np.square(wealth).sum(dtype=np.float64))
        total_n += count
    empirical_mean = total_sum / total_n
    empirical_variance = max(0.0, total_sumsq / total_n - empirical_mean * empirical_mean)

    analytic = analytical_moments(protocol)
    analytic_compare = {
        "mean_abs_error_vs_paper": abs(analytic["mean"] - float(target["analytical_mean"])),
        "variance_abs_error_vs_paper": abs(analytic["variance"] - float(target["analytical_variance"])),
    }
    analytic_compare["within_tolerance"] = (
        analytic_compare["mean_abs_error_vs_paper"] <= float(tolerance["analytical_mean_absolute"])
        and analytic_compare["variance_abs_error_vs_paper"] <= float(tolerance["analytical_variance_absolute"])
    )
    neural_compare = {
        "mean_abs_error_vs_paper": abs(empirical_mean - float(target["paper_neural_mean"])),
        "variance_abs_error_vs_paper": abs(empirical_variance - float(target["paper_neural_variance"])),
    }
    neural_compare["within_tolerance"] = (
        neural_compare["mean_abs_error_vs_paper"] <= float(tolerance["neural_mean_absolute"])
        and neural_compare["variance_abs_error_vs_paper"] <= float(tolerance["neural_variance_absolute"])
    )

    if not analytic_compare["within_tolerance"]:
        verdict = "BLOCKED"
        verdict_reason = "paper parameter interpretation failed the analytical Table 1 sanity check"
    elif neural_compare["within_tolerance"]:
        verdict = "REPRODUCED"
        verdict_reason = "independent full-count training/evaluation matched the predeclared Table 1 beta=2.0 tolerances"
    else:
        verdict = "FAILED"
        verdict_reason = "independent full-count training/evaluation missed one or more predeclared Table 1 beta=2.0 tolerances"

    output_dir.mkdir(parents=True, exist_ok=True)
    trace_payload = {"schema_version": 1, "trace": trace}
    model_payload = model_state(model)
    trace_bytes = canonical_bytes(trace_payload)
    model_bytes = canonical_bytes(model_payload)
    trace_path = output_dir / "training_trace.json"
    model_path = output_dir / "model_state.json"
    trace_path.write_bytes(trace_bytes)
    model_path.write_bytes(model_bytes)

    protocol_path = Path(protocol["_protocol_path"])
    source_pdf = download_sha256(protocol["paper"]["pdf_url"])
    report = {
        "schema_version": SCHEMA_VERSION,
        "paper_id": "warin_2101_02044",
        "arxiv_id": "2101.02044",
        "paper_version": protocol["paper"]["selected_version"],
        "empirical_reproduction_state": "EMPIRICALLY_RUN",
        "empirical_verdict": verdict,
        "verdict_reason": verdict_reason,
        "scope": scope,
        "protocol": {
            "path": str(protocol_path.relative_to(ROOT)),
            "sha256": sha256_file(protocol_path),
        },
        "source_pdf": source_pdf,
        "runtime": {
            "python": platform.python_version(),
            "tensorflow": tf.__version__,
            "numpy": np.__version__,
            "platform": platform.platform(),
            "machine": platform.machine(),
            "device_policy": lock["device"],
            "seed": seed,
            "deterministic_ops_requested": True,
        },
        "training": {
            "gradient_iterations": iterations,
            "batch_size": batch_size,
            "optimizer": network["optimizer"],
            "learning_rate_initial": initial_lr,
            "learning_rate_final": final_lr,
            "trace_points": len(trace),
            "trace_sha256": sha256_bytes(trace_bytes),
            "model_state_sha256": sha256_bytes(model_bytes),
        },
        "evaluation": {
            "simulation_count": total_n,
            "terminal_wealth_mean": empirical_mean,
            "terminal_wealth_population_variance": empirical_variance,
            "independent_random_stream": True,
        },
        "analytical_reference": analytic,
        "comparison": {
            "analytical": analytic_compare,
            "neural": neural_compare,
            "predeclared_tolerance": tolerance,
        },
        "known_reproducibility_limits": lock["paper_protocol_deviations_known_before_run"],
        "artifact_policy": {
            "large_hf_artifacts_created": False,
            "reason": "model state and raw trace are small JSON artifacts; no large checkpoint or third-party dataset was generated",
            "mutable_path_without_git_hash_is_evidence": False,
        },
        "licenses": protocol["license_checks"],
    }
    report_bytes = canonical_bytes(report)
    report["report_content_sha256_without_self_hash"] = sha256_bytes(report_bytes)
    (output_dir / "report.json").write_bytes(canonical_bytes(report))
    return report


def load_protocol(path: Path) -> dict[str, Any]:
    protocol = json.loads(path.read_text(encoding="utf-8"))
    protocol["_protocol_path"] = str(path.resolve())
    return protocol


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report = run(load_protocol(args.protocol), args.output_dir)
    print(
        json.dumps(
            {
                "empirical_verdict": report["empirical_verdict"],
                "mean": report["evaluation"]["terminal_wealth_mean"],
                "variance": report["evaluation"]["terminal_wealth_population_variance"],
                "analytical_match": report["comparison"]["analytical"]["within_tolerance"],
                "neural_match": report["comparison"]["neural"]["within_tolerance"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
