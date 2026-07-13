"""iios/investment/company/valuation/peer_valuation.py
Peer comparison — derive target multiples from peer ValuationSnapshots.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from iios.investment.company.valuation.valuation_statistics import safe_median


class PeerValuationEngine:
    """
    Extract peer-median multiples from a list of peer ValuationSnapshots.
    The output is a dict of median multiples suitable for use as
    RelativeValuationAssumptions targets.
    """

    def derive_peer_multiples(
        self,
        peer_snapshots: List[Any],  # List[ValuationSnapshot]
    ) -> Dict[str, Optional[float]]:
        """
        Returns median P/E, EV/EBITDA, P/B, P/FCF across peers.
        Skips peers with no market data.
        """
        pes:       List[float] = []
        evs:       List[float] = []
        pbs:       List[float] = []
        pfcfs:     List[float] = []
        ev_sales:  List[float] = []

        for snap in peer_snapshots:
            mults = getattr(snap, "trading_multiples", None)
            if mults is None:
                continue
            if getattr(mults, "pe", None) and mults.pe > 0:
                pes.append(mults.pe)
            if getattr(mults, "ev_ebitda", None) and mults.ev_ebitda > 0:
                evs.append(mults.ev_ebitda)
            if getattr(mults, "pb", None) and mults.pb > 0:
                pbs.append(mults.pb)
            if getattr(mults, "pfcf", None) and mults.pfcf > 0:
                pfcfs.append(mults.pfcf)
            if getattr(mults, "ev_sales", None) and mults.ev_sales > 0:
                ev_sales.append(mults.ev_sales)

        return {
            "target_pe":        safe_median(pes),
            "target_ev_ebitda": safe_median(evs),
            "target_pb":        safe_median(pbs),
            "target_pfcf":      safe_median(pfcfs),
            "target_ev_sales":  safe_median(ev_sales),
            "peer_count":       len(peer_snapshots),
        }
