"""One-off script to fix T138 in test_rc.py"""
import sys

path = r"C:\Users\UCIC\OneDrive\Desktop\ai_trading_brain\test_rc.py"
data = open(path, "rb").read()

old_block = (
    b"    # All stages disabled (except always-run report)\r\n"
    b"    rc_all_off = ResearchCoordinator(config=RCConfig(\r\n"
    b"        study_plan_enabled=False, replay_enabled=False, validation_enabled=False,\r\n"
    b"        evidence_integration_enabled=False, knowledge_integration_enabled=False,\r\n"
    b"        synthesis_enabled=False, repository_update_enabled=False, dry_run=True,\r\n"
    b"    ))\r\n"
    b"    run_all_off = rc_all_off.run_research(_make_mock_plan())\r\n"
    b"    skipped_count = sum(1 for s in run_all_off.stages if s.state == ResearchStageState.SKIPPED)\r\n"
    b"    r.ok(\"T138 all disabled \xc3\xa2\xe2\x80\xa0\xe2\x80\x99 7 SKIPPED\", skipped_count == 7)"
)
new_block = (
    b"    # All stages disabled (except always-run report + evolution)\r\n"
    b"    rc_all_off = ResearchCoordinator(config=RCConfig(\r\n"
    b"        study_plan_enabled=False, replay_enabled=False, validation_enabled=False,\r\n"
    b"        methodology_audit_enabled=False,\r\n"
    b"        evidence_integration_enabled=False, knowledge_integration_enabled=False,\r\n"
    b"        synthesis_enabled=False, repository_update_enabled=False,\r\n"
    b"        scientific_evolution_enabled=False, dry_run=True,\r\n"
    b"    ))\r\n"
    b"    run_all_off = rc_all_off.run_research(_make_mock_plan())\r\n"
    b"    skipped_count = sum(1 for s in run_all_off.stages if s.state == ResearchStageState.SKIPPED)\r\n"
    b"    r.ok(\"T138 all disabled \xc3\xa2\xe2\x80\xa0\xe2\x80\x99 9 SKIPPED\", skipped_count == 9)"
)

if old_block in data:
    data = data.replace(old_block, new_block, 1)
    open(path, "wb").write(data)
    print("REPLACED")
else:
    print("NOT FOUND")
    # Debug: find T138 location
    idx = data.find(b"T138 all disabled")
    if idx >= 0:
        print("T138 found at", idx)
        print("Context:", data[idx-500:idx+100])
    else:
        print("T138 all disabled NOT in file at all")
        idx2 = data.find(b"T138")
        print("T138 raw at:", idx2)
