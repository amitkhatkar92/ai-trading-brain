# SHARED UTILITIES FRAMEWORK
## Investment Intelligence Operating System (IIOS)

**Document Code:** IIOS-SUT-FWK-001
**Version:** 1.0.0
**Status:** Active
**Classification:** Architecture Reference — Engineering Specification
**Scope:** All IIOS engines, agents, workflows, services, and infrastructure

---

## Document Purpose

This document defines the complete Shared Utilities Framework for the Investment
Intelligence Operating System (IIOS). It specifies the reusable services, helper
libraries, common infrastructure components, cross-cutting capabilities, and
engineering support modules that can be used by every subsystem of the platform.

This is an engineering architecture specification. It defines structure, behaviour,
organization, policies, and governance. It does not define source code, implementation
language, API contracts, or database schemas.

---

## Scope

This framework applies to:
- All 18 IIOS engines (GlobalIntelligence through ControlTower).
- All AI agents operating within the Debate and Decision engine.
- All data feed integrations (primary and fallback).
- All broker integrations (paper and live).
- All infrastructure components (containers, volumes, networking).
- All logging, monitoring, and observability components.
- All configuration management components.
- All testing, development, and operational tooling.

---

## Table of Contents

- Part I: Shared Utilities Philosophy
- Part II: Utility Taxonomy (57 categories)
- Part III: Framework Architecture (18 components)
- Part IV: Utility Organization (10-layer hierarchy)
- Part V: Lifecycle Management (12 stages)
- Part VI: Dependency Framework (12 domains)
- Part VII: Quality Framework (12 dimensions)
- Part VIII: Utility Governance
- Part IX: Engineering Constitution (110 rules)
- Part X: Readiness Checklist (8 domains)
- Supplement A: Utility Catalog Reference
- Supplement B: Dependency Matrix
- Supplement C: Lifecycle Reference
- Supplement D: Version Compatibility Guide
- Supplement E: Naming Reference
- Supplement F: Engineering Decision Records
- Supplement G: Common Anti-Patterns
- Supplement H: Operational Runbook
- Supplement I: Comprehensive Glossary

---

# PART I — SHARED UTILITIES PHILOSOPHY

## 1.1 Purpose of Shared Utilities

Shared utilities are the foundational building blocks that every component of a
complex system needs but none should implement independently. They represent the
distilled engineering knowledge of how to solve common problems well — once — and
make those solutions universally available throughout the platform.

In IIOS, shared utilities serve three essential purposes:

**Elimination of duplication:** Without shared utilities, every engine would
implement its own date formatting, its own UUID generation, its own retry logic,
its own configuration loading. Across 18 engines, this creates 18 different versions
of the same logic — each with its own bugs, edge cases, and assumptions. Shared
utilities eliminate this multiplication of effort and error surface.

**Enforcement of platform standards:** A shared utility is not just convenient —
it is authoritative. When the platform defines that timestamps are always in ISO 8601
UTC, the shared Date-Time Utility enforces this. No engine can accidentally use a
different format because the shared utility makes the correct format the easiest path.

**Concentration of quality investment:** Engineering effort invested in a shared
utility improves every component that uses it. A bug fixed in the shared retry utility
is fixed for all 18 engines simultaneously. A performance improvement in the shared
serialization utility benefits every workflow. This concentration of quality investment
makes the entire platform stronger with less total effort.

---

## 1.2 Benefits of Reusability

Reusability is the defining characteristic of shared utilities. A utility is shared
precisely because its solution to a problem is general enough to apply across diverse
contexts. The benefits of achieving genuine reusability are substantial:

**Reduced total engineering cost:** Writing a utility once and using it 50 times
costs far less than writing 50 similar but distinct implementations.

**Consistent behavior across the platform:** When two components use the same
utility, they behave consistently. Inconsistencies are one of the hardest categories
of bugs to find — a date parsed correctly in one engine and incorrectly in another
creates subtle discrepancies that are difficult to trace.

**Faster feature development:** When developers can rely on a rich library of
high-quality shared utilities, new features are built by composing existing capabilities
rather than reimplementing them. Development velocity increases as the utility library
matures.

**Lower defect density:** A shared utility that has been used extensively across
the platform has been exposed to many diverse inputs and scenarios. Its defects have
been found and fixed. A newly written local implementation has none of this exposure.

**Simplified maintenance:** When a utility needs to change (security fix, performance
improvement, new standard), the change is made once in the shared utility and
benefits the entire platform immediately.

---

## 1.3 Single Responsibility

Every shared utility must serve exactly one clearly defined purpose. The single
responsibility principle applied to shared utilities means that each utility does
one thing and does it well. It is not a general-purpose toolkit but a focused,
expert implementation of a specific capability.

**Why single responsibility matters for shared utilities:**
- A utility that tries to do too many things is harder to understand, test, and
  maintain.
- Combining responsibilities in a utility creates coupling between otherwise
  unrelated concerns — a change to one responsibility can break another.
- A focused utility with a single purpose has a clear, stable interface that rarely
  needs to change.
- Single-responsibility utilities compose better — complex behaviors can be built
  by combining simple, focused utilities.

**Signals that a utility has too many responsibilities:**
- The utility's name requires "and" (e.g., "DateTimeAndTimezoneAndFormattingUtility").
- The utility's interface has methods that serve different user types for different
  purposes.
- Two different components use the utility but only use different parts of it.

**The split rule:** If a utility naturally splits into two non-overlapping areas of
responsibility, it should be split into two utilities.

---

## 1.4 Loose Coupling

Shared utilities must be loosely coupled from the components that use them. A component
that uses a shared utility depends only on the utility's interface (what it does) —
not on its internal implementation (how it does it).

**Coupling dimensions to minimize:**
- **Data coupling:** The utility and its caller share only the minimum necessary
  data through its interface.
- **Control coupling:** The utility does not expose flags that tell it which of
  several behaviors to perform (this is a sign the utility has multiple responsibilities).
- **Common coupling:** The utility does not depend on global shared state that its
  callers also modify.
- **Content coupling:** No component reaches inside a utility's implementation to
  access or modify its internal state.

**Implications for IIOS:**
- Utilities do not depend on IIOS-specific configuration or state. They are self-contained.
- Utilities accept their inputs through their interface and produce outputs through
  their interface. They do not read global state.
- Utilities can be tested in complete isolation from the rest of IIOS.
- A utility can be replaced with an improved implementation without changing any
  component that uses it (assuming the interface is preserved).

---

## 1.5 High Cohesion

While loose coupling describes how a utility relates to the outside world, cohesion
describes the internal organization of the utility itself. A highly cohesive utility
has all its capabilities serving the same purpose. Everything inside a high-cohesion
utility belongs there.

**High cohesion in practice:**
- A Date-Time Utility contains all date and time operations: parsing, formatting,
  arithmetic, comparison, conversion. All of these serve the same purpose.
- A Statistical Utility contains statistical functions: mean, median, standard
  deviation, percentiles, correlation. All statistical operations belong together.
- A Security Utility contains security operations: hashing, encryption, sanitization,
  token validation. All security operations belong together.

**Low cohesion warning signs:**
- Functions inside a utility that have no logical relationship to each other.
- A utility that is the "everything else" place for functions that don't fit elsewhere.
- A utility where different functions are used by completely different consumers
  for completely different purposes.

---

## 1.6 Platform-Wide Consistency

Shared utilities create consistency across the IIOS platform. Consistency is not
merely a stylistic preference — it is an engineering requirement that reduces
cognitive overhead, decreases defect rates, and enables platform-wide improvements.

**Consistency dimensions achieved through shared utilities:**

**Behavioral consistency:** The same input always produces the same output across
all components. When every engine uses the same UUID utility, all UUIDs follow the
same format and uniqueness guarantees.

**Error handling consistency:** When utilities handle errors consistently, the entire
platform's error handling becomes consistent. The same exception types, the same
error message format, the same escalation patterns.

**Format consistency:** Timestamps, identifiers, file names, log messages — all
follow the same format because they all pass through the same utilities.

**Performance consistency:** Operations with known performance characteristics
behave consistently. A component that calls the shared compression utility knows
its latency profile.

---

## 1.7 Standardization

Standardization is the deliberate decision to use a single approach for a given
problem across the entire platform. Shared utilities are the primary mechanism for
enforcing standards.

**Standards enforced by shared utilities in IIOS:**
- All timestamps: ISO 8601 UTC (enforced by Date-Time Utility).
- All identifiers: UUID v4 (enforced by UUID Utility).
- All configuration files: YAML format (enforced by YAML Utility).
- All compressed archives: gzip format (enforced by Compression Utility).
- All file hashes: SHA-256 (enforced by Hashing Utility).
- All log messages: structured format with defined fields (enforced by Logging
  Helper Utility).
- All financial values: decimal with defined precision (enforced by Financial
  Utility).

**Standardization governance:** Each standard has an owner (Architecture Council or
designated component owner) who is responsible for maintaining and evolving it.
Deviations from platform standards require Architecture Council approval.

---

## 1.8 Engineering Productivity

Shared utilities directly accelerate engineering productivity. When a developer
building a new engine can reach for a rich, high-quality utility library, they
spend their time on the unique, valuable problems their engine solves — not on
re-implementing date parsing or retry logic.

**Productivity impact areas:**
- **Faster initial development:** The scaffolding of common capabilities is already
  done. New components start from a higher baseline.
- **Faster debugging:** When a problem is traced to a shared utility, it is debugged
  once and fixed everywhere.
- **Easier code review:** Reviewers familiar with the shared utility library can
  quickly understand code that uses it.
- **Easier onboarding:** New team members learn the shared utilities once and
  immediately understand how all components handle common concerns.
- **Less cognitive load:** A developer who knows the shared utilities knows most of
  the platform's boilerplate behavior without reading each component.

---

## 1.9 Maintainability

Maintainability is the ease with which a system can be changed. Shared utilities
improve platform maintainability in two ways: they reduce the total amount of code
that must be maintained, and they concentrate maintenance effort in high-value places.

**Maintainability properties of shared utilities:**
- A well-designed utility has a stable interface that rarely needs to change.
- Internal implementation improvements can be made without affecting callers.
- Deprecation of utilities is managed centrally (one deprecation affects all callers
  simultaneously — which is a responsibility, not just a benefit).
- Documentation maintained once for a utility is effective for all its users.

**Maintainability principles:**
- Shared utilities must be simple enough that any team member can understand them.
- Shared utilities must have comprehensive tests — they are too important to leave
  under-tested.
- Shared utilities must have clear ownership — if nobody owns a utility, nobody
  maintains it.

---

## 1.10 Extensibility

Shared utilities must be designed for extensibility. The platform will evolve, and
utilities must be able to grow with it without breaking existing consumers.

**Extensibility mechanisms:**
- **Additive changes:** New utility functions can always be added to an existing
  utility without breaking existing callers.
- **Configuration over modification:** Behavior variations are achieved through
  configuration or parameters rather than modifications to the utility itself.
- **Composability:** New capabilities can be built by combining existing utilities.
- **Plugin interfaces:** Some utilities define extension points that allow new
  implementations to be registered without modifying the core utility.

**Extensibility limits:**
- Interfaces (the way callers invoke a utility) must not change incompatibly.
- If an interface must change, it follows the deprecation lifecycle (old interface
  maintained during transition, new interface introduced, old interface retired).

---

## 1.11 Testability

Shared utilities must be designed for testing. Because they are used throughout
the platform, a defect in a utility has platform-wide impact. Every utility must
have comprehensive, fast, deterministic tests.

**Testability design requirements:**
- Pure functions (same input always produces same output) wherever possible.
- No hidden dependencies on global state, file system, or network.
- Test-specific configuration options (e.g., injectable clock for date-time testing).
- Deterministic behavior for any inputs within the defined contract.
- Edge cases explicitly handled and tested (null inputs, empty collections, extreme
  values, boundary conditions).

**Testing standards for shared utilities:**
- Unit test coverage: > 95% for all shared utilities.
- Edge case tests: every utility must have tests for empty, null, boundary, and
  overflow inputs.
- Property-based tests where applicable (random input generators to find edge cases
  not anticipated by the developer).
- Performance tests: utilities with performance requirements have benchmark tests.
- Thread safety tests: any utility intended for concurrent use is tested under
  concurrent load.

---

## 1.12 Dependency Minimization

Shared utilities must minimize their own dependencies. A utility that has many
dependencies creates a web of coupling that undermines the platform's modularity.
The ideal shared utility has no external dependencies — it implements its functionality
using only the platform's own standard types and other foundational shared utilities.

**Dependency minimization rules:**
- Utilities in the Core Layer have zero external dependencies.
- Utilities in the Platform Layer may depend only on Core Layer utilities.
- Utilities in higher layers may depend on lower layers but not on the same or
  higher layers (directed dependency graph, no cycles).
- External library dependencies must be approved by the Architecture Council.
- Any utility that introduces a new external dependency must justify it: why can
  no existing utility provide this capability?

**Dependency budget concept:** Each utility is allocated a "dependency budget" —
a maximum number of direct dependencies. Utilities that exceed their budget require
Architecture Council review.

---

## 1.13 Cross-Platform Compatibility

Shared utilities must operate correctly in all environments where IIOS runs:
development workstations (Windows), CI/CD pipelines (Linux), and production
VPS servers (Linux/Docker).

**Compatibility requirements:**
- File path handling: utilities must use the platform's path abstraction, not
  hardcoded separators.
- File encoding: all text file operations default to UTF-8.
- Line endings: utilities produce platform-appropriate line endings but can be
  configured to produce specific formats.
- Time zone handling: all timestamps are UTC internally; conversion to local time
  is explicit and controlled.
- Integer sizes: utilities avoid assumptions about integer size that differ across
  platforms.
- Character encoding: string utilities correctly handle multi-byte characters.

---

## 1.14 Version Independence

Shared utilities must be version-independent from the components that use them.
A component must be able to use a shared utility without being tightly coupled to
a specific version of it.

**Version independence principles:**
- Shared utility interfaces are versioned explicitly.
- Multiple versions of a utility interface can coexist during a migration period.
- Callers declare the minimum utility version they require, not an exact version.
- A utility version upgrade is transparent to callers unless it changes the interface.
- The Version Manager tracks compatibility between utility versions and component
  declarations.

---

## 1.15 Future-Proof Engineering

Shared utilities must be designed with the expectation that the platform will grow,
requirements will change, and new patterns will emerge. Future-proofing is not about
predicting the future — it is about designing utilities that can evolve without
requiring simultaneous changes to every consumer.

**Future-proofing patterns:**
- **Interface stability:** Define the utility's contract precisely and keep it stable.
  Internal implementation can change; the interface should rarely need to change.
- **Versioning from day one:** Every utility is versioned from the first release.
  There is no "pre-versioning" period.
- **Deprecation planning:** Every utility eventually needs to be retired or replaced.
  The deprecation lifecycle is defined before the utility is first released, not
  when retirement becomes urgent.
- **Documentation of design decisions:** Recording why a utility was designed a
  certain way prevents future engineers from unknowingly reversing good decisions.
- **Extension points:** Utilities that are likely to need extension expose explicit
  extension interfaces rather than requiring modification.

---

*End of Part I*

---

# PART II — UTILITY TAXONOMY

## 2.1 Taxonomy Overview

The IIOS Shared Utility Taxonomy defines 57 utility categories organized into
10 functional layers. Each category represents a distinct domain of shared
capability. Together they cover the full range of common engineering concerns
that arise throughout the IIOS platform.

---

## 2.2 Layer 1 — Core Utilities

### Category 1 — Core Utilities (CORE)

**Namespace:** CORE
**Layer:** Core
**Description:** The foundational utilities upon which all other utilities build.
Core utilities are the most primitive building blocks: no other IIOS utility can
serve the role they serve. They have zero dependencies outside the language runtime.

**Covered capabilities:**
- Value presence checking (null, empty, undefined checks across all types).
- Basic type coercion and conversion (number to string, string to number).
- Identity comparisons (deep equality, shallow equality).
- Contract enforcement (precondition checking, postcondition checking).
- Result types (representing the outcome of an operation that may succeed or fail).
- Optional types (representing the presence or absence of a value).
- Basic error types (foundational error classification for the entire platform).

**Engineering notes:** Core utilities are the most heavily tested utilities in the
platform. Their defects have the widest possible impact. They are owned by the
Architecture Council directly and require unanimous vote to change.

---

### Category 2 — Configuration Utilities (CFG)

**Namespace:** CFG
**Layer:** Core
**Description:** Utilities for loading, validating, accessing, and watching
configuration values. Configuration utilities provide the bridge between the raw
configuration data (YAML files, environment variables, secrets) and the type-safe,
validated configuration objects that IIOS components use.

**Covered capabilities:**
- Configuration file loading (YAML, JSON, TOML formats).
- Configuration schema validation (required keys, type checking, range validation).
- Environment-specific configuration overlay (production overrides development defaults).
- Secret value injection (replacing placeholder values with actual secrets).
- Configuration change watching (detecting file modifications at runtime).
- Configuration access with type safety (read a value as a string, number, list).
- Configuration templating (references between configuration values).
- Default value resolution (what to use when a value is not explicitly configured).

**IIOS-specific requirements:** The Configuration Utility must integrate with the
Configuration Framework (IIOS-CFG-FWK-001). It enforces the 12-level configuration
hierarchy and the inheritance model defined in that framework.

---

### Category 3 — Environment Utilities (ENV)

**Namespace:** ENV
**Layer:** Core
**Description:** Utilities for detecting, reading, and reasoning about the runtime
environment.

**Covered capabilities:**
- Environment detection (development, staging, paper, production).
- Environment variable reading with type coercion and default values.
- Environment variable validation (required variables checked at startup).
- Runtime property detection (operating system, Python version, available memory).
- Deployment context detection (local, Docker container, VPS, CI/CD).
- Environment snapshot creation (full environment state for diagnostic purposes).
- Environment difference detection (compare current environment to reference).

---

## 2.3 Layer 2 — File and Storage Utilities

### Category 4 — File Utilities (FILE)

**Namespace:** FILE
**Layer:** Platform
**Description:** Utilities for all file operations: reading, writing, copying, moving,
deleting, and querying files.

**Covered capabilities:**
- Atomic file writes (write to temp file, then rename — prevents partial writes).
- File reading with encoding detection and explicit encoding specification.
- File existence, size, and modification time queries.
- File locking (preventing concurrent modifications).
- Safe file deletion (with recoverability where required).
- Binary and text file handling.
- File integrity verification (checksum computation and verification).
- Large file streaming (reading files too large to fit in memory).

**Engineering notes:** All file writes in IIOS that involve critical data (positions,
audit records, configuration) must use the atomic write capability. A non-atomic
write that leaves a partial file is treated as a storage exception.

---

### Category 5 — Directory Utilities (DIR)

**Namespace:** DIR
**Layer:** Platform
**Description:** Utilities for directory creation, traversal, listing, and management.

**Covered capabilities:**
- Recursive directory creation with error handling.
- Directory listing with filtering (by extension, by modification date, by size).
- Directory tree traversal (depth-first, breadth-first).
- Temporary directory creation and cleanup.
- Directory size computation.
- Directory comparison (find files present in one but not another).
- Directory watching (detecting new or modified files).
- Directory permission management.

---

### Category 6 — Path Utilities (PATH)

**Namespace:** PATH
**Layer:** Platform
**Description:** Utilities for path construction, normalization, and decomposition.

**Covered capabilities:**
- Platform-independent path construction (handles Windows/Linux differences).
- Path normalization (canonical form, resolving . and ..).
- Path decomposition (directory, stem, extension components).
- Relative to absolute path resolution.
- Path existence and type checking (is it a file? a directory? a symlink?).
- Path sanitization (removing dangerous components, preventing traversal attacks).
- Workspace-relative path resolution (all IIOS paths relative to the workspace root).

**Security note:** Path sanitization is a security utility as well as a convenience.
Any path constructed from user-provided or external data must be sanitized to prevent
path traversal attacks.

---

### Category 7 — Serialization Utilities (SER)

**Namespace:** SER
**Layer:** Platform
**Description:** Utilities for converting in-memory objects to serialized formats
for storage or transmission.

**Covered capabilities:**
- Object-to-format serialization (to JSON, YAML, CSV, binary).
- Serialization schema management (which fields to include, field naming conventions).
- Serialization versioning (including schema version in the output).
- Circular reference detection and handling.
- Large object serialization (streaming for objects too large for memory).
- Custom serializer registration (for IIOS-specific types).
- Serialization performance profiling.

---

### Category 8 — Deserialization Utilities (DESER)

**Namespace:** DESER
**Layer:** Platform
**Description:** Utilities for converting serialized formats back to in-memory objects.

**Covered capabilities:**
- Format-to-object deserialization (from JSON, YAML, CSV, binary).
- Schema validation during deserialization.
- Type coercion during deserialization (string "42" to integer 42).
- Missing field handling (defaults, errors).
- Unknown field handling (ignore, error, or capture).
- Version migration (deserializing old-format data into current schema).
- Deserialization error reporting with field-level diagnostics.

---

### Category 9 — JSON Utilities (JSON)

**Namespace:** JSON
**Layer:** Platform
**Description:** JSON-specific utilities beyond basic serialization.

