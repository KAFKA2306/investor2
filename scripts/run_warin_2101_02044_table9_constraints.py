#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
from pathlib import Path
from typing import Any

import numpy as np
import tensorflow as tf

ROOT = Path(__file__).resolve().parents[1]


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def build_model(width: int, dimension: int, name: str) -> tf.keras.Model:
    return tf.keras.Sequential(
        [
            tf.keras.layers.Input(shape=(2,), dtype=tf.float32),
            tf.keras.layers.Dense(width, activation="tanh"),
            tf.keras.layers.Dense(width, activation="tanh"),
            tf.keras.layers.Dense(width, activation="tanh"),
            tf.keras.layers.Dense(dimension, activation="sigmoid"),
        ],
        name=name,
    )


def model_state(model: tf.keras.Model) -> dict[str, Any]:
    rows = []
    for layer in model.layers:
        arrays = layer.get_weights()
        if arrays:
            rows.append(
                {
                    "name": layer.name,
                    "class": layer.__class__.__name__,
                    "arrays": [a.tolist() for a in arrays],
                    "shapes": [list(a.shape) for a in arrays],
                }
            )
    return {"format": "canonical-json-keras-weights-v1", "layers": rows}


def paper_projection(weights: tf.Tensor, lower: tf.Tensor, upper: tf.Tensor) -> tf.Tensor:
    projected = weights
    dimension = int(weights.shape[-1])
    for j in range(dimension):
        deficit = tf.constant(1.0, tf.float32) - tf.reduce_sum(projected, axis=1)
        column = tf.clip_by_value(projected[:, j] + deficit, lower[j], upper[j])
        one_hot = tf.one_hot(j, dimension, dtype=tf.float32)[None, :]
        projected = projected * (1.0 - one_hot) + column[:, None] * one_hot
    return projected


def transform_weights(raw: tf.Tensor, model_id: int, lower: tf.Tensor, upper: tf.Tensor) -> tf.Tensor:
    if model_id == 1:
        denom = tf.maximum(tf.reduce_sum(raw, axis=1, keepdims=True), tf.constant(1e-8, tf.float32))
        return raw / denom
    if model_id == 4:
        bounded = lower + raw * (upper - lower)
        return paper_projection(bounded, lower, upper)
    raise ValueError(f"unsupported model {model_id}")


