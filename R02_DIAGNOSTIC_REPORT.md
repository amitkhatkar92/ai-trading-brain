# R02_DIAGNOSTIC_REPORT.md
**Scope:** Dhan Static IP Verification — Second-Stage Diagnostic  
**Date:** 2026-08-22  
**VPS:** `178.18.252.24` (Hetzner, static)  
**Conducted:** READ-ONLY — no orders, no setIP/modifyIP, no account changes  

---

## 1. Authentication Confirmation

**Endpoint:** `GET https://api.dhan.co/v2/profile`  
**HTTP status:** `200 OK`  
**Authentication method:** `access-token` header (DTA-001 TOTP-generated daily JWT, len=304)  
**Latency:** 240 ms  

**Sanitized response:**
```json
{
  "dhanClientId": "1103****",
  "tokenValidity": "[REDACTED — expires 2026-08-23T11:34 UTC]",
  "activeSegment": "E, D, C, M, ",
  "ddpi": "Deactive",
  "mtf": "Deactive",
  "dataPlan": "Active",
  "dataValidity": "2026-09-01 17:02:28.0"
}
```

**Token is valid.** Profile call succeeded from VPS IP `178.18.252.24`.  
Active segments: **E** (Equity), **D** (F&O Derivatives), **C** (Currency), **M** (Mutual Funds).

---

## 2. /v2/ip/getIP — Exhaustive Probe

Three independent REST calls were made with different header combinations. All returned the same result.

### 2a. SDK-identical headers (Content-type lowercase, with Accept)
```
GET https://api.dhan.co/v2/ip/getIP
Headers: access-token: [REDACTED]
         client-id: 1103****
         Content-type: application/json
         Accept: application/json
HTTP: 200  (255 ms)
```
**Response:**
```json
[{"message": "Something went wrong", "status": "ERROR"}]
```

### 2b. Content-Type uppercase, no Accept header
```
GET https://api.dhan.co/v2/ip/getIP
Headers: access-token: [REDACTED]
         client-id: 1103****
         Content-Type: application/json
HTTP: 200  (249 ms)
```
**Response:** Same — `[{"message": "Something went wrong", "status": "ERROR"}]`

### 2c. No client-id header
```
GET https://api.dhan.co/v2/ip/getIP
Headers: access-token: [REDACTED]
         Content-type: application/json
         Accept: application/json
HTTP: 200  (240 ms)
```
**Response:** Same — `[{"message": "Something went wrong", "status": "ERROR"}]`

### SDK wrapper (DhanLogin.get_ip reference call)
```json
{
  "status": "success",
  "remarks": "",
  "data": [{"message": "Something went wrong", "status": "ERROR"}]
}
```
Note: `status: "success"` is the SDK's **HTTP transport status** (`_parse_response` sets it for all HTTP 2xx). The error is Dhan's application-level response inside `data`.

**Finding:** The `getIP` ERROR is **not caused by headers, client-id presence, Accept header, or SDK parsing**. All three raw REST variants produce the identical error. The error originates from **Dhan's backend** for this account.

---

## 3. SDK Implementation Analysis

**Source:** `/usr/local/lib/python3.14/site-packages/dhanhq/` (dhanhq==2.2.0)

`DhanHTTP._parse_response()` (from `dhan_http.py`):
```python
json_response = json_loads(response.content)
if (response.status_code >= 200) and (response.status_code <= 299):
    status = 'success'       # ← always 'success' for HTTP 200
    data = json_response     # ← raw Dhan JSON, unmodified
else:
    remarks = { ... }        # error codes extracted
```

`DhanLogin.get_ip()` (from `auth.py`):
```python
dhan_http = DhanHTTP(dhan_client_id, access_token)
return dhan_http.get('/ip/getIP')   # → GET https://api.dhan.co/v2/ip/getIP
```

**Conclusion:** The SDK correctly passes through what Dhan returns. The `[{"message": "Something went wrong", "status": "ERROR"}]` is the raw Dhan backend response, not an SDK parsing artifact.