**Covered capabilities:**
- JSON parsing with line/column error reporting.
- JSON path queries (read a deeply nested field without full deserialization).
- JSON merging (combine two JSON objects).
- JSON diff (compute the differences between two JSON objects).
- JSON schema validation (validate against a JSON Schema).
- JSON pretty printing and minification.
- JSON comment stripping (JSONC format support).
- Large JSON streaming (process large JSON files without full loading).

---

### Category 10 — YAML Utilities (YAML)

**Namespace:** YAML
**Layer:** Platform
**Description:** YAML-specific utilities.

**Covered capabilities:**
- YAML parsing with error location reporting.
- YAML anchors and aliases handling.
- YAML multi-document support.
- YAML to JSON conversion.
- YAML schema validation.
- YAML comments preservation (for round-trip editing).
- YAML formatting standards enforcement (2-space indentation, consistent quoting).

---

### Category 11 — XML Utilities (XML)

**Namespace:** XML
**Layer:** Platform
**Description:** XML processing utilities.

**Covered capabilities:**
- XML parsing (DOM and streaming SAX approaches).
- XPath queries.
- XML validation (DTD and XSD schema validation).
- XML to JSON conversion.
- XML generation with formatting.
- Namespace handling.
- XML security (XXE prevention, entity expansion limits).

**Security note:** XML parsing is a security-sensitive operation. XXE (XML External
Entity) injection is a known attack vector. The XML Utility prevents XXE by default.

---

### Category 12 — CSV Utilities (CSV)

**Namespace:** CSV
**Layer:** Platform
**Description:** CSV file handling utilities.

**Covered capabilities:**
- CSV parsing with configurable delimiter, quoting, and encoding.
- CSV validation (required columns, data type checking).
- CSV generation from collections.
- Large CSV streaming (row-by-row processing for large files).
- CSV to JSON conversion.
- CSV column mapping and renaming.
- CSV merge and split operations.
- Handling of malformed rows.

---

### Category 13 — Compression Utilities (COMP)

**Namespace:** COMP
**Layer:** Platform
**Description:** Data and file compression utilities.

**Covered capabilities:**
- File compression and decompression (gzip, bzip2, lz4, zstd formats).
- In-memory data compression and decompression.
- Archive creation and extraction (tar.gz, zip formats).
- Compression ratio estimation.
- Streaming compression (compress data as it is produced).
- Integrity verification after decompression.
- Compression level configuration (speed vs ratio trade-off).

---

## 2.4 Layer 3 — Security Utilities

### Category 14 — Encryption Utilities (ENC)

**Namespace:** ENC
**Layer:** Security
**Description:** Encryption and decryption utilities for data protection.

**Covered capabilities:**
- Symmetric encryption (AES-256-GCM for data at rest).
- Asymmetric encryption (RSA for key exchange).
- Key derivation from passwords (PBKDF2, Argon2).
- Key management integration (secrets manager lookup).
- Encrypted file writing and reading.
- In-memory encryption for sensitive runtime values.
- Encryption algorithm abstraction (can swap algorithms without changing callers).

**Security note:** Encryption keys are never embedded in code or configuration
files. They are always retrieved from the secrets management system at runtime.

---

### Category 15 — Hashing Utilities (HASH)

**Namespace:** HASH
**Layer:** Security
**Description:** Cryptographic and non-cryptographic hashing utilities.

**Covered capabilities:**
- Cryptographic hash computation (SHA-256, SHA-512 for security use cases).
- Hash chain construction and verification (used in audit records).
- Password hashing (bcrypt, Argon2 — slow hashes for credential storage).
- File content hashing (integrity verification).
- Fast non-cryptographic hashing (for hash tables, bloom filters).
- HMAC computation (hash-based message authentication codes).
- Hash comparison (constant-time comparison to prevent timing attacks).

**Security note:** The hash comparison function uses constant-time comparison.
Variable-time comparison (standard equality) of hash values is vulnerable to timing
attacks.

---

### Category 16 — Validation Utilities (VAL)

**Namespace:** VAL
**Layer:** Security (also used in Business layer)
**Description:** Data validation utilities for enforcing data quality at system boundaries.

**Covered capabilities:**
- Schema validation (validate data against a defined schema).
- Range validation (numeric values within bounds).
- Format validation (email addresses, dates, identifiers, phone numbers).
- Required field validation.
- Enumeration validation (value is in a defined set).
- Cross-field validation (field A's value constrains field B's valid values).
- Validation error collection (all errors found, not just the first).
- Validation result types (structured validation results, not exceptions).

**Engineering principle:** Validation runs at system boundaries — inputs from
external sources (configuration files, data feeds, broker responses, user input)
are validated before entering the system. Internal data produced by IIOS engines
is trusted (not re-validated).

---

### Category 17 — Security Utilities (SEC)

**Namespace:** SEC
**Layer:** Security
**Description:** Security-specific utilities beyond encryption and hashing.

**Covered capabilities:**
- Input sanitization (preventing injection attacks in log messages, file paths).
- Sensitive value detection (identifying potential credentials in strings).
- Token validation (checking format and expiry of authentication tokens).
- Rate limiting (tracking request rates and enforcing limits).
- Security context management (current security context for access checks).
- Audit trail interface (recording security-relevant events).
- Attack pattern detection (SQL injection patterns, path traversal, etc.).

---

### Category 18 — Authentication Helpers (AUTHN)

**Namespace:** AUTHN
**Layer:** Security
**Description:** Utilities supporting authentication operations.

**Covered capabilities:**
- Credential formatting and validation.
- Token lifecycle management (creation time, expiry, refresh triggers).
- Authentication state management.
- Credential storage helpers (reading from secrets manager, never from disk).
- Authentication retry logic (with backoff and account lockout awareness).
- Multi-factor authentication state tracking.

---

### Category 19 — Authorization Helpers (AUTHZ)

**Namespace:** AUTHZ
**Layer:** Security
**Description:** Utilities supporting authorization decisions.

**Covered capabilities:**
- Permission checking interface.
- Role resolution (what permissions does this role grant?).
- Access decision recording (audit trail for authorization checks).
- Authorization caching (reduce repeated authorization lookups).
- Policy rule evaluation.
- Resource-action pair encoding.

---

## 2.5 Layer 4 — Formatting and Conversion Utilities

### Category 20 — Formatting Utilities (FMT)

**Namespace:** FMT
**Layer:** Platform
**Description:** Utilities for formatting values for display or transmission.

**Covered capabilities:**
- Number formatting (decimal places, thousands separators, scientific notation).
- Percentage formatting.
- Currency formatting (amounts with currency symbols).
- Financial value formatting (P&L, portfolio values with appropriate precision).
- Boolean formatting (true/false, yes/no, 1/0 — context-configurable).
- List formatting (comma-separated, bullet points, numbered).
- Table formatting (aligned columns for console output).
- Color formatting for terminal output.

---

### Category 21 — Conversion Utilities (CONV)

**Namespace:** CONV
**Layer:** Platform
**Description:** Utilities for converting between types and representations.

**Covered capabilities:**
- Numeric type conversions with precision preservation.
- Unit conversions (percentages, basis points, price units).
- Encoding conversions (base64, hex, bytes).
- Data structure conversions (list to dictionary, dictionary to list).
- Financial measure conversions (returns to log-returns, prices to returns).
- Timezone conversions.
- Measurement unit conversions (useful for strategy parameters).

---

### Category 22 — Date-Time Utilities (DT)

**Namespace:** DT
**Layer:** Platform
**Description:** Comprehensive date and time management utilities.

**Covered capabilities:**
- Current time retrieval (always UTC; explicit local time conversion).
- Date and time parsing (multiple input formats to canonical UTC).
- Date and time formatting (ISO 8601 and human-readable formats).
- Date arithmetic (add/subtract days, hours, minutes, seconds).
- Date comparison (before, after, between, same day).
- Business day calculation (considering market holidays for NSE/BSE).
- Trading session time checks (is the market currently open?).
- Market holiday calendar management.
- Date range generation (all business days between two dates).
- Duration formatting (human-readable "2 hours 15 minutes").
- Monotonic clock access (for latency measurement, not wall time).
- Testable time (injectable clock for deterministic tests).

**IIOS-specific:** The market open window is 09:15–15:30 IST. Pre-market
is 08:45–09:15. Post-market is 15:30–16:00. These are defined as constants
in the Date-Time Utility.

---

### Category 23 — Timezone Utilities (TZ)

**Namespace:** TZ
**Layer:** Platform
**Description:** Timezone management utilities.

**Covered capabilities:**
- Timezone database access (IANA timezone names).
- UTC to local time conversion.
- Local time to UTC conversion.
- Market timezone management (India/Kolkata for NSE/BSE).
- Daylight saving time awareness.
- Timezone offset computation.
- Timezone-aware datetime comparison.

---

### Category 24 — Localization Utilities (L10N)

**Namespace:** L10N
**Layer:** Platform
**Description:** Localization utilities for regional formatting.

**Covered capabilities:**
- Number formatting per locale (decimal separator, thousands separator).
- Currency formatting per locale.
- Date formatting per locale.
- String translation interface.
- Locale detection.
- Locale-aware sorting.

**IIOS note:** IIOS primarily operates in the India locale (INR currency, NSE/BSE
exchange formats) but the localization utility supports other locales for any
future international expansion.

---

## 2.6 Layer 5 — Identifier and Randomization Utilities

### Category 25 — Identifier Utilities (ID)

**Namespace:** ID
**Layer:** Platform
**Description:** Utilities for generating and managing identifiers across the platform.

**Covered capabilities:**
- Platform-standard identifier format definition.
- Identifier validation (is a given string a valid IIOS identifier?).
- Identifier parsing (extract type, timestamp, and sequence from an identifier).
- Identifier comparison and sorting.
- Identifier prefixing by component (cycle_id, trade_id, session_id).
- Collision-free identifier generation.
- Short identifier generation for human-readable references.

**IIOS identifier format:** All IIOS identifiers follow the format
[type_prefix]-[ISO_date]-[sequence] for human-readable IDs (e.g.,
cycle-20260704-001) or UUID v4 for machine-generated IDs.

---

### Category 26 — UUID Utilities (UUID)

**Namespace:** UUID
**Layer:** Platform
**Description:** UUID generation and management utilities.

**Covered capabilities:**
- UUID v4 generation (random, suitable for event IDs, correlation IDs).
- UUID v7 generation (time-ordered, suitable for database primary keys).
- UUID validation (is this string a valid UUID?).
- UUID parsing (extract timestamp from v7 UUID).
- Nil UUID (the zero UUID — used as a placeholder value).
- UUID formatting (standard hyphenated format, compact format).
- UUID sorting (by creation time for v7 UUIDs).

---

### Category 27 — Randomization Utilities (RAND)

**Namespace:** RAND
**Layer:** Platform
**Description:** Random value generation utilities with security and reproducibility modes.

**Covered capabilities:**
- Cryptographically secure random bytes (for security use cases).
- Reproducible pseudo-random number generation (seeded PRNG for simulations).
- Random choice from a collection.
- Random sample (without replacement) from a collection.
- Random shuffle.
- Weighted random choice (select with defined probabilities).
- Random float in a range.
- Random integer in a range.
- Gaussian (normal distribution) random values.
- Reproducible PRNG reset (reset to seed for test reproducibility).

---

## 2.7 Layer 6 — Mathematical and Statistical Utilities

### Category 28 — Math Utilities (MATH)

**Namespace:** MATH
**Layer:** Platform
**Description:** Mathematical computation utilities.

**Covered capabilities:**
- Safe division (handles divide-by-zero with defined behavior).
- Rounding modes (round half up, round half to even, truncate).
- Clamping (constraining a value to a range).
- Interpolation (linear, logarithmic).
- Percentage computation.
- Basis point computation.
- Power and logarithm functions with edge case handling.
- Numerical precision comparison (is this float "equal" within epsilon?).
- Overflow-safe arithmetic.

---

### Category 29 — Statistical Utilities (STAT)

**Namespace:** STAT
**Layer:** Platform
**Description:** Statistical computation utilities.

**Covered capabilities:**
- Descriptive statistics: mean, median, mode, variance, standard deviation.
- Percentiles and quantiles.
- Correlation coefficient (Pearson, Spearman).
- Rolling window statistics (rolling mean, rolling standard deviation).
- Exponentially weighted moving averages (EWMA).
- Z-score computation.
- Outlier detection (IQR method, Z-score method).
- Distribution fitting (normal distribution parameters from data).
- Histogram construction.
- Moving average (simple, weighted, exponential).

---

### Category 30 — Financial Utilities (FIN)

**Namespace:** FIN
**Layer:** Business
**Description:** Financial computation utilities specific to trading and portfolio management.

**Covered capabilities:**
- Return computation (simple returns, log-returns, annualized returns).
- Sharpe ratio computation.
- Sortino ratio computation.
- Maximum drawdown computation.
- Drawdown duration.
- Win rate computation.
- Risk/reward ratio computation.
- Position value computation (quantity × price).
- P&L computation (realized and unrealized).
- Compounding return computation.
- Volatility computation (historical, realized).
- Value at Risk (VaR) computation.
- Portfolio-level metrics aggregation.

**IIOS-specific:** Financial utilities operate in INR by default. They handle
NSE/BSE lot sizes, circuit limit filters, and settlement rules.

---

### Category 31 — Market Utilities (MKT)

**Namespace:** MKT
**Layer:** Business
**Description:** Market-specific computation utilities.

**Covered capabilities:**
- Trading day determination (is today a trading day for NSE?).
- Market session determination (pre-market, market, post-market, closed).
- Expiry date computation (weekly options expiry, monthly expiry).
- Strike price computation (ATM strike, ITM/OTM strikes).
- Options Greeks computation (Delta, Gamma, Theta, Vega).
- Index symbol mapping (NIFTY → ^NSEI, BANKNIFTY → ^NSEBANK).
- Exchange-specific symbol formatting (append .NS for NSE stocks).
- Circuit breaker level computation.
- Market holiday calendar.

---

## 2.8 Layer 7 — String and Collection Utilities

### Category 32 — String Utilities (STR)

**Namespace:** STR
**Layer:** Platform
**Description:** String manipulation and analysis utilities.

**Covered capabilities:**
- String normalization (trim, case, whitespace reduction).
- String splitting and joining.
- String matching (exact, prefix, suffix, contains, regex).
- String formatting with templates.
- String truncation with ellipsis.
- String similarity (Levenshtein distance, fuzzy matching).
- Case conversion (camelCase, snake_case, UPPER_SNAKE_CASE, kebab-case).
- String escaping (for HTML, JSON, SQL contexts).
- Multi-line string handling.
- String encoding utilities (bytes to string, string to bytes).
- Slug generation (URL-safe lowercase identifier from a string).
- Sensitive pattern detection and redaction in strings.

---

### Category 33 — Collection Utilities (COL)

**Namespace:** COL
**Layer:** Platform
**Description:** Utilities for working with collections: lists, dictionaries,
sets, and queues.

**Covered capabilities:**
- Filtering, mapping, and reducing collections.
- Sorting with custom comparators.
- Grouping by key.
- Partitioning into chunks.
- Flattening nested collections.
- Uniqueness enforcement (deduplication).
- Set operations (union, intersection, difference).
- Dictionary merging (shallow and deep).
- Safe collection access (get with default, get or error).
- Collection statistics (min, max, first, last with empty handling).
- Priority queues and sorted collections.
- Immutable collection views.
- Circular buffer implementation.
- Sliding window collections.

---

## 2.9 Layer 8 — Performance and Resource Utilities

### Category 34 — Memory Utilities (MEM)

**Namespace:** MEM
**Layer:** Infrastructure
**Description:** Memory management and monitoring utilities.

**Covered capabilities:**
- Current memory usage reporting (RSS, virtual, heap).
- Memory limit checking.
- Large object tracking (identify objects consuming significant memory).
- Memory leak detection helpers.
- Object size estimation.
- Memory pool management for frequently allocated/deallocated objects.

---

### Category 35 — Performance Utilities (PERF)

**Namespace:** PERF
**Layer:** Infrastructure
**Description:** Performance measurement and profiling utilities.

**Covered capabilities:**
- High-resolution timer (nanosecond precision for latency measurement).
- Latency histogram (track and report operation latency distributions).
- Throughput counter (operations per second measurement).
- CPU usage measurement.
- Execution time budgeting (warn if an operation exceeds its time budget).
- Performance profile reporting.
- Context manager for timed code blocks.
- Cumulative execution time tracking per operation type.

**IIOS-specific:** The Performance Utility provides the timing infrastructure
for the System Monitor's per-layer latency tracking. Every engine's execution is
timed using this utility.

---

### Category 36 — Caching Utilities (CACHE)

**Namespace:** CACHE
**Layer:** Platform
**Description:** In-memory caching utilities.

**Covered capabilities:**
- LRU (Least Recently Used) cache.
- TTL (Time-To-Live) cache (entries expire after a defined duration).
- LFU (Least Frequently Used) cache.
- Write-through and write-behind cache patterns.
- Cache statistics (hit rate, miss rate, eviction count).
- Cache invalidation (by key, by tag, full invalidation).
- Thread-safe cache implementations.
- Cache size limits (by count and by memory).
- Distributed cache interface (for future horizontal scaling).

**IIOS-specific:** The GlobalIntelligence engine's 5-minute cache uses the TTL
cache from this utility. Cache hit rates are monitored and reported via the
Metrics system.

---

### Category 37 — Retry Utilities (RETRY)

**Namespace:** RETRY
**Layer:** Platform
**Description:** Retry policy implementations.

**Covered capabilities:**
- Immediate retry policy.
- Linear backoff retry policy.
- Exponential backoff retry policy with jitter.
- Fixed delay retry policy.
- Retry with fallback (on exhaustion, execute fallback action).
- Conditional retry (retry only if exception matches predicate).
- Retry context tracking (attempt count, total time, last exception).
- Retry statistics (success on first attempt, second attempt, etc.).
- Non-idempotent operation guard (prevents accidental retry of unsafe operations).

---

### Category 38 — Scheduling Utilities (SCHED)

**Namespace:** SCHED
**Layer:** Infrastructure
**Description:** Task scheduling and execution utilities.

**Covered capabilities:**
- Cron-expression based scheduling.
- Interval-based scheduling.
- One-time future execution.
- Market-hours-aware scheduling (execute only during trading hours).
- Schedule modification at runtime.
- Scheduled task monitoring (detect overdue tasks).
- Graceful shutdown handling (complete in-flight tasks before stopping).
- Schedule state persistence (survive restarts).
- Overlap prevention (do not start a new execution if the previous is still running).

---

### Category 39 — Concurrency Utilities (CONC)

**Namespace:** CONC
**Layer:** Infrastructure
**Description:** Concurrency primitives and coordination utilities.

**Covered capabilities:**
- Thread-safe counter (atomic increment/decrement).
- Thread-safe flag (set/clear/check with visibility guarantees).
- Mutex and lock management helpers.
- Condition variable helpers.
- Read-write lock (many readers, exclusive writer).
- Event signaling.
- Barrier synchronization.
- Semaphore with timeout.
- Thread pool management.
- Task queue (producer-consumer pattern).
- Deadlock detection helper.
- Thread local storage management.

---

### Category 40 — Resource Utilities (RES)

**Namespace:** RES
**Layer:** Infrastructure
**Description:** Resource lifecycle management utilities.

**Covered capabilities:**
- Resource pool management (manage a pool of reusable resources).
- Connection pool management (database connections, HTTP connections).
- Resource acquisition/release with guaranteed cleanup.
- Resource timeout enforcement.
- Resource health monitoring.
- Resource limit enforcement.
- Context manager for automatic resource release.

---

## 2.10 Layer 9 — Observability Utilities

### Category 41 — Logging Helpers (LOG)

**Namespace:** LOG
**Layer:** Observability
**Description:** Logging utilities that simplify correct log event creation.

**Covered capabilities:**
- Logger factory (get a correctly configured logger for a component).
- Structured log record builders (build log events with correct fields).
- Context manager for log context injection (cycle_id, trade_id).
- Log level configuration helpers.
- Log message template management.
- Sensitive field redaction in log parameters.
- Log event validation (ensure all required fields are present).
- Batch log event builders (create multiple related events).

---

### Category 42 — Monitoring Helpers (MON)

**Namespace:** MON
**Layer:** Observability
**Description:** Monitoring utility helpers.

**Covered capabilities:**
- Health check registration and execution.
- OHS contribution reporting (a component reports its health sub-scores).
- Health status propagation.
- Monitoring probe creation.
- Status page data contribution.

---

### Category 43 — Metrics Helpers (MET)

**Namespace:** MET
**Layer:** Observability
**Description:** Metrics recording utilities.

**Covered capabilities:**
- Counter increment.
- Gauge setting.
- Histogram recording.
- Rate computation helpers.
- Metric labeling.
- Metric batch recording.
- Metric naming validation (ensure names conform to the platform naming convention).
- Metric documentation (record the description and unit of each metric).

---

### Category 44 — Tracing Helpers (TRACE)

**Namespace:** TRACE
**Layer:** Observability
**Description:** Distributed tracing utilities.

**Covered capabilities:**
- Span creation and completion.
- Span context propagation.
- Span annotation (add events and attributes to a span).
- Context manager for span lifecycle.
- Trace context injection into outgoing calls.
- Trace context extraction from incoming calls.
- Span status reporting (success, error).

