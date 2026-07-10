"""evaluation/evaluation_engine.py — Orchestrates model evaluation."""
from __future__ import annotations

import inspect
import time
import threading
from typing import Any, Optional

from iios.integration.research.learning.learning_constants import ModelTask, ValidationStatus
from iios.integration.research.learning.learning_exceptions import EvaluationError
from iios.integration.research.learning.evaluation.metrics_engine   import MetricsEngine
from iios.integration.research.learning.evaluation.evaluation_report import EvaluationReport


class EvaluationEngine:
    """
    Runs model evaluation against a dataset and produces an EvaluationReport.

    The engine calls ``model.evaluate(dataset)`` if available, otherwise it
    calls ``model.predict_batch()`` and computes metrics itself via MetricsEngine.
    """

    def __init__(self) -> None:
        self._metrics   = MetricsEngine()
        self._lock      = threading.RLock()
        self._total_run = 0

    async def evaluate(
        self,
        model:    Any,      # BaseModel
        dataset:  Any,      # TrainingDataset / ValidationDataset / TestDataset
        task:     ModelTask,
        *,
        label_name: Optional[str] = None,
        report_id:  Optional[str] = None,
    ) -> EvaluationReport:
        """
        Run evaluation for a model on a dataset and return an EvaluationReport.

        If the model exposes ``evaluate(dataset) -> dict``, that is called
        directly.  Otherwise the engine extracts actuals from the dataset and
        calls ``model.predict_batch(records)``.
        """
        t0 = time.time()
        try:
            eval_fn = getattr(model, "evaluate", None)
            if eval_fn is not None:
                if inspect.iscoroutinefunction(eval_fn):
                    metrics = await eval_fn(dataset)
                else:
                    metrics = eval_fn(dataset)
                n_samples = len(dataset) if hasattr(dataset, "__len__") else 0
            else:
                # Manual evaluation via predict_batch
                records   = dataset.records() if hasattr(dataset, "records") else []
                n_samples = len(records)
                lname     = label_name or getattr(dataset, "label_name", None)

                record_dicts = [r.features if hasattr(r, "features") else r for r in records]
                predict_fn   = getattr(model, "predict_batch", None)

                if predict_fn is not None:
                    if inspect.iscoroutinefunction(predict_fn):
                        preds_raw = await predict_fn(record_dicts)
                    else:
                        preds_raw = predict_fn(record_dicts)
                    predictions = [p.get("prediction") for p in preds_raw]
                else:
                    predictions = []

                actuals = [getattr(r, "label", None) for r in records]
                if actuals and predictions and None not in actuals and None not in predictions:
                    metrics = self._metrics.compute(task, actuals, predictions)
                else:
                    metrics = {}

            evaluation_sec = time.time() - t0
            report = EvaluationReport.create(
                model_id       = getattr(model, "model_id", "unknown"),
                model_version  = getattr(model, "version", "1.0.0"),
                dataset_id     = getattr(dataset, "dataset_id", "unknown"),
                model_task     = task,
                metrics        = {k: float(v) for k, v in metrics.items()
                                  if isinstance(v, (int, float))},
                evaluation_sec = evaluation_sec,
                n_samples      = n_samples,
                report_id      = report_id,
            )

            with self._lock:
                self._total_run += 1
            return report

        except EvaluationError:
            raise
        except Exception as exc:
            evaluation_sec = time.time() - t0
            return EvaluationReport.create(
                model_id       = getattr(model, "model_id", "unknown"),
                model_version  = getattr(model, "version", "1.0.0"),
                dataset_id     = getattr(dataset, "dataset_id", "unknown"),
                model_task     = task,
                metrics        = {},
                evaluation_sec = evaluation_sec,
                status         = ValidationStatus.FAILED,
                error          = str(exc),
                report_id      = report_id,
            )

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {"total_evaluations": self._total_run}
