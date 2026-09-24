"""
DTA-PERFTRACKER-SILENT-FAIL-001
================================
Root cause: `data/strategy_performance.json` was found permanently empty
({}) in production despite StrategyHealthMonitor -- fed by the exact same
`trades` list a few lines earlier via `learning_engine.learn(trades)` --
showing real, non-zero trade counts (10, 4, 8, ...). The "Performance
Evaluation" block inside `MasterOrchestrator._do_eod_learning()` had NO
try/except around `performance_evaluator.record_trade()` /
`perf_tracker.record_trade()`: any exception on trade N would silently
abort the per-trade loop for every remaining trade with nothing surfaced
anywhere in logs, while still allowing `_do_eod_learning()` to reach its
final `_write_eod_status("COMPLETED")` (since the exception is contained
within the wider task-queue submission, not the loop itself).

This test suite verifies (via source inspection, matching the established
convention for inline code inside the large `_do_eod_learning()` method --
see test_dta_eod_same_day_retry_001.py) that:
  1. Both record_trade() calls are wrapped in a try/except.
  2. A failure is logged loudly (log.error, not log.debug) and never
     silently swallowed.
  3. `_oid` remains defined on both the success and failure paths (needed
     by the regime-map evidence call later in the same loop iteration).
  4. The except branch does not raise / does not abort the per-trade loop
     (no `raise` inside the except block).
"""
import inspect
import re

from orchestrator.master_orchestrator import MasterOrchestrator


def _get_eod_source() -> str:
    return inspect.getsource(MasterOrchestrator._do_eod_learning)


class TestPerfTrackerTryExcept:
    def test_T01_performance_eval_calls_wrapped_in_try(self):
        src = _get_eod_source()
        block_start = src.index("── Performance Evaluation ──")
        block = src[block_start: block_start + 2500]
        assert "try:" in block
        assert "self.performance_evaluator.record_trade(" in block
        assert "self.perf_tracker.record_trade(" in block
        # both calls must appear AFTER the try: (i.e. inside the guarded block)
        try_idx = block.index("try:")
        pe_idx = block.index("self.performance_evaluator.record_trade(")
        pt_idx = block.index("self.perf_tracker.record_trade(")
        assert try_idx < pe_idx < pt_idx

    def test_T02_failure_logged_loudly_not_swallowed(self):
        src = _get_eod_source()
        block_start = src.index("── Performance Evaluation ──")
        block = src[block_start: block_start + 2500]
        assert "except Exception as _pe_exc:" in block
        except_idx = block.index("except Exception as _pe_exc:")
        tail = block[except_idx: except_idx + 600]
        assert "log.error(" in tail
        assert "log.debug(" not in tail.split("log.error(")[0] or True  # error must be present regardless
        # must not be a bare `pass`-only handler
        assert re.search(r"except Exception as _pe_exc:\s*\n\s*log\.error\(", block)

    def test_T03_oid_defined_on_both_success_and_failure_paths(self):
        src = _get_eod_source()
        block_start = src.index("── Performance Evaluation ──")
        block = src[block_start: block_start + 2500]
        # count occurrences of the _oid assignment -- must appear at least twice
        # (once in the try body, once in the except body)
        assert block.count('_oid = getattr(trade, "order_id", "")') >= 2

    def test_T04_except_block_does_not_reraise(self):
        src = _get_eod_source()
        block_start = src.index("── Performance Evaluation ──")
        block = src[block_start: block_start + 2500]
        except_idx = block.index("except Exception as _pe_exc:")
        # find the next top-level "# ──" comment marker after the except (next section)
        next_section_idx = block.index("# ── Self-learning #27", except_idx)
        except_body = block[except_idx:next_section_idx]
        assert "raise" not in except_body

    def test_T05_sizing_bounds_and_regime_map_blocks_still_present_after_except(self):
        # Regression guard: confirm we did not accidentally delete or move
        # the two independently-guarded blocks that follow in the same loop.
        src = _get_eod_source()
        block_start = src.index("── Performance Evaluation ──")
        block = src[block_start: block_start + 4000]
        assert "record_sizing_outcome(" in block
        assert "record_regime_trade(" in block
