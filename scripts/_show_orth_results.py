import json, pandas as pd

with open('reports/mover_discovery_v3/v3_orthogonal_direction_results.json') as f:
    r = json.load(f)

def show(label, s):
    if not s or not s.get('n'): return
    conc = (s.get('concentration') or {}).get('lift')
    print(f"  {label:35s}: dir={s['dir_acc']:.3f}  ge2={s['ge2_rate']:.3f}  "
          f"ge3={s.get('ge3_rate','NA')}  n={s['n']}  lift={conc}")

print("=== BASELINES OOS ===")
for d in ['UP', 'DOWN']:
    for m in ['V3_20','V3_Top5','V3_Top6','Random_5','Random_6']:
        show(f"{m} {d}", r['baselines'][d]['OOS'][m])

print("\n=== TRACK A (SECTOR) OOS ===")
for d in ['UP','DOWN']:
    for m in ['A1_Top5','A1_Top6','A1_Low_Top5',
              'A1_SECTOR_SUPPORTS_STOCK','A1_SECTOR_NEUTRAL','A1_SECTOR_CONTRADICTS_STOCK']:
        s = r['track_a_sector'].get(d,{}).get('OOS',{}).get(m,{})
        show(f"{m} {d}", s)

print("\n=== TRACK A TRAIN/VAL (A1_Top5 UP only) ===")
for sp in ['TRAIN','VAL','OOS']:
    s = r['track_a_sector'].get('UP',{}).get(sp,{}).get('A1_Top5',{})
    show(f"A1_Top5 UP {sp}", s)

print("\n=== TRACK D (GAP) OOS ===")
for d in ['UP','DOWN']:
    for m in ['D1_Top5','D1_Top6','D1_Low_Top5','D1_GAP_UP','D1_NO_GAP','D1_GAP_DOWN']:
        s = r['track_d_gap'].get(d,{}).get('OOS',{}).get(m,{})
        show(f"{m} {d}", s)

print("\n=== TRACK D TRAIN/VAL (D1_Top5 UP) ===")
for sp in ['TRAIN','VAL','OOS']:
    s = r['track_d_gap'].get('UP',{}).get(sp,{}).get('D1_Top5',{})
    show(f"D1_Top5 UP {sp}", s)

print("\n=== TRACK F (INVERSE KN) OOS ===")
print("TRAIN hypothesis:", r['track_f_inv_kn'].get('_train_hypothesis'))
for d in ['UP','DOWN']:
    for m in ['F1_High_Top5','F1_High_Top6','F1_Low_Top5','F1_Low_Top6','F1_InvKn_Top5','F1_InvKn_Top6']:
        s = r['track_f_inv_kn'].get(d,{}).get('OOS',{}).get(m,{})
        show(f"{m} {d}", s)

print("\n=== TRACK F TRAIN/VAL (F1_Low_Top5 UP) ===")
for sp in ['TRAIN','VAL','OOS']:
    s = r['track_f_inv_kn'].get('UP',{}).get(sp,{}).get('F1_Low_Top5',{})
    show(f"F1_Low_Top5 UP {sp}", s)

print("\n=== TRACK G (COMBINATION) OOS ===")
for d in ['UP','DOWN']:
    for m in ['G1_V3_Sector_Top5','G1_V3_Sector_Top6',
              'G2_V3_InvKn_Top5','G2_V3_InvKn_Top6',
              'G3_V3_Sect_InvKn_Top5','G3_V3_Sect_InvKn_Top6',
              'G4_V3_Gap_Top5','G4_V3_Gap_Top6']:
        s = r['track_g_combination'].get(d,{}).get('OOS',{}).get(m,{})
        show(f"{m} {d}", s)

print("\n=== ANSWERS ===")
for k, v in r['answers'].items():
    print(f"  {k}: {v}")
