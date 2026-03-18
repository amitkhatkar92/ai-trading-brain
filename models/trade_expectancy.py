"""
Trade Expectancy Model
======================
The core insight: profitability comes from EXPECTANCY, not win rate.

Formula:
    Expectancy = (WinRate × AvgWin_R) − (LossRate × AvgLoss_R)

A system with 40% win rate and 3R payoff:
    (0.40 × 3) − (0.60 × 1) = 1.20 − 0.60 = +0.60R per trade   ← PROFITABLE

A system with 70% win rate and 0.5R payoff / 2R loss:
    (0.70 × 0.5) − (0.30 × 2) = 0.35 − 0.60 = −0.25R per trade ← LOSING

Key principle: Cut losses quickly, let winners run, capture rare large moves.
"""

from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import List, Optional


# ── Classification thresholds ─────────────────────────────────────────────
EXCELLENT_EXPECTANCY_R  =  0.5    # +0.5R or better per trade
GOOD_EXPECTANCY_R       =  0.2    # +0.2R to +0.5R
MARGINAL_EXPECTANCY_R   =  0.0    # 0 to +0.2R  (breakeven zone)
# Below 0.0 → NEGATIVE

# Minimum rewarded R:R — any strategy below this is rejected regardless
MIN_SYSTEM_RR_RATIO     =  2.0    # asymmetric payoff philosophy

# "Fat tail" threshold — a trade producing this R or more is a "year-maker"
FAT_TAIL_THRESHOLD_R    =  3.0    # 3R+ trade is a large winner

# Win rate to break even at a given R:R
# breakeven_wr = 1 / (1 + RR)


# ── Data Model ────────────────────────────────────────────────────────────

@dataclass
class ExpectancyProfile:
    """
    Full statistical expectancy profile for a signal or strategy.

    Attributes:
        win_rate          Fraction of trades that were winners [0.0–1.0]
        avg_win_r         Average winner expressed in R multiples (positive)
        avg_loss_r        Average loser expressed in R multiples (positive, e.g. 1.0)
        n_samples         Number of trades used to compute these stats
        expectancy_r      Core metric: expected R gained per trade
        breakeven_wr      Win rate needed to break even at this R:R
        reward_risk_ratio avg_win_r / avg_loss_r
        fat_tail_pct      Fraction of trades that produced ≥ FAT_TAIL_THRESHOLD_R
        classification    "EXCELLENT" | "GOOD" | "MARGINAL" | "NEGATIVE"
    """
    win_rate:           float
    avg_win_r:          float
    avg_loss_r:         float
    n_samples:          int
    expectancy_r:       float       = field(init=False)
    breakeven_wr:       float       = field(init=False)
    reward_risk_ratio:  float       = field(init=False)
    fat_tail_pct:       float       = 0.0
    classification:     str         = field(init=False)

    def __post_init__(self) -> None:
        loss_rate             = 1.0 - self.win_rate
        self.expectancy_r     = (self.win_rate * self.avg_win_r) - (loss_rate * self.avg_loss_r)
        self.reward_risk_ratio= (self.avg_win_r / self.avg_loss_r) if self.avg_loss_r else 0.0
        self.breakeven_wr     = 1.0 / (1.0 + self.reward_risk_ratio) if self.reward_risk_ratio else 1.0
        self.classification   = ExpectancyCalculator.classify(self.expectancy_r)

    def summary(self) -> str:
        sign = "+" if self.expectancy_r >= 0 else ""
        return (
            f"Expectancy={sign}{self.expectancy_r:.3f}R  "
            f"[WR={self.win_rate:.0%}  AvgW={self.avg_win_r:.2f}R  "
            f"AvgL=-{self.avg_loss_r:.2f}R  "
            f"RR={self.reward_risk_ratio:.1f}  "
            f"Breakeven≥{self.breakeven_wr:.0%}  "
            f"FatTail={self.fat_tail_pct:.0%}]  "
            f"{self.classification}"
        )


@dataclass
class SignalExpectancy:
    """
    Per-signal forward-looking expectancy based on its price levels.
    Computed before a trade is taken — shows what is needed to be profitable.
    """
    symbol:            str
    strategy:          str
    rr_ratio:          float            # reward / risk
    breakeven_wr:      float            # WR needed to break even
    estimated_wr:      float            # estimated WR (from strategy history or 0.5 default)
    estimated_exp_r:   float            # (est_wr × RR) − (1−est_wr × 1)
    classification:    str
    notes:             List[str] = field(default_factory=list)


# ── Calculator ────────────────────────────────────────────────────────────