---

### Category 45 — Notification Helpers (NOTIF)

**Namespace:** NOTIF
**Layer:** Observability
**Description:** Notification dispatch utilities.

**Covered capabilities:**
- Notification template management.
- Notification formatting (text and rich format).
- Notification channel abstraction (Telegram, email, webhook).
- Notification deduplication helper.
- Notification acknowledgement tracking.
- Notification severity formatting.

---

## 2.11 Layer 10 — AI and Knowledge Utilities

### Category 46 — AI Helper Utilities (AI)

**Namespace:** AI
**Layer:** AI
**Description:** Utilities supporting AI model operations within IIOS engines.

**Covered capabilities:**
- Feature vector construction and normalization.
- Feature validation (correct dimensions, no NaN values, bounded ranges).
- Model output validation (output within expected range and format).
- Confidence score normalization.
- Score aggregation (combining scores from multiple models).
- Prediction interval computation.
- Model input preprocessing helpers.
- Inference context management.

---

### Category 47 — Knowledge Utilities (KNW)

**Namespace:** KNW
**Layer:** AI
**Description:** Utilities for the Knowledge Base and learning system.

**Covered capabilities:**
- Knowledge entry creation and validation.
- Knowledge search interface (retrieve entries matching a pattern).
- Knowledge version management.
- Knowledge export and import.
- Knowledge graph navigation.
- Pattern matching for incident classification.

---

### Category 48 — Ontology Utilities (ONT)

**Namespace:** ONT
**Layer:** AI
**Description:** Ontology management utilities for structured domain knowledge.

**Covered capabilities:**
- Domain concept definition and validation.
- Relationship mapping between concepts.
- Concept hierarchy navigation.
- Concept similarity computation.
- Ontology export (for documentation and analysis).
- Ontology consistency checking.

---

### Category 49 — Document Utilities (DOC)

**Namespace:** DOC
**Layer:** AI
**Description:** Document processing utilities.

**Covered capabilities:**
- Document parsing (PDF, Markdown, HTML text extraction).
- Document chunking (split into sections for processing).
- Document metadata extraction.
- Document similarity computation.
- Document format conversion.
- Document indexing helpers.

---

### Category 50 — Search Utilities (SRCH)

**Namespace:** SRCH
**Layer:** AI
**Description:** Search and retrieval utilities.

**Covered capabilities:**
- Full-text search indexing.
- Full-text search querying.
- Fuzzy search.
- Faceted search helpers.
- Search result ranking.
- Search query parsing.

---

## 2.12 Layer 11 — Versioning and Migration Utilities

### Category 51 — Version Utilities (VER)

**Namespace:** VER
**Layer:** Platform
**Description:** Version management utilities.

**Covered capabilities:**
- Semantic version parsing and comparison (SemVer 2.0).
- Version range evaluation (is version X compatible with range Y?).
- Version ordering and sorting.
- Version changelog management.
- Minimum version enforcement.
- Version metadata retrieval (for utilities, components, data schemas).

---

### Category 52 — Migration Utilities (MIG)

**Namespace:** MIG
**Layer:** Platform
**Description:** Data and configuration migration utilities.

**Covered capabilities:**
- Migration script registration and ordering.
- Migration state tracking (which migrations have been applied).
- Forward migration execution.
- Migration validation (verify successful migration).
- Migration rollback (undo a migration).
- Migration dry-run mode (validate without applying).
- Migration dependency management.

---

## 2.13 Layer 12 — Developer and Testing Utilities

### Category 53 — Testing Utilities (TEST)

**Namespace:** TEST
**Layer:** Developer
**Description:** Utilities for building tests across the IIOS platform.

**Covered capabilities:**
- Test fixture builders for IIOS domain objects (create a trade, a decision, a cycle).
- Mock data generators (realistic market data, realistic P&L distributions).
- Time control utilities (freeze time, advance time, inject a specific time).
- Event bus test helpers (capture and assert on emitted events).
- Mock external service factories (fake data feed, fake broker).
- Assertion helpers for domain-specific types.
- Integration test setup and teardown helpers.
- Property-based test generators.
- Test data cleanup utilities.

---

### Category 54 — Debug Utilities (DBG)

**Namespace:** DBG
**Layer:** Developer
**Description:** Debugging utilities for development and diagnosis.

**Covered capabilities:**
- Object state snapshot (human-readable dump of any IIOS object).
- Variable inspection helpers.
- Call stack inspection.
- Breakpoint helpers for conditional halting.
- Debug mode detection (is the system running in debug mode?).
- Debug output formatting.
- Differential state comparison (what changed between two states?).

---

### Category 55 — Developer Utilities (DEV)

**Namespace:** DEV
**Layer:** Developer
**Description:** Utilities for development workflow support.

**Covered capabilities:**
- Code generation helpers (templates for new engine boilerplate).
- Development environment validation (all required tools and versions present).
- Local data seeding (populate development databases with realistic test data).
- Feature flag management (enable/disable in-progress features).
- Development mode configuration overrides.
- Interactive REPL helpers for development exploration.

---

## 2.14 Layer 13 — Reflection and Dependency Utilities

### Category 56 — Reflection Utilities (REFL)

**Namespace:** REFL
**Layer:** Platform
**Description:** Runtime reflection and introspection utilities.

