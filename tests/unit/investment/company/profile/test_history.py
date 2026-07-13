"""tests/unit/investment/company/profile/test_history.py"""
from __future__ import annotations

import pytest

from iios.investment.company.profile.corporate_events import CorporateEventStore
from iios.investment.company.profile.models import CorporateEvent, CorporateEventType
from iios.investment.company.profile.timeline import Timeline


class TestCorporateEventStore:
    def test_add_and_retrieve_all(self):
        store = CorporateEventStore()
        ev    = CorporateEvent.new(CorporateEventType.FOUNDING, "1973-05-08", "Founded")
        store.add(ev)
        assert len(store) == 1
        assert store.all()[0].event_type is CorporateEventType.FOUNDING

    def test_no_duplicate_by_event_id(self):
        store = CorporateEventStore()
        ev    = CorporateEvent.new(CorporateEventType.FOUNDING, "1973-05-08", "Founded")
        store.add(ev)
        store.add(ev)   # same event_id
        assert len(store) == 1

    def test_sorted_chronologically(self):
        store = CorporateEventStore()
        store.add(CorporateEvent.new(CorporateEventType.MILESTONE, "2020-01-01", "M1"))
        store.add(CorporateEvent.new(CorporateEventType.IPO,       "1977-01-01", "IPO"))
        store.add(CorporateEvent.new(CorporateEventType.FOUNDING,  "1973-05-08", "Founded"))
        dates = [e.date for e in store.all()]
        assert dates == sorted(dates)

    def test_remove(self):
        store = CorporateEventStore()
        ev    = CorporateEvent.new(CorporateEventType.FOUNDING, "1973-05-08", "Founded")
        store.add(ev)
        removed = store.remove(ev.event_id)
        assert removed is True
        assert len(store) == 0

    def test_by_type(self):
        store = CorporateEventStore()
        store.add(CorporateEvent.new(CorporateEventType.FOUNDING,    "1973-05-08", "F"))
        store.add(CorporateEvent.new(CorporateEventType.IPO,         "1977-01-01", "I"))
        store.add(CorporateEvent.new(CorporateEventType.ACQUISITION, "2020-01-01", "A"))
        acquisitions = store.by_type(CorporateEventType.ACQUISITION)
        assert len(acquisitions) == 1

    def test_between(self):
        store = CorporateEventStore()
        store.add(CorporateEvent.new(CorporateEventType.FOUNDING,    "1973-05-08", "F"))
        store.add(CorporateEvent.new(CorporateEventType.IPO,         "1977-01-01", "I"))
        store.add(CorporateEvent.new(CorporateEventType.ACQUISITION, "2020-06-01", "A"))
        between = store.between("1975-01-01", "2000-01-01")
        assert len(between) == 1
        assert between[0].event_type is CorporateEventType.IPO

    def test_founding_event(self):
        store = CorporateEventStore()
        store.add(CorporateEvent.new(CorporateEventType.FOUNDING, "1973-05-08", "Founded"))
        ev = store.founding_event()
        assert ev is not None
        assert ev.date == "1973-05-08"

    def test_ipo_event(self):
        store = CorporateEventStore()
        store.add(CorporateEvent.new(CorporateEventType.IPO, "1977-01-01", "IPO"))
        ev = store.ipo_event()
        assert ev is not None

    def test_has_merger_or_acquisition(self):
        store = CorporateEventStore()
        assert store.has_merger_or_acquisition() is False
        store.add(CorporateEvent.new(CorporateEventType.ACQUISITION, "2020-01-01", "Acq"))
        assert store.has_merger_or_acquisition() is True

    def test_by_year(self):
        store = CorporateEventStore()
        store.add(CorporateEvent.new(CorporateEventType.MILESTONE, "2020-01-01", "M"))
        store.add(CorporateEvent.new(CorporateEventType.MILESTONE, "2020-06-15", "M2"))
        by_year = store.by_year()
        assert 2020 in by_year
        assert len(by_year[2020]) == 2

    def test_latest_n(self):
        store = CorporateEventStore()
        for year in range(2010, 2016):
            store.add(CorporateEvent.new(CorporateEventType.MILESTONE,
                                         f"{year}-01-01", f"M{year}"))
        latest = store.latest(3)
        assert len(latest) == 3
        assert latest[0].date == "2015-01-01"


class TestTimeline:
    def test_add_and_retrieve(self):
        tl = Timeline()
        ev = tl.add(CorporateEventType.FOUNDING, "1973-05-08", "Founded")
        assert len(tl) == 1
        assert ev.event_type is CorporateEventType.FOUNDING

    def test_founding_year(self):
        tl = Timeline()
        tl.add(CorporateEventType.FOUNDING, "1973-05-08", "Founded")
        assert tl.founding_year() == 1973

    def test_ipo_year(self):
        tl = Timeline()
        tl.add(CorporateEventType.IPO, "1977-01-01", "Listed")
        assert tl.ipo_year() == 1977

    def test_age_years(self):
        tl = Timeline()
        tl.add(CorporateEventType.FOUNDING, "2000-01-01", "Founded")
        assert tl.age_years(2026) == 26

    def test_acquisitions(self):
        tl = Timeline()
        tl.add(CorporateEventType.ACQUISITION, "2021-06-01", "Acquired XYZ")
        tl.add(CorporateEventType.ACQUISITION, "2023-03-01", "Acquired ABC")
        assert len(tl.acquisitions()) == 2

    def test_spinoffs(self):
        tl = Timeline()
        tl.add(CorporateEventType.SPINOFF, "2019-01-01", "Spun off Jio")
        assert len(tl.spinoffs()) == 1

    def test_milestones(self):
        tl = Timeline()
        tl.add(CorporateEventType.MILESTONE, "2015-01-01", "Jio launched")
        assert len(tl.milestones()) == 1

    def test_name_changes(self):
        tl = Timeline()
        tl.add(CorporateEventType.NAME_CHANGE, "1990-01-01", "Renamed from X to Y")
        assert len(tl.name_changes()) == 1

    def test_summary_nonempty(self):
        tl = Timeline()
        tl.add(CorporateEventType.FOUNDING, "1973-05-08", "Founded")
        tl.add(CorporateEventType.IPO,      "1977-01-01", "Listed")
        summary = tl.summary()
        assert len(summary) > 0
        assert "1973" in summary