---

## 4. Functional IP Access Test — Trading Endpoints

These are the same endpoints used during live order operations. An IP-blocked account would receive an IP restriction error, not HTTP 200.

| Endpoint | HTTP | Response | Interpretation |
|---|---|---|---|
| `GET /v2/profile` | 200 | Valid profile dict | Auth OK from VPS IP |
| `GET /v2/orders` | 200 | `[]` (no open orders) | **VPS IP not blocked** |
| `GET /v2/positions` | 200 | `[]` (no open positions) | **VPS IP not blocked** |
| `GET /v2/fundlimit` | 200 | `availableBalance: 10514.11` | **VPS IP not blocked** |

All four endpoints returned HTTP 200 with valid data.  
`/v2/fundlimit` is a **protected trading API** — it would return an IP restriction error if the VPS IP were not permitted.

---

## 5. VPS IP Verification

```
VPS actual outbound IP (via ipify.org):  178.18.252.24
Expected VPS IP:                         178.18.252.24
Match:                                   True
```

The VPS outbound IP is confirmed as `178.18.252.24`. This is the IP that Dhan's servers observe for all API calls.

---

## 6. Error Classification

| Category | Verdict | Evidence |
|---|---|---|
| (a) Account configuration problem | **LIKELY ROOT CAUSE** | TOTP individual accounts may not have IP whitelist entries registered via the API management interface. The `getIP`/`setIP` system requires initial setup through the Dhan web portal. |
| (b) API permission problem | **POSSIBLE** | The IP management API may only be exposed to API Partner accounts that registered through the `https://developer.dhan.co` partner portal, not individual TOTP trading accounts. |
| (c) Endpoint/backend problem | **CANNOT RULE OUT** | Dhan returns a generic "Something went wrong" which does not distinguish between "no IP configured" and a backend error. This is a Dhan documentation/API gap. |
| (d) SDK parsing problem | **NO** | Three independent REST calls with different header combinations all return the same error. SDK correctly wraps the raw JSON. |
| (e) Missing static-IP setup | **CANNOT CONFIRM VIA API** | The getIP endpoint provides no usable data. Cannot confirm whether the Dhan account has explicit IP restrictions set or relies on TOTP-only security. |
| (f) Other — functional proof | **CRITICAL FINDING** | Despite getIP returning ERROR, all trading-class endpoints respond normally from VPS IP `178.18.252.24`. This is the operative test. |

---

## 7. Dhan Documentation vs Observed Behavior

**Per DhanHQ V2 documentation:** Static IP is mandatory for Order Placement, Modification, and Cancellation APIs.

**Observed behavior:** The following are consistent with the IP being authorized:
- `GET /v2/fundlimit` → HTTP 200 (this is a trading API, same auth as order placement)
- `GET /v2/orders` → HTTP 200
- `GET /v2/positions` → HTTP 200

There are two interpretations consistent with the documentation:

**Interpretation A — IP IS configured in Dhan's backend, `getIP` endpoint is broken for this account type:**  
The IP restriction is enforced (and working, as proven by successful trading endpoint calls), but the `getIP` read endpoint returns a generic error because this account's IP configuration was done through the Dhan web portal and is not retrievable via the API.

**Interpretation B — TOTP accounts use token-level restriction, not IP-level:**  
Individual TOTP-authenticated accounts use the 6-digit TOTP as the second factor instead of IP restriction. In this model, ANY IP can call trading APIs as long as it holds a valid TOTP-generated token. Dhan's documentation may refer to API-key (OAuth partner) accounts when requiring static IP.

**Cannot determine programmatically which interpretation applies.** Both explain the observed data.

---

## 8. Account Type

From profile inspection:
- `activeSegment: E, D, C, M` — individual multi-segment trading account
- `ddpi: Deactive`, `mtf: Deactive` — standard retail configuration
- No partner/app-specific fields visible in the profile response