def run_one(protocol: dict[str, Any], model_id: int, restart: int, output_dir: Path) -> dict[str, Any]:
    market = protocol["market_model"]
    constraints = protocol["constraints"]
    network = protocol["network"]
    evaluation = protocol["evaluation"]
    scope = protocol["reproduction_scope"]
    lock = protocol["implementation_lock"]

    if tf.__version__ != lock["tensorflow"]:
        raise ValueError(f"TensorFlow {tf.__version__} != locked {lock['tensorflow']}")
    iterations = int(network["gradient_iterations"])
    batch_size = int(network["batch_size"])
    if iterations != 10000 or batch_size != 300 or int(network["restarts"]) != 4:
        raise ValueError("Table 9 run must retain paper iteration/batch/restart counts")

    seed = int(lock["seed_start"]) + restart
    tf.keras.utils.set_random_seed(seed)
    try:
        tf.config.experimental.enable_op_determinism()
    except Exception:
        pass

    mu = tf.constant(market["mu"], tf.float32)
    vol = tf.constant(market["sigma_diagonal"], tf.float32)
    rho = tf.constant(market["correlation"], tf.float32)
    chol = tf.linalg.cholesky(rho)
    dimension = len(market["mu"])
    n_steps = int(market["rebalancing_steps"])
    dt = float(market["horizon_years"]) / n_steps
    sqrt_dt = math.sqrt(dt)
    drift = (mu - 0.5 * tf.square(vol)) * tf.constant(dt, tf.float32)
    lower = tf.constant(constraints["weight_lower"], tf.float32)
    upper = tf.constant(constraints["weight_upper"], tf.float32)
    initial_weights = tf.constant(constraints["initial_weights"], tf.float32)
    eta = tf.constant(constraints["max_absolute_weight_change_per_rebalance"], tf.float32)
    epsilon = float(constraints["penalty_epsilon"])
    beta = float(scope["beta"])
    initial_wealth = float(market["initial_wealth"])

    model = build_model(int(network["hidden_width"]), dimension, f"warin_table9_model{model_id}_restart{restart}")
    model(tf.zeros((1, 2), tf.float32), training=False)
    optimizer = tf.keras.optimizers.Adam(float(network["learning_rate_initial"]))

    @tf.function(reduce_retracing=True)
    def simulate(step_key: tf.Tensor, sample_count: tf.Tensor, training: bool):
        wealth = tf.fill([sample_count], tf.constant(initial_wealth, tf.float32))
        previous = tf.tile(initial_weights[None, :], [sample_count, 1])
        local_penalty = tf.zeros([sample_count], tf.float32)
        lower_penalty = tf.zeros([sample_count], tf.float32)
        upper_penalty = tf.zeros([sample_count], tf.float32)
        sum_error = tf.zeros([sample_count], tf.float32)

        for i in tf.range(n_steps):
            if i == 0:
                weights = previous
            else:
                t_value = tf.cast(i, tf.float32) / tf.cast(n_steps, tf.float32)
                inputs = tf.stack([tf.fill([sample_count], t_value), wealth], axis=1)
                raw = model(inputs, training=training)
                weights = transform_weights(raw, model_id, lower, upper)
                local_penalty += tf.reduce_sum(tf.nn.relu(tf.abs(weights - previous) - eta), axis=1)
                if model_id == 1:
                    lower_penalty += tf.reduce_sum(tf.nn.relu(lower - weights), axis=1)
                    upper_penalty += tf.reduce_sum(tf.nn.relu(weights - upper), axis=1)
                sum_error += tf.abs(tf.reduce_sum(weights, axis=1) - 1.0)

            stateless_seed = tf.stack(
                [tf.constant(seed, tf.int32) + step_key * 1009, tf.cast(i, tf.int32) + step_key * n_steps]
            )
            z = tf.random.stateless_normal([sample_count, dimension], seed=stateless_seed, dtype=tf.float32)
            dw = tf.matmul(z, chol, transpose_b=True) * tf.constant(sqrt_dt, tf.float32)
            simple_returns = tf.exp(drift + vol * dw) - 1.0
            wealth *= 1.0 + tf.reduce_sum(weights * simple_returns, axis=1)
            previous = weights

        return wealth, local_penalty, lower_penalty, upper_penalty, sum_error

    @tf.function(reduce_retracing=True)
    def train_step(iteration: tf.Tensor):
        with tf.GradientTape() as tape:
            wealth, local_p, lower_p, upper_p, _ = simulate(iteration, tf.constant(batch_size, tf.int32), True)
            mean = tf.reduce_mean(wealth)
            variance = tf.reduce_mean(tf.square(wealth - mean))
            total_penalty = tf.reduce_mean(local_p + lower_p + upper_p)
            base_loss = -mean + tf.constant(beta, tf.float32) * variance
            loss = base_loss + total_penalty / tf.constant(epsilon, tf.float32)
        gradients = tape.gradient(loss, model.trainable_variables)
        if any(g is None for g in gradients):
            raise RuntimeError("missing gradient")
        optimizer.apply_gradients(zip(gradients, model.trainable_variables))
        return loss, mean, variance, total_penalty

    trace = []
    lr0 = float(network["learning_rate_initial"])
    lr1 = float(network["learning_rate_final"])
    for i in range(iterations):
        fraction = i / max(iterations - 1, 1)
        lr = lr0 + (lr1 - lr0) * fraction
        optimizer.learning_rate.assign(lr)
        loss, mean, variance, penalty = train_step(tf.constant(i + 1, tf.int32))
        values = [float(v.numpy()) for v in (loss, mean, variance, penalty)]
        if not all(math.isfinite(v) for v in values):
            raise FloatingPointError(f"non-finite training metric at iteration {i+1}")
        if i == 0 or (i + 1) % 100 == 0 or i + 1 == iterations:
            trace.append(
                {
                    "iteration": i + 1,
                    "learning_rate": lr,
                    "penalized_loss": values[0],
                    "batch_mean": values[1],
                    "batch_variance": values[2],
                    "batch_constraint_penalty": values[3],
                }
            )

    eval_count = int(evaluation["simulation_count"])
    chunk_size = 5000
    total_n = 0
    total_sum = total_sumsq = 0.0
    local_total = lower_total = upper_total = sum_error_total = 0.0
    for chunk_index, start in enumerate(range(0, eval_count, chunk_size)):
        count = min(chunk_size, eval_count - start)
        wealth, local_p, lower_p, upper_p, sum_error = simulate(
            tf.constant(1_000_000 + chunk_index, tf.int32), tf.constant(count, tf.int32), False
        )
        wealth_np = wealth.numpy().astype(np.float64, copy=False)
        if not np.isfinite(wealth_np).all():
            raise FloatingPointError("non-finite evaluation wealth")
        total_n += count
        total_sum += float(wealth_np.sum(dtype=np.float64))
        total_sumsq += float(np.square(wealth_np).sum(dtype=np.float64))
        local_total += float(tf.reduce_sum(local_p).numpy())
        lower_total += float(tf.reduce_sum(lower_p).numpy())
        upper_total += float(tf.reduce_sum(upper_p).numpy())
        sum_error_total += float(tf.reduce_sum(sum_error).numpy())

    mean = total_sum / total_n
    variance = max(0.0, total_sumsq / total_n - mean * mean)
    unpenalized_score = mean - beta * variance
    total_constraint_penalty = (local_total + lower_total + upper_total) / total_n
    opposite_penalized_objective = unpenalized_score - total_constraint_penalty / epsilon
    diagnostics = {
        "mean_local_excess_path_sum": local_total / total_n,
        "mean_lower_bound_excess_path_sum": lower_total / total_n,
        "mean_upper_bound_excess_path_sum": upper_total / total_n,
        "mean_sum_to_one_error_path_sum": sum_error_total / total_n,
        "total_mean_constraint_penalty": total_constraint_penalty,
    }

    target_key = f"model_{model_id}_unpenalized_score"
    penalized_key = f"model_{model_id}_opposite_penalized_objective"
    target = scope["paper_target"]
    tolerance = scope["predeclared_tolerance"]
    score_error = abs(unpenalized_score - float(target[target_key]))
    objective_error = abs(opposite_penalized_objective - float(target[penalized_key]))
    within = score_error <= float(tolerance["unpenalized_score_absolute"]) and objective_error <= float(
        tolerance["penalized_objective_absolute"]
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    trace_path = output_dir / "training_trace.json"
    state_path = output_dir / "model_state.json"
    trace_path.write_bytes(canonical_bytes({"trace": trace}))
    state_path.write_bytes(canonical_bytes(model_state(model)))
    report = {
        "schema_version": "investor2.warin-table9-run.v1",
        "paper_id": "warin_2101_02044",
        "paper_version": "v4",
        "model_id": model_id,
        "restart": restart,
        "seed": seed,
        "beta": beta,
        "training": {
            "iterations": iterations,
            "batch_size": batch_size,
            "learning_rate_initial": lr0,
            "learning_rate_final": lr1,
            "training_trace_sha256": sha256_file(trace_path),
            "model_state_sha256": sha256_file(state_path),
        },
        "evaluation": {
            "simulation_count": total_n,
            "mean": mean,
            "variance": variance,
            "unpenalized_score": unpenalized_score,
            "opposite_penalized_objective": opposite_penalized_objective,
            "constraint_diagnostics": diagnostics,
        },
        "comparison": {
            "paper_unpenalized_score": target[target_key],
            "paper_opposite_penalized_objective": target[penalized_key],
            "unpenalized_score_abs_error": score_error,
            "penalized_objective_abs_error": objective_error,
            "within_predeclared_tolerance": within,
        },
        "runtime": {
            "python": platform.python_version(),
            "tensorflow": tf.__version__,
            "numpy": np.__version__,
            "device_policy": lock["device"],
            "github_sha": os.environ.get("GITHUB_SHA", "LOCAL_WORKTREE"),
        },
    }
    report_path = output_dir / "report.json"
    report_path.write_bytes(canonical_bytes(report))
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    protocol_path = args.protocol if args.protocol.is_absolute() else ROOT / args.protocol
    output_root = args.output_root if args.output_root.is_absolute() else ROOT / args.output_root
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))

    all_runs: dict[str, list[dict[str, Any]]] = {"1": [], "4": []}
    selected: dict[str, dict[str, Any]] = {}
    for model_id in (1, 4):
        for restart in range(int(protocol["network"]["restarts"])):
            run_dir = output_root / f"model{model_id}" / f"restart{restart}"
            report = run_one(protocol, model_id, restart, run_dir)
            all_runs[str(model_id)].append(report)
            print(
                json.dumps(
                    {
                        "model": model_id,
                        "restart": restart,
                        "score": report["evaluation"]["unpenalized_score"],
                        "opposite_penalized_objective": report["evaluation"]["opposite_penalized_objective"],
                        "within": report["comparison"]["within_predeclared_tolerance"],
                    },
                    sort_keys=True,
                ),
                flush=True,
            )
        best = max(all_runs[str(model_id)], key=lambda r: r["evaluation"]["opposite_penalized_objective"])
        selected[str(model_id)] = best

    model_verdicts = {
        model_id: "REPRODUCED" if report["comparison"]["within_predeclared_tolerance"] else "FAILED"
        for model_id, report in selected.items()
    }
    overall = "REPRODUCED" if all(v == "REPRODUCED" for v in model_verdicts.values()) else "FAILED"
    summary = {
        "schema_version": "investor2.warin-table9-summary.v1",
        "paper_id": "warin_2101_02044",
        "protocol": str(protocol_path.relative_to(ROOT)),
        "protocol_sha256": sha256_file(protocol_path),
        "selection_rule": "maximum opposite penalized objective, equivalent to minimum penalized objective",
        "selected": selected,
        "model_verdicts": model_verdicts,
        "empirical_verdict": overall,
        "paper_wide_reproduction_claim": false if False else False
    }
    output_root.mkdir(parents=True, exist_ok=True)
    summary_path = output_root / "summary.json"
    summary_path.write_bytes(canonical_bytes(summary))
    print(json.dumps({"summary": str(summary_path.relative_to(ROOT)), "verdict": overall}, sort_keys=True))


if __name__ == "__main__":
    main()
