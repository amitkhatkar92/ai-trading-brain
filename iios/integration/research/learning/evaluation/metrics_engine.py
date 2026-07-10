"""evaluation/metrics_engine.py — Model-agnostic metric computations."""
from __future__ import annotations

import math
from typing import Any, Optional

from iios.integration.research.learning.learning_constants import ModelTask
from iios.integration.research.learning.learning_exceptions import MetricsError


def _safe_div(a: float, b: float, default: float = 0.0) -> float:
    return a / b if b != 0 else default


class MetricsEngine:
    """
    Pure-Python metric computations — no external ML libraries required.

    All methods accept plain Python lists of actuals and predictions.
    """

    # ── Classification ────────────────────────────────────────────────────────

    def compute_classification(
        self,
        actuals:     list,
        predictions: list,
    ) -> dict[str, float]:
        if len(actuals) != len(predictions):
            raise MetricsError("actuals and predictions must have the same length")
        n = len(actuals)
        if n == 0:
            return {}

        # Per-class TP/FP/FN for macro averaging
        classes = sorted(set(actuals) | set(predictions))
        tp:  dict[Any, int] = {c: 0 for c in classes}
        fp:  dict[Any, int] = {c: 0 for c in classes}
        fn:  dict[Any, int] = {c: 0 for c in classes}
        correct = 0

        for a, p in zip(actuals, predictions):
            if a == p:
                correct += 1
                tp[a]   += 1
            else:
                fp[p] = fp.get(p, 0) + 1
                fn[a] = fn.get(a, 0) + 1

        accuracy = correct / n

        precisions = [_safe_div(tp[c], tp[c] + fp.get(c, 0)) for c in classes]
        recalls    = [_safe_div(tp[c], tp[c] + fn.get(c, 0)) for c in classes]

        macro_precision = sum(precisions) / len(classes)
        macro_recall    = sum(recalls)    / len(classes)
        macro_f1        = _safe_div(
            2 * macro_precision * macro_recall,
            macro_precision + macro_recall,
        )

        return {
            "accuracy":         accuracy,
            "precision_macro":  macro_precision,
            "recall_macro":     macro_recall,
            "f1_macro":         macro_f1,
            "n_classes":        float(len(classes)),
            "n_samples":        float(n),
        }

    # ── Regression ────────────────────────────────────────────────────────────

    def compute_regression(
        self,
        actuals:     list[float],
        predictions: list[float],
    ) -> dict[str, float]:
        if len(actuals) != len(predictions):
            raise MetricsError("actuals and predictions must have the same length")
        n = len(actuals)
        if n == 0:
            return {}

        errors    = [p - a for a, p in zip(actuals, predictions)]
        abs_errs  = [abs(e) for e in errors]
        sq_errs   = [e ** 2 for e in errors]

        mae  = sum(abs_errs) / n
        mse  = sum(sq_errs)  / n
        rmse = math.sqrt(mse)

        # MAPE — skip zero actuals
        mape_terms = [abs(e) / abs(a) for a, e in zip(actuals, errors) if a != 0]
        mape = (sum(mape_terms) / len(mape_terms) * 100) if mape_terms else 0.0

        # R²
        mean_actual = sum(actuals) / n
        ss_res = sum(sq_errs)
        ss_tot = sum((a - mean_actual) ** 2 for a in actuals)
        r2 = 1 - _safe_div(ss_res, ss_tot, default=0.0) if ss_tot != 0 else 0.0

        return {
            "mae":       mae,
            "mse":       mse,
            "rmse":      rmse,
            "mape":      mape,
            "r_squared": r2,
            "n_samples": float(n),
        }

    # ── Forecasting ───────────────────────────────────────────────────────────

    def compute_forecasting(
        self,
        actuals:     list[float],
        predictions: list[float],
    ) -> dict[str, float]:
        metrics = self.compute_regression(actuals, predictions)
        if len(actuals) >= 2:
            direction_correct = sum(
                1 for a1, a2, p1, p2 in zip(actuals, actuals[1:], predictions, predictions[1:])
                if (a2 - a1) * (p2 - p1) > 0
            )
            metrics["directional_accuracy"] = direction_correct / (len(actuals) - 1)
        return metrics

    # ── Ranking ───────────────────────────────────────────────────────────────

    def compute_ranking(
        self,
        actuals: list[float],
        scores:  list[float],
    ) -> dict[str, float]:
        """Basic ranking metric: Spearman rank correlation."""
        n = len(actuals)
        if n < 2:
            return {"spearman_rho": 0.0, "n_samples": float(n)}

        def _rank(lst: list[float]) -> list[float]:
            sorted_i = sorted(range(n), key=lambda i: lst[i])
            ranks    = [0.0] * n
            for rank, idx in enumerate(sorted_i):
                ranks[idx] = float(rank + 1)
            return ranks

        ra = _rank(actuals)
        rs = _rank(scores)
        d2 = sum((ra[i] - rs[i]) ** 2 for i in range(n))
        rho = 1 - 6 * d2 / (n * (n ** 2 - 1))
        return {"spearman_rho": rho, "n_samples": float(n)}

    # ── Router ────────────────────────────────────────────────────────────────

    def compute(
        self,
        task:        ModelTask,
        actuals:     list,
        predictions: list,
        scores:      Optional[list] = None,
    ) -> dict[str, float]:
        if task == ModelTask.CLASSIFICATION:
            return self.compute_classification(actuals, predictions)
        if task == ModelTask.REGRESSION:
            return self.compute_regression(actuals, predictions)
        if task == ModelTask.FORECASTING:
            return self.compute_forecasting(actuals, predictions)
        if task == ModelTask.RANKING:
            return self.compute_ranking(actuals, scores or predictions)
        # Fallback for clustering / anomaly / custom
        return {}