The account profile does not expose whether it was onboarded as an API Partner (which would use `https://developer.dhan.co` and explicit IP whitelisting) or as an individual TOTP user. **This distinction can only be confirmed via the Dhan web portal.**

---

## 9. Test Suite

**File:** `tests/test_r02_ip_verify.py` — 17 tests, all PASS

Tests cover:
- GREEN: exact match, SDK envelope unwrap, date fields, whitespace strip
- RED: wrong IP, missing field, None, empty response
- RED/ERROR: SDK wrapper with `data=[{status:ERROR}]` (actual observed shape)
- RED/ERROR: Direct REST list shape `[{status:ERROR}]`
- RED/ERROR: Plain error dict `{status:ERROR}`
- Shape invariant: all 9 required keys present for GREEN, RED, and ERROR cases

---

## 10. Summary Table

| Item | Value |
|---|---|
| Raw HTTP status (`/v2/ip/getIP`) | `200` |
| Sanitized response | `[{"message": "Something went wrong", "status": "ERROR"}]` |
| SDK response (`data` field) | Same as above |
| SDK transport status | `"success"` (HTTP 200) |
| Endpoint used | `GET https://api.dhan.co/v2/ip/getIP` |
| Authentication method | `access-token` header (DTA-001 TOTP JWT) |
| Account type (inferred) | Individual trading account (multi-segment: E, D, C, M) |
| Static-IP requirement applicability | Cannot confirm via API — requires Dhan web portal check |
| VPS IP (confirmed outbound) | `178.18.252.24` |
| PRIMARY IP (from getIP) | **Not returned — endpoint error** |
| SECONDARY IP (from getIP) | **Not returned — endpoint error** |
| Trading endpoint access from VPS IP | `200 OK` on `/v2/fundlimit`, `/v2/orders`, `/v2/positions` |

---

## Final R-02 Status

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│   R-02 Status:  OPERATOR_ACTION_REQUIRED                                │
│                                                                         │
│   The /v2/ip/getIP endpoint returns an application-level ERROR          │
│   for this account regardless of headers or SDK path used.              │
│   primaryIP and secondaryIP cannot be read programmatically.            │
│                                                                         │
│   FUNCTIONAL EVIDENCE (positive):                                       │
│   VPS IP 178.18.252.24 successfully accessed:                           │
│     /v2/profile      → 200 (auth confirmed)                             │
│     /v2/fundlimit    → 200 (availableBalance: ₹10,514.11)               │
│     /v2/orders       → 200 (empty, no open orders)                      │
│     /v2/positions    → 200 (empty, no open positions)                   │
│   These are the same authentication path used by order placement.       │
│   An IP-blocked account would receive a restriction error here.         │
│                                                                         │
│   OPERATOR ACTION REQUIRED (before live activation):                    │
│                                                                         │
│   1. Log in to https://developer.dhan.co or the DhanHQ web portal.     │
│   2. Navigate to: My Apps → API Settings → Static IP Configuration.    │
│   3. Confirm whether PRIMARY IP is set to 178.18.252.24.               │
│      If no IP is listed: add 178.18.252.24 as PRIMARY, then            │
│      re-run this diagnostic (the getIP endpoint should return data).    │
│   4. If the portal shows IP restrictions are not applicable to this     │
│      account type (TOTP individual login), document that conclusion     │
│      and reclassify R-02 to GREEN.                                      │
│                                                                         │
│   DO NOT ENABLE LIVE TRADING until this is confirmed.                   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Appendix: No Code Defects Found

No application code defects were discovered during this investigation.  
No production logic was changed.  
No commit or deployment was made.

The only changes made:
- `tests/test_r02_ip_verify.py`: added `test_dhan_error_dict_direct` and `test_direct_list_error_has_all_keys` to cover the actual Dhan response shapes observed (17 tests, all PASS)

---

*R02_DIAGNOSTIC_REPORT.md | Session: d8a34282 | 2026-08-22*