**Covered capabilities:**
- Component introspection (discover an object's type, fields, methods).
- Interface implementation checking.
- Dynamic invocation (call a method by name).
- Attribute and annotation reading.
- Class hierarchy inspection.
- Component discovery by interface.

**Security note:** Dynamic invocation is a potential injection vector. The
Reflection Utility restricts dynamic invocation to registered, approved invocation
targets only. Arbitrary dynamic invocation of any callable is prohibited.

---

### Category 57 — Dependency Utilities (DEP)

**Namespace:** DEP
**Layer:** Platform
**Description:** Dependency management utilities.

**Covered capabilities:**
- Dependency registration.
- Dependency resolution.
- Dependency graph construction.
- Circular dependency detection.
- Optional dependency resolution (return null if not available).
- Dependency health checking.
- Dependency version compatibility checking.
- Dependency lifecycle management (initialize before first use, release on shutdown).

---

*End of Part II*

---
# PART III — FRAMEWORK ARCHITECTURE

## 3.1 Architecture Overview

The Shared Utilities Framework is governed by 18 components. These components
manage the registration, discovery, lifecycle, configuration, quality, and
governance of all shared utilities throughout the IIOS platform.

Together they ensure that utilities are consistently discoverable, correctly
initialized, properly versioned, and operationally monitored.

---

## 3.2 Component 1 — Utility Registry

**Purpose:**
The Utility Registry is the authoritative, runtime-maintained catalog of all
shared utility instances available to IIOS components. It is the single source
of truth for utility availability.

**Responsibilities:**
- Accept utility registration requests from the Initialization Manager.
- Maintain a map from utility identity (namespace + name + version) to its
  runtime instance.
- Serve utility lookup requests from consuming components.
- Track the operational state of each registered utility.
- Enforce registration constraints (no two utilities may share the same namespace/name/version triple).
- Emit registration events to the Event Bus.

**Inputs:**
- Utility registration requests (utility descriptor + runtime instance).
- Utility lookup requests from consuming components.
- Utility unregistration requests on shutdown.

**Outputs:**
- Registered utility instances to requesting components.
- Registration events to the Event Bus.
- Registry health status to the Monitoring Manager.

**Interactions:**
- Receives registrations from the Initialization Manager.
- Provides lookups to the Dependency Manager.
- Reports status to the Monitoring Manager.
- Emits events to the Event Bus.

**Dependencies:**
- Core Utilities (for identity and comparison).
- Event Bus (for registration events).

**Lifecycle:**
The Registry is the first framework component initialized (before any utilities).
It is the last component shut down (after all utilities have been unregistered).

**Failure Modes:**
- Duplicate registration: rejected with an error. The caller must deregister first.
- Registry unavailable: all lookups fail. This prevents any component from obtaining
  utilities. This is a CRITICAL failure.

**Recovery:**
Registry unavailability triggers a system restart. The registry is rebuilt from
the initialization sequence on restart.

**Monitoring:**
- Metric: total registered utilities (gauge).
- Metric: lookup requests per second (counter).
- Metric: lookup latency (histogram).
- Health: registry responds to health probe.

**Scalability:**
The Registry is an in-memory component. It supports all 57 utility categories
without performance concern at IIOS scale. No horizontal scaling is required.

**Engineering Notes:**
The Registry is a read-heavy component. Lookups vastly outnumber registrations.
The lookup data structure must be optimized for read performance. Writes
(registrations) are infrequent and can tolerate higher latency.

---

## 3.3 Component 2 — Utility Catalog

**Purpose:**
The Utility Catalog provides the human-readable, queryable documentation of all
utilities — what they do, how to use them, their version, and their quality status.

**Responsibilities:**
- Maintain documentation for each utility: purpose, capabilities, version history.
- Provide search capability (find utilities by keyword, category, or capability).
- Track utility quality certifications.
- Generate documentation reports.
- Detect catalog inconsistencies (documented utilities not found in Registry).

**Inputs:**
- Utility documentation entries (from the Documentation Manager).
- Quality certification records (from the Certification Manager).
- Registry state (for consistency checking).

**Outputs:**
- Utility documentation to developers and governance reports.
- Catalog search results.
- Inconsistency reports.

**Interactions:**
- Reads from the Utility Registry (for consistency verification).
- Receives documentation from the Documentation Manager.
- Receives certification records from the Certification Manager.

**Dependencies:**
- Utility Registry.
- Documentation Manager.
- Certification Manager.
- Search Utilities.

**Lifecycle:**
Initialized after the Registry. Updated continuously as utilities are added,
modified, deprecated, or retired.

**Failure Modes:**
- Catalog read failure: developers cannot discover utilities. Non-critical (utilities
  still function).
- Documentation out of date: catalog describes utilities that no longer exist or
  does not describe utilities that do.

**Recovery:**
Catalog rebuild from Registry state. Documentation regenerated from source.

**Monitoring:**
- Metric: total catalogued utilities.
- Metric: utilities without documentation (should be zero).
- Health: catalog accessible.

**Scalability:**
The Catalog is documentation-only. It scales trivially with the number of utilities.

**Engineering Notes:**
The Catalog is the primary tool for developers discovering and learning about
utilities. Its quality directly affects engineering productivity. Poor catalog
quality causes developers to implement utilities that already exist.

---

## 3.4 Component 3 — Dependency Manager

**Purpose:**
The Dependency Manager resolves utility dependencies, ensuring that each utility
receives the other utilities it needs before it is initialized.

**Responsibilities:**
- Maintain the dependency graph of all utilities.
- Compute initialization order from the dependency graph (topological sort).
- Detect circular dependencies (which are a configuration error).
- Provide dependency injection (give each utility its resolved dependencies).
- Track optional vs mandatory dependencies.
- Validate version compatibility between dependencies.

**Inputs:**
- Utility dependency declarations (from each utility's descriptor).
- Utility version metadata.
- Optional dependency flags.

**Outputs:**
- Initialization order sequence.
- Resolved dependency instances for each utility.
- Circular dependency error reports.
- Version incompatibility error reports.

**Interactions:**
- Reads utility descriptors from the Utility Catalog.
- Provides resolved dependencies to the Initialization Manager.
- Reports circular dependencies to the Governance Manager.

**Dependencies:**
- Utility Registry.
- Utility Catalog.
- Version Manager.

**Lifecycle:**
The Dependency Manager is initialized before utilities. It processes the dependency
graph before any utility initialization begins.

**Failure Modes:**
- Circular dependency detected: initialization halts. No circular dependency in
  the utility graph is ever correct — it indicates a design error.
- Missing mandatory dependency: initialization halts. A utility cannot start
  without its mandatory dependency.
- Version incompatibility: initialization halts until resolved.

**Recovery:**
Dependency failures require code changes — they cannot be auto-recovered. The
framework reports the exact cycle or missing dependency for rapid diagnosis.

**Monitoring:**
- Metric: dependency graph depth (deepest dependency chain).
- Metric: total dependency edges.
- Alert: circular dependency detected (should never fire in a healthy system).

**Scalability:**
The dependency graph is static (defined at build time). Resolution is computed
once at startup. No runtime performance concern.

**Engineering Notes:**
The Dependency Manager is the enforcement mechanism for the directed dependency
hierarchy. The 10-layer architecture requires that dependencies only point
downward (higher layers depend on lower layers, never the reverse).

---

## 3.5 Component 4 — Lifecycle Manager

**Purpose:**
The Lifecycle Manager orchestrates the initialization, activation, and shutdown
of all shared utilities in the correct order.

**Responsibilities:**
- Execute the utility initialization sequence in dependency order.
- Track lifecycle state for each utility.
- Coordinate activation of utilities after initialization.
- Manage graceful shutdown (reverse initialization order).
- Handle initialization failures (with defined rollback behavior).
- Publish lifecycle events.

**Inputs:**
- Initialization order from the Dependency Manager.
- Lifecycle state reports from each utility.
- Shutdown signal from the platform.

**Outputs:**
- Lifecycle events to the Event Bus.
- Utility lifecycle states to the Monitoring Manager.
- Initialization complete signal to IIOS orchestrator.

**Interactions:**
- Receives initialization order from Dependency Manager.
- Coordinates with the Initialization Manager for each utility.
- Reports states to the Monitoring Manager.
- Emits events to the Event Bus.

**Dependencies:**
- Dependency Manager.
- Initialization Manager.
- Monitoring Manager.
- Event Bus.

**Lifecycle:**
The Lifecycle Manager itself is bootstrapped before utilities. It has no
dependencies on other utilities.

**Failure Modes:**
- Utility initialization failure: Lifecycle Manager decides whether to retry,
  skip (if optional), or abort the entire initialization sequence.
- Graceful shutdown timeout: a utility takes too long to shut down. After timeout,
  the Lifecycle Manager forces termination.

**Recovery:**
Failed mandatory utility initialization aborts system startup. The system does
not enter operational state until all mandatory utilities are initialized.

**Monitoring:**
- Metric: initialization duration per utility.
- Metric: total initialization time.
- Metric: utilities in each lifecycle state.
- Alert: any utility stuck in INITIALIZING state for more than 30 seconds.

**Scalability:**
Initialization is a startup-time operation. No runtime scalability concern.

**Engineering Notes:**
Initialization order is strictly determined by the dependency graph. No manual
ordering overrides are permitted (they would become stale as the dependency
graph changes).

---

## 3.6 Component 5 — Initialization Manager

**Purpose:**
The Initialization Manager manages the initialization of each individual utility —
passing configuration, performing health checks, and registering the utility in
the Registry.

**Responsibilities:**
- Load utility-specific configuration for each utility being initialized.
- Instantiate utilities in the correct lifecycle order.
- Execute post-initialization health checks.
- Register successfully initialized utilities in the Registry.
- Report initialization outcomes (success, failure, partial) to the Lifecycle Manager.

**Inputs:**
- Initialization request from Lifecycle Manager (one utility at a time).
- Utility configuration from the Configuration Loader.
- Utility descriptors (factory function, dependencies, version).

**Outputs:**
- Initialized utility instance to the Registry.
- Initialization health check result to the Lifecycle Manager.
- Configuration validation results.

**Interactions:**
- Receives initialization requests from the Lifecycle Manager.
- Requests configuration from the Configuration Loader.
- Registers utilities in the Registry.
- Reports outcomes to the Lifecycle Manager.

**Dependencies:**
- Lifecycle Manager.
- Configuration Loader.
- Utility Registry.
- Core Utilities.

**Lifecycle:**
Active only during the initialization phase. After all utilities are initialized,
the Initialization Manager enters a passive monitoring state.

**Failure Modes:**
- Configuration invalid for utility: initialization fails. Configuration error
  must be corrected before retry.
- Health check failure after initialization: utility is deregistered and treated
  as a failed initialization.
- Timeout during initialization: utility initialization that takes more than the
  defined budget is terminated and treated as a failure.

**Recovery:**
Mandatory utility failures abort the initialization sequence. The system halts
and reports the failure clearly.

**Monitoring:**
- Metric: per-utility initialization time.
- Alert: initialization time exceeds budget for any utility.

**Engineering Notes:**
Every utility's initialization path must be deterministic and fast. Utilities
that perform expensive initialization operations (e.g., reading large files)
must do so asynchronously and not block the initialization sequence.

---

## 3.7 Component 6 — Configuration Loader

**Purpose:**
The Configuration Loader provides utilities with their configuration values
from the IIOS configuration hierarchy.

**Responsibilities:**
- Load the configuration for a named utility from the configuration hierarchy.
- Apply environment-specific overrides.
- Inject secrets from the secrets manager.
- Validate the loaded configuration against the utility's config schema.
- Cache loaded configurations for the runtime duration.

**Inputs:**
- Configuration load request (utility name, version, environment).
- IIOS configuration files (YAML).
- Environment variables.
- Secrets from the secrets manager.

**Outputs:**
- Validated configuration object for the requesting utility.
- Configuration validation errors.

**Interactions:**
- Called by the Initialization Manager during utility initialization.
- Reads from the Configuration Framework.
- Reads secrets from the secrets manager.

**Dependencies:**
- Configuration Framework.
- YAML Utilities.
- Validation Utilities.
- Environment Utilities.

**Lifecycle:**
Active continuously. Configuration changes are detected and applied on change.

**Failure Modes:**
- Configuration file not found: utility uses defaults where defined; otherwise
  initialization fails.
- Configuration validation failure: initialization fails. Invalid configuration
  is never silently accepted.
- Secret lookup failure: initialization fails. Utilities requiring secrets cannot
  start without them.

**Recovery:**
Configuration failures require operator correction of the configuration. The
Loader provides clear error messages identifying the missing or invalid field.

**Monitoring:**
- Metric: configuration load time per utility.
- Metric: configuration changes detected.
- Alert: configuration validation failure.

**Engineering Notes:**
The Configuration Loader never logs secret values. It logs the presence or
absence of secrets (found/not found) only.

---

## 3.8 Component 7 — Resource Manager

**Purpose:**
The Resource Manager manages shared resources (file handles, connection pools,
thread pools) used across multiple utilities.

**Responsibilities:**
- Maintain shared resource pools.
- Allocate and release resources to utilities on demand.
- Enforce resource limits (maximum concurrent uses).
- Monitor resource utilization.
- Handle resource cleanup on failure.

**Inputs:**
- Resource acquisition requests from utilities.
- Resource release notifications.
- Resource health status from underlying systems.

**Outputs:**
- Resource handles to requesting utilities.
- Resource utilization metrics.
- Resource pool health status.

**Interactions:**
- Serves resource requests from utilities.
- Reports metrics to the Metrics system.
- Reports health to the Monitoring Manager.

**Dependencies:**
- Core Utilities.
- Monitoring Manager.
- Metrics Helpers.

**Lifecycle:**
Initialized before utilities that require shared resources. Cleaned up after all
consuming utilities are shut down.

**Failure Modes:**
- Resource pool exhaustion: requesting utility waits (with timeout) for a resource
  to become available.
- Resource pool unavailable: requesting utilities receive an error and apply fallback.

**Recovery:**
Pool exhaustion is addressed by resource timeout and release cycle. If a resource
is held too long, it is forcibly reclaimed.

**Monitoring:**
- Metric: pool utilization per resource type.
- Metric: resource acquisition wait time.
- Alert: pool utilization above 90%.

**Scalability:**
Pool sizes are configurable. Pools can be expanded without restarting the system.

**Engineering Notes:**
Resources that require cleanup on abnormal termination (e.g., file locks) are
registered with the platform's shutdown handler to ensure cleanup even on crash.

---

## 3.9 Component 8 — Plugin Manager

**Purpose:**
The Plugin Manager manages the registration and discovery of utility plugins —
extensions that add new implementations or capabilities to existing utilities.

**Responsibilities:**
- Accept plugin registration from external modules.
- Validate plugin interface compliance.
- Provide plugin discovery to utilities that support plugins.
- Manage plugin lifecycle (activation, deactivation).
- Enforce plugin security constraints.

**Inputs:**
- Plugin registration requests.
- Plugin validation results.
- Plugin lifecycle events.

**Outputs:**
- Plugin registry to requesting utilities.
- Plugin validation reports.
- Plugin lifecycle events to the Event Bus.

**Interactions:**
- Registered plugins are passed to the Extension Manager.
- Reports to the Governance Manager.

**Dependencies:**
- Utility Registry.
- Validation Utilities.
- Governance Manager.

**Lifecycle:**
Initialized after the Registry. Plugins can be registered at any time during
the active lifecycle.

**Failure Modes:**
- Invalid plugin (does not implement required interface): rejected with validation error.
- Plugin initialization failure: plugin is rejected; host utility is not affected.

**Recovery:**
Plugin failures are isolated. The host utility operates without the failed plugin.

**Monitoring:**
- Metric: total registered plugins per utility.
- Metric: plugin validation failures.

**Engineering Notes:**
Plugins run in the same process as the host utility. They are not sandboxed.
Plugin code must pass the same code quality gates as first-party utilities.

---

## 3.10 Component 9 — Extension Manager

**Purpose:**
The Extension Manager manages the extension points exposed by utilities — the
defined interfaces that allow utilities to be extended without modification.

**Responsibilities:**
- Register extension point definitions from utilities.
- Accept extension implementations.
- Validate extension implementations against their extension point contract.
- Provide extension lists to utilities at initialization time.
- Manage extension priority and ordering.

**Inputs:**
- Extension point definitions from utilities.
- Extension implementations from plugins or other utilities.
- Extension ordering configuration.

**Outputs:**
- Ordered, validated extension lists to utilities.
- Extension validation reports.

**Interactions:**
- Receives extension points from utilities during initialization.
- Receives extensions from the Plugin Manager.
- Provides extension lists to utilities.

**Dependencies:**
- Plugin Manager.
- Validation Utilities.
- Utility Registry.

**Lifecycle:**
Active after the Plugin Manager. Extensions are resolved before the consuming
utility completes initialization.

**Failure Modes:**
- Extension implementation invalid: rejected. Host utility operates with remaining
  valid extensions.
- No extensions registered for an extension point: host utility uses its default
  behavior.

**Engineering Notes:**
Extension points are the preferred mechanism for customizing utility behavior.
Modifying a utility's core code to accommodate a new use case is discouraged —
adding an extension point is preferred.

---

## 3.11 Component 10 — Compatibility Manager

**Purpose:**
The Compatibility Manager verifies that all utilities are compatible with each
other and with the platform environment before initialization proceeds.

**Responsibilities:**
- Check utility-to-utility version compatibility.
- Check utility-to-platform compatibility.
- Verify that required capabilities are available in the runtime environment.
- Report compatibility issues before initialization is attempted.

**Inputs:**
- Utility version declarations.
- Platform version and capabilities.
- Compatibility matrices.

**Outputs:**
- Compatibility check results.
- Incompatibility reports with resolution guidance.

**Interactions:**
- Runs before the Initialization Manager begins.
- Reports to the Lifecycle Manager (which may abort initialization).

**Dependencies:**
- Version Manager.
- Environment Utilities.
- Utility Registry.

**Lifecycle:**
Runs once during the startup phase before utility initialization begins.

**Failure Modes:**
- Incompatibility detected: initialization halts with a clear incompatibility report.

**Recovery:**
Incompatibilities require code or configuration changes. They cannot be auto-recovered.

**Engineering Notes:**
Compatibility checks are designed to detect issues at startup, not at runtime.
Finding an incompatibility during operation is far more disruptive than finding
it at startup.

---

## 3.12 Component 11 — Version Manager

**Purpose:**
The Version Manager manages the versioning of utilities and tracks the version
history of the framework.

**Responsibilities:**
- Maintain the version registry for all utilities.
- Evaluate version compatibility (is v1.2.3 compatible with the range >= 1.0.0 < 2.0.0?).
- Track version history (when each version was deployed).
- Support the deprecation workflow (mark versions as deprecated).

**Inputs:**
- Utility version declarations.
- Version compatibility ranges from dependency declarations.
- Deprecation requests.

**Outputs:**
- Version metadata to requesting components.
- Version compatibility evaluation results.
- Version history reports.

**Dependencies:**
- Version Utilities.
- Utility Catalog.

**Engineering Notes:**
Semantic versioning (SemVer 2.0) is the required versioning scheme for all
IIOS shared utilities. The major.minor.patch format is mandatory. Pre-release
versions (e.g., 1.0.0-alpha.1) are allowed in development and staging only.

---

## 3.13 Component 12 — Discovery Manager

**Purpose:**
The Discovery Manager provides the mechanism for IIOS components to discover
available utilities at runtime — finding all utilities of a given type or capability.

**Responsibilities:**
- Provide query capabilities over the registered utility set.
- Support discovery by namespace, category, capability, and version.
- Support discovery of all utilities implementing a given interface.
- Cache discovery results for performance.

**Inputs:**
- Discovery queries from IIOS components.
- Registry updates (to invalidate cached results).

**Outputs:**
- Lists of matching utilities to requesting components.

**Interactions:**
- Reads from the Utility Registry.
- Receives cache invalidation signals from the Registry.

**Dependencies:**
- Utility Registry.
- Caching Utilities.

**Lifecycle:**
Active from after Registry initialization through shutdown.

**Engineering Notes:**
The Discovery Manager enables the plugin architecture: a utility that supports
plugins can discover all registered plugin implementations without knowing them
in advance. This is the mechanism for extensibility without coupling.

---

## 3.14 Component 13 — Utility Validator

**Purpose:**
The Utility Validator verifies that utilities meet their documented contracts
and quality requirements before they are accepted into the framework.

**Responsibilities:**
- Run utility validation tests (contract tests, interface tests).
- Verify that the utility's interface matches its documentation.
- Run performance tests against defined benchmarks.
- Verify thread safety under concurrent load.
- Report validation results to the Quality Manager and Governance Manager.

**Inputs:**
- Utility to be validated.
- Utility contract specification.
- Performance benchmark targets.

**Outputs:**
- Validation report (PASS/FAIL with detail for each check).
- Quality metrics for the validated utility.

**Interactions:**
- Triggered by the Certification Manager during the utility promotion process.
- Reports to the Quality Manager.
- Reports to the Governance Manager.

**Dependencies:**
- Testing Utilities.
- Performance Utilities.
- Quality Manager.

**Lifecycle:**
Active during the development and certification lifecycle. Not active during
normal production operation.

**Engineering Notes:**
The Validator is a gate: a utility cannot be promoted to production status
without passing all validation checks. Partial passes (some checks passing,
some failing) do not qualify for promotion.

---

## 3.15 Component 14 — Documentation Manager

**Purpose:**
The Documentation Manager manages the creation, maintenance, and delivery of
utility documentation.

**Responsibilities:**
- Accept documentation contributions for utilities.
- Validate documentation completeness (required sections present).
- Publish documentation to the Utility Catalog.
- Track documentation freshness (documentation updated when utility changes).
- Generate documentation reports.

**Inputs:**
- Documentation contributions from utility authors.
- Documentation validation requests.
- Utility change events (triggers documentation freshness check).

**Outputs:**
- Validated documentation entries to the Utility Catalog.
- Documentation quality reports.
- Stale documentation alerts.

**Dependencies:**
- Utility Catalog.
- Document Utilities.
- Validation Utilities.

**Engineering Notes:**
A utility without documentation is not considered complete. The Documentation
Manager enforces this: utilities in the EXPERIMENTAL state may exist without
full documentation, but utilities in STABLE or PRODUCTION states require
complete documentation.

---

## 3.16 Component 15 — Quality Manager

**Purpose:**
The Quality Manager tracks and reports the quality dimensions of each shared
utility against the platform's quality standards.

**Responsibilities:**
- Maintain quality dimension scores for each utility.
- Aggregate quality scores into an overall Utility Quality Score (UQS).
- Compare quality scores against minimum thresholds.
- Identify quality regressions.
- Report quality trends over time.

**Inputs:**
- Validation results from the Utility Validator.
- Test coverage reports.
- Performance benchmark results.
- Documentation completeness scores.
- Usage metrics.

**Outputs:**
- Quality dimension scores per utility.
- Utility Quality Score (UQS) per utility.
- Quality regression alerts.
- Quality trend reports.

**Dependencies:**
- Utility Validator.
- Certification Manager.
- Metrics Helpers.

**Lifecycle:**
Active throughout the lifecycle. Quality is tracked continuously.

**Engineering Notes:**
The Quality Manager's quality scores are the primary governance input for the
Architecture Council's utility reviews. Utilities with declining quality scores
are flagged for architectural review.

---

## 3.17 Component 16 — Certification Manager

**Purpose:**
The Certification Manager manages the formal certification of utilities for
production use.

**Responsibilities:**
- Define certification requirements for each utility lifecycle state.
- Execute the certification process (validating all requirements are met).
- Issue certificates to qualifying utilities.
- Revoke certificates from utilities that regress below quality thresholds.
- Maintain the certification registry.

**Inputs:**
- Certification requests from utility authors.
- Validation results from the Utility Validator.
- Quality scores from the Quality Manager.
- Architecture Council approvals.

**Outputs:**
- Certification decisions (granted, denied, revoked).
- Certification registry updates.
- Certification reports.

**Interactions:**
- Requests validation from the Utility Validator.
- Requests quality assessment from the Quality Manager.
- Reports to the Governance Manager.

**Lifecycle:**
Active throughout the platform lifecycle.

**Certification Levels:**
- EXPERIMENTAL: no formal requirements. Used for in-development utilities.
- INCUBATING: basic documentation and tests required. Not suitable for production.
- STABLE: full documentation, test coverage > 90%, performance benchmarks met.
- PRODUCTION: all STABLE requirements plus security review and Architecture Council approval.
- DEPRECATED: utility is scheduled for retirement. No new usage permitted.
- RETIRED: utility is removed from the Registry and Catalog.

---

## 3.18 Component 17 — Monitoring Manager

**Purpose:**
The Monitoring Manager provides the framework-level observability for all shared
utilities — their operational health, performance, and usage.

**Responsibilities:**
- Collect health status from all registered utilities.
- Aggregate framework-level health (overall SUT health score).
- Track utility usage metrics.
- Detect anomalous utility behavior.
- Report utility health to the IIOS monitoring system.

**Inputs:**
- Health status from individual utilities.
- Usage metrics from the Metrics system.
- Performance data.

**Outputs:**
- SUT (Shared Utilities Tier) health score.
- Per-utility health status.
- Anomaly alerts.
- Monitoring reports.

**Dependencies:**
- Utility Registry.
- Metrics Helpers.
- Monitoring Helpers.
- Logging Helpers.

**Engineering Notes:**
Utility health is a component of the overall IIOS System Reliability Score (SRS).
If the SUT health degrades, it directly impacts the SRS and may trigger the OHS
DEGRADED tier for IIOS engines.

---

## 3.19 Component 18 — Governance Manager

**Purpose:**
The Governance Manager enforces the policies, standards, and rules that govern
all shared utilities in the IIOS platform.

**Responsibilities:**
- Enforce naming conventions for all utilities.
- Enforce documentation standards.
- Track governance compliance per utility.
- Generate governance reports.
- Receive and process governance exceptions.
- Interface with the Architecture Council for governance decisions.

**Inputs:**
- Utility metadata from all registered utilities.
- Policy definitions from the Architecture Council.
- Compliance check requests.
- Governance exception requests.

**Outputs:**
- Governance compliance reports.
- Non-compliance alerts.
- Governance exception decisions.

**Dependencies:**
- Utility Catalog.
- Documentation Manager.
- Certification Manager.
- Quality Manager.

**Engineering Notes:**
The Governance Manager does not block the production operation of the platform.
It enforces governance through visibility and reporting. Governance violations
are surfaced to the Architecture Council for action — the system does not halt
for a documentation deficiency.

---

*End of Part III*

---

# PART IV — UTILITY ORGANIZATION

## 4.1 Organization Overview

Shared utilities in IIOS are organized into a 10-layer hierarchy. Each layer
represents a distinct level of abstraction. Higher layers build on lower layers.
Dependencies flow downward only — no utility depends on a utility in a higher layer
or the same layer (except within the same layer's cohesive group).

---

## 4.2 Layer Dependency Rules

The fundamental rule of the IIOS utility organization:

`
LAYER 10 (Operational)    can depend on layers 1-9
LAYER 9  (Testing)        can depend on layers 1-8
LAYER 8  (Developer)      can depend on layers 1-7
LAYER 7  (Integration)    can depend on layers 1-6
LAYER 6  (Knowledge/AI)   can depend on layers 1-5
LAYER 5  (Business)       can depend on layers 1-4
LAYER 4  (Infrastructure) can depend on layers 1-3
LAYER 3  (Security)       can depend on layers 1-2
LAYER 2  (Platform)       can depend on layer 1 only
LAYER 1  (Core)           has NO dependencies on other utility layers
`

This is a strictly directed dependency graph with no cycles permitted.

---

## 4.3 Layer Hierarchy Diagram

`
+===========================================================+
|  LAYER 10: OPERATIONAL LAYER                              |
|  Scheduling Utilities | Resource Utilities                |
|  Monitoring Helpers | Metrics Helpers | Tracing Helpers   |
+===========================================================+
          |
+===========================================================+
|  LAYER 9: TESTING LAYER                                   |
|  Testing Utilities | Debug Utilities                      |
+===========================================================+
          |
+===========================================================+
|  LAYER 8: DEVELOPER LAYER                                 |
|  Developer Utilities | Reflection Utilities               |
+===========================================================+
          |
+===========================================================+
|  LAYER 7: INTEGRATION LAYER                               |
|  Notification Helpers | Document Utilities                |
|  Search Utilities | Migration Utilities                   |
+===========================================================+
          |
+===========================================================+
|  LAYER 6: KNOWLEDGE/AI LAYER                              |
|  AI Helper Utilities | Knowledge Utilities                |
|  Ontology Utilities                                       |
+===========================================================+
          |
+===========================================================+
|  LAYER 5: BUSINESS LAYER                                  |
|  Financial Utilities | Market Utilities                   |
|  Validation Utilities (business rules)                    |
+===========================================================+
          |
+===========================================================+
|  LAYER 4: INFRASTRUCTURE LAYER                            |
|  Concurrency Utilities | Memory Utilities                 |
|  Performance Utilities | Retry Utilities                  |
|  Scheduling Utilities | Resource Utilities                |
+===========================================================+
          |
+===========================================================+
|  LAYER 3: SECURITY LAYER                                  |
|  Encryption Utilities | Hashing Utilities                 |
|  Security Utilities | Auth Helpers                        |
|  Validation Utilities (security boundaries)               |
+===========================================================+
          |
+===========================================================+
|  LAYER 2: PLATFORM LAYER                                  |
|  File/Dir/Path | Serialization/Deserialization            |
|  JSON/YAML/XML/CSV | Compression | Caching               |
|  Date-Time | Timezone | String | Collection               |
|  Formatting | Conversion | UUID | Randomization           |
|  Version | Dependency | Localization | Identifier         |
+===========================================================+
          |
+===========================================================+
|  LAYER 1: CORE LAYER                                      |
|  Core Utilities | Configuration Utilities                 |
|  Environment Utilities | Math Utilities                   |
|  Statistical Utilities                                    |
+===========================================================+
`

---

## 4.4 Core Layer (Layer 1)

**Layer Purpose:** Foundational primitives. No IIOS dependency. Maximum stability.

**Contents:**
- Core Utilities (CORE): type checking, result types, contract enforcement.
- Configuration Utilities (CFG): configuration loading and validation.
- Environment Utilities (ENV): runtime environment detection.
- Math Utilities (MATH): arithmetic, rounding, precision.
- Statistical Utilities (STAT): descriptive statistics, rolling computations.

**Layer Constraints:**
- Zero dependencies on other IIOS utilities.
- Must have 100% test coverage.
- Changes require Architecture Council unanimous vote.
- No utility in this layer may perform I/O operations.

---

## 4.5 Platform Layer (Layer 2)

**Layer Purpose:** General-purpose platform capabilities needed across all domains.

**Contents:**
- File/Dir/Path Utilities: all file system operations.
- Serialization/Deserialization Utilities: object-to-format conversion.
- JSON/YAML/XML/CSV Utilities: format-specific operations.
- Compression Utilities: data compression.
- Caching Utilities: in-memory cache implementations.
- Date-Time and Timezone Utilities: temporal operations.
- String and Collection Utilities: data structure manipulation.
- Formatting and Conversion Utilities: display and conversion.
- UUID, Identifier, and Randomization Utilities: identity generation.
- Version Utilities: SemVer operations.
- Localization Utilities: regional formatting.

**Layer Constraints:**
- May depend only on Layer 1 utilities.
- No knowledge of IIOS business domain.
- Must be reusable in non-IIOS contexts.

---

## 4.6 Security Layer (Layer 3)

**Layer Purpose:** Security-specific capabilities. All components requiring
cryptography, access control, or input sanitization draw from this layer.

**Contents:**
- Encryption Utilities (ENC): AES-256, RSA, key management.
- Hashing Utilities (HASH): cryptographic hashing, password hashing, hash chains.
- Validation Utilities (VAL): security boundary validation.
- Security Utilities (SEC): injection prevention, sensitive value detection.
- Authentication Helpers (AUTHN): credential management.
- Authorization Helpers (AUTHZ): permission checking.

**Layer Constraints:**
- May depend on Layers 1–2.
- Security exceptions must not be swallowed (they must be escalated).
- All security utility changes require a dedicated security review.
- Security utilities are excluded from the automatic deprecation cycle until
  a replacement is fully certified.

---

## 4.7 Infrastructure Layer (Layer 4)

**Layer Purpose:** Platform infrastructure: concurrency, performance, resource
management, retry, and scheduling.

**Contents:**
- Concurrency Utilities (CONC): locks, semaphores, thread pools.
- Memory Utilities (MEM): memory monitoring and management.
- Performance Utilities (PERF): timing, profiling, benchmarking.
- Retry Utilities (RETRY): retry policies and strategies.
- Scheduling Utilities (SCHED): task scheduling.
- Resource Utilities (RES): resource pool management.

**Layer Constraints:**
- May depend on Layers 1–3.
- No knowledge of IIOS business domain.
- All concurrent utilities must have published thread safety guarantees.

---

## 4.8 Business Layer (Layer 5)

**Layer Purpose:** IIOS business domain utilities: financial calculations, market
operations, and business rule validation.

**Contents:**
- Financial Utilities (FIN): returns, Sharpe ratio, P&L, drawdown.
- Market Utilities (MKT): trading days, expiry dates, market sessions.
- Validation Utilities — business rules domain (shares namespace VAL with Layer 3).

**Layer Constraints:**
- May depend on Layers 1–4.
- Financial computations use decimal arithmetic (not floating-point) for precision.
- Market Utilities use the NSE market calendar.

---

## 4.9 Knowledge/AI Layer (Layer 6)

**Layer Purpose:** AI and machine learning support utilities.

**Contents:**
- AI Helper Utilities (AI): feature vectors, model output validation.
- Knowledge Utilities (KNW): knowledge base operations.
- Ontology Utilities (ONT): domain concept management.

**Layer Constraints:**
- May depend on Layers 1–5.
- No access to broker or execution systems.

---

## 4.10 Integration Layer (Layer 7)

**Layer Purpose:** Integration with external systems and cross-cutting concerns
that involve multiple domains.

**Contents:**
- Notification Helpers (NOTIF): alert and notification dispatch.
- Document Utilities (DOC): document processing.
- Search Utilities (SRCH): search and retrieval.
- Migration Utilities (MIG): data and schema migration.

**Layer Constraints:**
- May depend on Layers 1–6.
- All external integrations use the circuit breaker pattern from Layer 4.

---

## 4.11 Developer Layer (Layer 8)

**Layer Purpose:** Developer productivity utilities not intended for production
code paths.

**Contents:**
- Developer Utilities (DEV): feature flags, code generation.
- Reflection Utilities (REFL): runtime introspection.

**Layer Constraints:**
- DEV utilities are available in non-production environments only (enforced
  by the Environment Utility).
- REFL utilities are available in all environments but restricted to registered
  invocation targets.

---

## 4.12 Testing Layer (Layer 9)

**Layer Purpose:** Test infrastructure utilities.

**Contents:**
- Testing Utilities (TEST): fixtures, mocks, test data.
- Debug Utilities (DBG): inspection and debugging.

**Layer Constraints:**
- Available in all environments (production debug capability must remain available).
- DBG utilities in production emit at DEBUG level only (filtered from alerts).
- TEST utilities must not create persistent side effects in production.

---

## 4.13 Operational Layer (Layer 10)

**Layer Purpose:** Operational observability utilities.

**Contents:**
- Logging Helpers (LOG).
- Monitoring Helpers (MON).
- Metrics Helpers (MET).
- Tracing Helpers (TRACE).
- Dependency Utilities (DEP).

**Layer Constraints:**
- Must be available throughout the entire lifecycle, including during failure conditions.
- Logging Helpers must never throw exceptions (they absorb errors internally).
- Monitoring Helpers continue operating even when the monitored components are failing.

---

*End of Part IV*

---
# PART V — LIFECYCLE MANAGEMENT

## 5.1 Lifecycle Overview

Every shared utility in IIOS follows a defined 12-stage lifecycle. The lifecycle
governs a utility from the moment it is proposed through its active use and
eventually to its retirement. Each stage has defined entry criteria, activities,
and exit criteria.

---

## 5.2 Lifecycle State Diagram

`
PROPOSED
   |
   v
DESIGNING -----> REJECTED (design not accepted)
   |
   v
IMPLEMENTING --> ABANDONED (implementation discontinued)
   |
   v
EXPERIMENTAL --> (internal use only, early feedback)
   |
   v
INCUBATING -----> (testing, documentation, benchmarking)
   |
   v
STABLE ---------> (production-eligible; most utilities target this state)
   |
   v
PRODUCTION -----> (fully certified; used in critical paths)
   |
   v
DEPRECATED -----> (replacement exists; new usage prohibited)
   |
   v
SUNSET ---------> (usage wind-down period)
   |
   v
RETIRED --------> (removed from Registry and Catalog)
   |
   v
ARCHIVED      --> (documentation-only record)
`

---

## 5.3 Stage 1 — Registration

**Definition:** A utility enters the lifecycle at the Registration stage.
Registration is the formal declaration that a new shared utility is needed or
proposed.

**Entry Criteria:** Any IIOS engine owner, component team, or Architecture Council
member may propose a new utility by submitting a registration request.

**Activities:**
- Register the utility's proposed namespace, name, and category.
- Document the problem the utility solves.
- Identify the consuming components.
- Identify who will own the utility.
- Verify that no existing utility already solves the same problem.
- Obtain initial Architecture Council acknowledgement.

**Exit Criteria:** Registration is accepted by the Governance Manager.
The utility moves to the DESIGNING stage.

**Failure Mode:** A utility that duplicates an existing utility is rejected at
registration. The proposer is directed to the existing utility.

---

## 5.4 Stage 2 — Discovery

**Definition:** During Discovery, the utility team investigates the full scope
of the utility's requirements — what it must do, who will use it, and what
constraints apply.

**Entry Criteria:** Registration accepted.

**Activities:**
- Interview all identified consuming components.
- Document all required capabilities.
- Identify edge cases and platform-specific requirements.
- Identify security considerations.
- Document performance requirements.
- Identify all dependencies the utility will need.

**Exit Criteria:** Requirements specification is complete and reviewed by the
Architecture Council.

**Failure Mode:** Discovery reveals that the problem is too narrow (only one
consumer) or too broad (should be split into multiple utilities). Both outcomes
require redesign before proceeding.

---

## 5.5 Stage 3 — Initialization

**Definition:** The Initialization stage prepares the utility for use within the
IIOS framework — configuring it, connecting it to its dependencies, and starting
its runtime machinery.

**Entry Criteria:** The utility has passed the STABLE certification.

**Activities:**
- Configuration Loader provides the utility's configuration values.
- Dependency Manager resolves and injects dependencies.
- Utility executes its own initialization routine.
- Post-initialization health check is executed.
- Registry receives the utility and marks it INITIALIZED.

**Exit Criteria:** Health check passes. Utility registered in INITIALIZED state.

**Failure Mode:** Initialization failure. See Component 5 (Initialization Manager)
for full failure handling.

---

## 5.6 Stage 4 — Configuration

**Definition:** The Configuration stage ensures the utility's runtime behavior
is correctly parameterized for the current environment.

**Entry Criteria:** Utility initialized successfully.

**Activities:**
- Apply environment-specific configuration overrides.
- Apply any runtime operator-provided configuration (loaded from the configuration
  hierarchy).
- Validate all configuration values against the schema.
- Log the resolved configuration (with sensitive values redacted).

**Exit Criteria:** Configuration validated. Utility moves to CONFIGURED state.

**Failure Mode:** Configuration validation failure. Initialization is aborted.
Clear error messages identify the invalid configuration field.

---

## 5.7 Stage 5 — Activation

**Definition:** Activation is the transition from initialized-and-configured to
actively serving requests.

**Entry Criteria:** Configuration validated.

**Activities:**
- Utility executes its activation routine (start background workers, warm caches,
  open resource pools).
- Activation health check: verify the utility is ready to serve requests.
- Register ACTIVE state in the Registry.
- Emit ACTIVATED event to Event Bus.

**Exit Criteria:** Activation health check passes. ACTIVE state registered.

**Failure Mode:** Activation failure returns the utility to the INITIALIZED state.
The Lifecycle Manager may retry activation (up to 3 times). After 3 failures,
the utility is considered FAILED.

---

## 5.8 Stage 6 — Usage

**Definition:** The active operational stage. The utility is serving requests
from consuming components.

**Entry Criteria:** Activation complete.

**Activities:**
- Serve utility function requests from consuming components.
- Record usage metrics.
- Execute periodic health checks.
- Apply configuration changes detected by the Configuration Loader.
- Respond to lifecycle signals (pause, resume, configuration reload).

**Exit Criteria:** Utility exits usage on explicit shutdown, failure, or
deprecation transition.

**Key Metrics During Usage:**
- Request rate (requests per second).
- Error rate (errors per 1000 requests).
- Latency (p50, p95, p99).
- Availability (percentage of time accepting requests).

---

## 5.9 Stage 7 — Monitoring

**Definition:** Continuous health and performance observation throughout the
utility's active life.

**Entry Criteria:** Utility in ACTIVE state.

**Activities:**
- Execute periodic health probes.
- Collect and export usage metrics.
- Detect OHS degradation.
- Detect latency regression.
- Detect error rate spikes.
- Report health status to the Monitoring Manager.

**Health States During Monitoring:**
- HEALTHY: all metrics within thresholds.
- DEGRADED: one or more metrics outside warning thresholds.
- CRITICAL: one or more metrics outside critical thresholds. Alerts emitted.
- FAILED: utility is not responding to health probes.

---

## 5.10 Stage 8 — Optimization

**Definition:** Performance and quality improvement of an active utility based
on observed usage patterns.

**Entry Criteria:** Utility in ACTIVE state with at least 30 days of usage data.

**Activities:**
- Analyze usage patterns (most-called functions, typical input distributions).
- Identify performance bottlenecks.
- Benchmark current performance against the utility's design targets.
- Implement improvements (internal changes only; interface preserved).
- Re-run all validation checks after optimization.
- Deploy optimized version through the standard version process.

**Exit Criteria:** Optimization deployed and performance improvement confirmed.

**Engineering Notes:** Optimization must never change the utility's interface.
Callers must be unaffected by an optimization.

---

## 5.11 Stage 9 — Version Upgrade

**Definition:** The process of releasing a new version of an active utility.

**Entry Criteria:** New version ready for promotion; current version in ACTIVE state.

**Activities:**
- Validate the new version passes all certification requirements.
- Determine whether the change is backward-compatible.
  - Backward-compatible: bump minor version. Deploy transparently.
  - Breaking change: bump major version. Run deprecation process for old version.
- Deploy new version to staging. Verify in staging.
- Deploy new version to production.
- Monitor error rates and latency after deployment.
- Confirm successful deployment.

**Rollback Criteria:** If error rate increases or latency regresses within 30 minutes
of deployment, roll back to the previous version automatically.

---

## 5.12 Stage 10 — Deprecation

**Definition:** A utility is formally marked as deprecated when a replacement is
available or the utility's function is no longer needed.

**Entry Criteria:** A replacement utility is in STABLE or PRODUCTION state, or
the utility's function has been eliminated.

**Activities:**
- Announce deprecation with a transition timeline (minimum 60 days).
- Mark the utility DEPRECATED in the Registry and Catalog.
- Document the replacement or migration path.
- Notify all known consuming components.
- Block new usage registrations (existing users may continue).
- Set a sunset date.

**Engineering Rule:** No utility may be deprecated without a defined migration
path. If the capability is being eliminated entirely, the elimination rationale
must be documented.

---

## 5.13 Stage 11 — Replacement

**Definition:** The active migration period during which consumers transition
from a deprecated utility to its replacement.

**Entry Criteria:** Utility is DEPRECATED. Replacement exists.

**Activities:**
- Provide migration tooling (automated migration scripts where possible).
- Track which consumers have migrated.
- Assist consuming teams with the migration.
- Run both old and new utility in parallel to validate equivalence.
- Monitor migration progress against the sunset timeline.

**Exit Criteria:** All consumers have migrated to the replacement. Sunset date
is confirmed.

---

## 5.14 Stage 12 — Retirement

**Definition:** The final removal of a utility from the active registry.

**Entry Criteria:** All consumers have migrated. Sunset date reached.

**Activities:**
- Final usage audit (verify no remaining active callers).
- Deregister utility from the Registry.
- Archive documentation in the Catalog (RETIRED state — documentation preserved
  for historical reference).
- Remove utility from the codebase (via standard code removal process).
- Emit RETIRED event to the Event Bus.

**Exit Criteria:** Utility deregistered and removed. Documentation archived.

**Engineering Rule:** Retirement is irreversible. The utility's namespace is
reserved for 12 months after retirement to prevent accidental reuse.

---

*End of Part V*

---

# PART VI — DEPENDENCY FRAMEWORK

## 6.1 Dependency Framework Purpose

The Dependency Framework defines how shared utilities declare, resolve, and
manage their dependencies on each other and on external resources. A well-managed
dependency graph is essential for:
- Predictable initialization order.
- Avoiding circular dependencies.
- Understanding the impact of a utility change.
- Controlling the blast radius of a utility failure.

---

## 6.2 Dependency Registration

Every shared utility declares its dependencies explicitly in its utility descriptor.
Dependency declarations are not inferred from the code — they are stated explicitly,
validated during the build process, and tracked by the Dependency Manager.

**Dependency declaration format:**
- **Name:** The namespace and name of the required utility.
- **Version range:** The compatible version range (SemVer range notation).
- **Optionality:** Whether the dependency is mandatory or optional.
- **Purpose:** A brief description of why this dependency is needed.

**Engineering rule:** Undeclared dependencies are a build error. A utility that
uses another utility without declaring it in its descriptor will fail the
compatibility check during the build phase.

---

## 6.3 Dependency Resolution

Dependency resolution is the process of determining, for each utility, which
specific version of each declared dependency will be used at runtime.

**Resolution process:**
1. The Dependency Manager reads all utility descriptors.
2. For each dependency declaration, the Version Manager identifies the highest
   compatible version available.
3. If multiple utilities require the same dependency at incompatible versions,
   a version conflict is reported (initialization halts).
4. The resolved dependency map is computed (utility → list of resolved dependency
   instances).
5. The initialization order is derived from the resolved dependency map using
   topological sort.

**Resolution outputs:**
- For each utility: the specific resolved instance of each declared dependency.
- The initialization order for the Lifecycle Manager.
- Any version conflicts or missing dependency errors.

---

## 6.4 Dependency Injection Concepts

IIOS uses constructor-based dependency injection for shared utilities. When the
Initialization Manager creates a utility instance, it passes the resolved
dependencies as constructor arguments.

**Injection principles:**
- Dependencies are injected at initialization time, not retrieved lazily at
  call time.
- A utility cannot substitute a different implementation for an injected
  dependency after initialization.
- Dependencies are never retrieved from a global registry at call time (this
  is the service-locator anti-pattern, which is prohibited).
- Testability: because dependencies are injected, tests can inject mock
  implementations without modifying the utility under test.

---

## 6.5 Optional Dependencies

An optional dependency is one that the utility can function without. When an
optional dependency is not available, the utility adjusts its behavior (using
a fallback or disabling a capability that requires that dependency).

**Optional dependency rules:**
- Every optional dependency has a defined behavior for the case when it is
  absent.
- The utility must function correctly without optional dependencies — reduced
  capability, not failure.
- Optional dependency absence is logged at INFO level (not ERROR).
- Optional dependencies that become permanently absent trigger a warning after
  48 hours (the dependency may have been retired without updating the utility).

---

## 6.6 Mandatory Dependencies

A mandatory dependency is one that the utility cannot function without. If a
mandatory dependency is not available, the utility itself cannot initialize.

**Mandatory dependency rules:**
- A utility whose mandatory dependency fails to initialize is itself treated
  as a failed initialization.
- The failure propagates upward: any utility that has the failed utility as a
  mandatory dependency also fails.
- The Lifecycle Manager reports the root cause (the first failure in the
  dependency chain) to accelerate diagnosis.
- Mandatory dependency unavailability is an ERROR-level event.

---

## 6.7 Circular Dependency Prevention

A circular dependency exists when utility A depends on utility B, and utility B
depends on utility A (directly or through intermediaries). Circular dependencies
make topological sort impossible and indicate a design problem.

**Prevention mechanisms:**
- The Layer Hierarchy rules prevent most cycles: a utility in Layer 2 cannot
  depend on a utility in Layer 5 (which would create a cycle if the Layer 5
  utility depends on Layer 2 utilities).
- The Dependency Manager performs cycle detection during the dependency graph
  construction phase (before any initialization begins).
- A detected cycle is a CRITICAL build error — it must be resolved before the
  system can start.

**Cycle resolution approaches:**
- If A depends on B and B depends on A, one dependency is likely unnecessary —
  remove it.
- If both directions are genuinely needed, an event-based or callback mechanism
  can decouple them.
- If they are so tightly coupled that neither can function without the other,
  they should be merged into a single utility.

---

## 6.8 Version Compatibility

Version compatibility defines whether a specific version of a utility is usable
in place of another version within the same major version line.

**Compatibility rules (SemVer):**
- **Major version change:** Breaking change. Old and new versions are incompatible.
  Migration is required.
- **Minor version change:** Backward-compatible addition. A consumer requiring
  v1.2.0 can use v1.3.0 (which adds capabilities) but not v1.1.0 (which may
  lack the capabilities the consumer needs).
- **Patch version change:** Backward-compatible fix. A consumer requiring v1.2.0
  can use any v1.2.x.

**Version range declarations:** All dependency declarations use ranges, not
exact versions:
- >= 1.2.0 < 2.0.0: any minor or patch update within major version 1.
- >= 2.0.0 < 3.0.0: any minor or patch update within major version 2.

---

## 6.9 Conflict Resolution

Version conflicts occur when two utilities require incompatible versions of a
shared dependency.

**Conflict resolution process:**
1. The Dependency Manager identifies the conflict and lists all parties.
2. The Version Manager determines whether a version exists that satisfies all
   requirements simultaneously (version unification).
3. If unification is possible: deploy the unified version. All parties are satisfied.
4. If unification is impossible: one of the conflicting parties must update its
   dependency declaration.
5. If neither party can be updated immediately: a temporary fork of one utility
   version may be maintained (requires Architecture Council approval).

---

## 6.10 Isolation

Dependency isolation ensures that the failure of one utility does not cascade to
unrelated utilities.

**Isolation mechanisms:**
- Optional dependencies are isolated: their failure does not propagate.
- The Lifecycle Manager tracks dependency chains: it knows exactly which utilities
  would be affected by the failure of any given utility.
- Circuit breakers (from the Infrastructure Layer) are applied to any utility
  that performs I/O operations (file, network, database).

---

## 6.11 Plugin Dependency

Plugins introduce dynamic dependencies that are not known at initialization time.
Plugin dependencies are managed separately from static dependencies.

**Plugin dependency rules:**
- A plugin declares its own dependencies in its plugin descriptor.
- The Plugin Manager validates plugin dependencies before accepting the plugin.
- Plugin dependencies must be available at the time the plugin is registered.
- If a plugin's dependency becomes unavailable, the plugin is deactivated
  automatically (not the host utility).

---

## 6.12 Shared Resource Management

Some utilities share underlying resources (e.g., a connection pool or a thread
pool). These shared resources are managed by the Resource Manager and injected
as dependencies.

**Shared resource rules:**
- Shared resources are owned by the Resource Manager, not by any individual utility.
- Utilities acquire resources through the Resource Manager's interface.
- A utility that holds a resource beyond its operation must release it immediately
  after use.
- Resource hold time is monitored. Resources held for more than the defined maximum
  duration are forcibly reclaimed.

---

## 6.13 Engineering Governance

Dependency management is governed by the following rules:
- All dependencies are declared explicitly (no implicit dependencies).
- The dependency graph is reviewed at every Architecture Council quarterly review.
- Utilities with more than 8 direct dependencies are flagged for architectural
  review.
- The utility with the most dependents (the "most critical utility") receives
  additional quality investment.
- Dependency debt (deprecated dependencies still in use) is tracked and addressed
  within 60 days.

---

*End of Part VI*

---

# PART VII — QUALITY FRAMEWORK

## 7.1 Quality Framework Purpose

The Quality Framework defines the dimensions of quality for shared utilities and
specifies the minimum quality standards that utilities must meet to achieve each
certification level. Quality is not a single dimension — it is a composite of
12 distinct engineering properties.

---

## 7.2 Utility Quality Score (UQS)

Every shared utility has an overall Utility Quality Score (UQS), computed as a
weighted composite of its 12 quality dimension scores.

**UQS formula:**
`
UQS = (Reusability     × 0.10)
    + (Reliability     × 0.15)
    + (Performance     × 0.10)
    + (Scalability     × 0.05)
    + (Maintainability × 0.10)
    + (Security        × 0.15)
    + (Thread Safety   × 0.10)
    + (Documentation   × 0.05)
    + (Consistency     × 0.05)
    + (Compatibility   × 0.05)
    + (Observability   × 0.05)
    + (Op. Stability   × 0.05)
= 0.0 to 1.0
`

**UQS thresholds:**
- PRODUCTION certification: UQS >= 0.90
- STABLE certification: UQS >= 0.75
- INCUBATING: UQS >= 0.50
- EXPERIMENTAL: no minimum UQS

---

## 7.3 Quality Dimension 1 — Reusability

**Definition:** The degree to which a utility can be applied in diverse contexts
without modification.

**Measurement criteria:**
- Number of distinct consuming components.
- Number of use cases covered by the utility's interface.
- Absence of hardcoded assumptions about the calling context.
- Parameterization of variable behaviors.

**Score 1.0:** Used by > 10 distinct components in > 3 different layers. No
hardcoded context assumptions.

**Score 0.5:** Used by 3–10 components. Minor context assumptions that limit
applicability to some contexts.

**Score 0.0:** Used by 1 component only. Significant hardcoded assumptions that
prevent use in other contexts.

**Improvement guidance:** When a utility's reusability score is below threshold,
investigate: Are there hardcoded assumptions that could be parameterized? Are
there missing capabilities that would enable more components to use it?

---

## 7.4 Quality Dimension 2 — Reliability

**Definition:** The probability that the utility produces the correct result for
all valid inputs within its documented contract.

**Measurement criteria:**
- Test coverage (line, branch, condition coverage).
- Number of production defects per 1000 invocations.
- Edge case coverage.
- Property-based test results.

**Score 1.0:** > 98% coverage. Zero production defects in the last 90 days.
Full edge case coverage. Property-based tests pass.

**Score 0.5:** > 85% coverage. < 2 production defects per 1000 invocations.
Partial edge case coverage.

**Score 0.0:** < 70% coverage. > 10 production defects per 1000 invocations.

**Minimum for PRODUCTION:** > 95% coverage, < 1 defect per 10,000 invocations.

---

## 7.5 Quality Dimension 3 — Performance

**Definition:** The degree to which the utility meets its defined latency and
throughput targets.

**Measurement criteria:**
- p99 latency at rated load.
- Throughput at rated load.
- Performance consistency (latency variance).
- Resource efficiency (CPU and memory per unit of work).

**Score 1.0:** All latency targets met at 2x rated load. Resource utilization
within design budget.

**Score 0.5:** All latency targets met at rated load. Minor resource overrun.

**Score 0.0:** Latency targets missed at rated load.

**IIOS performance note:** Core utility operations (UUID generation, timestamp
formatting, hash computation) must complete in < 1 ms. Data serialization for
typical IIOS payloads must complete in < 5 ms.

---

## 7.6 Quality Dimension 4 — Scalability

**Definition:** The ability of the utility to maintain performance as load
increases and as the platform grows.

**Measurement criteria:**
- Performance at 10x current load.
- Behavior at edge-case input sizes (very large inputs).
- Scaling characteristics (linear, sub-linear, or super-linear).

**Score 1.0:** Performance scales linearly or sub-linearly with load.
Tested at 10x current load without degradation.

**Score 0.5:** Performance scales at most quadratically. Tested at 5x load.

**Score 0.0:** Performance degrades rapidly. Not tested above current load.

---

## 7.7 Quality Dimension 5 — Maintainability

**Definition:** The ease with which the utility can be understood, modified,
and extended by a developer unfamiliar with its implementation.

**Measurement criteria:**
- Code complexity metrics (cyclomatic complexity per function).
- Average time to diagnose and fix a reported defect.
- Developer self-reported comprehension score (from code review feedback).
- Documentation-to-code ratio.

**Score 1.0:** All functions have cyclomatic complexity < 5. Average defect
resolution time < 2 hours. Complete documentation.

**Score 0.5:** Most functions have complexity < 10. Average defect resolution
< 8 hours.

**Score 0.0:** Functions with complexity > 20. Average defect resolution > 24 hours.

---

## 7.8 Quality Dimension 6 — Security

**Definition:** The degree to which the utility is free from security
vulnerabilities and actively prevents security risks.

**Measurement criteria:**
- Static analysis security findings.
- Dependency vulnerability findings.
- Security test coverage (injection, overflow, authentication bypass).
- Compliance with OWASP guidelines.
- Cryptographic practice correctness.

**Score 1.0:** Zero static analysis findings. Zero vulnerable dependencies.
Full security test coverage. Passes OWASP compliance checklist.

**Score 0.5:** Zero HIGH or CRITICAL static analysis findings. No known
critical dependency vulnerabilities.

**Score 0.0:** Any HIGH or CRITICAL static analysis finding. Known critical
dependency vulnerability.

**Minimum for PRODUCTION:** Score 1.0 on all security-adjacent utilities
(Security, Encryption, Hashing, Authentication, Authorization layers).

---

## 7.9 Quality Dimension 7 — Thread Safety

**Definition:** The correctness of the utility under concurrent invocation from
multiple threads.

**Measurement criteria:**
- Thread safety guarantees documented.
- Concurrent load tests pass without data races or consistency violations.
- Synchronization mechanisms correct and minimal.
- No deadlocks detected under concurrent load.

**Score 1.0:** Fully thread-safe for all documented thread safety levels.
Concurrent load tests pass at 10x typical concurrency.

**Score 0.5:** Thread-safe for read operations. Write operations require
external synchronization (documented).

**Score 0.0:** Not safe for concurrent use. Produces incorrect results or
crashes under concurrent invocation.

**Thread safety levels:**
- IMMUTABLE: The utility's state never changes after initialization. Fully
  thread-safe by design.
- THREAD-SAFE: All operations are safe for concurrent use without external
  synchronization.
- NOT-THREAD-SAFE: Callers must provide external synchronization.

---

## 7.10 Quality Dimension 8 — Documentation

**Definition:** The completeness and quality of the utility's documentation.

**Measurement criteria:**
- Required documentation sections present.
- Documentation accuracy (matches implementation).
- Example quality (examples are correct and useful).
- Documentation freshness (updated with each release).

**Score 1.0:** All required sections present. All examples correct and
runnable. Documentation updated with every release. Reviewed by a consumer
team member.

**Score 0.5:** Most required sections present. Some examples. Updated in
last 2 releases.

**Score 0.0:** Missing critical sections. No examples. Not updated in > 2 releases.

**Required documentation sections:**
1. Purpose and problem solved.
2. Capabilities (what the utility does).
3. Interface reference.
4. Configuration reference.
5. Examples.
6. Performance characteristics.
7. Thread safety guarantees.
8. Known limitations.
9. Version history.
10. Migration guide (if applicable).

---

## 7.11 Quality Dimension 9 — Consistency

**Definition:** The degree to which the utility behaves consistently with
platform conventions and its own documented behavior.

**Measurement criteria:**
- Naming convention compliance.
- Error handling pattern compliance.
- Interface convention compliance.
- Behavioral consistency across inputs (same class of input always handled the
  same way).

**Score 1.0:** Full naming and convention compliance. Behavior is fully
predictable and consistent across all input classes.

**Score 0.5:** Minor naming deviations. Mostly consistent behavior with
documented exceptions.

**Score 0.0:** Significant naming violations. Inconsistent behavior that
cannot be predicted from the documentation.

---

## 7.12 Quality Dimension 10 — Compatibility

**Definition:** The degree to which the utility works correctly across all
supported deployment environments.

**Measurement criteria:**
- Tests pass on all target platforms (Windows, Linux, Docker).
- Character encoding handling correct.
- File path handling correct on all platforms.
- No platform-specific assumptions in the implementation.

**Score 1.0:** Tests pass on all three platforms. No platform-specific code
paths. Encoding and path handling fully portable.

**Score 0.5:** Tests pass on Linux and Docker. Minor issues on Windows
(Windows is development only, so score 0.5 is acceptable for most utilities).

**Score 0.0:** Tests fail on any production platform (Linux, Docker).

---

## 7.13 Quality Dimension 11 — Observability

**Definition:** The degree to which the utility's internal state and behavior
can be observed through metrics, logs, and health checks.

**Measurement criteria:**
- Key operations instrumented with metrics.
- Health check implemented.
- Log output correctly formatted and leveled.
- Errors clearly logged with context.

**Score 1.0:** All key operations have metrics. Health check implemented.
All log events correctly formatted. Error logs include full context.

**Score 0.5:** Most key operations have metrics. Health check implemented.

**Score 0.0:** No metrics. No health check. Unformatted log output.

---

## 7.14 Quality Dimension 12 — Operational Stability

**Definition:** The degree to which the utility operates reliably in production
over time without requiring intervention.

**Measurement criteria:**
- Uptime (percentage of time in HEALTHY state).
- Auto-recovery success rate.
- Mean time between failures.
- Operations team intervention frequency.

**Score 1.0:** > 99.9% uptime over last 90 days. Auto-recovery succeeds
in > 95% of failure events. No operations interventions required.

**Score 0.5:** > 99.0% uptime. Auto-recovery succeeds in > 80% of failure
events. < 2 operations interventions in last 90 days.

**Score 0.0:** < 99.0% uptime. Frequent operations interventions required.

---

*End of Part VII*

---
# PART VIII — UTILITY GOVERNANCE

## 8.1 Governance Purpose

Governance of shared utilities ensures that the framework remains coherent,
high-quality, and productive as the platform evolves. Without governance,
utility libraries tend to become fragmented (many utilities that almost solve
the same problem), stale (utilities that are no longer fit for purpose), and
unmaintained (utilities with no clear owner).

IIOS utility governance is designed to prevent these failure modes through
clear ownership, explicit standards, regular reviews, and structured processes.

---

## 8.2 Naming Conventions

All shared utilities follow a strict naming convention. Consistent names allow
developers to predict a utility's location and behavior from its name alone.

**Namespace naming:**
- All uppercase abbreviation of the utility domain.
- 2–6 characters.
- Examples: CORE, CFG, DT, HASH, FIN, MKT, STAT.
- Namespaces are registered in the Utility Catalog and are unique.

**Utility function naming:**
- Verb-noun format for operations: compute_, ormat_, parse_, alidate_,
  convert_, generate_, check_, get_, list_, create_.
- Adjective-noun format for properties: is_valid_, is_present_, is_empty_.
- Consistent verb vocabulary: the same verb has the same meaning across all utilities.

**File and module naming:**
- Module name = namespace in lowercase + _util: dt_util, hash_util, in_util.
- No abbreviations in module names beyond the namespace prefix.
- All lowercase with underscores (snake_case).

**Constant naming:**
- All uppercase with underscores: MAX_RETRY_ATTEMPTS, DEFAULT_HASH_ALGORITHM.
- Module-level constants preferred over class-level constants.
- No magic numbers — all numeric constants are named.

**Verb vocabulary:**
- parse: convert a string representation to a structured type.
- ormat: convert a structured type to a string representation.
- serialize: convert an object to a storable/transmittable format.
- deserialize: convert a stored/transmitted format back to an object.
- alidate: check that a value conforms to a schema or constraint.
- compute: perform a mathematical or algorithmic calculation.
- generate: create a new value (ID, UUID, random value).
- convert: change a value from one type or unit to another.
- get: retrieve a value that already exists.
- list: retrieve a collection of values.
- create: instantiate a new object.
- check: return a boolean based on a condition.

---

## 8.3 Packaging Standards

**Package organization:**
- Each utility namespace corresponds to a package.
- Packages are organized under shared_utilities/.
- Each package has: main module, test module, and documentation.

**Package directory structure:**
`
shared_utilities/
  core_util/
    core_util.py         (main implementation)
    core_util_test.py    (tests)
    CATALOG.md           (documentation)
  dt_util/
    dt_util.py
    dt_util_test.py
    CATALOG.md
  ... (one directory per namespace)
`

**Package version file:**
- Each package has a VERSION file containing the current SemVer version.
- The version is bumped according to SemVer rules with each release.

**Dependency declaration file:**
- Each package has a DEPENDENCIES.toml file declaring all dependencies
  (name, version range, optionality, purpose).

---

## 8.4 Ownership

Every shared utility has exactly one owner. Ownership conveys:
- Accountability for the utility's quality.
- Authority to approve changes to the utility.
- Responsibility for the utility's documentation.
- Responsibility for responding to defect reports.
- Responsibility for executing the deprecation and retirement lifecycle.

**Ownership tiers:**

**Architecture Council:** Owns Core Layer utilities (CORE, MATH, STAT) and the
framework governance components. Changes to these utilities require unanimous
Architecture Council vote.

**Engine Owners:** Utilities primarily serving a specific engine (e.g., Market
Utilities serve the Market Intelligence engine) are owned by the responsible
engine team. Other engines can use these utilities but cannot modify them without
the owner's approval.

**Platform Team:** Infrastructure Layer utilities (CONC, MEM, PERF, RETRY, SCHED)
are owned by the Platform Team responsible for IIOS infrastructure.

**Security Team:** Security Layer utilities (ENC, HASH, SEC, AUTHN, AUTHZ) are
owned by the Security Team.

**Unowned utilities are not permitted.** A utility in the STABLE or PRODUCTION
state without an identified owner must be claimed within 30 days or is deprecated.

---

## 8.5 Version Policy

**SemVer 2.0** is the mandatory versioning standard for all IIOS shared utilities.

**Version increment rules:**
- **PATCH** (x.y.Z): Bug fixes only. No new capabilities. No interface changes.
  Safe to update automatically.
- **MINOR** (x.Y.0): New capabilities added backward-compatibly. No breaking
  interface changes. Safe to update for consuming components that do not use
  the new capabilities.
- **MAJOR** (X.0.0): Breaking changes. All consuming components must review
  and update their usage.

**Version freeze policy:**
- A PRODUCTION utility's major version may not be incremented more than once
  per quarter.
- PATCH releases may be deployed at any time.
- MINOR releases require 48-hour advance notice to consuming teams.
- MAJOR releases require the full deprecation process (minimum 60 days).

---

## 8.6 Approval Process

**PATCH releases:** Owner approval only. Automated tests must pass.

**MINOR releases:** Owner approval + one Architecture Council review.
Automated tests must pass. Performance benchmarks must not regress.

**MAJOR releases:** Full deprecation process. Architecture Council formal review.
All consuming components must be notified and given migration time.

**New utility proposal:** Architecture Council design review. Duplicate detection.
Ownership assignment. Layer assignment. Initial documentation.

**Utility retirement:** Architecture Council approval required. All consuming
components must have migrated. Sunset period enforced.

---

## 8.7 Documentation Standards

All shared utilities must meet the following documentation standards before
reaching STABLE certification:

**Utility-level documentation (CATALOG.md):**
- Purpose and problem solved.
- Layer and namespace.
- Version and certification status.
- List of all capabilities.
- Performance characteristics (typical latency and throughput).
- Thread safety guarantees.
- Configuration reference (all configuration keys with types and defaults).
- Known limitations and edge cases.
- Usage examples (at least 3 realistic examples).
- Related utilities (alternative or complementary utilities).
- Migration guides (if this utility replaces a previous utility).
- Changelog.

**Function-level documentation:**
- Every public function must have: description, parameter descriptions,
  return value description, exception/error behavior documentation.
- Functions with non-obvious behavior must include examples.
- Functions with performance-sensitive behavior must include a complexity note
  (O(1), O(n), etc.).

**Documentation freshness policy:**
- Documentation must be updated as part of the same release that contains
  the code change.
- A release without updated documentation fails the documentation quality check.

---

## 8.8 Review Process

**Weekly:** Engine owners review utility usage metrics for anomalies.

**Monthly:**
- Platform Team reviews utility performance metrics.
- Security Team reviews security utility scan results.
- Quality Manager generates monthly quality score report.
- Deprecated utilities with no migration progress receive escalation.

**Quarterly:**
- Architecture Council reviews the full utility registry.
- Quality scores reviewed. Utilities below threshold scheduled for improvement.
- Dependency graph reviewed for unnecessary complexity.
- Long-deprecated utilities reviewed for forced retirement.
- New utility proposals from the previous quarter reviewed.
- Governance compliance report presented.

**Annual:**
- Full framework architecture review.
- Layer structure review.
- Naming convention review.
- Version policy review.

---

## 8.9 Certification

Certification is the formal process that a utility must pass to advance through
its lifecycle states.

**Certification requirements by level:**

**INCUBATING:**
- Owner identified.
- Basic documentation (purpose, capabilities).
- Basic tests (coverage > 70%).
- Architecture Council review (10-minute slot at monthly meeting).

**STABLE:**
- Full documentation complete.
- Test coverage > 90%.
- Performance benchmarks met.
- No HIGH or CRITICAL security findings.
- Architecture Council review and approval.
- At least one consuming team has used the utility and provided feedback.

**PRODUCTION:**
- All STABLE requirements.
- Test coverage > 95%.
- Security review complete.
- Operational review (30 days in STABLE without incidents).
- Architecture Council formal vote (simple majority).
- Documentation reviewed by a non-author team member.
- Performance benchmarks met at 2x rated load.

---

## 8.10 Deprecation Policy

Utilities are deprecated when:
- A better replacement exists.
- The capability the utility provides is no longer needed.
- The utility has become unmaintainable.
- The utility fails to meet quality standards and cannot be improved.

**Deprecation procedure:**
1. Owner proposes deprecation with justification and migration path.
2. Architecture Council approves (simple majority).
3. Utility marked DEPRECATED in Registry and Catalog.
4. All consuming teams notified.
5. Sunset period begins (minimum 60 days; extended if many consumers need migration time).
6. During sunset: migration assistance provided. New usage blocked.
7. At sunset date: usage audit. If all consumers have migrated, retire.
8. If consumers remain at sunset: extend sunset by 30 days per consumer that
   needs more time (up to 90 day maximum extension).
9. After final extension: forced retirement. Remaining consumers are blocked
   from deploying until they migrate.

---

## 8.11 Continuous Improvement

The Shared Utilities Framework is continuously improved based on:
- Defect analysis: patterns in defects reveal structural problems.
- Developer experience surveys: friction points reveal documentation or design issues.
- Performance monitoring: performance trends reveal optimization opportunities.
- Usage analytics: usage patterns reveal missing capabilities and over-engineered utilities.
- Architecture Council retrospectives: quarterly reflection on framework effectiveness.

**Improvement backlog:** A prioritized backlog of framework improvements is maintained
by the Architecture Council. Items are addressed in priority order during each
development cycle.

---

*End of Part VIII*

---

# PART IX — ENGINEERING CONSTITUTION

## 9.1 Constitution Purpose

The Engineering Constitution for the IIOS Shared Utilities Framework defines
110 binding engineering rules organized into 13 categories. These rules are
non-negotiable design constraints. Every shared utility, regardless of domain,
must comply with all applicable rules.

Rules are identified by code: SUT-[CATEGORY]-[NUMBER].

---

## 9.2 Category 1 — Reuse (SUT-REUSE)

**SUT-REUSE-001:** Before implementing any capability, search the Utility Catalog
for an existing utility that provides it. Re-implementing existing capabilities
is prohibited.

**SUT-REUSE-002:** A utility must be designed to serve at least 3 distinct consumers.
A utility with only one consumer is not a shared utility — it is a private module.

**SUT-REUSE-003:** Utilities must not be tailored to the specific requirements of
a single consuming engine. They must be general enough to be useful to any engine
that has the same type of problem.

**SUT-REUSE-004:** When a capability can be achieved by composing two existing utilities,
it must be composed — not reimplemented as a third utility.

**SUT-REUSE-005:** Utility interfaces must be designed from the consumer's perspective,
not the implementer's. The API must express what the consumer wants to do, not
how the utility does it.

**SUT-REUSE-006:** Utilities must not embed business logic specific to IIOS trading
decisions. Business logic belongs in the engine layers, not in shared utilities.
(Exception: the Business Layer utilities provide business-domain calculations,
not decisions.)

**SUT-REUSE-007:** Utilities that are candidates for use outside IIOS (general-purpose
utilities) must be designed with that possibility in mind and must not contain
any IIOS-specific assumptions.

**SUT-REUSE-008:** Existing utilities may be extended via the plugin or extension
mechanism. Modifying an existing utility to add a single-consumer feature is
prohibited.

---

## 9.3 Category 2 — Consistency (SUT-CONS)

**SUT-CONS-001:** All utility namespaces, function names, and parameter names follow
the naming convention defined in Section 8.2. No deviations without Architecture
Council approval.

**SUT-CONS-002:** All utilities in the same namespace use the same error handling
patterns. Mixing patterns within a namespace is prohibited.

**SUT-CONS-003:** All utilities that return collections use the same collection types
for the same semantic purposes (list for ordered sequences, set for unique items,
dict for key-value maps).

**SUT-CONS-004:** All utilities follow the same logging convention (using the Logging
Helper utility). Custom log formatting within utilities is prohibited.

**SUT-CONS-005:** All utilities follow the same metric naming pattern defined by the
Metrics Helpers. Custom metric naming is prohibited.

**SUT-CONS-006:** All utilities that perform I/O operations use the same timeout
approach and the same timeout configuration key format.

**SUT-CONS-007:** All utilities that have configuration use the same configuration
loading pattern (via the Configuration Loader). Hardcoded configuration values
in utility code are prohibited (they must be loaded from configuration).

**SUT-CONS-008:** All utilities that can fail produce structured error results using
the platform's Result type. Unstructured exceptions are only permitted for genuinely
unexpected failures.

**SUT-CONS-009:** All utility functions that return empty results use the same
representation for "no result" (the platform's None/Optional pattern). Using
different representations for the same semantic (empty collection, None, empty
string) is prohibited.

**SUT-CONS-010:** All utilities that are stateful define their state transitions
explicitly and document them.

---

## 9.4 Category 3 — Dependency Management (SUT-DEP)

**SUT-DEP-001:** Every dependency is declared explicitly in the DEPENDENCIES.toml
file. Undeclared dependencies are a build error.

**SUT-DEP-002:** A utility in Layer N may not depend on a utility in Layer N or
higher. All dependencies are downward-only.

**SUT-DEP-003:** Circular dependencies are prohibited. Any design that would create
a circular dependency must be restructured.

**SUT-DEP-004:** A utility must not have more than 8 direct dependencies. Utilities
approaching this limit are flagged for architectural review.

**SUT-DEP-005:** Optional dependencies must have a documented fallback behavior
that is tested as thoroughly as the primary behavior.

**SUT-DEP-006:** External library dependencies (non-IIOS) require Architecture
Council approval. Each external library must be justified with: what IIOS capability
it provides, why no existing utility provides it, and what the licensing implications are.

**SUT-DEP-007:** A utility must not dynamically discover or load other utilities
at runtime (except the Discovery Manager, which is responsible for this). Runtime
utility lookup is the service-locator anti-pattern and is prohibited.

**SUT-DEP-008:** Dependency version ranges must be as permissive as possible while
ensuring correctness. Pinning to exact versions is prohibited (it prevents the
platform from resolving conflicts).

---

## 9.5 Category 4 — Initialization (SUT-INIT)

**SUT-INIT-001:** Every utility must be initializable without side effects visible
outside the framework. Initialization must not modify shared state, start background
processes, or open network connections without the framework's explicit direction.

**SUT-INIT-002:** Initialization must be idempotent. Calling initialization twice
on a utility that is already initialized must be a no-op (or return an error that
the caller can handle).

**SUT-INIT-003:** Initialization must complete within the utility's defined
initialization time budget. Utilities that require expensive initialization must
perform that work asynchronously after the synchronous initialization phase.

**SUT-INIT-004:** Initialization failure must produce a clear, actionable error
message that identifies the exact configuration or dependency issue.

**SUT-INIT-005:** A utility must perform a self-test as part of initialization.
The self-test must verify that the utility's core capabilities are functioning
correctly in the current environment.

**SUT-INIT-006:** After initialization, the utility must register its health probe
with the Monitoring Manager.

---

## 9.6 Category 5 — Lifecycle (SUT-LIFE)

**SUT-LIFE-001:** Every utility implements the full lifecycle interface
(initialize, activate, health_check, shutdown). Partial lifecycle implementations
are not permitted.

**SUT-LIFE-002:** Lifecycle transitions must be atomic from the perspective of
the framework. A utility that is partially in ACTIVE and partially in SHUTTING_DOWN
is an error state.

**SUT-LIFE-003:** Utilities must respect shutdown signals. When the platform sends
a shutdown signal, a utility must complete all in-flight operations and release
all resources within the shutdown timeout.

**SUT-LIFE-004:** Shutdown must be reversible during the DEPRECATED and SUNSET stages:
the utility can be re-activated if a consumer is found to still need it.

**SUT-LIFE-005:** Utilities must tolerate being activated, deactivated, and
re-activated multiple times. This is used in restart scenarios.

**SUT-LIFE-006:** Every lifecycle event (INITIALIZED, ACTIVATED, DEGRADED, FAILED,
SHUTDOWN) is emitted to the Event Bus. Utilities must not suppress lifecycle events.

---

## 9.7 Category 6 — Security (SUT-SEC)

**SUT-SEC-001:** Utilities must never log or emit sensitive values (credentials,
tokens, API keys, personal data). Log parameters containing potentially sensitive
values must be redacted before logging.

**SUT-SEC-002:** Utilities that process external input (data from files, network,
configuration) must validate and sanitize all inputs before processing.

**SUT-SEC-003:** Utilities must not use deprecated or known-weak cryptographic
algorithms. Only algorithms approved in the Security Layer specification are permitted.

**SUT-SEC-004:** Secret values (encryption keys, passwords, tokens) must never be
hardcoded in utility code or configuration. They must always be loaded from the
secrets manager at runtime.

**SUT-SEC-005:** Utilities that perform dynamic invocation (calling code by name)
must restrict the callable targets to an explicit allowlist. Unrestricted dynamic
invocation is prohibited.

**SUT-SEC-006:** Utilities that process file paths from external sources must
sanitize the paths to prevent directory traversal attacks before using them.

**SUT-SEC-007:** Utilities that perform XML processing must disable external entity
loading (XXE prevention) by default.

**SUT-SEC-008:** Utilities that compare security-sensitive values (hashes, tokens)
must use constant-time comparison to prevent timing attacks.

**SUT-SEC-009:** All security-related utility changes (Security Layer) require a
dedicated security code review before deployment.

**SUT-SEC-010:** Utilities must not store sensitive values in process memory longer
than necessary. After use, sensitive values must be cleared.

---

## 9.8 Category 7 — Documentation (SUT-DOC)

**SUT-DOC-001:** Every utility must have a CATALOG.md in its package directory
before reaching STABLE certification.

**SUT-DOC-002:** Every public function must have a documentation block (purpose,
parameters, return value, exceptions/errors).

**SUT-DOC-003:** Documentation must be updated in the same release as the code change.
A release with code changes but no documentation update fails the documentation check.

**SUT-DOC-004:** Every utility must document its performance characteristics:
typical latency, throughput, and resource usage at rated load.

**SUT-DOC-005:** Every utility must document its thread safety guarantees explicitly.
The default is NOT-THREAD-SAFE unless explicitly documented otherwise.

**SUT-DOC-006:** Every utility must document its known limitations and edge cases.
A utility without a known-limitations section is assumed to have undiscovered limitations.

**SUT-DOC-007:** Usage examples must be realistic. Examples based on toy inputs
that do not represent the actual IIOS use case are insufficient.

**SUT-DOC-008:** Migration guides must be provided for any MINOR release that
changes existing behavior (even backward-compatibly) and for all MAJOR releases.

---

## 9.9 Category 8 — Testing (SUT-TEST)

**SUT-TEST-001:** Every shared utility must have unit tests achieving > 90%
coverage (line, branch, and condition) before reaching STABLE certification.

**SUT-TEST-002:** Every utility must have tests for: null inputs, empty inputs,
boundary values, and maximum-size inputs.

**SUT-TEST-003:** Utilities with random behavior (UUID generation, randomization)
must be tested using seeded random generators to produce deterministic test results.

**SUT-TEST-004:** Utilities with time-dependent behavior must be tested using the
injectable clock from the Date-Time Utility, not the system clock.

**SUT-TEST-005:** Thread-safe utilities must be tested under concurrent load with
at least 10 simultaneous threads.

**SUT-TEST-006:** Utilities with performance requirements must have benchmark tests
that verify those requirements are met.

**SUT-TEST-007:** Tests must be deterministic. Tests that pass sometimes and fail
sometimes (flaky tests) are treated as defects and must be fixed.

**SUT-TEST-008:** Tests must be isolated. A test must not depend on the execution
order of other tests or on shared mutable state.

**SUT-TEST-009:** Security utilities must have specific tests for injection attempts,
overflow attempts, and invalid input patterns.

**SUT-TEST-010:** Every utility must have a minimal integration test that verifies
it can be initialized and used in the actual IIOS environment (not just in isolation).

---

## 9.10 Category 9 — Performance (SUT-PERF)

**SUT-PERF-001:** Every utility function must have a defined performance budget
(maximum expected latency for a typical input at rated concurrency).

**SUT-PERF-002:** Utilities that are called in the critical path of a trading cycle
must meet their latency budget at p99, not just p50.

**SUT-PERF-003:** Utilities must not perform synchronous I/O (file reads, network
calls) in functions that are called synchronously in the trading cycle.

**SUT-PERF-004:** Utilities must not perform unbounded memory allocations. All
collection utilities must have defined maximum size limits.

**SUT-PERF-005:** Utilities that cache data must expose cache hit/miss rates as
metrics, and cache sizes must be configurable.

**SUT-PERF-006:** A performance regression (p99 latency increases > 20% between
versions) is a MINOR version bump blocker. The regression must be investigated
before release.

**SUT-PERF-007:** Utility benchmarks are re-run at every MINOR and MAJOR release.
PATCH releases require benchmark re-run only if the change is in a performance-sensitive
code path.

**SUT-PERF-008:** Utilities must not spin-wait. Any waiting must be done using
proper blocking or async primitives with appropriate timeouts.

---

## 9.11 Category 10 — Compatibility (SUT-COMPAT)

**SUT-COMPAT-001:** All shared utilities must pass their full test suite on Linux
(the production environment) and Docker (the container environment).

**SUT-COMPAT-002:** Utilities must not use file path separators directly. They must
use the Path Utility for all path construction.

**SUT-COMPAT-003:** All text file operations default to UTF-8 encoding. Utilities
must not assume platform-default encoding.

**SUT-COMPAT-004:** Utilities must not assume a specific timezone for the system
clock. All time operations use UTC unless explicitly converting.

**SUT-COMPAT-005:** Utilities must not use integer types that have platform-dependent
sizes. All integer types must be explicitly sized.

**SUT-COMPAT-006:** Utility behavior must not differ between debug and production
builds, except for performance characteristics.

**SUT-COMPAT-007:** Utilities must not require specific environment variables to
be present unless they declare those variables as mandatory in their documentation.

---

## 9.12 Category 11 — Governance (SUT-GOV)

**SUT-GOV-001:** Every utility must have an identified owner. Utilities without
an owner within 30 days of reaching STABLE state are deprecated automatically.

**SUT-GOV-002:** Version bumps must follow SemVer rules exactly. Underversioning
(a breaking change released as a patch version) is a governance violation.

**SUT-GOV-003:** Deprecation decisions cannot be reversed once announced for more
than 30 days. If the decision was made in error, a new utility replaces the deprecated
one.

**SUT-GOV-004:** Utilities in the PRODUCTION state may not be changed without an
Architecture Council review.

**SUT-GOV-005:** The Utility Catalog must reflect the current state of every
utility within 24 hours of any change.

**SUT-GOV-006:** No utility may be deployed to production without passing the
Certification Manager's certification check for its target certification level.

**SUT-GOV-007:** All governance exceptions (deviations from any SUT rule) must be
approved by the Architecture Council and documented in the Utility Catalog entry
for the affected utility.

---

## 9.13 Category 12 — Extensibility (SUT-EXT)

**SUT-EXT-001:** Utilities expected to need behavioral variation across contexts
must define extension points before reaching STABLE state.

**SUT-EXT-002:** Extension points must be documented as fully as the utility's
primary interface.

**SUT-EXT-003:** Adding a new extension point to a utility is a MINOR version change.
Removing or changing an existing extension point is a MAJOR version change.

**SUT-EXT-004:** The default behavior of a utility with extension points must be
correct and complete without any extensions registered. Extensions add capability;
they do not define base behavior.

**SUT-EXT-005:** Utilities must not make unvalidated assumptions about the
behavior of registered extensions. All extension return values must be validated
before use.

**SUT-EXT-006:** Extension registration must be idempotent. Registering the same
extension twice must be a no-op (or a well-defined error, not undefined behavior).

---

## 9.14 Category 13 — Future Evolution (SUT-FUT)

**SUT-FUT-001:** Every utility design decision that was non-obvious must be
documented in the utility's CATALOG.md in an Engineering Decision Records section.
Future engineers must be able to understand why the utility was designed the way
it was.

**SUT-FUT-002:** Utilities must not expose implementation details in their interfaces.
Today's implementation is not tomorrow's implementation. The interface must describe
what, not how.

**SUT-FUT-003:** Utilities must tolerate unexpected inputs gracefully (reject with
a clear error) rather than crashing. This ensures new callers with different
assumptions do not cause cascade failures.

**SUT-FUT-004:** All constants in utilities must be configurable, or at minimum
documented with their rationale. Magic constants that cannot be overridden create
inflexibility.

**SUT-FUT-005:** When a utility's design could be interpreted in two ways,
choose the design that is harder to misuse. Ease of correct use is more valuable
than flexibility of incorrect use.

**SUT-FUT-006:** Utilities must be designed for replacement. Every utility will
eventually be deprecated and replaced. The design should not create barriers to
being replaced (e.g., by spreading implementation-specific assumptions across
many consumers).

**SUT-FUT-007:** New IIOS capabilities that require new utility support are
proposed as utility additions before they are implemented as engine-local code.
The utility path is evaluated first.

**SUT-FUT-008:** The framework itself (the 18 governance components) is subject
to the same quality standards as the utilities it governs. The framework has its
own lifecycle, documentation, and quality management.

---

*End of Part IX*

---
# PART X — READINESS CHECKLIST

## 10.1 Readiness Framework

The Readiness Checklist is the formal evaluation gate that every shared utility
must pass before being certified at its target level. Each check is classified
as HARD (blocking — the utility cannot advance without a PASS) or SOFT
(advisory — must be addressed within 30 days of certification).

---

## 10.2 Domain 1 — Utility Ready

| # | Check | Type | Criteria |
|---|-------|------|---------|
| 1.1 | Single responsibility verified | HARD | Utility has exactly one clearly defined purpose |
| 1.2 | Namespace assigned | HARD | Namespace registered in Utility Catalog |
| 1.3 | Layer assignment verified | HARD | Layer correctly identifies dependency constraints |
| 1.4 | Owner identified | HARD | Named owner with contact on record |
| 1.5 | Duplicate check passed | HARD | No existing utility provides the same capability |
| 1.6 | Consumer count verified | HARD | At least 3 distinct consumers identified |
| 1.7 | Interface review complete | HARD | Architecture Council reviewed interface design |
| 1.8 | Extension points defined | SOFT | Extension points documented if applicable |
| 1.9 | Constants externalized | HARD | No magic numbers in implementation |
| 1.10 | Result type consistent | HARD | All functions use platform Result types |

---

## 10.3 Domain 2 — Dependency Ready

| # | Check | Type | Criteria |
|---|-------|------|---------|
| 2.1 | All dependencies declared | HARD | DEPENDENCIES.toml complete and accurate |
| 2.2 | Layer rule complied | HARD | No upward dependencies detected |
| 2.3 | No circular dependencies | HARD | Dependency graph is acyclic |
| 2.4 | Version ranges specified | HARD | No exact version pins in declarations |
| 2.5 | Optional dependencies handled | HARD | Each optional dependency has fallback behavior |
| 2.6 | Dependency count within budget | SOFT | Fewer than 8 direct dependencies |
| 2.7 | External library justified | HARD | All external dependencies Council-approved |
| 2.8 | Service-locator pattern absent | HARD | No runtime utility lookup within utility code |
| 2.9 | Plugin dependencies validated | SOFT | Plugin descriptors declare their dependencies |
| 2.10 | Shared resources released | HARD | All acquired resources released on completion |

---

## 10.4 Domain 3 — Version Ready

| # | Check | Type | Criteria |
|---|-------|------|---------|
| 3.1 | SemVer format correct | HARD | Version follows x.y.z format |
| 3.2 | Version bump classification correct | HARD | Patch/minor/major correctly applied |
| 3.3 | VERSION file present | HARD | Package directory contains VERSION file |
| 3.4 | Changelog updated | HARD | Changes described in changelog |
| 3.5 | Migration guide provided | HARD | Required for MINOR+ changes affecting behavior |
| 3.6 | Previous version compatibility tested | HARD | New version tested with consumers of previous |
| 3.7 | Version registered in Catalog | HARD | Catalog reflects new version |
| 3.8 | Deprecation notices reviewed | SOFT | Any deprecated dependencies addressed in this version |

---

## 10.5 Domain 4 — Performance Ready

| # | Check | Type | Criteria |
|---|-------|------|---------|
| 4.1 | Performance budgets defined | HARD | All functions have documented latency budgets |
| 4.2 | Benchmark tests pass | HARD | All functions meet p99 latency budget |
| 4.3 | Load tests pass | HARD | Performance maintained at rated load |
| 4.4 | No synchronous I/O in critical path | HARD | Critical path functions are I/O-free |
| 4.5 | Memory allocation bounded | HARD | No unbounded allocations |
| 4.6 | Cache metrics exported | SOFT | Caching utilities export hit/miss rates |
| 4.7 | No spin-waits | HARD | All waiting uses proper blocking/async primitives |
| 4.8 | Performance regression checked | HARD | p99 latency within 20% of previous version |
| 4.9 | Resource efficiency profiled | SOFT | CPU and memory per unit of work documented |
| 4.10 | 2x load test passed | HARD | PRODUCTION level: performance maintained at 2x load |

---

## 10.6 Domain 5 — Security Ready

| # | Check | Type | Criteria |
|---|-------|------|---------|
| 5.1 | No sensitive values logged | HARD | Log statements audited for sensitive data |
| 5.2 | All external inputs validated | HARD | All externally-sourced inputs go through VAL |
| 5.3 | Approved cryptographic algorithms only | HARD | No deprecated or weak algorithms used |
| 5.4 | No hardcoded secrets | HARD | Zero hardcoded credentials, keys, or tokens |
| 5.5 | Dynamic invocation restricted | HARD | All dynamic invocations use allowlist |
| 5.6 | Path traversal prevention | HARD | External path inputs sanitized |
| 5.7 | XXE prevention in XML processing | HARD | External entity loading disabled |
| 5.8 | Constant-time comparison used | HARD | Security-sensitive comparisons are constant-time |
| 5.9 | Static analysis passed | HARD | Zero HIGH/CRITICAL findings |
| 5.10 | Security test coverage | HARD | Security utilities: injection and overflow tests present |
| 5.11 | Dependency vulnerabilities checked | HARD | No known CRITICAL dependency vulnerabilities |
| 5.12 | Security code review complete | HARD | Security Layer utilities: dedicated security review done |

---

## 10.7 Domain 6 — Documentation Ready

| # | Check | Type | Criteria |
|---|-------|------|---------|
| 6.1 | CATALOG.md present | HARD | Package directory contains CATALOG.md |
| 6.2 | All required sections present | HARD | 10 required sections in CATALOG.md |
| 6.3 | All public functions documented | HARD | Description, parameters, return, errors for each |
| 6.4 | Performance characteristics documented | HARD | Latency and throughput documented |
| 6.5 | Thread safety documented | HARD | Explicit thread safety guarantee stated |
| 6.6 | Known limitations documented | SOFT | Limitations section present and non-trivial |
| 6.7 | Usage examples present | HARD | At least 3 realistic examples |
| 6.8 | Examples correct and runnable | HARD | Examples tested as part of test suite |
| 6.9 | Documentation reviewed by non-author | HARD | PRODUCTION level: external reviewer signature |
| 6.10 | Documentation freshness confirmed | HARD | Updated in current release |

---

## 10.8 Domain 7 — Operational Ready

| # | Check | Type | Criteria |
|---|-------|------|---------|
| 7.1 | Health probe implemented | HARD | Utility responds to framework health probe |
| 7.2 | Metrics exported | HARD | At least 3 operational metrics published |
| 7.3 | Log output correctly formatted | HARD | All log events use platform structured format |
| 7.4 | Error context logged | HARD | All errors logged with sufficient context for diagnosis |
| 7.5 | Graceful shutdown implemented | HARD | Utility cleans up all resources on shutdown signal |
| 7.6 | Lifecycle events emitted | HARD | All state transitions emit Event Bus events |
| 7.7 | Configuration change handled | SOFT | Utility responds to runtime configuration changes |
| 7.8 | 30-day production stability record | HARD | PRODUCTION level: 30 days in STABLE without incidents |
| 7.9 | Operations runbook written | SOFT | Common failure scenarios documented for operators |
| 7.10 | Alert rules defined | SOFT | Operational alerts configured for the utility |

---

## 10.9 Domain 8 — Certification Ready

| # | Check | Type | Criteria |
|---|-------|------|---------|
| 8.1 | Architecture Council review complete | HARD | Review meeting occurred and recorded |
| 8.2 | UQS above threshold | HARD | UQS >= 0.75 for STABLE, >= 0.90 for PRODUCTION |
| 8.3 | All HARD checks PASS | HARD | Zero HARD check failures |
| 8.4 | SOFT check plan in place | HARD | All SOFT failures have an owner and target date |
| 8.5 | Test coverage verified | HARD | Coverage > 90% (STABLE) or > 95% (PRODUCTION) |
| 8.6 | Owner acceptance confirmed | HARD | Owner has formally accepted responsibility |
| 8.7 | Consuming team feedback incorporated | SOFT | At least one consuming team provided feedback |
| 8.8 | Certification record created | HARD | Certification entry in the Certification Manager |

---

## 10.10 Certification Matrix

`
CERTIFICATION  HARD  SOFT  UQS     COVERAGE  COUNCIL   SECURITY  OPS-STABILITY
               PASS  PLAN  MIN     MIN       VOTE      REVIEW    REQUIRED
                                                        
INCUBATING      no   no    0.50    70%       Ack       No        No
STABLE          YES  YES   0.75    90%       Approve   Layer 3+  No
PRODUCTION      YES  YES   0.90    95%       Vote      Always    30 days
`

---

*End of Part X*

---

# SUPPLEMENT A — UTILITY CATALOG REFERENCE

## A.1 All 57 Utility Categories

| # | Namespace | Category | Layer | Owner Tier | IIOS Priority |
|---|-----------|---------|-------|------------|---------------|
| 1 | CORE | Core Utilities | Layer 1 | Architecture Council | Critical |
| 2 | CFG | Configuration Utilities | Layer 1 | Architecture Council | Critical |
| 3 | ENV | Environment Utilities | Layer 1 | Platform Team | Critical |
| 4 | FILE | File Utilities | Layer 2 | Platform Team | High |
| 5 | DIR | Directory Utilities | Layer 2 | Platform Team | High |
| 6 | PATH | Path Utilities | Layer 2 | Platform Team | High |
| 7 | SER | Serialization Utilities | Layer 2 | Platform Team | High |
| 8 | DESER | Deserialization Utilities | Layer 2 | Platform Team | High |
| 9 | JSON | JSON Utilities | Layer 2 | Platform Team | High |
| 10 | YAML | YAML Utilities | Layer 2 | Platform Team | High |
| 11 | XML | XML Utilities | Layer 2 | Platform Team | Medium |
| 12 | CSV | CSV Utilities | Layer 2 | Platform Team | High |
| 13 | COMP | Compression Utilities | Layer 2 | Platform Team | Medium |
| 14 | ENC | Encryption Utilities | Layer 3 | Security Team | Critical |
| 15 | HASH | Hashing Utilities | Layer 3 | Security Team | Critical |
| 16 | VAL | Validation Utilities | Layer 3 | Security Team | Critical |
| 17 | SEC | Security Utilities | Layer 3 | Security Team | Critical |
| 18 | AUTHN | Authentication Helpers | Layer 3 | Security Team | Critical |
| 19 | AUTHZ | Authorization Helpers | Layer 3 | Security Team | Critical |
| 20 | FMT | Formatting Utilities | Layer 2 | Platform Team | High |
| 21 | CONV | Conversion Utilities | Layer 2 | Platform Team | High |
| 22 | DT | Date-Time Utilities | Layer 2 | Architecture Council | Critical |
| 23 | TZ | Timezone Utilities | Layer 2 | Platform Team | High |
| 24 | L10N | Localization Utilities | Layer 2 | Platform Team | Low |
| 25 | ID | Identifier Utilities | Layer 2 | Architecture Council | Critical |
| 26 | UUID | UUID Utilities | Layer 2 | Platform Team | Critical |
| 27 | RAND | Randomization Utilities | Layer 2 | Platform Team | High |
| 28 | MATH | Math Utilities | Layer 1 | Architecture Council | Critical |
| 29 | STAT | Statistical Utilities | Layer 1 | Architecture Council | Critical |
| 30 | FIN | Financial Utilities | Layer 5 | Engine Owners | Critical |
| 31 | MKT | Market Utilities | Layer 5 | Engine Owners | Critical |
| 32 | STR | String Utilities | Layer 2 | Platform Team | High |
| 33 | COL | Collection Utilities | Layer 2 | Platform Team | High |
| 34 | MEM | Memory Utilities | Layer 4 | Platform Team | Medium |
| 35 | PERF | Performance Utilities | Layer 4 | Platform Team | High |
| 36 | CACHE | Caching Utilities | Layer 2 | Platform Team | High |
| 37 | RETRY | Retry Utilities | Layer 4 | Platform Team | Critical |
| 38 | SCHED | Scheduling Utilities | Layer 4 | Platform Team | High |
| 39 | CONC | Concurrency Utilities | Layer 4 | Platform Team | High |
| 40 | RES | Resource Utilities | Layer 4 | Platform Team | High |
| 41 | LOG | Logging Helpers | Layer 10 | Architecture Council | Critical |
| 42 | MON | Monitoring Helpers | Layer 10 | Architecture Council | Critical |
| 43 | MET | Metrics Helpers | Layer 10 | Architecture Council | Critical |
| 44 | TRACE | Tracing Helpers | Layer 10 | Architecture Council | High |
| 45 | NOTIF | Notification Helpers | Layer 7 | Platform Team | High |
| 46 | AI | AI Helper Utilities | Layer 6 | Engine Owners | High |
| 47 | KNW | Knowledge Utilities | Layer 6 | Engine Owners | High |
| 48 | ONT | Ontology Utilities | Layer 6 | Engine Owners | Medium |
| 49 | DOC | Document Utilities | Layer 7 | Platform Team | Medium |
| 50 | SRCH | Search Utilities | Layer 7 | Platform Team | Medium |
| 51 | VER | Version Utilities | Layer 2 | Architecture Council | High |
| 52 | MIG | Migration Utilities | Layer 7 | Platform Team | Medium |
| 53 | TEST | Testing Utilities | Layer 9 | Platform Team | High |
| 54 | DBG | Debug Utilities | Layer 9 | Platform Team | Medium |
| 55 | DEV | Developer Utilities | Layer 8 | Platform Team | Medium |
| 56 | REFL | Reflection Utilities | Layer 8 | Platform Team | Low |
| 57 | DEP | Dependency Utilities | Layer 10 | Architecture Council | High |

---

# SUPPLEMENT B — DEPENDENCY MATRIX

## B.1 Core Layer Dependencies

| Utility | Depends On | Direction | Mandatory |
|---------|-----------|-----------|-----------|
| CORE | (none) | — | — |
| CFG | CORE | Downward | Yes |
| ENV | CORE | Downward | Yes |
| MATH | CORE | Downward | Yes |
| STAT | MATH | Downward | Yes |

## B.2 Platform Layer Dependencies (selected)

| Utility | Depends On | Notes |
|---------|-----------|-------|
| DT | CORE, TZ | DT depends on TZ for timezone conversions |
| TZ | CORE | No other dependencies |
| UUID | RAND, CORE | Uses RAND for v4 randomness |
| CACHE | CORE, PERF | Uses PERF for TTL tracking |
| SER | CORE, JSON, YAML | Format selection based on configuration |
| STR | CORE | Pure string operations |
| COL | CORE | Pure collection operations |
| RETRY | CORE, DT | Uses DT for backoff timing |
| VER | CORE, STR | Parses version strings |

## B.3 Business Layer Dependencies

| Utility | Depends On | Notes |
|---------|-----------|-------|
| FIN | MATH, STAT, DT | Financial math requires all three |
| MKT | DT, TZ, FIN | Market session uses DT, MKT depends on FIN |
| VAL (business) | CORE, DT, FIN | Business rule validation uses domain utilities |

## B.4 Critical Path Utilities

The following utilities are in the critical latency path of every trading cycle:
- DT (timestamp generation for every event).
- UUID (correlation ID generation for every event).
- LOG (event logging).
- HASH (audit chain computation).
- STAT (rolling statistics for engine scores).
- FIN (financial metrics in real-time).
- MKT (market session checks at each cycle).

These utilities have the most stringent latency requirements and the highest
quality investment priority.

---

# SUPPLEMENT C — LIFECYCLE REFERENCE

## C.1 Lifecycle State Summary

| State | Description | Duration |
|-------|-------------|---------|
| PROPOSED | Registered as needed | Hours to days |
| DESIGNING | Requirements being defined | Days to weeks |
| IMPLEMENTING | Under development | Weeks |
| EXPERIMENTAL | Early testing, single consumer | Weeks to months |
| INCUBATING | Multi-consumer testing, basic quality | Months |
| STABLE | Production-eligible, full quality | Indefinite |
| PRODUCTION | Fully certified, critical-path eligible | Indefinite |
| DEPRECATED | Replacement available | Minimum 60 days |
| SUNSET | Consumer migration in progress | 60–150 days |
| RETIRED | Removed from Registry | Permanent |
| ARCHIVED | Documentation-only record | Permanent |

## C.2 Lifecycle Transition Authority

| Transition | Authority |
|-----------|-----------|
| PROPOSED to DESIGNING | Owner (self-service) |
| DESIGNING to IMPLEMENTING | Architecture Council ack |
| IMPLEMENTING to EXPERIMENTAL | Owner (self-service) |
| EXPERIMENTAL to INCUBATING | Owner + basic cert |
| INCUBATING to STABLE | Architecture Council approval |
| STABLE to PRODUCTION | Architecture Council vote |
| Any to DEPRECATED | Architecture Council approval |
| DEPRECATED to RETIRED | Architecture Council + usage audit |

---

# SUPPLEMENT D — VERSION COMPATIBILITY GUIDE

## D.1 Compatibility Rules Summary

| Change Type | Version Bump | Consumer Action Required | Migration Time |
|------------|-------------|--------------------------|----------------|
| Bug fix (behavior unchanged) | PATCH | None | Immediate |
| New function added | MINOR | None (old code still works) | Optional upgrade |
| New parameter (with default) | MINOR | None (default preserves old behavior) | Optional upgrade |
| New required parameter | MAJOR | Must update all call sites | 60+ days |
| Function removed | MAJOR | Must remove all call sites | 60+ days |
| Function renamed | MAJOR | Must update all call sites | 60+ days |
| Return type changed | MAJOR | Must update all consumers | 60+ days |
| Error type changed | MINOR or MAJOR | Review error handling | 30–60 days |
| Performance regression | PATCH or MINOR | None | Immediate (fix required) |
| Security fix (interface unchanged) | PATCH | None | Immediate |

## D.2 Compatibility Testing Protocol

Before releasing any version, the following compatibility tests must pass:
1. Consumers at the previous PATCH version can use the new version without changes.
2. Consumers at the previous MINOR version can use the new version without changes
   (unless this is a MAJOR release).
3. All consumers in the IIOS codebase are tested against the new version before release.

---

# SUPPLEMENT E — NAMING REFERENCE

## E.1 Approved Verb Vocabulary

| Verb | Meaning | Example |
|------|---------|---------|
| compute | Calculate a result | compute_sharpe_ratio |
| format | Convert to string representation | format_currency |
| parse | Convert from string to structure | parse_timestamp |
| serialize | Convert object to storage format | serialize_trade |
| deserialize | Convert from storage format to object | deserialize_trade |
| validate | Check conformance to constraints | validate_symbol |
| generate | Create a new value | generate_uuid |
| convert | Change type or unit | convert_to_log_return |
| get | Retrieve existing value | get_market_session |
| list | Retrieve collection | list_trading_days |
| create | Instantiate new object | create_candle |
| check | Return boolean | check_is_trading_day |
| load | Read from persistent store | load_config |
| save | Write to persistent store | save_config |
| register | Add to a registry | register_utility |
| resolve | Find and return | resolve_dependency |
| publish | Send to subscribers | publish_event |
| subscribe | Register for notifications | subscribe_event |
| compress | Reduce storage size | compress_data |
| decompress | Restore from compressed | decompress_data |
| hash | Compute hash | hash_content |
| encrypt | Apply encryption | encrypt_value |
| decrypt | Reverse encryption | decrypt_value |
| sanitize | Remove dangerous content | sanitize_path |

## E.2 Naming Anti-Patterns (Prohibited)

| Anti-Pattern | Example | Reason Prohibited |
|-------------|---------|-------------------|
| Abbreviation beyond namespace | get_ts() | Non-obvious; use get_timestamp() |
| Manager suffix in function | manage_config() | Non-specific; use load_/save_/update_ |
| Do/process prefix | do_validation() | Non-specific; use validate_ |
| Mixed case styles | GetTimestamp() | Must be snake_case |
| Numeric suffixes | validate2() | Indicates duplication; refactor instead |
| Generic names | handle() | Too broad; always include noun |

---

# SUPPLEMENT F — ENGINEERING DECISION RECORDS

## F.1 Framework Design Decisions

| Record ID | Decision | Rationale | Date |
|-----------|---------|-----------|------|
| SUT-EDR-001 | 57 utility categories in 10 layers | Provides full coverage without over-fragmentation | Inception |
| SUT-EDR-002 | Directed dependency graph, no cycles | Enables topological initialization and blast radius control | Inception |
| SUT-EDR-003 | Constructor injection for dependencies | Testability and explicitness over service locator convenience | Inception |
| SUT-EDR-004 | SemVer 2.0 mandatory for all utilities | Industry standard; tooling support; consumer-predictable compatibility | Inception |
| SUT-EDR-005 | Core Layer has zero external dependencies | Maximum stability; any external dependency creates a coupling risk | Inception |
| SUT-EDR-006 | UQS weighted toward Reliability (0.15) and Security (0.15) | IIOS operates with real capital; reliability and security are existential | Inception |
| SUT-EDR-007 | 60-day minimum deprecation period | Empirical: most consumers need 4–8 weeks to plan and execute migrations | Inception |
| SUT-EDR-008 | PRODUCTION certification requires 30-day stability record | A utility with 0 days of stable operation cannot be called production-ready | Inception |

---

# SUPPLEMENT G — COMMON ANTI-PATTERNS

## G.1 Eight Utility Anti-Patterns

### Anti-Pattern 1 — God Utility

**Description:** A single utility that handles many unrelated concerns.

**Signs:** The utility name contains "and", "or", or "utils" with no domain qualifier.
Functions in the utility are used by completely different teams for completely
different purposes.

**Problem:** Changes to one area of the utility can unexpectedly affect another.
Testing is complex. The utility becomes unmaintainable.

**Correct approach:** Split into multiple single-responsibility utilities.

---

### Anti-Pattern 2 — Private Module as Shared Utility

**Description:** A module that is only used by one engine is promoted to the shared
utility library to provide a central home, even though it has no other consumers.

**Problem:** The utility library grows with utilities that are not genuinely reusable,
creating noise and maintenance burden.

**Correct approach:** A utility must have at least 3 distinct consumers to be
shared. Single-consumer modules remain private to their engine.

---

### Anti-Pattern 3 — Leaking Implementation Details

**Description:** The utility's interface exposes the types, data structures, or
conventions of its internal implementation, coupling consumers to the implementation.

**Signs:** Consumers need to import internal types from the utility. Interface
types are implementation-specific (e.g., named after a specific library).

**Problem:** Changing the implementation requires changing every consumer.

**Correct approach:** The interface uses platform-standard types only. Implementation
types stay internal.

---

### Anti-Pattern 4 — Configuration-Heavy Utility

**Description:** A utility requires extensive configuration to use correctly, making
it difficult to use and easy to misconfigure.

**Signs:** 20+ configuration keys. New consumers spend hours reading documentation
to configure the utility.

**Problem:** High configuration burden reduces productivity and increases
misconfiguration defects.

**Correct approach:** Sensible defaults for all configuration. A utility with good
defaults requires zero configuration for the common case.

---

### Anti-Pattern 5 — Utility Dependency on Engine State

**Description:** A shared utility reads or writes state belonging to a specific
IIOS engine.

**Signs:** The utility imports from an engine module. The utility reads from a
database table owned by an engine.

**Problem:** The utility is tightly coupled to the engine. It cannot be tested
independently. It cannot be used by other engines.

**Correct approach:** Utilities receive their inputs through their interface.
They do not reach out to external state.

---

### Anti-Pattern 6 — Undocumented Behavior Change

**Description:** A utility's behavior changes in a new version without adequate
documentation or version bump.

**Signs:** Consumers report unexpected behavior after a patch release. The changelog
does not mention the behavior change.

**Problem:** Consumers cannot detect or plan for the change. Subtle bugs appear.

**Correct approach:** Any behavior change, even a bug fix where "wrong behavior"
was relied upon, is explicitly documented. Breaking behavior changes are MAJOR version bumps.

---

### Anti-Pattern 7 — Retry Without Idempotency Check

**Description:** A retry utility is applied to non-idempotent operations.

**Signs:** A function that places orders or modifies records is wrapped in a
retry decorator.

**Problem:** A transient failure after partial execution causes the operation
to be executed twice. Orders are doubled. Records are corrupted.

**Correct approach:** Retry is only applied to idempotent operations. Non-idempotent
operations have explicit idempotency tokens and server-side deduplication.

---

### Anti-Pattern 8 — Version Pinning

**Description:** A utility declares an exact version dependency (e.g., == 1.2.3)
instead of a version range.

**Signs:** DEPENDENCIES.toml contains == or an exact version string.

**Problem:** Exact version pinning prevents the Dependency Manager from resolving
conflicts when two utilities require the same library at different patch versions.
It causes the dependency graph to be brittle.

**Correct approach:** Use version ranges (>= 1.2.0 < 2.0.0). Only the Dependency
Manager determines the specific version at resolution time.

---

# SUPPLEMENT H — OPERATIONAL RUNBOOK

## H.1 Common Operational Scenarios

### Scenario 1 — Utility Initialization Failure at Startup

**Indicators:** System fails to start. Logs show initialization failure for a specific
utility. Lifecycle Manager reports FAILED state.

**Operator Actions:**
1. Identify the failed utility from the initialization log.
2. Check whether the failure is a missing configuration, missing dependency, or
   self-test failure.
3. If missing configuration: add the required configuration key and value.
4. If missing dependency: check if the dependency is registered. If not, it may
   have been retired — check the Catalog for the retirement notice.
5. If self-test failure: check the utility's CATALOG.md for known self-test
   failure scenarios.
6. Restart the system after addressing the root cause.
7. If the utility is optional and consistently failing: consider disabling it
   via configuration until the root cause is resolved.

---

### Scenario 2 — Utility Performance Degradation

**Indicators:** Monitoring alert for utility p99 latency above threshold.
Trading cycle latency increasing. Utility metrics show latency regression.

**Operator Actions:**
1. Identify which utility is experiencing degradation.
2. Check the utility's dependencies — degradation may be caused by a dependency.
3. Check resource metrics: is memory or CPU constrained?
4. Check for configuration changes in the last 48 hours.
5. If the utility is in the critical path, consider activating the fallback
   path while the root cause is investigated.
6. Check the utility's version: was a new version deployed recently?
7. File a performance defect with the utility owner.

---

### Scenario 3 — Utility Version Conflict

**Indicators:** System fails to start. Dependency Manager reports version conflict.
Two utilities require incompatible versions of a shared dependency.

**Operator Actions:**
1. Read the version conflict error message. Identify the two conflicting consumers
   and the shared dependency they conflict on.
2. Check if either conflicting consumer can update to a compatible version range.
3. If yes: update the version range in the consumer's DEPENDENCIES.toml.
4. If neither can be updated immediately: contact the Architecture Council for
   a temporary fork authorization.
5. Schedule a permanent resolution (update at least one consumer) within 30 days.

---

### Scenario 4 — Deprecated Utility Still in Use After Sunset

**Indicators:** System startup warning that a consumer is using a retired utility.
System may refuse to start if the retired utility has been removed.

**Operator Actions:**
1. Identify which engine is using the retired utility.
2. Check the retired utility's Catalog entry for the recommended migration path.
3. Update the consuming engine to use the replacement utility.
4. Test the engine in staging before deploying to production.
5. Deploy the update.

---

### Scenario 5 — Security Utility Vulnerability Discovered

**Indicators:** Security advisory for a cryptographic library used by an IIOS
security utility. Or static analysis scan finds a new security finding.

**Operator Actions:**
1. Assess the severity: CRITICAL, HIGH, or MEDIUM/LOW.
2. CRITICAL: immediate halt of any feature deployment. Security Team to assess
   exploitability in the IIOS context.
3. If exploitable: security incident procedure. Trading may be halted pending fix.
4. If not exploitable in IIOS context: document the rationale. Schedule fix
   within 7 days (CRITICAL/HIGH) or 30 days (MEDIUM).
5. Fix: update the affected library version or replace the algorithm.
6. Deploy fix through the emergency deployment path (no sunset period required
   for security fixes to security-critical utilities).
7. Verify the fix with the Security Team before resuming normal operation.

---

# SUPPLEMENT I — COMPREHENSIVE GLOSSARY

| Term | Definition |
|------|-----------|
| Architecture Council | Governing body for IIOS architecture decisions. Owns Core Layer and governance. |
| Blast Radius | The set of utilities and components affected by the failure of a given utility. |
| Catalog | The searchable documentation store for all registered utilities. |
| Certification | The formal process of validating a utility meets quality standards for a given lifecycle state. |
| Circular Dependency | A dependency cycle where utility A depends on B which depends back on A. Prohibited. |
| Cohesion | The degree to which a utility's capabilities all serve the same purpose. High cohesion is required. |
| Compatible Version | A version that satisfies a declared version range without breaking changes. |
| Configuration Loader | Framework component that supplies utility-specific configuration from the IIOS config hierarchy. |
| Constitution | The 110 binding engineering rules in 13 categories that govern all shared utilities. |
| Consumer | An IIOS engine or component that uses a shared utility. |
| Core Layer | Layer 1 of the utility hierarchy. No dependencies on other IIOS utilities. |
| Coupling | The degree of dependency between two components. Loose coupling is required for utilities. |
| Dependency Budget | The maximum number of direct dependencies a utility may have (default: 8). |
| Dependency Injection | Providing a utility its dependencies through the constructor rather than having it look them up. |
| Dependency Manager | Framework component that resolves and orders utility dependencies. |
| Discovery Manager | Framework component that provides runtime utility discovery by type or capability. |
| Engineering Decision Record | A document recording why a design decision was made as it was. |
| EXPERIMENTAL | Lifecycle state for a utility in early development with limited consumers. |
| Extension Manager | Framework component managing utility extension points and their implementations. |
| Extension Point | A defined interface that allows utilities to be extended without modification. |
| Governance Manager | Framework component enforcing naming, documentation, and policy standards. |
| HARD check | A readiness checklist item that is blocking — the utility cannot advance without PASS. |
| INCUBATING | Lifecycle state for a utility with basic quality, being tested by multiple consumers. |
| Layer | One of 10 abstraction levels in the utility hierarchy. Higher layers depend on lower layers. |
| Lifecycle Manager | Framework component orchestrating utility initialization and shutdown sequences. |
| Mandatory Dependency | A dependency that must be available for a utility to initialize and operate. |
| Migration Guide | Documentation explaining how to update consuming code when a utility version changes behavior. |
| Namespace | The short uppercase identifier for a utility category (e.g., CORE, DT, FIN). |
| Optional Dependency | A dependency that the utility can operate without (at reduced capability). |
| Owner | The individual or team accountable for a utility's quality, documentation, and evolution. |
| Performance Budget | The maximum allowable latency for a utility function at rated concurrency. |
| Plugin | An external extension that adds a new implementation to a utility's plugin interface. |
| Plugin Manager | Framework component managing plugin registration and lifecycle. |
| PRODUCTION | The highest certification level. Requires 90-day stability, security review, and Council vote. |
| Quality Manager | Framework component tracking quality dimension scores and UQS for each utility. |
| Registry | The runtime-maintained map of all active shared utility instances. |
| Resource Manager | Framework component managing shared resources (connection pools, thread pools). |
| RETIRED | Final lifecycle state. Utility removed from Registry. Documentation preserved in Catalog. |
| SemVer | Semantic Versioning 2.0 — the mandatory versioning scheme for all IIOS utilities. |
| Service Locator | An anti-pattern where a component retrieves its own dependencies at runtime. Prohibited. |
| Single Responsibility | Design principle requiring each utility to have exactly one clearly defined purpose. |
| SOFT check | A readiness checklist item that is advisory — must be addressed within 30 days of certification. |
| STABLE | Certification level for production-eligible utilities with full documentation and test coverage. |
| Sunset | The period during which consumers of a deprecated utility must migrate to a replacement. |
| Topological Sort | The algorithm that determines initialization order from a directed acyclic dependency graph. |
| UQS | Utility Quality Score — a 0.0 to 1.0 weighted composite of 12 quality dimension scores. |
| Utility Catalog | See Catalog. |
| Utility Registry | See Registry. |
| Utility Validator | Framework component running validation and benchmark tests for utility certification. |
| Version Manager | Framework component tracking utility version history and evaluating version compatibility. |
| Version Range | A declaration of compatible versions using inequality expressions (e.g., >= 1.0.0 < 2.0.0). |
| Version Unification | The process of finding a single version that satisfies all dependent utility requirements. |
| XXE | XML External Entity injection — a security vulnerability in XML parsers that IIOS prevents. |

---

# DOCUMENT METRICS

| Attribute | Value |
|-----------|-------|
| Document Code | IIOS-SUT-FWK-001 |
| Framework Version | 1.0.0 |
| Document Status | Active |
| Total Parts | 10 |
| Total Supplements | 9 (A through I) |
| Total Utility Categories | 57 |
| Total Framework Components | 18 |
| Total Utility Layers | 10 |
| Total Lifecycle Stages | 12 |
| Total Dependency Domains | 13 |
| Total Quality Dimensions | 12 |
| Total Constitution Rules | 110 |
| Total Readiness Checks | 73 HARD + 15 SOFT = 88 total |
| Total Certification Levels | 6 |
| Total Failure Patterns | 8 |
| Total Operational Scenarios | 5 |
| Total Glossary Entries | 50 |
| Total Engineering Decision Records | 8 |

---

# AMENDMENT HISTORY

| Version | Date | Author | Change Description |
|---------|------|--------|-------------------|
| 1.0.0 | 2026-07-04 | Architecture Council | Initial publication |

---

# CLOSING STATEMENT

This document — the Shared Utilities Framework for the Investment Intelligence
Operating System (IIOS), bearing document code IIOS-SUT-FWK-001 — is the complete,
authoritative specification for all reusable services, helper libraries, common
infrastructure components, cross-cutting capabilities, and engineering support
modules that serve the entire IIOS platform.

The framework is organized into 57 utility categories, 10 architectural layers,
and governed by 18 framework components. Its 110-rule Engineering Constitution
ensures consistent quality, security, and maintainability across every utility.
Its 12-stage lifecycle ensures every utility is born deliberately, used confidently,
and retired responsibly.

The underlying principle is simple: a shared utility is a concentrated investment
in quality. The effort and care devoted to one shared utility multiplies across
every engine, agent, and workflow that uses it. This is the compounding engine
of platform engineering excellence.

Every utility named in this framework is the platform's promise to the engineers
who build on it: we have already solved this problem well. You do not need to
solve it again.

---

*IIOS-SUT-FWK-001 / Version 1.0.0 / Status: Active*
*Shared Utilities Framework — Investment Intelligence Operating System*
*Architecture Council Approved*