class ExpectancyCalculator:
    """
    Stateless utility. All methods are static / class methods.
    Provides the primary expectancy analytics used system-wide.
    """

    # ── Core formula ──────────────────────────────────────────────────────

    @staticmethod
    def expectancy_r(win_rate: float, avg_win_r: float, avg_loss_r: float) -> float:
        """
        Expectancy in R-multiples.
            E = (WR × AvgWin_R) − (LR × AvgLoss_R)
        """
        loss_rate = 1.0 - win_rate
        return (win_rate * avg_win_r) - (loss_rate * avg_loss_r)

    @staticmethod
    def breakeven_win_rate(rr_ratio: float) -> float:
        """
        Minimum win rate to break even at a given R:R.
            breakeven_wr = 1 / (1 + RR)
        E.g. RR=2 → need 33.3%, RR=3 → need 25%, RR=4 → need 20%
        """
        return 1.0 / (1.0 + rr_ratio) if rr_ratio > 0 else 1.0

    @staticmethod
    def classify(expectancy_r: float) -> str:
        """Classify the expectancy profile into human-readable quality tier."""
        if expectancy_r >= EXCELLENT_EXPECTANCY_R:
            return "EXCELLENT"
        if expectancy_r >= GOOD_EXPECTANCY_R:
            return "GOOD"
        if expectancy_r >= MARGINAL_EXPECTANCY_R:
            return "MARGINAL"
        return "NEGATIVE"

    # ── Build profiles ────────────────────────────────────────────────────

    @classmethod
    def from_trades(
        cls,
        wins:      List[float],   # R multiples of winning trades (positive)
        losses:    List[float],   # R multiples of losing trades (can be negative or positive magnitude)
        fat_tail_r: float = FAT_TAIL_THRESHOLD_R,
    ) -> Optional[ExpectancyProfile]:
        """
        Build an ExpectancyProfile from completed trade R-multiples.

        Args:
            wins:   list of R-multiples for winning trades (e.g. [1.2, 3.5, 2.1])
            losses: list of R-multiples for losing trades  (e.g. [-0.8, -1.0, -1.2])
        """
        total = len(wins) + len(losses)
        if total == 0:
            return None

        win_rate  = len(wins) / total
        avg_win_r = (sum(wins) / len(wins)) if wins else 0.0
        avg_los_r = (sum(abs(l) for l in losses) / len(losses)) if losses else 1.0

        # Fat tail: fraction of ALL trades producing ≥ fat_tail_r
        all_r      = wins + [abs(l) for l in losses]
        fat_tail   = sum(1 for r in wins if r >= fat_tail_r) / total

        return ExpectancyProfile(
            win_rate  = win_rate,
            avg_win_r = avg_win_r,
            avg_loss_r= avg_los_r,
            n_samples = total,
            fat_tail_pct = fat_tail,
        )

    @classmethod
    def from_signal(
        cls,
        rr_ratio:       float,
        strategy_win_rate: Optional[float] = None,
    ) -> SignalExpectancy:
        """
        Pre-trade expectancy analysis for a single signal.

        If strategy_win_rate is unknown, uses conservative 0.45 estimate.
        A positive estimated_exp_r means even at a conservative WR,
        the R:R is favourable enough to take the trade.
        """
        est_wr   = strategy_win_rate if strategy_win_rate is not None else 0.45
        bkv_wr   = cls.breakeven_win_rate(rr_ratio)
        exp_r    = cls.expectancy_r(est_wr, rr_ratio, 1.0)

        notes = []
        if rr_ratio >= 4.0:
            notes.append(f"Fat-tail potential: only {bkv_wr:.0%} WR needed to profit")
        elif rr_ratio >= 2.0:
            notes.append(f"Asymmetric payoff: breakeven at {bkv_wr:.0%} WR")
        else:
            notes.append(f"Low R:R={rr_ratio:.1f} — needs {bkv_wr:.0%} WR to break even")

        if exp_r < 0:
            notes.append(f"Negative expected value at estimated {est_wr:.0%} WR")

        return SignalExpectancy(
            symbol           = "",
            strategy         = "",
            rr_ratio         = rr_ratio,
            breakeven_wr     = bkv_wr,
            estimated_wr     = est_wr,
            estimated_exp_r  = round(exp_r, 4),
            classification   = cls.classify(exp_r),
            notes            = notes,
        )

    # ── Kelly fraction (optional position sizing) ─────────────────────────

    @staticmethod
    def kelly_fraction(win_rate: float, rr_ratio: float) -> float:
        """
        Full Kelly: f = WR − (1−WR)/RR
        Returns fraction of capital to risk per trade.
        Typically use half-Kelly (× 0.5) in practice.
        """
        if rr_ratio <= 0:
            return 0.0
        f = win_rate - (1.0 - win_rate) / rr_ratio
        return max(0.0, f)

    # ── Reporting ─────────────────────────────────────────────────────────

    @staticmethod
    def expectancy_table(
        win_rates: List[float] = None,
        rr_ratios: List[float] = None,
    ) -> str:
        """
        ASCII table showing expectancy across win-rate × R:R combinations.
        Used for debugging and reporting.
        """
        wrs   = win_rates  or [0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60]
        rrs   = rr_ratios  or [1.0, 1.5, 2.0, 2.5, 3.0, 4.0]
        lines = ["Expectancy Table (R per trade)"]
        header = f"{'WR':>6}" + "".join(f"  RR={r:3.1f}" for r in rrs)
        lines.append(header)
        lines.append("─" * len(header))
        for wr in wrs:
            row = f"{wr:>5.0%} "
            for rr in rrs:
                exp = ExpectancyCalculator.expectancy_r(wr, rr, 1.0)
                tag = "✅" if exp >= 0.1 else ("⚠️" if exp >= 0 else "❌")
                row += f" {exp:+.2f}{tag}"
            lines.append(row)
        return "\n".join(lines)
