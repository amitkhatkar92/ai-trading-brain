# BUILD DEPLOYMENT ENGINEERING FRAMEWORK
## Investment Intelligence Operating System (IIOS)

**Document Code:** IIOS-BLD-DEP-001
**Version:** 1.0.0
**Status:** Active
**Classification:** Engineering Specification
**Scope:** Full IIOS Platform — Build, Release, Deployment, Environment, and Delivery Engineering
**Architecture Council:** Approved

---

> This document is the authoritative engineering specification for how the
> Investment Intelligence Operating System (IIOS) is built, packaged, validated,
> released, deployed, upgraded, rolled back, monitored, and maintained throughout
> its complete operational lifecycle. It is an engineering specification only:
> it contains no source code, no API definitions, and no implementation.
> It defines architecture, process, governance, and law.

---

# TABLE OF CONTENTS

- Part I    — Build and Deployment Philosophy
- Part II   — Build Taxonomy (25 build types)
- Part III  — Build Architecture (18 components)
- Part IV   — Environment Architecture (16 environments)
- Part V    — Deployment Lifecycle (12 stages)
- Part VI   — Release Engineering
- Part VII  — Operational Reliability
- Part VIII — Governance
- Part IX   — Engineering Constitution (110 rules)
- Part X    — Readiness Checklist (11 domains)
- Supplement A — Build Catalog
- Supplement B — Environment Catalog
- Supplement C — Release Catalog
- Supplement D — Deployment Patterns
- Supplement E — Rollback Patterns
- Supplement F — Version Compatibility Matrix
- Supplement G — Engineering Decision Records
- Supplement H — Operational Runbook
- Supplement I — Deployment Anti-Patterns
- Supplement J — Comprehensive Glossary

---

# PART I — BUILD AND DEPLOYMENT PHILOSOPHY

## 1.1 Purpose

The Build and Deployment Engineering Framework exists to answer a single
foundational question: how does a software system transition safely, verifiably,
and repeatably from written code to a running production system that manages
real capital in live financial markets?

For IIOS, this question carries exceptional weight. The system operates across
17 interdependent layers, manages financial positions in live markets, and must
maintain strict operational continuity across deployments, upgrades, and
recoveries. A failed deployment is not merely a technical incident — it is a
financial risk event. A deployment that corrupts data, leaves state inconsistent,
or causes a trading position to be misreported may result in financial loss that
no rollback can recover.

The framework therefore imposes engineering discipline on every stage of the
build and deployment lifecycle. It defines what correct looks like, what safe
means, what done requires, and what reversible demands. It is both a process
specification and a quality contract.

---

## 1.2 Engineering Objectives

The Build and Deployment Engineering Framework has seven primary objectives:

**Objective 1 — Reproducibility:**
The same source at the same version must always produce the same artifact.
Build outputs are not a function of the environment in which the build was
executed. Two engineers, on two different machines, building the same commit,
must produce byte-identical artifacts (within deterministic tolerance).

**Objective 2 — Verifiability:**
Every artifact that enters any environment must be provably authentic. Artifact
integrity hashes are computed at build time and verified at deployment time.
An artifact whose hash does not match its manifest is never deployed.

**Objective 3 — Safety:**
No deployment introduces a condition worse than the previous state. If a
deployment cannot be safely completed, it is not completed. Rollback is always
available and always tested before deployment.

**Objective 4 — Zero Data Loss:**
Data written to persistent stores is never lost as a result of a deployment,
upgrade, rollback, or recovery operation. The IIOS data directory is a
persistent volume, not part of the deployed container image.

**Objective 5 — Operational Continuity:**
Trading operations are disrupted for the minimum possible duration during any
deployment. Deployments are planned, announced, and executed during defined
maintenance windows whenever possible.

**Objective 6 — Full Auditability:**
Every build, every deployment, every configuration change, and every environment
modification is recorded with sufficient detail to reconstruct exactly what
changed, who authorized it, when it happened, and what the state was before and
after.

**Objective 7 — Long-Term Maintainability:**
The deployment system does not create technical debt. Every component of the
build and deployment pipeline is documented, tested, and governed by the same
standards applied to the IIOS system itself.

---

## 1.3 Reproducible Builds

A reproducible build is a build whose output is deterministic given the same
inputs. Inputs include: source code at a specific commit, dependency versions
as pinned in requirements.txt, the base container image at a specific digest,
build configuration at a specific version, and the build environment specification.

IIOS achieves reproducible builds through:

- **Pinned dependencies:** All Python dependencies are pinned to exact versions
  in requirements.txt. No floating version specifiers (e.g., >=, ~=) are used
  in production builds.

- **Digest-pinned base images:** Docker base images are referenced by SHA256
  digest, not by mutable tag. python:3.14-slim is never used; the digest-
  pinned equivalent is used instead.

- **Hermetic build environment:** Builds are executed in isolated containers
  with no access to external network resources at build time (dependencies are
  pre-fetched and vendored).

- **Timestamp normalization:** Build timestamps are set to a canonical value
  derived from the source commit timestamp, not the current wall-clock time.

- **Build manifest:** Every build produces a manifest recording all inputs,
  their exact versions and hashes, and the resulting output hash.

---

## 1.4 Deterministic Deployments

A deterministic deployment produces the same system state given the same artifact
and the same pre-deployment state. Determinism in deployment is achieved through:

- **Idempotent deployment steps:** Every deployment step can be re-executed
  without producing an inconsistent state. Running the same deployment twice
  produces the same result as running it once.

- **Schema migration determinism:** Database schema migrations are forward-only
  and idempotent. A migration that has already been applied produces no change
  when re-executed.

- **Configuration atomicity:** Configuration changes are applied atomically.
  The system never runs with a partially-applied configuration.

- **Ordered shutdown:** The running system is shut down in the correct layer
  order before new components are started, ensuring no layer processes events
  with a partially-upgraded peer.

---

## 1.5 Deployment Safety

Deployment safety is a first-class engineering requirement, not an operational
afterthought. Safety is achieved through structural engineering, not through
operator care.

**Pre-deployment verification:** Every artifact is verified against its manifest
before deployment begins. If verification fails, the deployment does not proceed.

**Kill switch check:** The kill switch state is verified before deployment. A
deployment is never initiated while the kill switch is active.

**Market hours guard:** Deployments to the production environment are blocked
during market hours (09:00–15:30 IST, Monday–Friday). The deployment system
enforces this at the tooling level; it is not solely an operator responsibility.

**Staged deployment:** Production deployments proceed through staging first.
No artifact reaches production without first being successfully deployed in
staging.

**Rollback pre-verification:** Before every production deployment, rollback is
verified to be available and tested. A deployment for which rollback cannot be
demonstrated is not authorized.

---

## 1.6 Zero Data Loss Architecture

IIOS maintains a strict zero data loss posture for all persistent state:

**Volume separation:** The data directory (data/) is a Docker volume that is
not part of the container image. Replacing the container image never touches the
data volume. The data volume persists across container stops, restarts, and image
upgrades.

**Pre-deployment backup:** A snapshot of the data volume is taken before every
production deployment. The snapshot is verified for integrity before the
deployment proceeds.

**Database WAL mode:** All SQLite databases operate in Write-Ahead Logging mode.
WAL mode ensures that an abrupt container termination cannot corrupt the database.

**Migration safety:** Database migrations are applied before new container code
runs. Migrations are tested against a copy of the production database schema
in staging before production application.

**Trade journal persistence:** The paper trade journal (data/paper_trades.csv)
is never truncated or overwritten by a deployment.

---

## 1.7 Rollback-First Engineering

The IIOS deployment philosophy is rollback-first: every deployment is designed
from the assumption that it may need to be reversed. Rollback is not a
contingency — it is a primary design requirement.

**Rollback must be instant:** A production rollback must restore the previous
known-good state within 5 minutes of the rollback decision. Rollbacks that
require extended rebuild or re-download are not acceptable.

**Previous image retained:** The previous production container image is always
retained in the image registry for a minimum of 90 days. The image that is
currently in production is never the only copy of the production image.

**Rollback does not lose data:** A rollback never results in data loss. Data
written after the most-recent deployment and before the rollback is preserved.
Schema rollbacks are forward-compatible.

**Rollback is tested:** Rollback procedures are tested in staging before every
production deployment. If rollback cannot be successfully demonstrated in
staging, the production deployment does not proceed.

---

## 1.8 Infrastructure Independence

IIOS is engineered to be deployable on any compliant host without modification
to the application code. Infrastructure independence is achieved through:

**Containerization:** All IIOS components run as Docker containers. The
container runtime provides the abstraction between application code and host
infrastructure.

**Configuration externalization:** All environment-specific configuration is
externalized to environment variables. No host-specific path, endpoint, or
credential is embedded in the container image.

**Volume abstraction:** All persistent state is accessed through Docker volumes.
The application does not reference host filesystem paths directly.

**Port mapping abstraction:** Service ports are mapped through Docker port
bindings. The application binds to its container-internal port; the host
port mapping is managed externally.

**Platform-agnostic build:** The build pipeline runs on any host with Docker
installed. It does not require specific cloud provider tooling.

---

## 1.9 Platform Portability

IIOS is designed to run on:
- Linux x86-64 (primary production target — VPS at 178.18.252.24)
- Linux ARM64 (future target — cloud ARM instances)
- Windows x86-64 (development workstation — current developer environment)
- macOS ARM64 (development target — Apple Silicon)

Platform portability is maintained through:
- Python source code with no platform-specific extensions
- Docker multi-platform build manifests
- Dependency validation against all target platforms
- CI testing on both Linux and the developer platform

---

## 1.10 Continuous Delivery

IIOS operates a continuous delivery pipeline in which any commit to the main
branch that passes all quality gates can be deployed to production. Continuous
delivery does not mean continuous deployment — the production deployment step
requires explicit human authorization. It means that the artifact for production
is always ready.

The pipeline stages are: Commit → Build → Test → Certify → Stage → Authorize → Deploy.
Every stage is automated up to Authorize. The Authorize step is a human gate.

---

## 1.11 Release Governance

Releases are not created without governance. Every production release:
- Has a release ticket with the change list and impact assessment.
- Has been staged and verified in the staging environment.
- Has received written approval from the Architecture Council.
- Has a tested rollback plan.
- Has a post-deployment monitoring plan.
- Is announced to all system stakeholders before execution.

Emergency releases bypass parts of this process under defined conditions
(see Part VI, Section 6.11).

---

## 1.12 Operational Stability

Operational stability means that the deployed system maintains its performance
and behavioral baselines between releases. Stability is monitored through:
- Continuous health checks (every 30 seconds in production)
- Baseline comparison (current cycle metrics vs 7-day rolling average)
- Alert escalation when any metric deviates by more than 20% from baseline
- Automatic incident creation when any health check fails for two consecutive cycles

---

## 1.13 Long-Term Maintainability

The build and deployment engineering must remain maintainable as the system
evolves. Maintainability principles:
- The deployment system is documented to the same standard as the application.
- Deployment scripts are version-controlled alongside application code.
- Deployment tooling is reviewed quarterly for currency.
- Deprecated tooling is removed within 90 days of replacement.
- Every deployment system change is tested before it is used in production.

---

*End of Part I*

---

# PART II — BUILD TAXONOMY

## 2.1 Build Taxonomy Overview

IIOS defines 25 distinct build types across 6 groups: source builds, development
builds, quality builds, release builds, special builds, and container builds.
Each build type has a defined purpose, trigger condition, artifact class, and
governance requirement.

---

## 2.2 Group 1 — Source Builds

### 2.2.1 Source Build

**Definition:** Any compilation and packaging of IIOS source code.
**Purpose:** The fundamental build operation from which all other build types derive.
**Trigger:** Manual invocation or CI pipeline trigger.
**Artifact:** Python wheel or Docker image.
**Governance:** None required for feature branches; PR approval required for main branch.

---

### 2.2.2 Incremental Build

**Definition:** A build that recompiles only changed source modules, reusing
cached outputs for unchanged modules.
**Purpose:** Accelerates the development feedback loop.
**Trigger:** Local developer invocation.
**Artifact:** Partial artifacts combined with cached prior outputs.
**Governance:** None. Incremental builds are for local development only and
never produce release artifacts.
**Constraint:** Incremental builds must never be used for artifacts deployed
beyond the local development environment.

---

### 2.2.3 Clean Build

**Definition:** A build from a completely empty build directory. All caches
are cleared before the build begins.
**Purpose:** Eliminates any stale artifact contamination.
**Trigger:** Mandatory before release candidate builds; optional otherwise.
**Artifact:** Full artifact set from scratch.
**Governance:** Required for all artifacts destined for staging or production.

---

### 2.2.4 Full Build

**Definition:** A build of all IIOS components, including all optional modules,
all integration adapters, and the complete dependency graph.
**Purpose:** Produces the definitive complete IIOS artifact.
**Trigger:** Scheduled nightly build; release candidate trigger.
**Artifact:** Complete Docker image and wheel distribution.
**Governance:** Architecture Council notification required for full builds
destined for production.

---

## 2.3 Group 2 — Development Builds

### 2.3.1 Development Build

**Definition:** A build configured for local development use, with debug
instrumentation, verbose logging, and no performance optimizations.
**Purpose:** Supports iterative development and debugging.
**Trigger:** Local developer invocation; IDE build actions.
**Artifact:** Local Docker image or local Python package installation.
**Governance:** None. Development builds never leave the developer environment.
**Characteristics:** Extended logging, disabled caches, injectable clock active,
paper trading forced on.

---

### 2.3.2 Debug Build

**Definition:** A build with maximum diagnostic instrumentation: per-layer
timing, full exception traces, decision engine detailed outputs, and AI agent
rationale logging.
**Purpose:** Deep diagnostic investigations and defect reproduction.
**Trigger:** Manual invocation by engineer investigating a specific defect.
**Artifact:** Local Docker image.
**Governance:** None. Debug builds are ephemeral and never deployed.
**Constraint:** Debug builds contain sensitive diagnostic information and must
never be distributed or deployed outside the developer machine.

---

### 2.3.3 Testing Build

**Definition:** A build configured for use in the automated testing suite.
**Purpose:** Provides an artifact with injectable dependencies, controlled
clocks, mock data feeds, and test-specific configuration.
**Trigger:** CI pipeline on every commit to any branch.
**Artifact:** Docker image tagged with commit SHA.
**Governance:** PR merge gate — testing build must pass for any PR to merge.
**Characteristics:** Injectable clock, mock broker, mock data feeds, test
databases, test Telegram mock.

---

## 2.4 Group 3 — Quality Builds

### 2.4.1 QA Build

**Definition:** A build deployed to the QA environment for structured quality
assurance testing by the QA team.
**Purpose:** Formal quality validation before staging.
**Trigger:** After successful testing build and automated test gate passage.
**Artifact:** Docker image tagged with build number and QA designation.
**Governance:** Testing team sign-off required before QA build is promoted.

---

### 2.4.2 Staging Build

**Definition:** A build deployed to the staging environment, which is the
production-equivalent environment used for final validation.
**Purpose:** Final production-equivalent validation before production deployment.
**Trigger:** After QA build approval.
**Artifact:** Docker image tagged with release candidate number.
**Governance:** Architecture Council approval required for staging build promotion.

---

## 2.5 Group 4 — Release Builds

### 2.5.1 Production Build

**Definition:** The final, certified, signed artifact deployed to the production
environment.
**Purpose:** The definitive IIOS production artifact.
**Trigger:** After Architecture Council production deployment authorization.
**Artifact:** Docker image tagged with production version number.
**Governance:** Architecture Council written authorization required.
**Characteristics:** Signed artifact, integrity-verified, deployment manifest
included, rollback artifact pre-stored.

---

### 2.5.2 Nightly Build

**Definition:** A scheduled full build executed every night at 00:00 IST.
**Purpose:** Early detection of integration issues, dependency drift, and
build system health.
**Trigger:** Scheduled CI/CD pipeline.
**Artifact:** Docker image tagged with date.
**Governance:** Architecture Council notified of failures; no deployment
without additional authorization.

---

### 2.5.3 Release Candidate

**Definition:** A build that is a candidate for production release, pending
final validation.
**Purpose:** Provides a stable artifact for staging validation and Architecture
Council review.
**Trigger:** Feature freeze completion.
**Artifact:** Docker image tagged with RC version (e.g., v1.2.0-rc1).
**Governance:** Architecture Council review required before RC promotion.

---

### 2.5.4 Hotfix Build

**Definition:** A build produced for an emergency fix to a critical production
defect.
**Purpose:** Resolve critical defects affecting financial operations without
waiting for the normal release cycle.
**Trigger:** P0 or P1 defect classification by Architecture Council.
**Artifact:** Docker image tagged with hotfix designation.
**Governance:** Architecture Council P0/P1 classification, emergency approval process.
**Constraint:** Hotfix builds are scoped to the minimum change required to
resolve the defect. No feature additions are permitted.

---

### 2.5.5 Patch Release

**Definition:** A build resolving one or more defects without introducing new
features.
**Purpose:** Targeted defect resolution between planned feature releases.
**Trigger:** Accumulated P2 defects meeting the patch release threshold.
**Artifact:** Docker image tagged with patch version (e.g., v1.2.1).
**Governance:** Standard release governance process.

---

### 2.5.6 Major Release

**Definition:** A build introducing architectural changes, new subsystems, or
breaking changes to internal interfaces.
**Purpose:** Delivers significant platform evolution.
**Trigger:** Architecture Council approval of major release scope.
**Artifact:** Docker image tagged with major version (e.g., v2.0.0).
**Governance:** Full Architecture Council release review, extended staging period
(minimum 14 days), explicit production authorization.

---

### 2.5.7 Minor Release

**Definition:** A build introducing new features compatible with the existing
architecture.
**Purpose:** Delivers planned feature evolution without architectural change.
**Trigger:** Feature freeze date.
**Artifact:** Docker image tagged with minor version (e.g., v1.3.0).
**Governance:** Standard release governance.

---

### 2.5.8 Long-Term Support Release

**Definition:** A designated release that receives extended maintenance, security
patches, and critical defect fixes for a defined support period.
**Purpose:** Provides a stable base for production systems that cannot accept
frequent updates.
**Trigger:** Architecture Council LTS designation.
**Support Period:** 12 months from designation.
**Governance:** Architecture Council LTS committee.

---

### 2.5.9 Emergency Release

**Definition:** A release bypassing parts of the standard release governance
process due to an active financial risk or safety incident.
**Purpose:** Restore safe operation as quickly as possible during an incident.
**Trigger:** Active P0 incident declared by Architecture Council.
**Governance:** Reduced to: Architecture Council chair authorization, safety
test passage, and immediate post-deployment review.

---

### 2.5.10 Rollback Build

**Definition:** Not a new build — the previous production artifact retrieved
from the artifact registry and re-deployed.
**Purpose:** Restore the previous production state in response to a failed
deployment.
**Trigger:** Deployment failure, post-deployment health check failure, or
Architecture Council rollback decision.
**Artifact:** Previously certified production image.
**Governance:** Architecture Council or on-call engineer authorization.

---

### 2.5.11 Recovery Build

**Definition:** A build specifically produced to restore a system from a
degraded or partial failure state.
**Purpose:** Targeted recovery from specific failure modes.
**Trigger:** Incident recovery procedure activation.
**Governance:** Emergency release process.

---

## 2.6 Group 5 — Container Builds

### 2.6.1 Container Build

**Definition:** A Docker image build producing a complete, runnable IIOS container.
**Purpose:** The standard production artifact format for IIOS.
**Trigger:** All production, staging, and QA build types.
**Artifact:** Docker image.
**Governance:** Per the build type being containerized.

---

### 2.6.2 Artifact Build

**Definition:** A build producing a distributable Python wheel package.
**Purpose:** Enables installation of IIOS components into other Python environments.
**Trigger:** Release builds.
**Artifact:** Python wheel (.whl file).
**Governance:** Standard release governance.

---

### 2.6.3 Offline Build

**Definition:** A build executed with no external network access, using only
pre-fetched, vendored dependencies.
**Purpose:** Ensures builds are independent of external service availability.
**Trigger:** Production release builds.
**Artifact:** Same as clean build.
**Governance:** Required for all production artifacts.

---

### 2.6.4 Cloud Build

**Definition:** A build executed in a cloud-hosted CI environment.
**Purpose:** Provides a consistent, reproducible build environment independent
of developer hardware.
**Trigger:** All branch commits via GitHub Actions.
**Artifact:** Docker image pushed to container registry.
**Governance:** GitHub Actions configuration is version-controlled and reviewed.

---

### 2.6.5 Multi-Platform Build

**Definition:** A build producing Docker images for multiple CPU architectures
(x86-64 and ARM64).
**Purpose:** Ensures IIOS can run on both x86 servers and ARM-based cloud instances.
**Trigger:** Release candidate and production builds.
**Artifact:** Docker manifest list referencing architecture-specific images.
**Governance:** Architecture Council approval for new platform targets.

---

*End of Part II*

---

# PART III — BUILD ARCHITECTURE

## 3.1 Architecture Overview

The Build Architecture defines 18 framework components that collectively manage
every aspect of the build, packaging, deployment, and operational lifecycle.

`
BUILD ARCHITECTURE — IIOS

+------------------+    +------------------+    +------------------+
|  Build Registry  |<-->| Artifact Registry|<-->|Dependency Resolver|
+------------------+    +------------------+    +------------------+
         |                       |                        |
         v                       v                        v
+------------------+    +------------------+    +------------------+
| Package Manager  |    | Version Manager  |    | Release Manager  |
+------------------+    +------------------+    +------------------+
         |                       |                        |
         v                       v                        v
+------------------+    +------------------+    +------------------+
|Environment Manager|   |Configuration Mgr |    |  Container Mgr   |
+------------------+    +------------------+    +------------------+
         |                       |                        |
         v                       v                        v
+------------------+    +------------------+    +------------------+
|  Image Registry  |    |Deployment Manager|    | Upgrade Manager  |
+------------------+    +------------------+    +------------------+
         |                       |                        |
         v                       v                        v
+------------------+    +------------------+    +------------------+
| Rollback Manager |    | Migration Manager|    |Health Verif. Mgr |
+------------------+    +------------------+    +------------------+
         |                       |
         v                       v
+------------------+    +------------------+    +------------------+
| Monitoring Mgr   |    |Certification Mgr |    | Governance Mgr   |
+------------------+    +------------------+    +------------------+
`

---

## 3.2 Component 1 — Build Registry

**Purpose:** The Build Registry is the authoritative record of every build
ever executed in the IIOS build system. It provides complete traceability from
source commit to deployed artifact.

**Responsibilities:**
- Register every build with its triggering event (commit SHA, pipeline run ID).
- Record all build inputs: source commit, dependency lock file hash, base image digest.
- Record all build outputs: artifact hash, artifact location, build duration.
- Record build outcomes: success, failure, partial failure, and failure reason.
- Maintain build history for a minimum of 2 years.
- Provide build-to-deployment traceability (which build is in which environment).
- Detect duplicate builds (same source producing the same artifact — can be reused).

**Inputs:**
- Build trigger events from CI/CD pipeline.
- Source commit metadata from version control.
- Dependency lock file from requirements.txt.
- Build configuration from Dockerfile and docker-compose.yml.

**Outputs:**
- Build record (build ID, status, inputs, outputs, timestamps).
- Build manifest (all inputs and their hashes, output hash).
- Build traceability report (source → artifact → deployment chain).

**Dependencies:**
- Version control system (git).
- Artifact Registry.
- CI/CD pipeline.

**Lifecycle:**
1. Build trigger received.
2. Build record initialized with PENDING status.
3. Build inputs recorded and hashed.
4. Build executed; progress events recorded.
5. Build outcome (PASS/FAIL) recorded.
6. Artifact hash recorded from Artifact Registry.
7. Build record finalized with COMPLETE or FAILED status.

**Failure Modes:**
- Build Registry unavailable during build: build proceeds but records are written
  on completion.
- Build record corruption: detected by integrity hash; affected record is quarantined.

**Recovery:**
- Registry is rebuilt from CI/CD pipeline logs and Artifact Registry metadata.

**Monitoring:**
- Build success rate (target: >= 95% of main branch builds succeed).
- Build duration trend (alert if build time increases > 30% over 7-day average).
- Registry storage utilization.

**Engineering Notes:**
Build records are append-only. No build record is ever modified after COMPLETE
status. Amendments are recorded as separate amendment records referencing the
original.

---

## 3.3 Component 2 — Artifact Registry

**Purpose:** The Artifact Registry is the secure, versioned repository of all
IIOS build artifacts. Every artifact deployed to any environment must be
retrieved from the Artifact Registry.

**Responsibilities:**
- Store all build artifacts with integrity hashes.
- Enforce artifact immutability (stored artifacts are never overwritten).
- Provide artifact retrieval with integrity verification.
- Manage artifact lifecycle (promotion, retirement, deletion after retention period).
- Enforce access control (only authorized pipelines can push artifacts).
- Maintain artifact metadata (build ID, source commit, creation time, signature).
- Scan artifacts for known vulnerabilities before registration.

**Inputs:**
- Artifact binary from CI/CD build step.
- Artifact metadata from Build Registry.
- Signing certificate for artifact signing.
- Vulnerability scan results.

**Outputs:**
- Artifact location (registry URI and tag).
- Artifact integrity hash (SHA256).
- Artifact signature.
- Vulnerability scan report.

**Dependencies:**
- Build Registry.
- Container Manager (for Docker images).
- Security Team (for signing certificates).

**Lifecycle:**
1. Artifact submitted from build pipeline.
2. Artifact integrity hash computed and recorded.
3. Artifact vulnerability scan executed.
4. Artifact signed by Build Infrastructure.
5. Artifact registered with metadata.
6. Artifact available for deployment.
7. Artifact promoted or retired based on governance.
8. Artifact deleted after retention period expires.

**Failure Modes:**
- Registry unavailable: build artifacts are held in CI/CD local storage until
  registry is restored.
- Vulnerability scan failure: artifact is quarantined; deployment blocked.
- Signature verification failure at deployment: deployment blocked; incident raised.

**Recovery:**
- Registry restored from backup. Artifact hashes re-verified against Build Registry.

**Monitoring:**
- Registry availability (target: 99.9%).
- Artifact count by type and age.
- Scan failure rate.

**Engineering Notes:**
The Artifact Registry is the single source of truth for what exists. No artifact
that is not in the Artifact Registry is ever deployed. Deploying an artifact
that was built locally and not registered is prohibited.

---

## 3.4 Component 3 — Dependency Resolver

**Purpose:** The Dependency Resolver manages the complete IIOS dependency graph,
ensuring that all dependencies are pinned, reproducible, and free of known
vulnerabilities.

**Responsibilities:**
- Resolve the complete transitive dependency graph from requirements.txt.
- Generate a locked dependency manifest (requirements.lock) pinning every
  transitive dependency to an exact version and hash.
- Verify that all dependencies are available in the offline dependency cache.
- Detect dependency conflicts.
- Scan dependencies for known CVEs.
- Detect dependency drift (new versions of pinned dependencies).
- Produce a dependency SBOM (Software Bill of Materials).

**Inputs:**
- requirements.txt (direct dependencies with version constraints).
- Offline dependency cache.
- CVE database.

**Outputs:**
- requirements.lock (fully resolved, pinned, hashed dependency list).
- Dependency SBOM.
- CVE scan report.
- Dependency drift report.

**Dependencies:**
- Offline dependency cache.
- CVE database (updated daily).
- Package Manager.

**Lifecycle:**
1. Triggered at build start.
2. requirements.txt parsed.
3. Transitive graph resolved.
4. All dependency versions and hashes recorded.
5. CVE scan executed.
6. requirements.lock generated.
7. Lock file hashed and stored in Build Registry.

**Failure Modes:**
- Dependency conflict: build blocked; dependency conflict report raised.
- CVE found in dependency: build blocked; security incident raised.
- Offline cache miss: build blocked; dependency must be added to cache.

**Engineering Notes:**
The Dependency Resolver runs before any compilation step. A build with an
unresolved dependency or a CVE is not a valid build.

---

## 3.5 Component 4 — Package Manager

**Purpose:** The Package Manager handles the installation, organization, and
verification of Python packages within the build environment.

**Responsibilities:**
- Install all pinned dependencies from requirements.lock into the build container.
- Verify installed package hashes against requirements.lock.
- Manage the offline package cache.
- Produce a package installation manifest.
- Validate that no extraneous packages are installed.

**Inputs:**
- requirements.lock from Dependency Resolver.
- Offline package cache.

**Outputs:**
- Installed package environment.
- Package installation manifest.
- Installation verification report.

**Dependencies:**
- Dependency Resolver.
- Offline package cache.

**Engineering Notes:**
The Package Manager enforces that installed packages exactly match requirements.lock.
Any deviation (missing package, hash mismatch, extra package) is a build failure.

---

## 3.6 Component 5 — Version Manager

**Purpose:** The Version Manager maintains the authoritative version numbering
system for IIOS, ensuring that every build, release, and artifact has a unique,
meaningful, and correctly formatted version identifier.

**Responsibilities:**
- Generate version numbers for all build types per the version numbering policy.
- Enforce semantic versioning (MAJOR.MINOR.PATCH with optional pre-release suffix).
- Prevent duplicate version numbers.
- Record the commit associated with every version.
- Manage version tags in the version control system.
- Produce version compatibility declarations.
- Validate version numbers on artifact ingestion.

**Inputs:**
- Build type (determines version number format).
- Previous version from version history.
- Source commit SHA.

**Outputs:**
- Version number for the current build.
- Version tag applied to source commit.
- Version compatibility declaration.

**Dependencies:**
- Build Registry.
- Version control system.

**Lifecycle:**
1. Build type and intent declared.
2. Previous version retrieved.
3. New version number computed per policy.
4. Version uniqueness verified.
5. Version tag applied to commit.
6. Version recorded in Build Registry.

**Failure Modes:**
- Version collision: build blocked; Version Manager alerts.
- Version control tag failure: Version Manager retries; if persistent, alerts.

---

## 3.7 Component 6 — Release Manager

**Purpose:** The Release Manager orchestrates the complete release lifecycle from
feature freeze through production deployment authorization.

**Responsibilities:**
- Manage the release schedule and feature freeze enforcement.
- Coordinate the release candidate build sequence.
- Track release gate status (all gates must pass before promotion).
- Manage the release approval workflow.
- Produce the release manifest (all components, versions, changes).
- Archive release artifacts and evidence.
- Coordinate rollback artifact preparation.

**Inputs:**
- Release scope (feature list, version intent).
- Gate results from all quality checks.
- Architecture Council approval decisions.

**Outputs:**
- Release manifest.
- Release schedule.
- Release gate status report.
- Release evidence archive.

**Dependencies:**
- Build Registry, Artifact Registry, Version Manager.
- Certification Manager.
- Architecture Council.

**Release Gates:**
All of the following must be PASS before production deployment:
1. Clean build successful.
2. All automated tests passed.
3. Coverage thresholds met (SCS >= 0.92).
4. Staging deployment successful.
5. Staging health checks passing for 24 hours.
6. Rollback verified in staging.
7. Security scan clean.
8. Architecture Council written approval.
9. Market hours guard confirmed (deployment outside trading hours).

---

## 3.8 Component 7 — Environment Manager

**Purpose:** The Environment Manager creates, configures, and maintains all 16
IIOS environments, ensuring that each environment accurately represents its
intended purpose and is isolated from adjacent environments.

**Responsibilities:**
- Provision new environments per environment specification.
- Apply environment-specific configuration.
- Enforce environment isolation (no cross-environment communication).
- Manage environment lifecycle (create, maintain, retire).
- Audit environment configuration drift.
- Provide environment status dashboards.
- Coordinate environment access control.

**Inputs:**
- Environment specification (from Part IV).
- Configuration values (from Configuration Manager).
- Access control lists.

**Outputs:**
- Running environment with verified configuration.
- Environment status report.
- Environment drift report.

**Failure Modes:**
- Environment configuration drift: alert raised; drift remediated within 24 hours.
- Environment unavailable: pipeline blocked; Environment Manager alerts.

---

## 3.9 Component 8 — Configuration Manager

**Purpose:** The Configuration Manager maintains all environment-specific
configuration for IIOS, ensuring that configuration is version-controlled,
auditable, and correctly applied to each environment.

**Responsibilities:**
- Store all environment configuration in version control.
- Apply configuration to environments at deployment time.
- Detect configuration drift between version control and running environment.
- Manage secrets (API keys, tokens) through a secrets manager.
- Produce configuration manifests for deployment records.
- Validate configuration against the configuration schema before application.

**Inputs:**
- Configuration files from version control.
- Secrets from secrets manager.
- Environment specification.

**Outputs:**
- Applied configuration set.
- Configuration manifest (hash of all applied configuration).
- Configuration drift report.

**Security Notes:**
Secrets are never stored in version control. All secrets are injected at
deployment time from the secrets manager. Configuration files that should
contain secrets contain only references (e.g., env var names), never values.

---

## 3.10 Component 9 — Container Manager

**Purpose:** The Container Manager handles the building, tagging, scanning,
and lifecycle management of all IIOS Docker containers.

**Responsibilities:**
- Execute Docker image builds from Dockerfile.
- Tag images per version and environment convention.
- Scan images for known vulnerabilities.
- Sign images after successful scan.
- Push signed images to Image Registry.
- Manage docker-compose configurations per environment.
- Execute container health checks.
- Manage container resource limits.

**Inputs:**
- Dockerfile.
- docker-compose.yml per environment.
- Source artifact from build.
- Image signing certificate.

**Outputs:**
- Docker image (signed, scanned).
- Image scan report.
- Container health check results.

**Failure Modes:**
- Image scan failure: deployment blocked; security incident raised.
- Image signing failure: deployment blocked; Security Team alerted.
- Container health check failure: deployment halted; rollback initiated.

---

## 3.11 Component 10 — Image Registry

**Purpose:** The Image Registry is the Docker image storage and distribution
system for all IIOS container images.

**Responsibilities:**
- Store all Docker images with immutability enforcement.
- Provide image pull for deployment pipelines.
- Enforce access control (push restricted to build pipeline; pull restricted
  to deployment environments).
- Retain all production images for minimum 90 days.
- Produce image pull SBOMs.
- Alert on image retention expiry.

**Inputs:**
- Docker images from Container Manager.

**Outputs:**
- Image pull URLs with digest references.
- Image metadata.
- Retention expiry alerts.

**Engineering Notes:**
Images are referenced by digest (SHA256) for all production deployments, never
by mutable tag alone. A mutable tag (e.g., latest) is a convenience reference
only and is never the sole reference in a production deployment manifest.

---

## 3.12 Component 11 — Deployment Manager

**Purpose:** The Deployment Manager orchestrates every aspect of the deployment
of IIOS artifacts to target environments.

**Responsibilities:**
- Execute the deployment sequence per the 12-stage lifecycle.
- Enforce pre-deployment checks (artifact verification, kill switch check,
  market hours check).
- Execute ordered shutdown of the running system before deployment.
- Apply database migrations before starting new code.
- Start new containers and verify health.
- Coordinate with Rollback Manager to pre-position rollback artifacts.
- Record all deployment events in the deployment audit log.
- Execute post-deployment verification.

**Inputs:**
- Deployment authorization from Architecture Council.
- Artifact location and integrity hash from Artifact Registry.
- Environment configuration from Configuration Manager.
- Database migration scripts.

**Outputs:**
- Running deployment with verified health.
- Deployment record.
- Post-deployment verification report.

**Failure Modes:**
- Pre-deployment check failure: deployment blocked; incident raised.
- Migration failure: deployment halted; previous state preserved; rollback available.
- Post-deployment health check failure: rollback automatically initiated.

**Recovery:**
- On any deployment failure, Deployment Manager automatically initiates rollback
  unless the rollback itself is the source of the failure.

---

## 3.13 Component 12 — Upgrade Manager

**Purpose:** The Upgrade Manager manages in-place system upgrades, handling
the transition from one version to the next with minimum disruption.

**Responsibilities:**
- Plan the upgrade sequence (layer order for shutting down and restarting components).
- Manage schema upgrades in coordination with Migration Manager.
- Ensure backward compatibility during the upgrade window.
- Execute health verification at each upgrade stage.
- Provide upgrade progress telemetry.
- Abort and rollback on any upgrade stage failure.

**Inputs:**
- Current version specification.
- Target version specification.
- Migration plan from Migration Manager.
- Health check definitions from Health Verification Manager.

**Outputs:**
- Upgraded system at target version.
- Upgrade manifest.
- Upgrade telemetry.

**Engineering Notes:**
IIOS is upgraded by replacing the Docker container image. The application code
inside the container is replaced atomically; there is no in-place file replacement.

---

## 3.14 Component 13 — Rollback Manager

**Purpose:** The Rollback Manager ensures that every deployment can be reversed
to the previous certified state within 5 minutes of a rollback decision.

**Responsibilities:**
- Pre-position rollback artifacts (previous certified image) before every deployment.
- Verify rollback artifacts are available and intact before every deployment.
- Execute the rollback sequence on demand.
- Verify system health after rollback.
- Record rollback events in the deployment audit log.
- Test the rollback procedure in staging before every production deployment.

**Inputs:**
- Rollback decision trigger (manual or automated).
- Previous certified image from Image Registry.
- Pre-deployment database snapshot.

**Outputs:**
- System restored to previous certified state.
- Rollback manifest.
- Post-rollback health verification report.

**Rollback Sequence:**
1. Rollback decision received.
2. Rollback artifacts verified.
3. Running containers stopped (ordered shutdown).
4. Previous image pulled.
5. Previous containers started.
6. Database snapshot restored if schema was changed.
7. Health checks executed.
8. Rollback declared complete or failed.

**SLA:** Rollback complete within 5 minutes of trigger. If rollback exceeds 5
minutes, Architecture Council is immediately notified.

---

## 3.15 Component 14 — Migration Manager

**Purpose:** The Migration Manager manages all database schema migrations,
ensuring that schema changes are applied safely, reversibly, and with zero
data loss.

**Responsibilities:**
- Maintain the ordered sequence of schema migration scripts.
- Detect which migrations need to be applied to the current database state.
- Apply migrations in the correct order.
- Verify migration success.
- Manage schema version tracking.
- Test migrations against a copy of the production schema before production application.
- Maintain forward-compatible schema versions (current code must run on both
  current and previous schema during the upgrade window).

**Inputs:**
- Current database schema version.
- Migration scripts from version control.
- Pre-migration database snapshot.

**Outputs:**
- Updated database at target schema version.
- Migration manifest.
- Migration verification report.

**Failure Modes:**
- Migration script fails: deployment halted; database restored from pre-migration
  snapshot; incident raised.
- Migration produces incorrect schema: verified by schema validator before new
  code is started.

**Engineering Notes:**
All IIOS migrations are forward-only. There are no rollback migrations. Schema
rollback, if required, is achieved by restoring the pre-migration database snapshot.

---

## 3.16 Component 15 — Health Verification Manager

**Purpose:** The Health Verification Manager defines and executes the complete
set of health checks that verify system correctness after any deployment, upgrade,
rollback, or recovery.

**Responsibilities:**
- Define health check suites per environment.
- Execute health checks after every lifecycle event.
- Verify: container health, data feed connectivity, broker mock response,
  database accessibility, cycle timing, Telegram bot response.
- Produce health verification reports.
- Trigger rollback on health check failure.
- Maintain health check history.

**Inputs:**
- Health check definitions.
- Running system under verification.

**Outputs:**
- Health verification report (PASS/FAIL per check).
- System health score.
- Rollback trigger if required.

**Health Check Suite — Production:**
- Container health probe: all containers report healthy.
- Full cycle execution: one trading cycle executes without error.
- Cycle latency: full cycle < 200ms.
- GlobalIntelligence latency: <= 17ms (cache hit).
- Database accessibility: all three SQLite databases respond.
- Data feed: yfinance fallback responds to test query.
- Telegram bot: /status command responds.
- Kill switch: reports correct state (inactive).
- Paper trading: order manager in paper mode.

---

## 3.17 Component 16 — Monitoring Manager

**Purpose:** The Monitoring Manager maintains continuous visibility into the
health, performance, and correctness of the deployed IIOS system.

**Responsibilities:**
- Configure monitoring for all production and staging environments.
- Define and maintain alert rules.
- Produce the monitoring dashboard configuration.
- Integrate with Streamlit dashboard for operational visibility.
- Route alerts to Telegram bot.
- Maintain monitoring history.
- Detect and alert on metric baselines deviating > 20%.

**Inputs:**
- Metric definitions from each IIOS layer.
- Alert threshold configurations.
- Baseline values.

**Outputs:**
- Running monitoring system.
- Alert notifications (Telegram).
- Monitoring dashboard.

---

## 3.18 Component 17 — Certification Manager

**Purpose:** The Certification Manager manages the deployment certification
process, ensuring that no artifact is deployed to production without a formal
certification record.

**Responsibilities:**
- Receive quality evidence from the testing framework.
- Compute the deployment certification score.
- Produce the deployment certification record.
- Coordinate Architecture Council review.
- Track certification validity (90-day expiry).
- Block deployments of uncertified artifacts.
- Archive all certification records.

**Inputs:**
- Testing quality evidence.
- Coverage scores.
- Security scan results.
- Architecture Council approval.

**Outputs:**
- Deployment certification record.
- Certification score.
- Architecture Council review request.

---

## 3.19 Component 18 — Governance Manager

**Purpose:** The Governance Manager maintains the enforcement of all governance
policies across the entire build and deployment lifecycle.

**Responsibilities:**
- Monitor compliance with all build standards.
- Monitor compliance with all deployment standards.
- Enforce approval workflows.
- Produce governance audit reports.
- Detect and report policy violations.
- Maintain the governance audit trail.
- Coordinate quarterly governance reviews.

**Inputs:**
- Policy definitions.
- Build and deployment events.
- Approval decisions.

**Outputs:**
- Governance audit trail.
- Policy compliance report.
- Governance violation alerts.

---

*End of Part III*

# PART IV — ENVIRONMENT ARCHITECTURE

## 4.1 Environment Philosophy

An environment is a fully provisioned, configured, and isolated instance of the
IIOS platform with a specific purpose, a specific configuration, and a specific
access control policy. Environments are not improvisations — each environment
has a formal specification, an owner, a lifecycle, and clear boundaries.

The foundational rule is strict environment isolation: components in one
environment never communicate with components in another environment unless the
communication is explicitly defined as cross-environment and specifically
authorized by the Architecture Council.

---

## 4.2 Environment Hierarchy

`
+---------------------------+
|  Research / Training      |  (No live data, no financial operations)
+---------------------------+
            |
+---------------------------+
|  Local Development        |  (Developer machine, max isolation)
+---------------------------+
            |
+---------------------------+
|  Developer Sandbox        |  (Shared dev integration)
+---------------------------+
            |
+---------------------------+
|  Integration              |  (Component integration verification)
+---------------------------+
            |
+---------------------------+
|  Testing                  |  (Automated test suite execution)
+---------------------------+
            |
+---------------------------+
|  QA                       |  (Structured quality assurance)
+---------------------------+
            |
+---------------------------+
|  UAT                      |  (User acceptance testing)
+---------------------------+
            |
+---------------------------+
|  Simulation               |  (Full market simulation)
+---------------------------+
            |
+---------------------------+
|  Replay                   |  (Historical data replay)
+---------------------------+
            |
+---------------------------+
|  Paper Trading            |  (Live paper trading simulation)
+---------------------------+
            |
+---------------------------+
|  Pre-Production           |  (Final production gate)
+---------------------------+
            |
+---------------------------+
|  PRODUCTION               |  (Live financial operations)
+---------------------------+
            |
+---------------------------+
|  Disaster Recovery        |  (Cold standby; activated on DR)
+---------------------------+
            |
+---------------------------+
|  Archive                  |  (Historical data and evidence)
+---------------------------+
`

---

## 4.3 Environment 1 — Local Development

**Code:** ENV-LOCAL
**Owner:** Individual engineer
**Purpose:** Personal development and debugging environment on the developer
workstation.

**Configuration:**
- PAPER_TRADING: true (forced)
- Data feed: yfinance mock or local fixture data
- Broker: mock broker
- Telegram: test bot (not production channel)
- Database: local SQLite files
- Kill switch: inactive (can be manually triggered for testing)
- Log level: DEBUG

**Isolation:**
- No connection to production systems.
- No connection to integration or QA environments.
- Network access: internet allowed for yfinance data only.
- Data: local files only.

**Lifecycle:**
- Created by developer on local machine.
- Exists for the duration of the development session.
- No formal provisioning required.
- Data is ephemeral (not persisted between sessions unless explicitly saved).

**Access:** Developer only.

**Deployment to this environment:** Local docker compose up.

---

## 4.4 Environment 2 — Developer Sandbox

**Code:** ENV-SANDBOX
**Owner:** Platform Team
**Purpose:** Shared development integration environment for testing multi-component
changes before raising a PR.

**Configuration:**
- PAPER_TRADING: true (forced)
- Data feed: yfinance (live)
- Broker: mock broker
- Telegram: sandbox bot
- Database: sandbox SQLite (shared, cleared weekly)
- Kill switch: functional

**Isolation:**
- No connection to production systems.
- Shared among developers — coordinate usage.
- No access to live broker.

**Lifecycle:**
- Continuously running on shared infrastructure.
- Cleared and re-provisioned weekly.
- Not subject to deployment governance (exploratory environment).

**Access:** All engineers.

---

## 4.5 Environment 3 — Integration

**Code:** ENV-INT
**Owner:** Platform Team
**Purpose:** Automated integration testing environment. Used by CI/CD pipeline
to run integration tests on every PR.

**Configuration:**
- PAPER_TRADING: true (forced)
- Data feed: fixture data (no live network)
- Broker: mock broker
- Telegram: test mock
- Database: fresh databases per test run
- All external dependencies: mocked

**Isolation:**
- Completely isolated from external networks.
- Created fresh for each CI run and destroyed after.
- Ephemeral — no persistent state between runs.

**Lifecycle:**
- Created by CI/CD pipeline on PR trigger.
- Integration tests executed.
- Results recorded.
- Environment destroyed.

**Access:** CI/CD pipeline only.

---

## 4.6 Environment 4 — Testing

**Code:** ENV-TEST
**Owner:** Testing Team
**Purpose:** Long-running test environment for automated test suite execution,
including performance and load tests.

**Configuration:**
- PAPER_TRADING: true (forced)
- Data feed: historical fixture data for determinism
- Broker: mock broker
- Performance benchmarks: enabled
- Resources: matches production sizing

**Isolation:**
- No connection to production.
- Persistent between test runs (baseline comparisons).

**Lifecycle:**
- Continuously running.
- Reset to baseline state before each certification run.
- Managed by Testing Team.

**Access:** Testing Team; CI/CD pipeline.

---

## 4.7 Environment 5 — QA

**Code:** ENV-QA
**Owner:** Quality Assurance Team
**Purpose:** Structured quality assurance environment for formal QA activities.

**Configuration:**
- PAPER_TRADING: true
- Data feed: mix of fixture and live yfinance data
- Configuration: matches staging

**Lifecycle:**
- Continuously running.
- Deployed with new builds for QA validation.
- QA sign-off required before build proceeds to UAT.

**Access:** QA Team; Testing Team lead.

---

## 4.8 Environment 6 — UAT

**Code:** ENV-UAT
**Owner:** Architecture Council
**Purpose:** User acceptance testing environment for Architecture Council review.

**Configuration:**
- PAPER_TRADING: true
- Data feed: live yfinance
- Configuration: matches production exactly except broker

**Lifecycle:**
- Deployed per release cycle.
- Architecture Council conducts review.
- Approval or rejection recorded.

**Access:** Architecture Council; QA Team lead.

---

## 4.9 Environment 7 — Simulation

**Code:** ENV-SIM
**Owner:** Research Lab Team
**Purpose:** Full market simulation environment running Monte Carlo and 14-scenario
simulations.

**Configuration:**
- PAPER_TRADING: true
- Data feed: synthetic and historical
- Monte Carlo engine: full 14-scenario suite enabled
- Long-running simulation mode

**Lifecycle:**
- Running during simulation campaigns.
- Results archived.

**Access:** Research Lab Team.

---

## 4.10 Environment 8 — Replay

**Code:** ENV-REPLAY
**Owner:** Learning System Team
**Purpose:** Historical data replay environment for strategy decision regression
testing.

**Configuration:**
- PAPER_TRADING: true
- Data feed: historical replay only
- Injectable clock: active
- Decision engine: full pipeline

**Lifecycle:**
- Activated for replay testing campaigns.
- Each replay run uses a specific historical date range.

**Access:** Learning System Team; Testing Team.

---

## 4.11 Environment 9 — Paper Trading

**Code:** ENV-PAPER
**Owner:** Architecture Council
**Purpose:** Live paper trading environment running the full IIOS pipeline with
simulated order execution against live market data.

**Configuration:**
- PAPER_TRADING: true (fundamental constraint)
- Data feed: live yfinance (real market data)
- Broker: paper broker (order manager with CSV journal)
- Kill switch: fully functional
- All 17 layers active

**Isolation:**
- No connection to live broker.
- Live market data only.
- Production-equivalent configuration in all respects except broker.

**Lifecycle:**
- Runs during market hours.
- Continuously available for Architecture Council review.
- Managed as production-like environment.

**Access:** Architecture Council; senior engineers.

---

## 4.12 Environment 10 — Pre-Production

**Code:** ENV-PREPROD
**Owner:** Architecture Council
**Purpose:** The final validation gate before production. Identical to production
in every configuration detail. The final staging environment.

**Configuration:**
- Identical to production in every respect.
- PAPER_TRADING: true (the only difference from production).
- Production data feeds.
- Production resource sizing.
- Production monitoring.

**Lifecycle:**
- Deployed with each release candidate.
- Minimum 24-hour soak period required.
- Architecture Council sign-off required before promotion.

**Access:** Architecture Council only.

---

## 4.13 Environment 11 — Production

**Code:** ENV-PROD
**Owner:** Architecture Council
**Purpose:** The live production environment running real financial operations.

**Configuration:**
- PAPER_TRADING: settable by Architecture Council (default true; paper by policy)
- Data feed: live yfinance with Dhan fallback
- Broker: live Dhan broker (when PAPER_TRADING=false)
- All 17 layers active
- Kill switch: fully functional
- Full monitoring active

**Server:** VPS at 178.18.252.24

**Isolation:**
- No connection to any non-production environment.
- Data volume is isolated and backed up.
- Access restricted to Architecture Council.

**Lifecycle:**
- Continuously running.
- Deployed per release cycle.
- Monitored 24/7 during market hours.

**Deployment window:** Outside market hours only (before 09:00 IST or after
15:30 IST, Monday–Friday). Emergency deployments excepted with Architecture
Council authorization.

**Access:** Architecture Council only.

---

## 4.14 Environment 12 — Disaster Recovery

**Code:** ENV-DR
**Owner:** Platform Team
**Purpose:** Cold standby environment activated in the event of a production
catastrophic failure.

**Configuration:**
- Identical to production.
- Data volume: daily snapshot from production.
- Activation time target: 30 minutes from DR declaration.

**Lifecycle:**
- Maintained in cold standby.
- Tested quarterly with a DR drill.
- Activated by Architecture Council DR declaration.

**Access:** Architecture Council; Platform Team on-call.

---

## 4.15 Environment 13 — Archive

**Code:** ENV-ARCHIVE
**Owner:** Platform Team
**Purpose:** Long-term storage of historical build artifacts, certification
evidence, database snapshots, and deployment records.

**Retention policy:** Minimum 5 years.
**Access:** Compliance; Architecture Council for retrieval.

---

## 4.16 Environment 14 — Training

**Code:** ENV-TRAIN
**Owner:** MetaLearning Team
**Purpose:** Isolated environment for AI model training runs using historical
market data.

**Configuration:**
- No live data access.
- Historical datasets only.
- No connection to trading systems.

**Access:** MetaLearning Team; Research Lab Team.

---

## 4.17 Environment 15 — Research

**Code:** ENV-RESEARCH
**Owner:** Research Lab Team
**Purpose:** Free-form research and experimentation environment with no
deployment governance requirements.

**Configuration:**
- No live data access (by default).
- Research datasets.
- No connection to trading systems.

**Access:** Research Lab Team.

---

*End of Part IV*

---

# PART V — DEPLOYMENT LIFECYCLE

## 5.1 Lifecycle Overview

`
IIOS DEPLOYMENT LIFECYCLE

COMMIT
  |
  v
[1. BUILD] --> Build registry entry created
  |
  v
[2. VALIDATE] --> Artifact integrity, dependency scan, CVE check
  |
  v
[3. PACKAGE] --> Container image assembled, signed
  |
  v
[4. SIGN] --> Artifact signed by Build Infrastructure
  |
  v
[5. STORE] --> Signed artifact pushed to Artifact Registry / Image Registry
  |
  v
[6. DEPLOY] --> Ordered shutdown -> Migration -> Container start
  |
  v
[7. VERIFY] --> Health checks, cycle execution, latency verification
  |             \
  |              --> [ROLLBACK] if FAIL
  v
[8. MONITOR] --> Continuous monitoring begins
  |
  v
[9. UPGRADE] --> Next deployment cycle begins (returns to COMMIT)
  |
  v
[10. ROLLBACK] --> On failure or decision: restore previous state
  |
  v
[11. RECOVER] --> On catastrophic failure: DR activation or recovery build
  |
  v
[12. RETIRE] --> End of version lifecycle; artifact archived
`

---

## 5.2 Stage 1 — Build

**Entry condition:** Source commit on a governed branch with CI/CD trigger.

**Actions:**
- Build Registry record initialized.
- Dependencies resolved from requirements.lock.
- Dependency CVE scan executed.
- Source compiled and packaged.
- Container image built from Dockerfile.
- Build manifest generated (all input hashes, output hash).

**Exit condition:** Container image successfully built. Build manifest complete.

**Failure handling:** Build failure recorded in Build Registry. CI/CD pipeline
fails. PR merge blocked if on a PR branch.

---

## 5.3 Stage 2 — Validate

**Entry condition:** Successful build. Container image and build manifest available.

**Actions:**
- Artifact integrity hash verified against build manifest.
- Container image vulnerability scan executed.
- Dependency SBOM generated.
- Test suite executed against the artifact.
- Coverage scores computed.
- Performance benchmarks executed (for release builds).

**Exit condition:** All validations PASS. Artifact cleared for packaging.

**Failure handling:** Any validation failure blocks progression. Security failures
trigger immediate security incident. Test failures block the PR merge.

---

## 5.4 Stage 3 — Package

**Entry condition:** Validated artifact.

**Actions:**
- Container image tagged with version and build ID.
- Release manifest assembled (version, component list, change list, artifact hashes).
- Deployment configuration generated for target environment.
- Rollback artifact pre-positioned (previous certified image retrieved and verified).

**Exit condition:** Tagged image and complete deployment package ready.

---

## 5.5 Stage 4 — Sign

**Entry condition:** Packaged artifact.

**Actions:**
- Container image signed using Build Infrastructure signing certificate.
- Signing record added to Artifact Registry metadata.
- Signature verification executed immediately after signing.

**Exit condition:** Signed artifact with verified signature.

**Failure handling:** Signing failure blocks all deployment. Security Team notified.

---

## 5.6 Stage 5 — Store

**Entry condition:** Signed artifact.

**Actions:**
- Signed image pushed to Image Registry.
- Artifact metadata stored in Artifact Registry.
- Build Registry updated with artifact location.
- Pre-deployment database snapshot taken (for production and staging).
- Snapshot integrity hash computed and stored.

**Exit condition:** Artifact stored in Registry. Snapshot completed and verified.

---

## 5.7 Stage 6 — Deploy

**Entry condition:** Authorization from Architecture Council (for staging and
production). Automated for lower environments.

**Pre-deployment checks (all must PASS):**
1. Artifact signature verified.
2. Artifact hash matches Registry record.
3. Kill switch verified INACTIVE.
4. Market hours guard: current time is outside trading hours.
5. Rollback artifact verified available.
6. Database snapshot verified.
7. Target environment health: environment is in expected pre-deployment state.

**Deployment sequence:**
1. Pre-deployment checks (all PASS required).
2. Announcement: Deployment beginning notification sent.
3. Ordered shutdown: all 17 layers stopped in reverse order (17→1).
4. Database migration: Migration Manager applies pending migrations.
5. Migration verification: schema validator confirms correct schema.
6. Container image pull: new image pulled from Image Registry (by digest).
7. Container start: ai-trading-brain container started.
8. Dashboard start: trading-dashboard container started.
9. Health probes: containers report healthy.
10. Post-deployment health suite: full health check suite executed.

**Exit condition:** All health checks PASS. System declared deployed.

**Failure handling:** Any failure triggers rollback. Deployment record updated
with failure reason.

---

## 5.8 Stage 7 — Verify

**Entry condition:** Deployment complete. New containers running.

**Actions:**
- Full health check suite executed (see Component 15 — Health Verification Manager).
- One complete trading cycle executed and verified.
- Cycle latency verified (< 200ms).
- GlobalIntelligence latency verified (<= 17ms cache hit).
- All 17 layers report HEALTHY in ControlTower.
- Telegram /status command returns correct state.

**Exit condition:** All verifications PASS. System declared HEALTHY.

**Failure handling:** Any verification failure initiates immediate rollback.

---

## 5.9 Stage 8 — Monitor

**Entry condition:** System verified HEALTHY after deployment.

**Actions:**
- Continuous monitoring activated.
- Baseline comparison established (current metrics vs pre-deployment metrics).
- Heightened monitoring for 24 hours post-deployment.
- Alert thresholds reduced by 50% for the first 24 hours (tighter sensitivity).

**Duration:** Permanent (until next deployment cycle).

**Failure handling:** Monitoring alert triggers on-call notification. Persistent
failures trigger Architecture Council incident declaration.

---

## 5.10 Stage 9 — Upgrade

**Entry condition:** New release ready. Architecture Council authorization received.

**Description:** The upgrade stage is a complete new execution of stages 1–8
for the next version. It is not a distinct lifecycle stage but rather the
re-entry into the lifecycle.

---

## 5.11 Stage 10 — Rollback

**Entry condition:** Deployment failure, health check failure, or explicit
Architecture Council rollback decision.

**Actions:**
1. Rollback trigger received (automatic or manual).
2. Current containers stopped immediately.
3. Previous certified image retrieved from Image Registry.
4. Previous image signature verified.
5. Database snapshot restored if schema migration was applied.
6. Previous containers started.
7. Health check suite executed.

**SLA:** Rollback complete within 5 minutes of trigger.

**Exit condition:** Previous state restored. Health checks PASS.

**Failure handling (rollback failure):** Architecture Council declares emergency.
On-call engineer manually intervenes. DR environment may be activated.

---

## 5.12 Stage 11 — Recover

**Entry condition:** Catastrophic failure that rollback cannot resolve. DR
environment activation required.

**Actions:**
1. Architecture Council declares DR.
2. DR environment activated.
3. Latest data volume snapshot restored to DR environment.
4. DR environment health verified.
5. Traffic switched to DR environment.
6. Incident post-mortem initiated.

**Recovery Time Objective:** 30 minutes from DR declaration.

---

## 5.13 Stage 12 — Retire

**Entry condition:** Version is no longer active (superseded by newer version
for more than 90 days; LTS support period expired).

**Actions:**
- Image marked RETIRED in Image Registry.
- Image moved to archive storage.
- Build records marked ARCHIVED.
- Retirement recorded in Governance Manager.

**Retention:** Retired images retained in archive for minimum 5 years.

---

*End of Part V*

---

# PART VI — RELEASE ENGINEERING

## 6.1 Release Policy

IIOS follows a structured release policy designed to balance the need for
continuous improvement with the requirement for stability in a financial
operations platform.

**Planned releases:** Quarterly major feature releases, with minor releases as
needed. Patch releases on an as-needed basis for defect resolution.

**Freeze periods:** No planned releases are executed within 5 trading days of
major market events (budget announcements, RBI monetary policy decisions,
F&O expiry weeks where the system is under elevated load).

**Code freeze:** Feature freeze occurs 7 days before the target release date.
Only defect fixes are accepted after feature freeze.

---

## 6.2 Semantic Versioning

IIOS uses Semantic Versioning 2.0.0 with the following interpretation:

`
MAJOR.MINOR.PATCH[-PRE_RELEASE][+BUILD_METADATA]

MAJOR: Architectural changes; breaking internal interfaces; 17-layer reordering.
       Increment when: new subsystem added that changes layer count;
       interface signatures change; data model breaks backward compatibility.

MINOR: New features compatible with existing architecture.
       Increment when: new engine capability; new trading strategy type;
       new monitoring dimension; new data feed integration.

PATCH: Defect fixes, performance improvements, configuration changes.
       Increment when: any change that does not add features or break interfaces.

PRE_RELEASE: -alpha.N, -beta.N, -rc.N for pre-production designations.

BUILD_METADATA: +build.YYYYMMDD.HHMMSS for traceability.
`

**Examples:**
- v1.0.0: Initial production release.
- v1.1.0: New trading strategy category added.
- v1.1.1: Bug fix in order manager.
- v1.1.2-rc1: Release candidate for next patch.
- v2.0.0: Major architectural version (17-layer count changed or interface broken).

---

## 6.3 Feature Freeze

Feature freeze is enforced at the tooling level. After feature freeze date:
- No new feature branches may be merged to the release branch.
- Only hotfix and defect-fix PRs are accepted.
- All PRs require Architecture Council reviewer approval after freeze.

Feature freeze date is declared 14 days before the planned release date.

---

## 6.4 Release Gates

All of the following must reach PASS status before a production release is authorized:

| Gate | Owner | Threshold |
|------|-------|----------|
| Build gate | Platform Team | Clean build successful |
| Unit test gate | Testing Team | 100% pass rate |
| Integration test gate | Testing Team | 100% pass rate |
| Coverage gate | Testing Team | SCS >= 0.92 |
| Performance gate | Platform Team | No regression > 10% |
| Security gate | Security Team | No CVE >= MEDIUM unresolved |
| Staging gate | Architecture Council | 24h soak in pre-production |
| Rollback gate | Platform Team | Rollback verified in staging |
| Documentation gate | Architecture Council | Release notes complete |
| Council vote gate | Architecture Council | Unanimous approval |

---

## 6.5 Approval Workflow

`
RELEASE APPROVAL WORKFLOW

Engineer raises release ticket
         |
         v
Platform Team confirms build and test gates
         |
         v
Security Team confirms security gate
         |
         v
Testing Team confirms coverage and test gates
         |
         v
Architecture Council receives complete evidence package
         |
         v
Architecture Council vote (unanimous required for PRODUCTION)
         |
    Pass |       Fail |
         |            +-> Return to engineering with deficiency list
         v
Deployment authorized -- Deployment Manager proceeds
`

---

## 6.6 Artifact Validation

Every artifact in the release package is validated before deployment:

1. **Hash verification:** Artifact SHA256 hash matches Artifact Registry record.
2. **Signature verification:** Artifact signature is valid against Build Infrastructure certificate.
3. **Version verification:** Artifact version matches the authorized version.
4. **Build Registry verification:** Artifact build record shows COMPLETE status.
5. **CVE scan verification:** Most recent scan result is CLEAN (or all findings ACCEPTED).
6. **Testing certification:** Artifact's testing certification is valid (within 90 days).

---

## 6.7 Compatibility Verification

Before any release, compatibility is verified in the following dimensions:

**Backward compatibility:** Existing persisted data (SQLite databases, CSV journals,
JSON strategy files) is readable by the new version.

**Forward compatibility (limited):** During the upgrade window, the new container
code must be able to read data written by the old code. This is enforced through
database migration design.

**Configuration compatibility:** New version must accept the previous environment
configuration without error. Breaking configuration changes require a migration
step.

**API compatibility:** All interfaces listed as Critical Interfaces in
copilot-instructions.md must maintain unchanged signatures.

---

## 6.8 Deployment Approval

Deployment approval is granted by the Architecture Council after all release
gates pass. Approval is:

- **Written:** Recorded in the governance audit trail.
- **Specific:** Specifies the exact artifact version and target environment.
- **Time-bounded:** Approval expires after 5 trading days. An expired approval
  requires re-authorization.
- **Revocable:** Architecture Council can revoke approval before deployment begins.

---

## 6.9 Rollback Criteria

A production rollback is initiated when any of the following occur:

1. Post-deployment health check fails for any HARD check.
2. Full cycle latency exceeds 300ms (1.5x baseline) for two consecutive cycles.
3. Kill switch triggers spontaneously within 30 minutes of deployment.
4. Any error rate > 5% in the first 30 minutes post-deployment.
5. Data integrity check fails post-deployment.
6. Architecture Council explicit rollback decision.

Rollback decisions are not reversible without a new deployment authorization.

---

## 6.10 Release Documentation

Every production release requires:

1. **Release notes:** Human-readable summary of all changes.
2. **Change list:** Enumeration of every file modified and the nature of each change.
3. **Impact assessment:** Analysis of which layers are affected.
4. **Migration notes:** Description of any schema or data migrations.
5. **Rollback procedure:** Step-by-step rollback instructions for this release.
6. **Post-deployment checks:** Specific checks for this release's changes.
7. **Known issues:** Any known issues in the release with workarounds.

---

## 6.11 Release Certification

A release certification is issued when:
- All release gates PASS.
- Architecture Council approval is recorded.
- Release documentation is complete.
- Rollback artifact is verified.
- Release evidence is archived.

The release certification is a formal record in the Certification Manager. It
expires after 90 days. An expired certification must be renewed before the
artifact can be deployed.

---

*End of Part VI*

# PART VII — OPERATIONAL RELIABILITY

## 7.1 Blue-Green Deployment

Blue-Green deployment maintains two identical production environments: Blue
(currently serving traffic) and Green (idle). A new deployment is applied to
Green. After Green is verified healthy, traffic is switched from Blue to Green.
Blue becomes the idle environment, ready for immediate rollback.

**Applicability to IIOS:** IIOS currently operates a single-server VPS
deployment. Blue-Green is implemented at the container level: the old containers
(Blue) are stopped and the new containers (Green) are started. The data volume
is shared between both. If the Green deployment fails health checks, the Blue
containers are restarted from the previous image.

**Rollback time:** < 2 minutes (previous image is locally cached; no registry
pull required).

**Requirements:**
- Previous production image is always retained on the VPS host.
- Both Blue and Green image versions are tagged and labeled in docker compose.
- Docker volume is not tied to either Blue or Green containers.

---

## 7.2 Canary Deployment

Canary deployment gradually shifts a small percentage of traffic to the new
version, monitoring its behavior before committing the full deployment.

**Applicability to IIOS:** Because IIOS does not serve external traffic but
runs as an autonomous trading engine, canary deployment is implemented as
a time-based canary: the new version runs paper trading for a defined soak
period (24 hours minimum) in the Pre-Production environment while the current
production version continues operating. If the canary soak succeeds, the full
production deployment proceeds.

**Canary success criteria:**
- No errors in 24-hour soak period.
- Full cycle latency within 10% of production baseline.
- Decision quality metrics comparable to production.
- Kill switch not triggered.

---

## 7.3 Rolling Deployment

Rolling deployment replaces instances one at a time, ensuring that some
instances of the old version are always running during the upgrade.

**Applicability to IIOS:** IIOS is a single-instance system (no horizontal
scaling at this time). Rolling deployment is implemented at the layer level:
layers are upgraded and verified in order from Layer 1 to Layer 17, with each
layer verified before the next is upgraded.

This is approximated through the ordered shutdown and ordered startup sequences
in the Deployment Manager.

---

## 7.4 Shadow Deployment

Shadow deployment runs the new version in parallel with the old version, feeding
the same inputs to both, comparing outputs, and detecting divergence without
affecting production behavior.

**Applicability to IIOS:** Shadow mode is used for decision engine validation.
A new decision engine version can be run in shadow mode, receiving the same
market data as production, with its decisions logged but not executed. Shadow
decision quality is compared to production decision quality over a 7-day period.

**Shadow mode configuration:**
- SHADOW_MODE: true
- Shadow decisions logged to data/shadow_decisions.csv
- No orders are placed from shadow mode, ever.

---

## 7.5 Feature Flags

Feature flags allow new capabilities to be deployed without being activated,
enabling progressive rollout and instant disable without redeployment.

**IIOS feature flag taxonomy:**

| Flag | Purpose | Default | Activation |
|------|---------|---------|-----------|
| ENABLE_LIVE_TRADING | Switch from paper to live orders | false | Council only |
| ENABLE_CONTINUOUS_SCAN | 30s market monitoring | true | Admin |
| ENABLE_SHADOW_DECISIONS | Shadow decision engine | false | Council |
| ENABLE_NEW_STRATEGY_TYPE | New strategy category | false | Testing |
| ENABLE_TELEGRAM_ALERTS | Telegram notifications | true | Admin |
| ENABLE_DHAN_FEED | Dhan data feed (when token available) | false | Admin |
| ENABLE_WALKFORWARD_TEST | Walk-forward testing in live cycle | false | Council |

**Flag governance:** Feature flags are version-controlled configuration. Changes
require the same approval as configuration changes.

---

## 7.6 Kill Switches

IIOS implements a hierarchical kill switch system for immediate operational halt:

**Level 1 — Global Kill Switch:**
Halts all trading operations immediately. Triggered by:
- VIX > 45.0 (automatic)
- Daily portfolio loss > 2.0% (automatic)
- Architecture Council manual trigger

**Level 2 — Strategy Kill Switch:**
Halts a specific strategy without affecting others. Triggered by:
- Win rate drops below OHS threshold (automatic)
- Architecture Council manual trigger per strategy

**Level 3 — Data Feed Kill Switch:**
Halts operations when data quality degrades below acceptable threshold.

**Kill switch state persistence:**
Kill switch state is persisted to three locations simultaneously:
- Primary: data/kill_switch.json
- Secondary: data/telemetry.db kill_switch_events table
- Tertiary: Telegram alert (not machine-readable, but human-notifiable)

Kill switch state survives container restart. The system restarts with the
kill switch in the same state it was in before the restart.

---

## 7.7 Health Checks

Docker health checks are configured for all IIOS containers:

**ai-trading-brain container:**
- Check interval: 30 seconds
- Timeout: 10 seconds
- Start period: 60 seconds (allows startup to complete)
- Retries: 3 (3 consecutive failures = UNHEALTHY)
- Check: Python script verifying database connectivity and last cycle timestamp

**trading-dashboard container:**
- Check interval: 30 seconds
- Timeout: 10 seconds
- Start period: 30 seconds
- Retries: 3
- Check: HTTP GET to Streamlit health endpoint

---

## 7.8 Heartbeat Monitoring

The IIOS ControlTower maintains a heartbeat record for each active layer. A
heartbeat is a timestamp written by each layer at the start of each cycle.

**Heartbeat failure detection:**
- Layer heartbeat not updated within 2 cycle intervals: WARNING alert.
- Layer heartbeat not updated within 5 cycle intervals: CRITICAL alert; layer
  considered failed.
- Global heartbeat (master orchestrator cycle) not updated: CRITICAL alert to
  Telegram.

**Heartbeat persistence:** Heartbeats are written to data/telemetry.db. The
dashboard reads from this table.

---

## 7.9 Readiness Checks

A readiness check verifies that the system is ready to accept work (process
trading cycles). Readiness is distinct from liveness.

**Readiness conditions:**
1. All 17 layers have completed their initialization.
2. Data feed is responding.
3. Database is accessible.
4. Kill switch is inactive (or system is in kill-switch-acknowledged mode).
5. Strategy pool has at least one active strategy.

During startup, the system declares itself NOT READY until all readiness
conditions are met. The scheduler does not begin processing trading cycles
until the system is READY.

---

## 7.10 Liveness Checks

A liveness check verifies that the system is running and not in a deadlock
or infinite wait state.

**Liveness conditions:**
- Master orchestrator last cycle timestamp < 10 minutes ago.
- No thread waiting on a lock for > 60 seconds.
- Log output being produced (system not silently hung).

A liveness check failure triggers container restart (via Docker health check
UNHEALTHY → restart policy).

---

## 7.11 Auto Recovery

Auto recovery is the system's ability to detect and recover from transient
failures without human intervention.

**Auto recovery triggers:**
- Data feed timeout: automatic fallback to yfinance within 90 seconds.
- Database write failure: retry 3 times with exponential backoff.
- Layer execution timeout: layer cycle skipped; next cycle proceeds.
- Telegram send failure: retry 3 times; if persistent, log and continue.

**Auto recovery limits:**
- If the same failure occurs in 5 consecutive cycles, auto recovery stops
  retrying and escalates to CRITICAL alert.
- Auto recovery never activates after kill switch trigger. The kill switch
  must be explicitly cleared.

---

## 7.12 Auto Restart

The ai-trading-brain container is configured with estart: unless-stopped
in docker-compose.yml. If the container exits unexpectedly (crash, OOM), Docker
automatically restarts it.

**Restart behavior:**
- Container restart does not reset kill switch state (persisted in volume).
- Container restart does not reset position state (persisted in data/).
- Container restart triggers a startup health check before accepting cycles.
- Three consecutive restarts within 5 minutes: CRITICAL alert to Telegram.

---

## 7.13 Disaster Recovery

**DR Declaration:** Architecture Council declares a DR event when the production
system cannot be restored within 30 minutes through normal rollback procedures.

**DR Activation Sequence:**
1. Architecture Council votes to declare DR.
2. Platform Team activates ENV-DR.
3. Latest data volume snapshot applied to DR environment.
4. DR environment health checks executed.
5. Architecture Council confirms DR environment is HEALTHY.
6. Operations switched to DR environment.
7. Post-DR incident review initiated (within 24 hours).

**DR Test:** DR activation is tested quarterly in a scheduled DR drill.
The drill verifies the complete DR sequence without affecting production.

---

## 7.14 Business Continuity

**Trading continuity objective:** Financial operations must be restorable within
30 minutes of any failure.

**Data continuity objective:** No financial transaction data is lost under any
failure scenario.

**Continuity mechanisms:**
- WAL mode on all SQLite databases prevents corruption on abrupt shutdown.
- Data volume snapshots taken before every deployment.
- Daily automated volume snapshots to off-site storage.
- Kill switch halts all new trading activity until system health is confirmed.
- All trades are journaled to data/paper_trades.csv which is in the persistent
  volume.

---

*End of Part VII*

---

# PART VIII — GOVERNANCE

## 8.1 Build Standards

All IIOS builds must conform to the following standards:

**Code standards:**
- All Python code passes the configured linter (flake8) at zero errors.
- No new pylint violations at severity W or above.
- All public interfaces include docstrings.
- No hardcoded credentials, API keys, or tokens in source.

**Build standards:**
- Every build is a clean build for staging and production.
- Every build is executed from a specific, tagged commit.
- Every build produces a build manifest.
- No build uses floating dependency versions.

**Artifact standards:**
- Every artifact has an integrity hash.
- Every production artifact is signed.
- Every artifact is vulnerability-scanned before registration.

---

## 8.2 Release Standards

**Version standards:**
- All releases follow semantic versioning 2.0.0.
- No two releases have the same version number.
- Release versions are immutable once published.

**Documentation standards:**
- Every release has complete release notes.
- Release notes are reviewed by the Architecture Council before approval.
- Release notes reference the specific version, build ID, and commit SHA.

**Process standards:**
- Feature freeze is observed for all planned releases.
- No release proceeds without passing all release gates.
- No release proceeds without Architecture Council written approval.

---

## 8.3 Deployment Standards

**Pre-deployment standards:**
- Market hours guard is enforced for production.
- Kill switch state is verified before every deployment.
- Rollback artifact is verified before every production deployment.
- Data snapshot is taken before every production deployment.

**Execution standards:**
- Deployments are executed by the Deployment Manager, not manually.
- Deployment steps are recorded in the governance audit trail.
- No deployment step is skipped, even in emergency.

**Post-deployment standards:**
- Health verification suite is executed after every deployment.
- Heightened monitoring is active for 24 hours post-deployment.
- Post-deployment report is filed within 4 hours of deployment.

---

## 8.4 Approval Workflow

| Decision | Approver | Record Type |
|---------|---------|------------|
| Feature merge to main | PR reviewers (2+) | GitHub PR approval |
| QA build promotion | QA Team lead | QA sign-off record |
| Staging deployment | Architecture Council | Written approval |
| Production deployment | Architecture Council (unanimous) | Deployment authorization |
| Rollback | Architecture Council or on-call | Rollback authorization |
| DR activation | Architecture Council (majority) | DR declaration |
| Feature flag activation (ENABLE_LIVE_TRADING) | Architecture Council (unanimous) | Flag activation record |
| Emergency release | Council chair | Emergency authorization |
| Hotfix deployment | Architecture Council (majority) | Hotfix authorization |

---

## 8.5 Environment Ownership

| Environment | Owner | Backup Owner |
|------------|-------|-------------|
| ENV-LOCAL | Individual engineer | N/A |
| ENV-SANDBOX | Platform Team | Any engineer |
| ENV-INT | Platform Team | CI/CD system |
| ENV-TEST | Testing Team | Platform Team |
| ENV-QA | QA Team | Testing Team |
| ENV-UAT | Architecture Council | QA Team |
| ENV-SIM | Research Lab Team | Platform Team |
| ENV-REPLAY | Learning System Team | Research Lab |
| ENV-PAPER | Architecture Council | Senior engineer |
| ENV-PREPROD | Architecture Council | Platform Team |
| ENV-PROD | Architecture Council | None (Council only) |
| ENV-DR | Platform Team | Architecture Council |
| ENV-ARCHIVE | Platform Team | Architecture Council |
| ENV-TRAIN | MetaLearning Team | Research Lab |
| ENV-RESEARCH | Research Lab Team | Any engineer |

---

## 8.6 Version Governance

**Version ownership:** The Version Manager is the single authority for version
numbers. No version number is assigned outside the Version Manager.

**Immutability:** Once a version number is associated with a released artifact,
the association is permanent. A released version cannot be re-released with
different content.

**Version retention:** Version history is retained permanently. The Version
Manager's history is never truncated.

**LTS designation:** LTS versions are designated by Architecture Council vote
and listed in the LTS registry.

---

## 8.7 Artifact Governance

**Immutability:** Stored artifacts are never modified. A new artifact with
a new version number replaces a changed artifact.

**Retention:** Production artifacts: 90 days in active registry; 5 years in
archive. All other artifacts: 30 days.

**Deletion:** Artifacts are only deleted after the retention period expires.
Early deletion requires Architecture Council authorization.

**Access:** Push to artifact registry: Build pipeline only. Pull from artifact
registry: Deployment pipeline and authorized environments only.

---

## 8.8 Audit Requirements

All of the following events must be recorded in the governance audit trail
with timestamp, actor, and outcome:

- Every build (success or failure).
- Every artifact registration.
- Every deployment to any environment.
- Every rollback.
- Every Architecture Council approval or rejection.
- Every kill switch activation or deactivation.
- Every configuration change.
- Every feature flag change.
- Every governance policy change.
- Every release certification.

Audit records are append-only. No audit record is ever deleted within its
retention period (minimum 5 years).

---

## 8.9 Compliance

**Regulatory compliance:** IIOS operates under SEBI regulations. All trading
activity records are retained for 7 years. The deployment audit trail includes
the exact software version active at the time of every trade.

**Security compliance:** All dependencies are scanned for CVEs at build time.
All CVEs at severity HIGH or CRITICAL must be resolved before production release.
MEDIUM CVEs must be resolved within 30 days of discovery.

**Code review compliance:** No code reaches the main branch without at least
two reviewer approvals. Architecture Council members are designated reviewers
for protected modules.

---

## 8.10 Continuous Improvement

**Quarterly governance review:** The Architecture Council reviews deployment
metrics quarterly: deployment frequency, success rate, rollback rate, MTTR,
build duration trends.

**Annual framework review:** This document is reviewed annually. Any section
found inconsistent with current practice is updated.

**Post-incident improvement:** Every P0/P1 incident produces at least one
improvement action item. Improvement actions are tracked to completion.

**Build duration target:** Build duration is tracked. If the build duration
exceeds 20 minutes for a clean production build, an optimization initiative
is initiated.

---

*End of Part VIII*

---

# PART IX — ENGINEERING CONSTITUTION

## 9.1 Preamble

The Engineering Constitution defines 110 binding rules that govern how IIOS
is built, deployed, maintained, and evolved. These rules are not guidelines —
they are engineering law. Any proposed change that violates a constitutional
rule requires Architecture Council review and an explicit Constitutional
Amendment Record before the change may proceed.

The rules are organized into 13 categories:
- BLD: Build Integrity (rules 001–010)
- DEP: Deployment Safety (rules 011–020)
- VER: Versioning (rules 021–030)
- RBK: Rollback (rules 031–040)
- REC: Recovery (rules 041–045)
- ART: Artifacts (rules 046–055)
- ENV: Environment Isolation (rules 056–065)
- SEC: Security (rules 066–075)
- AVL: Availability (rules 076–082)
- REL: Reliability (rules 083–090)
- DOC: Documentation (rules 091–097)
- GOV: Governance (rules 098–105)
- EVO: Future Evolution (rules 106–110)

---

## 9.2 Build Integrity Rules (BLD)

**BLD-001:** Every build must be reproducible. Given the same source commit,
the same dependency lock file, and the same base image digest, the build output
must be byte-identical (within deterministic tolerance for timestamp normalization).

**BLD-002:** Every build must start with a clean build directory for staging
and production builds. Incremental builds are prohibited for these artifact classes.

**BLD-003:** The dependency lock file (requirements.lock) must be committed to
version control and must exactly match the installed packages. Divergence between
requirements.lock and installed packages is a build failure.

**BLD-004:** No build uses floating dependency version specifiers (>=, ~=, ^)
in the production lock file. Every production dependency is pinned to an exact
version and hash.

**BLD-005:** Every build must produce a build manifest recording all inputs
and their hashes. A build without a manifest is not a valid build.

**BLD-006:** No hardcoded credentials, API keys, tokens, or secrets may be
present in any source file, Dockerfile, docker-compose file, or build script.

**BLD-007:** The base Docker image must be referenced by SHA256 digest in the
production Dockerfile. Mutable tags (e.g., :latest, :3.14-slim) may not be the
sole reference for production builds.

**BLD-008:** Every build must be triggered from a specific, tagged source
commit. Builds from untagged commits are valid only for development and testing
environments.

**BLD-009:** Dependency CVE scan must complete before any artifact is registered.
An artifact produced from a build with an incomplete CVE scan is not valid.

**BLD-010:** Build logs are retained for a minimum of 2 years. No build log is
deleted within this period.

---

## 9.3 Deployment Safety Rules (DEP)

**DEP-011:** No artifact is deployed to any environment without verification of
its integrity hash against the Artifact Registry record.

**DEP-012:** No artifact is deployed to any environment without verification of
its signature against the Build Infrastructure certificate.

**DEP-013:** No production deployment is executed during market hours (09:00–15:30
IST, Monday–Friday). This constraint is enforced at the tooling level. Manual
override requires Architecture Council written authorization.

**DEP-014:** The kill switch state is verified INACTIVE before every production
deployment begins. A deployment is never initiated while the kill switch is active.

**DEP-015:** The rollback artifact (previous certified image) must be verified
available and intact before any production deployment begins.

**DEP-016:** A database snapshot must be taken and verified before any production
deployment that includes schema migrations.

**DEP-017:** The deployment sequence is executed by the Deployment Manager.
Manual deployment steps that bypass the Deployment Manager are prohibited.

**DEP-018:** Every deployment step is recorded in the governance audit trail.
A deployment step that is not recorded is not a governed deployment.

**DEP-019:** Post-deployment health verification is mandatory. A deployment
for which health verification was not executed is not a complete deployment.

**DEP-020:** No production deployment proceeds without Architecture Council
written authorization. Verbal authorization is not sufficient.

---

## 9.4 Versioning Rules (VER)

**VER-021:** All IIOS releases follow Semantic Versioning 2.0.0. Non-SemVer
version identifiers are not valid for production releases.

**VER-022:** A released version number is immutable. A version that has been
published to the Artifact Registry with production status may never be re-used
for a different artifact.

**VER-023:** Every version number is assigned by the Version Manager. No
version number is assigned outside the Version Manager.

**VER-024:** Version history is retained permanently. The Version Manager's
history is never truncated or deleted.

**VER-025:** MAJOR version increments require Architecture Council unanimous
approval.

**VER-026:** Pre-release suffixes (-alpha, -beta, -rc) must correctly indicate
the maturity of the artifact. Using -rc for an alpha-quality artifact is a
governance violation.

**VER-027:** The version number embedded in the artifact must match the version
number in the Artifact Registry. A mismatch is a deployment blocker.

**VER-028:** All version-control tags corresponding to production releases are
protected tags. Only the Version Manager may create or delete them.

**VER-029:** LTS versions are designated by Architecture Council vote and entered
in the LTS registry. Self-declaration of LTS status is prohibited.

**VER-030:** Version compatibility declarations are maintained for all active
versions. An undeclared compatibility is assumed to be incompatible.

---

## 9.5 Rollback Rules (RBK)

**RBK-031:** Every production deployment must have a verified rollback available
before deployment begins. A deployment for which rollback cannot be demonstrated
in staging is not authorized.

**RBK-032:** Rollback must complete within 5 minutes of trigger. Any rollback
that cannot meet this SLA is a design failure requiring immediate remediation.

**RBK-033:** Rollback never causes data loss. Data written to persistent volumes
between deployment and rollback is preserved.

**RBK-034:** The previous production image is retained in the Image Registry
for a minimum of 90 days. It may not be deleted or overwritten.

**RBK-035:** Rollback is tested in staging before every production deployment.
A rollback that fails in staging blocks the production deployment.

**RBK-036:** Rollback decisions are recorded in the governance audit trail with
trigger reason, authorizer, start time, completion time, and outcome.

**RBK-037:** A failed rollback is a P0 incident. Architecture Council is
immediately notified and DR procedures are initiated.

**RBK-038:** After a rollback, the root cause of the deployment failure must
be documented before the next deployment attempt is authorized.

**RBK-039:** Schema rollback (undoing a database migration) is achieved by
restoring the pre-migration database snapshot, not by executing a reverse
migration. Reverse migration scripts are not used in IIOS.

**RBK-040:** The rollback procedure for every release is documented in the
release documentation before the release is authorized.

---

## 9.6 Recovery Rules (REC)

**REC-041:** The Disaster Recovery environment must be tested quarterly.
An untested DR environment is not a valid DR environment.

**REC-042:** The Recovery Time Objective for DR activation is 30 minutes.
Any recovery procedure that cannot meet this RTO must be redesigned.

**REC-043:** No financial transaction data may be lost under any single-system
failure. Mechanisms ensuring this (WAL mode, volume persistence, snapshots)
must be verified at every certification.

**REC-044:** Every P0/P1 incident must produce at least one improvement action
item. The action item must be tracked to completion.

**REC-045:** Post-mortem reports for P0 incidents are completed within 48 hours
of resolution and archived permanently.

---

## 9.7 Artifact Rules (ART)

**ART-046:** Every artifact registered in the Artifact Registry is immutable.
Registered artifacts are never modified.

**ART-047:** Every artifact has an integrity hash (SHA256) computed at build
time and stored in the Artifact Registry.

**ART-048:** Every production artifact is signed by the Build Infrastructure
signing certificate. Unsigned artifacts are never deployed to production.

**ART-049:** Every artifact is vulnerability-scanned before registration. An
artifact with unresolved CVE >= CRITICAL is not registered.

**ART-050:** Artifact deletion requires Architecture Council authorization and
is only permitted after the retention period expires.

**ART-051:** The Artifact Registry access control is enforced at the system
level. Push access is restricted to the build pipeline. Pull access is restricted
to deployment pipelines and authorized environments.

**ART-052:** Artifacts are referenced by digest for production deployments.
Mutable tags alone are not sufficient artifact references for production.

**ART-053:** Artifact retention periods are: production artifacts 90 days active
registry + 5 years archive; testing artifacts 30 days. No exception without
Architecture Council authorization.

**ART-054:** A Software Bill of Materials (SBOM) is produced for every production
artifact and archived with the release evidence.

**ART-055:** Local artifacts (built on developer machines and not registered in
the Artifact Registry) may never be deployed to any shared environment.

---

## 9.8 Environment Isolation Rules (ENV)

**ENV-056:** No component in one IIOS environment may communicate with a
component in another environment unless the communication is explicitly defined
and Architecture Council authorized.

**ENV-057:** Production data (market positions, trade records, kill switch state)
is never accessible from any non-production environment.

**ENV-058:** No production credential (Dhan API token, VPS SSH key, Telegram
production bot token) is used in any non-production environment.

**ENV-059:** Every environment has an identified owner who is responsible for
its configuration and access control.

**ENV-060:** Environment configuration is maintained in version control.
Manual environment configuration changes that are not reflected in version
control are governance violations.

**ENV-061:** Configuration drift (divergence between version control and running
environment) must be detected and remediated within 24 hours.

**ENV-062:** The Production environment (ENV-PROD) access is restricted to
Architecture Council members. No other engineer has direct access to the
production system.

**ENV-063:** Every environment is provisioned from the Environment Manager.
Ad hoc provisioning is not permitted for shared environments.

**ENV-064:** Environment retirement is a formal process. A retired environment
is deprovisioned by the Environment Manager. Manual deprovisioning is prohibited.

**ENV-065:** The pre-production environment (ENV-PREPROD) configuration must
match production configuration exactly except for the PAPER_TRADING flag.
Any divergence is a configuration defect.

---

## 9.9 Security Rules (SEC)

**SEC-066:** No secret, API key, token, or credential is stored in version
control. Violation is a P0 security incident.

**SEC-067:** All secrets are managed through the secrets manager. Hard-coded
secrets in any deployable artifact are prohibited.

**SEC-068:** All build artifacts are signed. Unsigned artifacts are never
deployed to production.

**SEC-069:** All dependencies are scanned for CVEs at build time. A production
release with an unresolved CVE >= HIGH is prohibited.

**SEC-070:** CVEs discovered after a release are tracked and addressed within:
CRITICAL — 24 hours; HIGH — 7 days; MEDIUM — 30 days; LOW — next release.

**SEC-071:** The production VPS SSH access uses key-based authentication only.
Password authentication is disabled.

**SEC-072:** All production configuration is applied through the Configuration
Manager. Direct SSH configuration changes to the production server are a
governance violation.

**SEC-073:** Security test results are archived as part of the release evidence.
A release without security test evidence is not certified.

**SEC-074:** The Dhan API token is rotated according to Dhan OAuth requirements.
A token rotation failure is a P1 incident.

**SEC-075:** Access to the production Telegram bot token is restricted to
Architecture Council members and the secrets manager.

---

## 9.10 Availability Rules (AVL)

**AVL-076:** The production system availability target during market hours is
99.5% (maximum 45 minutes unplanned downtime per month).

**AVL-077:** Planned maintenance windows are outside market hours. Unplanned
outages during market hours are P1 incidents.

**AVL-078:** The kill switch must be available and functional at all times,
even when other components are degraded.

**AVL-079:** Data feed failover to yfinance must complete within 90 seconds
of Dhan feed failure. Failover that takes longer is a reliability defect.

**AVL-080:** The restart policy (restart: unless-stopped) must be configured
for all production containers. A container without a restart policy is a
configuration defect.

**AVL-081:** The health check configuration must be active on all production
containers. A container without health checks is not a production-ready container.

**AVL-082:** Heartbeat monitoring must cover all 17 IIOS layers. A layer without
heartbeat monitoring is an availability blind spot.

---

## 9.11 Reliability Rules (REL)

**REL-083:** The full trading cycle latency must not exceed 200ms p99. A build
that regresses cycle latency beyond this threshold is not production-ready.

**REL-084:** GlobalIntelligence latency must not regress beyond 17ms p99 (cache
hit path). MarketIntelligence must not regress beyond 19ms p99.

**REL-085:** No deployment may regress any performance benchmark by more than
10% relative to the previous production version.

**REL-086:** Auto-recovery mechanisms must be tested in every certification
cycle. Untested recovery paths are unknown reliability risks.

**REL-087:** Database WAL mode must be verified active on all production
SQLite databases at every deployment.

**REL-088:** The paper trade journal (data/paper_trades.csv) must survive
any single container failure without data loss.

**REL-089:** Every transient failure handler must have a maximum retry count.
Infinite retry loops are reliability defects.

**REL-090:** After 5 consecutive failures of the same type, auto-recovery
stops retrying and escalates to CRITICAL alert. This escalation threshold
must not be changed without Architecture Council approval.

---

## 9.12 Documentation Rules (DOC)

**DOC-091:** Every production release has complete release notes approved by
the Architecture Council before deployment.

**DOC-092:** Every deployment procedure is documented in the deployment runbook.
Undocumented deployment steps are not part of the governed deployment.

**DOC-093:** Every rollback procedure is documented in the release documentation.
A release without a documented rollback procedure is not authorized.

**DOC-094:** Every configuration parameter has a documented purpose, allowed
values, default value, and environment applicability.

**DOC-095:** Every feature flag has documented purpose, activation criteria,
owner, and deactivation conditions.

**DOC-096:** Every Engineering Decision Record is archived permanently. Decision
records are never deleted.

**DOC-097:** This document is reviewed annually and updated to reflect current
practice. An outdated specification is a governance defect.

---

## 9.13 Governance Rules (GOV)

**GOV-098:** Architecture Council approval is required for all production
deployments, production rollbacks, DR activations, and feature flag changes
to ENABLE_LIVE_TRADING.

**GOV-099:** The governance audit trail is append-only. No record in the audit
trail is modified or deleted within its retention period.

**GOV-100:** Every governance policy change requires Architecture Council
approval and an Engineering Decision Record.

**GOV-101:** Quarterly governance reviews are mandatory. A quarter without a
governance review is a compliance defect.

**GOV-102:** Governance violations are recorded and tracked to resolution.
Unresolved governance violations older than 30 days are escalated to the
Architecture Council.

**GOV-103:** Emergency deployments bypass only the minimum required governance
steps. The bypassed steps are documented and executed post-emergency.

**GOV-104:** All deployment authorization records are retained for 7 years
for regulatory compliance.

**GOV-105:** The Architecture Council is the final authority on all governance
questions. There is no appeal above the Architecture Council.

---

## 9.14 Future Evolution Rules (EVO)

**EVO-106:** New IIOS layers may only be added with Architecture Council
unanimous approval and a complete architectural impact assessment.

**EVO-107:** The layer count (currently 17) is a fundamental architectural
constant. Any change triggers a MAJOR version increment.

**EVO-108:** New environment types may only be added with Architecture Council
approval and an Environment Specification document.

**EVO-109:** The build and deployment toolchain may be replaced with a new
implementation only after the new implementation has been verified to produce
identical results on all existing test cases.

**EVO-110:** This Engineering Constitution may be amended only by Architecture
Council unanimous vote, with a written Constitutional Amendment Record. No
constitutional rule is ever silently superseded.

---

*End of Part IX*

# PART X — READINESS CHECKLIST

## 10.1 Readiness Framework Overview

The Deployment Readiness Checklist defines the complete set of conditions that
must be verified before a production deployment is authorized. HARD checks are
blocking — failure prevents deployment. SOFT checks are advisory — failure must
be tracked with a plan but does not block deployment.

---

## 10.2 Domain 1 — Source Ready

| # | Check | Type | Criteria |
|---|-------|------|---------|
| 1.1 | All files committed to version control | HARD | No uncommitted changes on release branch |
| 1.2 | Release branch frozen | HARD | Feature freeze enforced; no feature merges after freeze |
| 1.3 | All PRs reviewed (2+ approvals) | HARD | No unreviewed PR in release scope |
| 1.4 | Release tag created | HARD | Source commit tagged with release version |
| 1.5 | No merge conflicts | HARD | Release branch has clean merge history |
| 1.6 | Linter passes at zero errors | HARD | flake8 reports zero errors on release branch |
| 1.7 | No hardcoded secrets in source | HARD | Secret scan clean |
| 1.8 | ARCHITECTURE.md current | SOFT | Architecture document reflects changes |
| 1.9 | Release notes authored | HARD | Release notes complete and reviewed |
| 1.10 | Change list complete | HARD | All modified files listed in change log |

---

## 10.3 Domain 2 — Dependency Ready

| # | Check | Type | Criteria |
|---|-------|------|---------|
| 2.1 | requirements.lock generated | HARD | Lock file present and committed |
| 2.2 | All dependencies hash-verified | HARD | All packages match lock file hashes |
| 2.3 | CVE scan complete | HARD | Dependency Resolver CVE scan finished |
| 2.4 | No CVE >= CRITICAL unresolved | HARD | All critical CVEs resolved or accepted |
| 2.5 | No CVE >= HIGH unresolved | HARD | All high CVEs resolved or accepted |
| 2.6 | SBOM generated | HARD | Software Bill of Materials produced and archived |
| 2.7 | No floating version specifiers | HARD | requirements.lock has no >= or ~= entries |
| 2.8 | Offline cache populated | HARD | All dependencies in offline cache |
| 2.9 | Medium CVEs tracked | SOFT | All medium CVEs have resolution plan |
| 2.10 | Dependency drift report reviewed | SOFT | Newer versions noted for next release |

---

## 10.4 Domain 3 — Artifact Ready

| # | Check | Type | Criteria |
|---|-------|------|---------|
| 3.1 | Clean build successful | HARD | Build from empty cache, zero errors |
| 3.2 | Build manifest present | HARD | All inputs and outputs hashed |
| 3.3 | Artifact hash computed | HARD | SHA256 of output image computed and stored |
| 3.4 | Artifact signed | HARD | Build Infrastructure signature applied |
| 3.5 | Signature verified | HARD | Signature verification succeeds |
| 3.6 | Artifact registered | HARD | Artifact present in Artifact Registry |
| 3.7 | Vulnerability scan clean | HARD | Container image scan shows no unresolved findings |
| 3.8 | Version number correct | HARD | Embedded version matches authorized version |
| 3.9 | Base image digest pinned | HARD | Production Dockerfile uses digest reference |
| 3.10 | Multi-platform build (if required) | SOFT | ARM64 image available if target requires |

---

## 10.5 Domain 4 — Environment Ready

| # | Check | Type | Criteria |
|---|-------|------|---------|
| 4.1 | Pre-production environment healthy | HARD | ENV-PREPROD all containers healthy |
| 4.2 | Pre-production soak >= 24 hours | HARD | New build has run 24 hours in ENV-PREPROD |
| 4.3 | No errors in 24-hour soak | HARD | Zero unhandled exceptions in soak log |
| 4.4 | Production environment baseline stable | HARD | No active alerts on ENV-PROD before deployment |
| 4.5 | Kill switch INACTIVE | HARD | Kill switch is not currently active |
| 4.6 | Market hours guard confirmed | HARD | Current time is outside trading hours |
| 4.7 | Data feed responding | HARD | yfinance (or Dhan) responding in ENV-PROD |
| 4.8 | VPS disk space >= 20% free | HARD | Sufficient space for new image layer |
| 4.9 | VPS memory >= 30% free | SOFT | Sufficient memory for new container |
| 4.10 | Docker Engine version current | SOFT | Docker Engine is within 2 major versions of current |

---

## 10.6 Domain 5 — Deployment Ready

| # | Check | Type | Criteria |
|---|-------|------|---------|
| 5.1 | Deployment script tested in staging | HARD | Same deploy command succeeded in ENV-PREPROD |
| 5.2 | Migration script tested | HARD | Any migrations tested against staging DB copy |
| 5.3 | Deployment checklist prepared | HARD | Step-by-step checklist ready for operator |
| 5.4 | Architecture Council authorization | HARD | Written authorization recorded |
| 5.5 | Deployment window confirmed | HARD | Agreed deployment time within maintenance window |
| 5.6 | Stakeholder notification sent | HARD | All stakeholders informed of planned deployment |
| 5.7 | On-call engineer identified | HARD | Engineer available for duration of deployment |
| 5.8 | Post-deployment verification plan | HARD | Health check list prepared for this deployment |
| 5.9 | Deployment duration estimate | SOFT | Estimated deployment time documented |
| 5.10 | CI/CD pipeline verified | HARD | Same pipeline executed successfully in staging |

---

## 10.7 Domain 6 — Rollback Ready

| # | Check | Type | Criteria |
|---|-------|------|---------|
| 6.1 | Rollback image available | HARD | Previous certified production image in Image Registry |
| 6.2 | Rollback image signature verified | HARD | Previous image signature valid |
| 6.3 | Rollback tested in staging | HARD | Rollback procedure executed in ENV-PREPROD |
| 6.4 | Rollback time <= 5 minutes | HARD | Staging rollback completed within 5 minutes |
| 6.5 | Database snapshot taken | HARD | Pre-deployment snapshot completed (if migrations) |
| 6.6 | Snapshot integrity verified | HARD | Snapshot hash verified |
| 6.7 | Rollback procedure documented | HARD | Step-by-step rollback in release documentation |
| 6.8 | Rollback authorization path | HARD | Authorization path defined (who can authorize rollback) |
| 6.9 | Data preservation verified in rollback | HARD | Rollback test confirmed no data loss |
| 6.10 | Rollback decision criteria documented | HARD | Explicit rollback trigger conditions listed |

---

## 10.8 Domain 7 — Recovery Ready

| # | Check | Type | Criteria |
|---|-------|------|---------|
| 7.1 | DR environment verified | HARD | ENV-DR last tested within 90 days |
| 7.2 | DR activation procedure documented | HARD | DR runbook current |
| 7.3 | Data volume backup current | HARD | Latest backup within 24 hours |
| 7.4 | Backup integrity verified | HARD | Backup hash verified |
| 7.5 | DR RTO confirmed | HARD | DR activation tested to complete within 30 minutes |
| 7.6 | Recovery runbook reviewed | SOFT | Runbook reviewed by on-call engineer |
| 7.7 | WAL mode on all databases | HARD | All SQLite databases confirmed in WAL mode |
| 7.8 | Volume persistence verified | HARD | Data volume survives container stop/start |

---

## 10.9 Domain 8 — Security Ready

| # | Check | Type | Criteria |
|---|-------|------|---------|
| 8.1 | Security scan complete | HARD | SAST scan clean (or all findings accepted) |
| 8.2 | Image scan clean | HARD | Container image scan clean |
| 8.3 | Dependency CVE scan clean | HARD | All CVE >= HIGH resolved |
| 8.4 | No secrets in version control | HARD | Secret scan confirms no credentials in repo |
| 8.5 | Signing certificate valid | HARD | Build Infrastructure certificate not expired |
| 8.6 | Dhan API token valid | HARD | Token validity checked (if Dhan feed active) |
| 8.7 | SSH key authentication | HARD | VPS password authentication disabled |
| 8.8 | Telegram bot token secured | HARD | Token in secrets manager, not in config files |
| 8.9 | Security review complete | HARD | Security Team sign-off for releases touching auth |
| 8.10 | SBOM archived | HARD | Software Bill of Materials in release evidence |

---

## 10.10 Domain 9 — Monitoring Ready

| # | Check | Type | Criteria |
|---|-------|------|---------|
| 9.1 | Monitoring system operational | HARD | All monitoring agents reporting |
| 9.2 | Alert rules configured | HARD | All alert rules defined for this release |
| 9.3 | Telegram bot operational | HARD | Test alert delivered to Telegram |
| 9.4 | Dashboard operational | HARD | Streamlit dashboard loading correctly |
| 9.5 | Heightened monitoring plan | HARD | 24-hour post-deployment monitoring plan defined |
| 9.6 | Baseline metrics recorded | HARD | Pre-deployment metrics captured for comparison |
| 9.7 | Alert thresholds verified | HARD | Thresholds set correctly for post-deployment sensitivity |
| 9.8 | Heartbeat monitoring confirmed | SOFT | All 17 layer heartbeats visible in dashboard |

---

## 10.11 Domain 10 — Operational Ready

| # | Check | Type | Criteria |
|---|-------|------|---------|
| 10.1 | Operational runbook current | HARD | Runbook covers all known failure scenarios |
| 10.2 | On-call coverage confirmed | HARD | On-call engineer available for 48 hours post-deploy |
| 10.3 | Paper trading confirmed active | HARD | PAPER_TRADING=true verified in deployment config |
| 10.4 | Kill switch functional | HARD | Kill switch activates and deactivates correctly |
| 10.5 | Container restart policy set | HARD | restart: unless-stopped on both containers |
| 10.6 | Health check configuration set | HARD | Docker health checks configured and tested |
| 10.7 | Log retention configured | SOFT | Log rotation active, retention >= 30 days |
| 10.8 | Operations team briefed | SOFT | Post-deployment operational notes communicated |

---

## 10.12 Domain 11 — Certification Ready

| # | Check | Type | Criteria |
|---|-------|------|---------|
| 11.1 | TQS >= 0.90 | HARD | Testing Quality Score meets threshold |
| 11.2 | SCS >= 0.92 | HARD | System Coverage Score meets threshold |
| 11.3 | All HARD readiness checks PASS | HARD | Zero HARD failures across all domains |
| 11.4 | Architecture Council vote | HARD | Unanimous approval recorded |
| 11.5 | Certification evidence archived | HARD | Complete evidence package in archive |
| 11.6 | Release certification issued | HARD | Certification Manager has issued certification record |
| 11.7 | Previous certification conditions resolved | HARD | All open conditions from prior certifications closed |
| 11.8 | Certification expiry tracked | SOFT | Expiry date communicated to Architecture Council |

---

## 10.13 Deployment Certification Matrix

`
DEPLOYMENT CERTIFICATION MATRIX

Level           Hard Checks  TQS    SCS    Soak      Security   Council
                             Min    Min    Period    Review     Required

DEV             No           None   None   None      No         No
TEST            No           0.50   0.50   None      No         No
QA              50% domain   0.65   0.60   None      No         Ack
STAGING         Yes (env+dep)0.80   0.75   None      Layer3     Approve
PRE-PRODUCTION  Yes (all)    0.85   0.82   24 hours  Full       Approve
PRODUCTION      Yes (all)    0.90   0.92   24 hours  Full       Unanimous
`

---

*End of Part X*

---

# SUPPLEMENT A — BUILD CATALOG

## A.1 Complete Build Type Reference

| # | Build Type | Environment | Governance | Artifact Tag |
|---|-----------|-------------|-----------|-------------|
| 1 | Source Build | Any | None (feature branch) | commit-{SHA} |
| 2 | Incremental Build | Local | None | local-{SHA} |
| 3 | Clean Build | Any | Required for staging+ | clean-{DATE} |
| 4 | Full Build | Nightly, Release | Notify Council | full-{DATE} |
| 5 | Development Build | Local | None | dev-{SHA} |
| 6 | Debug Build | Local | None | debug-{SHA} |
| 7 | Testing Build | INT, TEST | PR gate | test-{SHA} |
| 8 | QA Build | QA | QA team | qa-{BUILD} |
| 9 | Staging Build | PREPROD | Council | rc-{VER} |
| 10 | Production Build | PROD | Council (unanimous) | v{VER} |
| 11 | Nightly Build | TEST, QA | Notify Council on fail | nightly-{DATE} |
| 12 | Release Candidate | PREPROD | Council | v{VER}-rc{N} |
| 13 | Hotfix Build | PROD | Emergency process | v{VER}-hotfix |
| 14 | Patch Release | PROD | Standard | v{MAJ}.{MIN}.{PAT} |
| 15 | Major Release | PROD | Council (extended) | v{MAJ}.0.0 |
| 16 | Minor Release | PROD | Standard | v{MAJ}.{MIN}.0 |
| 17 | LTS Release | PROD | Council designated | v{VER}-lts |
| 18 | Emergency Release | PROD | Emergency | v{VER}-emg |
| 19 | Rollback Build | PROD | On-call authorized | v{PREV} |
| 20 | Recovery Build | PROD | Emergency | v{VER}-rec |
| 21 | Container Build | All | Per type | image-{SHA} |
| 22 | Artifact Build | Release | Standard | wheel-{VER} |
| 23 | Offline Build | PROD | Required for PROD | offline-{SHA} |
| 24 | Cloud Build | All | CI config review | ci-{SHA} |
| 25 | Multi-Platform Build | RC, PROD | Council for new targets | multi-{VER} |

---

# SUPPLEMENT B — ENVIRONMENT CATALOG

## B.1 Complete Environment Reference

| Code | Name | Owner | Isolation | PAPER | Live Data | Council Access |
|------|------|-------|----------|-------|----------|---------------|
| ENV-LOCAL | Local Development | Engineer | Full | Yes | yfinance (dev) | No |
| ENV-SANDBOX | Developer Sandbox | Platform | Partial | Yes | yfinance (live) | No |
| ENV-INT | Integration | Platform | Full | Yes | Fixture | No |
| ENV-TEST | Testing | Testing | Full | Yes | Historical | No |
| ENV-QA | Quality Assurance | QA | Full | Yes | Mixed | No |
| ENV-UAT | User Acceptance | Council | Full | Yes | yfinance (live) | Review |
| ENV-SIM | Simulation | Research | Full | Yes | Synthetic | No |
| ENV-REPLAY | Replay | Learning | Full | Yes | Historical | No |
| ENV-PAPER | Paper Trading | Council | Full | Yes | yfinance (live) | Full |
| ENV-PREPROD | Pre-Production | Council | Full | Yes | yfinance (live) | Full |
| ENV-PROD | Production | Council | Full | Config | yfinance/Dhan | Full |
| ENV-DR | Disaster Recovery | Platform | Full | Yes | Snapshot | Council |
| ENV-ARCHIVE | Archive | Platform | Full | N/A | None | Council |
| ENV-TRAIN | Training | MetaLearning | Full | N/A | Historical | No |
| ENV-RESEARCH | Research | Research | Partial | N/A | None | No |

---

# SUPPLEMENT C — RELEASE CATALOG

## C.1 Release Type Reference

| Type | Trigger | Governance Level | Avg Duration | Market Freeze |
|------|---------|-----------------|-------------|--------------|
| Major Release | Council decision | Full extended | 14-day staging | 5 days post |
| Minor Release | Feature freeze | Standard | 7-day staging | None |
| Patch Release | P2 defect threshold | Standard | 3-day staging | None |
| Hotfix | P0/P1 defect | Emergency | 1-day staging | None |
| Emergency | Active incident | Minimal | Hours | None |
| LTS Patch | LTS scheduled | Standard | 3-day staging | None |
| Rollback | Failure trigger | On-call | < 5 min | None |
| Recovery Build | P0 incident | Emergency | Hours | None |

---

## C.2 Release Schedule Template

| Stage | Day | Activity |
|-------|-----|---------|
| Feature freeze | T-14 | No new features accepted |
| QA entry | T-12 | QA build deployed to ENV-QA |
| QA exit | T-9 | QA sign-off received |
| RC build | T-8 | Release candidate built |
| Staging entry | T-7 | RC deployed to ENV-PREPROD |
| Security review | T-5 | Security Team review completed |
| Council review | T-3 | Architecture Council review scheduled |
| Council approval | T-2 | Unanimous written approval |
| Deployment window | T-0 | Production deployment executed |
| Heightened monitoring | T+1 | 24-hour post-deployment monitoring |
| Release complete | T+2 | Release declared complete |

---

# SUPPLEMENT D — DEPLOYMENT PATTERNS

## D.1 Pattern 1 — Standard Production Deployment

**Use case:** Planned minor or patch release to production.

**Steps:**
1. Architecture Council authorization received.
2. Confirm market hours guard: time is outside 09:00–15:30 IST.
3. Confirm kill switch is INACTIVE.
4. Confirm rollback image available and signature verified.
5. Take data volume snapshot.
6. Pull new image from Image Registry (by digest).
7. Execute: docker compose down
8. Apply pending database migrations.
9. Execute: docker compose up -d
10. Wait for health checks: both containers show (healthy).
11. Execute post-deployment health suite.
12. Confirm Telegram /status responds correctly.
13. Declare deployment complete.
14. Activate heightened monitoring.

**Time estimate:** 8–15 minutes.

---

## D.2 Pattern 2 — Emergency Hotfix Deployment

**Use case:** P0 defect in production requiring immediate fix.

**Steps:**
1. Architecture Council chair authorization.
2. Market hours check: if during market hours, kill switch activation required
   before deployment.
3. Hotfix branch created; fix committed.
4. Fast-path build executed (testing build with safety test subset).
5. Safety tests must pass. No exception.
6. Staging deployment to ENV-PREPROD with abbreviated 1-hour soak.
7. Production deployment per standard pattern (steps 4–14 above).
8. Post-emergency governance steps executed within 24 hours.

---

## D.3 Pattern 3 — Major Release Deployment

**Use case:** Planned major release with architectural changes.

**Steps:**
1. Extended staging soak (14 days minimum in ENV-PREPROD).
2. Full migration testing against production schema copy.
3. Architecture Council unanimous vote with evidence package.
4. Market hours guard confirmed.
5. Full DR drill executed within 7 days of deployment.
6. All standard pattern steps (1–14) executed.
7. 72-hour heightened monitoring period.
8. Post-deployment architectural review within 5 days.

---

## D.4 Pattern 4 — Schema Migration Deployment

**Use case:** Any release that includes database schema changes.

**Additional steps (inserted after step 5 of standard pattern):**
5a. Pre-migration database copy created.
5b. Migration tested against the pre-migration copy in ENV-TEST.
5c. Migration verified to produce expected schema.
5d. Migration rollback procedure: pre-migration snapshot restore confirmed.

**Additional post-deployment steps:**
After step 11: Schema validator confirms all tables have expected structure.
After step 11: Record counts verified (no data loss from migration).

---

# SUPPLEMENT E — ROLLBACK PATTERNS

## E.1 Pattern 1 — Automated Health Check Rollback

**Trigger:** Post-deployment health verification fails automatically.

**Sequence:**
1. Health Verification Manager reports FAIL.
2. Deployment Manager initiates automatic rollback.
3. Running containers stopped immediately.
4. Previous certified image pulled (from local cache — no registry pull needed).
5. Previous image signature verified.
6. docker compose up -d with previous image.
7. Health suite executed on previous version.
8. Architecture Council and on-call notified.
9. Root cause investigation initiated.

**SLA:** Complete within 5 minutes.

---

## E.2 Pattern 2 — Manual Architecture Council Rollback

**Trigger:** Architecture Council decision post-deployment (e.g., behavioral
issue detected but health checks passing).

**Sequence:**
1. Architecture Council authorization for rollback.
2. Market hours consideration: if during market hours, assess whether to wait
   for market close or proceed immediately.
3. Kill switch activation (if trading behavior is the concern).
4. Standard rollback sequence (same as E.1 steps 3–8).

---

## E.3 Pattern 3 — Schema Rollback

**Trigger:** Database migration produced incorrect schema or data corruption.

**Sequence:**
1. Rollback trigger received.
2. Both containers stopped immediately.
3. Current database renamed (archived with timestamp).
4. Pre-migration snapshot restored to data volume.
5. Previous container image started.
6. Database integrity check executed.
7. Health suite executed.

**Note:** Schema rollback is the only pattern where a previous data snapshot
is restored. All other rollbacks preserve the current data.

---

## E.4 Rollback Decision Matrix

| Failure Type | Auto Rollback | Manual Required | SLA |
|-------------|--------------|----------------|-----|
| Container fails to start | Yes | No | < 2 min |
| Health check fails | Yes | No | < 5 min |
| Cycle latency > 300ms | Yes | No | < 5 min |
| Error rate > 5% | Yes | No | < 5 min |
| Kill switch spurious | Yes | No | < 5 min |
| Data integrity fail | No | Yes | < 10 min |
| Behavioral issue | No | Yes (Council) | Market close |
| Schema corruption | No | Yes | < 15 min |

---

# SUPPLEMENT F — VERSION COMPATIBILITY MATRIX

## F.1 Data Format Compatibility

| Current Version | Can read v1.0.x data | Can read v0.x data | Migration Required |
|----------------|---------------------|-------------------|-------------------|
| v1.0.0 | Yes (baseline) | No | No |
| v1.1.0 | Yes | No | No |
| v1.2.0 | Yes | No | No |
| v2.0.0 | Yes (via migration) | No | Yes |

## F.2 Configuration Compatibility

| Config Parameter | Introduced | Breaking Change in | Forward Compatible |
|-----------------|-----------|-------------------|--------------------|
| PAPER_TRADING | v0.1.0 | Never | Yes |
| CONTINUOUS_SCAN_INTERVAL | v1.1.0 | N/A | Yes |
| SCHEDULE | v1.0.0 | v2.0.0 (format change) | Yes (v1-v1.x) |
| LAYER_LATENCY_WARN_MS | v1.0.0 | Never | Yes |
| LAYER_LATENCY_CRIT_MS | v1.0.0 | Never | Yes |

## F.3 Interface Compatibility by Version

**Critical interfaces (must remain stable across all MINOR versions):**

| Interface | Class | Signature | Stable Since |
|-----------|-------|----------|-------------|
| fetch | GlobalDataAI | fetch(force: bool) -> GlobalSnapshot | v1.0.0 |
| time_layer | SystemMonitor | time_layer(layer_name: str) -> contextmanager | v1.0.0 |
| run_full_cycle | MasterOrchestrator | run_full_cycle() -> None | v1.0.0 |
| start_scheduler | MasterOrchestrator | start_scheduler() -> None | v1.0.0 |
| get_quote | BaseFeed | get_quote(symbol: str) -> Optional[TickerQuote] | v1.0.0 |
| get_multiple_quotes | BaseFeed | get_multiple_quotes(symbols: List) -> Dict | v1.0.0 |
| get_history | BaseFeed | get_history(symbol, days, interval) -> List | v1.0.0 |

**Singleton interfaces (must never be instantiated twice):**

| Singleton | Getter | Stable Since |
|-----------|--------|-------------|
| PerformanceTracker | get_performance_tracker() | v1.1.0 |
| RegimeStrategyMap | get_regime_strategy_map() | v1.1.0 |
| TelegramBot | get_telegram_bot() | v1.0.0 |
| FeedManager | get_feed_manager() | v1.0.0 |

---

# SUPPLEMENT G — ENGINEERING DECISION RECORDS

## G.1 Build and Deployment Decision Records

### EDR-BLD-001 — Docker as the Primary Deployment Unit

**Decision:** All IIOS components are deployed as Docker containers using
docker-compose on a single VPS host.

**Rationale:** Docker provides infrastructure independence, reproducible
environments, and clean separation between application code and host OS. A
single VPS with docker-compose is the simplest topology that meets IIOS
operational requirements at current scale.

**Alternatives considered:**
- Bare-metal Python deployment: rejected (no isolation, environment drift).
- Kubernetes: rejected (over-engineered for single-node, adds operational
  complexity without benefit at current scale).
- Serverless: rejected (trading engine requires continuous state and cannot
  operate as stateless functions).

**Date:** Inception
**Status:** Active

---

### EDR-BLD-002 — Data Volume Separation from Container Image

**Decision:** All persistent IIOS state is stored in a Docker volume mounted
at /app/data. The container image contains no persistent state.

**Rationale:** This separation means that replacing the container image never
touches application data. Rollback of code does not roll back data.
Data integrity is independent of code lifecycle.

**Date:** Inception
**Status:** Active

---

### EDR-BLD-003 — Pinned Dependency Lock File

**Decision:** All Python dependencies are pinned to exact versions and hashes
in requirements.lock. No floating version specifiers in production.

**Rationale:** Floating versions produce non-reproducible builds. A build
executed today may produce a different artifact than the same build executed
next week due to a new transient dependency version.

**Date:** Inception
**Status:** Active

---

### EDR-BLD-004 — Market Hours Guard as Tooling-Level Enforcement

**Decision:** Production deployments outside market hours are enforced by the
deployment tooling, not solely by operator discipline.

**Rationale:** Operator discipline fails under pressure. An active incident
creates pressure to deploy immediately. Tooling-level enforcement ensures the
guard is respected even under pressure.

**Exception:** Emergency deployments may override with Architecture Council
chair written authorization.

**Date:** Inception
**Status:** Active

---

### EDR-BLD-005 — Rollback-First Design

**Decision:** Every production deployment must have a verified, tested rollback
before authorization is granted.

**Rationale:** A deployment whose rollback has not been tested is a deployment
that may not be reversible. In a financial system, an irreversible deployment
failure is a financial risk event.

**Date:** Inception
**Status:** Active

---

### EDR-BLD-006 — WAL Mode on All SQLite Databases

**Decision:** All IIOS SQLite databases operate in Write-Ahead Logging mode.

**Rationale:** WAL mode ensures that an abrupt process termination (container
crash, OOM kill) cannot corrupt the database. Without WAL mode, a container
crash during a write transaction can produce a corrupted database file.

**Date:** Inception
**Status:** Active

---

### EDR-BLD-007 — No Reverse Migrations

**Decision:** IIOS does not implement reverse database migrations. Schema
rollback is achieved by restoring the pre-migration snapshot.

**Rationale:** Reverse migrations are complex to implement correctly and create
a false sense of safety. The correct rollback approach — restoring a known-good
snapshot — is simpler, more reliable, and completely tested by the snapshot
integrity check.

**Date:** Inception
**Status:** Active

---

### EDR-BLD-008 — Artifact Digest Reference for Production

**Decision:** Production deployments reference container images by SHA256
digest, not by mutable tag.

**Rationale:** A mutable tag (such as latest or 1.2.0) can be reassigned
to a different image. A digest reference is permanent — the same digest always
refers to the same image content.

**Date:** Inception
**Status:** Active

---

### EDR-BLD-009 — Single VPS Production Host

**Decision:** The current production environment is a single VPS host at
178.18.252.24 running two Docker containers.

**Rationale:** At current trading scale, a single VPS provides adequate
capacity with simpler operational management than multi-node architectures.
The Disaster Recovery environment provides resilience.

**Review trigger:** This decision is reviewed when trading volume or complexity
requires horizontal scaling.

**Date:** Inception
**Status:** Active (review at scale inflection)

---

### EDR-BLD-010 — Architecture Council Unanimous Vote for Production

**Decision:** Production deployments require unanimous Architecture Council
approval, not a simple majority.

**Rationale:** A financial system deployed without full consensus introduces
risk that at least one council member has identified but was outvoted. Unanimous
consent ensures that all identified risks have been resolved before deployment.

**Date:** Inception
**Status:** Active

---

# SUPPLEMENT H — OPERATIONAL RUNBOOK

## H.1 Runbook Scope

This runbook covers the 5 most common operational scenarios for the IIOS
build and deployment system.

---

## H.2 Scenario 1 — Standard Production Deployment

**Frequency:** Every planned release (quarterly major, as-needed minor/patch).

**Pre-deployment (day before):**
- Verify all readiness checks PASS.
- Confirm Architecture Council authorization.
- Confirm maintenance window with all stakeholders.
- Verify rollback image available in Image Registry.

**Deployment day:**
1. Confirm market hours guard (time outside 09:00–15:30 IST).
2. Confirm kill switch INACTIVE.
3. Take data volume snapshot: docker run --rm -v /path/to/data:/source -v /backup:/dest alpine tar czf /dest/pre-deploy-{DATE}.tar.gz /source
4. Verify snapshot: sha256sum /backup/pre-deploy-{DATE}.tar.gz > /backup/pre-deploy-{DATE}.sha256
5. SSH to VPS: ssh -i ~/.ssh/trading_vps root@178.18.252.24
6. Pull and deploy: cd /root/ai-trading-brain && git pull origin main && docker compose build --no-cache && docker compose down && docker compose up -d
7. Wait 60 seconds for startup.
8. Check health: docker compose ps
9. Expected output: both containers show (healthy).
10. Send Telegram test: verify /status command responds.
11. Observe one full cycle: check logs for HEALTHY status on all 17 layers.
12. Declare deployment complete.

**Post-deployment:**
- Set heightened monitoring for 24 hours.
- Record deployment completion in governance audit trail.
- File post-deployment report within 4 hours.

---

## H.3 Scenario 2 — Emergency Rollback

**Trigger:** Health check failure; error rate spike; Architecture Council decision.

**Steps (must complete within 5 minutes):**
1. Stop running containers: docker compose down
2. Identify previous image: check Image Registry for last certified production image.
3. Update docker-compose.yml image reference to previous version digest.
4. Start previous version: docker compose up -d
5. Check health: docker compose ps — expect both (healthy).
6. Verify Telegram /status responds.
7. Notify Architecture Council of rollback completion.
8. Record rollback in governance audit trail.

**If rollback fails within 5 minutes:** Escalate to Architecture Council for
DR activation.

---

## H.4 Scenario 3 — Kill Switch Activation

**Trigger:** Automatic (VIX > 45 or daily loss > 2%) or Architecture Council
manual decision.

**Automatic trigger behavior:**
- System logs: KILL_SWITCH ACTIVATED: reason={reason}
- Telegram alert sent to all architecture council members.
- No new orders executed.
- All pending cycle processing halted.
- Kill switch state persisted to data/kill_switch.json.

**Operator response:**
1. Acknowledge alert.
2. Assess market conditions.
3. If automatic trigger is valid: leave kill switch active until conditions resolve.
4. If manual deactivation required: Architecture Council authorization needed.
5. Deactivation: update kill_switch.json ctive: false; restart containers.

---

## H.5 Scenario 4 — Data Feed Failover

**Trigger:** Dhan API returns 451 (data access blocked) or connection timeout.

**Automatic behavior:**
- System detects feed failure after 3 consecutive failed requests.
- yfinance fallback activated automatically within 90 seconds.
- Log entry: FEED_FAILOVER: primary=Dhan status=FAILED fallback=yfinance status=ACTIVE
- Telegram alert sent.

**Operator response:**
1. Acknowledge alert.
2. Investigate Dhan API status (token expiry, API issue, 451 block).
3. If token expired: rotate token per DHAN_DAILY_TOKEN_REQUIREMENT.md.
4. If token valid: monitor yfinance fallback; no immediate action required.
5. When Dhan feed restored: ENABLE_DHAN_FEED flag can be re-enabled.

---

## H.6 Scenario 5 — Disaster Recovery Activation

**Trigger:** Architecture Council declares DR event.

**Steps:**
1. Architecture Council vote: majority required.
2. DR declaration recorded in governance audit trail.
3. Platform Team activates ENV-DR.
4. Latest data volume snapshot identified: ls -la /backup/ | sort -k6,7 | tail -5
5. Snapshot restored to DR environment data volume.
6. DR containers started: docker compose up -d on DR host.
7. DR health checks executed: docker compose ps shows both (healthy).
8. Architecture Council confirms DR environment HEALTHY.
9. Operations shifted to DR host (Telegram bot, monitoring re-pointed).
10. Recovery Time: target 30 minutes from DR declaration.
11. Post-DR: root cause investigation on failed primary; recovery plan.

---

# SUPPLEMENT I — DEPLOYMENT ANTI-PATTERNS

## I.1 Eight Deployment Anti-Patterns

### Anti-Pattern 1 — Deploying During Market Hours

**Description:** Deploying a new version of the trading system during active
market hours (09:00–15:30 IST).

**Risk:** Deployment causes partial or complete trading system outage during
live market operation. Any active positions may not be managed correctly during
the deployment window.

**Correct approach:** All production deployments are executed outside market
hours. The market hours guard is enforced at the tooling level.

---

### Anti-Pattern 2 — Deploying Without Verified Rollback

**Description:** Proceeding with a production deployment without verifying that
the rollback artifact is available and that the rollback procedure has been
tested.

**Risk:** When the deployment fails (and deployments do fail), rollback cannot
be executed promptly. The system remains in a failed state for an extended period.

**Correct approach:** Rollback verification is a HARD readiness check. No
production deployment is authorized without a verified, staged-tested rollback.

---

### Anti-Pattern 3 — Manual Configuration Changes on Production Server

**Description:** Making configuration changes directly on the production VPS
via SSH without reflecting those changes in version control.

**Risk:** Configuration drift. The running system diverges from version control.
The next deployment overwrites the manual change, restoring the previous behavior.
Manual changes are not auditable.

**Correct approach:** All configuration changes are made in version control and
applied through the Configuration Manager. Direct SSH configuration changes are
a governance violation.

---

### Anti-Pattern 4 — Using Mutable Image Tags in Production

**Description:** Referencing the production container image by a mutable tag
(e.g., :latest or :production) rather than by SHA256 digest.

**Risk:** The tag is reassigned to a different image, and the next container
restart deploys a different version without an explicit deployment decision.

**Correct approach:** Production deployments reference images by SHA256 digest.
Mutable tags are convenience references only.

---

### Anti-Pattern 5 — Skipping the Health Check Soak Period

**Description:** Declaring a deployment complete immediately after the containers
start, without allowing the health check soak period to verify sustained correct
behavior.

**Risk:** The system may appear healthy immediately after startup but develop
problems over the first 30 minutes as caches warm, schedulers fire, and the
full trading cycle executes. Skipping the soak period misses these early failures.

**Correct approach:** Post-deployment monitoring is heightened for 24 hours.
A deployment is not declared complete until the system has operated correctly
through at least one complete monitoring interval.

---

### Anti-Pattern 6 — Floating Dependency Versions in Production Lock File

**Description:** Using version specifiers such as >=1.2.0 or ~=1.2 in the
production dependency lock file rather than exact pinned versions.

**Risk:** The production build picks up a new dependency version that was not
tested. The new version may have behavioral differences, bugs, or security
vulnerabilities.

**Correct approach:** requirements.lock pins every dependency to an exact
version and hash. No floating specifiers are permitted.

---

### Anti-Pattern 7 — Deploying Without Kill Switch Verification

**Description:** Initiating a production deployment without verifying that the
kill switch is in the INACTIVE state.

**Risk:** If the kill switch is active due to an ongoing incident, the new
deployment will start with the kill switch active. Depending on implementation,
the new version may incorrectly reset the kill switch to inactive, releasing
trading activity before the underlying condition is resolved.

**Correct approach:** Kill switch state is a HARD readiness check. Deployment
is blocked if the kill switch is active.

---

### Anti-Pattern 8 — Silent Schema Migration

**Description:** Applying a database schema migration without first testing
it against a copy of the production schema in a staging environment.

**Risk:** The migration script works on the development schema but fails on the
production schema due to differences in data content, row counts, or constraint
states. A failed migration in production may corrupt data.

**Correct approach:** Every migration is tested against a copy of the production
schema in ENV-TEST before being applied to production. This is a HARD readiness
check for any release that includes schema changes.

---

# SUPPLEMENT J — COMPREHENSIVE GLOSSARY

| Term | Definition |
|------|-----------|
| Artifact | A build output (Docker image, Python wheel) that is stored, signed, and deployed. |
| Artifact Registry | The secure, versioned repository of all IIOS build artifacts. |
| Blue-Green | Deployment pattern maintaining two identical environments; traffic switches between them. |
| Build | The process of transforming source code into a deployable artifact. |
| Build Manifest | A record of all build inputs and their hashes, plus the output hash. |
| Build Registry | The authoritative record of every build ever executed. |
| Canary Deployment | Gradually shifting traffic to a new version; monitoring before full commit. |
| Certification | Formal declaration that an artifact meets standards for a lifecycle level. |
| Clean Build | A build from an empty cache directory, with no reuse of prior outputs. |
| Configuration Drift | Divergence between version-controlled configuration and the running environment. |
| Container | A Docker container running one IIOS component or the full platform. |
| CVE | Common Vulnerabilities and Exposures — a security vulnerability identifier. |
| Data Volume | A Docker volume containing all IIOS persistent state (data/ directory). |
| Deployment Manager | Framework component orchestrating the complete deployment sequence. |
| Deployment Window | The period outside market hours during which production deployment is authorized. |
| Deterministic Build | A build whose output is the same for the same inputs, regardless of environment. |
| Digest Reference | A Docker image reference by SHA256 hash, which is immutable. |
| Disaster Recovery | The process of activating the DR environment in response to catastrophic failure. |
| Docker | The containerization platform used for IIOS deployment. |
| docker-compose | The tool orchestrating multi-container IIOS deployments. |
| Environment | A fully provisioned, configured, and isolated instance of the IIOS platform. |
| Environment Manager | Framework component creating and maintaining all 16 IIOS environments. |
| Feature Flag | A configuration switch enabling or disabling a feature without redeployment. |
| Feature Freeze | The point after which no new features are accepted into a release branch. |
| Governance Audit Trail | An append-only record of all governed build and deployment events. |
| Health Check | A Docker probe verifying that a container is operating correctly. |
| Heartbeat | A timestamp written by each layer indicating it is alive and processing. |
| Hotfix | An emergency defect fix applied outside the normal release cycle. |
| Image Registry | The Docker image storage and distribution system. |
| Immutability | The property that a stored artifact is never modified after registration. |
| Incremental Build | A build that reuses cached outputs for unchanged modules. |
| Kill Switch | The safety mechanism that halts all trading when risk thresholds are breached. |
| Layer | One of the 17 hierarchical subsystems of IIOS. |
| Lifecycle Level | A certification tier: DEV, TEST, QA, STAGING, PRE-PRODUCTION, PRODUCTION. |
| Liveness Check | A check verifying that the system is running and not in a deadlock. |
| Lock File | requirements.lock — the pinned, hash-verified dependency specification. |
| LTS | Long-Term Support — a release designated for extended maintenance. |
| Migration | A database schema change applied in an ordered, idempotent manner. |
| Monitoring Manager | Framework component maintaining continuous visibility into system health. |
| Mutable Tag | A Docker image tag that can be reassigned (e.g., :latest). |
| Offline Build | A build with no external network access, using vendored dependencies. |
| On-Call | The engineer responsible for responding to production incidents. |
| P0 Incident | A critical incident affecting financial operations. Requires immediate response. |
| P1 Incident | A severe incident with significant impact. Requires same-day response. |
| Paper Trading | Trading simulation mode where orders are journaled but not executed live. |
| Pre-Migration Snapshot | A backup of the database taken before a schema migration is applied. |
| Production | The live financial operations environment. |
| Readiness Check | A check verifying that the system is ready to process trading cycles. |
| Release | A versioned, certified, deployed instance of IIOS. |
| Release Candidate | A build that is a candidate for production release. |
| Release Gate | A quality threshold that must be met before a release proceeds. |
| Release Manager | Framework component orchestrating the complete release lifecycle. |
| Reproducible Build | A build that produces the same artifact given the same inputs. |
| Rollback | Restoring the previous production state after a deployment failure. |
| Rollback Manager | Framework component ensuring every deployment can be reversed within 5 minutes. |
| Rolling Deployment | Upgrading instances one at a time; some old instances always running. |
| RTO | Recovery Time Objective — the maximum acceptable time to restore a system. |
| SBOM | Software Bill of Materials — a complete list of all components in an artifact. |
| Semantic Versioning | Version numbering scheme: MAJOR.MINOR.PATCH. |
| Shadow Deployment | Running a new version in parallel, comparing outputs without affecting production. |
| Signing | Applying a cryptographic signature to an artifact to verify its authenticity. |
| Singleton | An object that must never be instantiated more than once in a running system. |
| Soak Period | A duration during which a new deployment is monitored before being declared stable. |
| Staging | The production-equivalent environment used for final validation (ENV-PREPROD). |
| Technical Debt | Design shortcuts that increase future maintenance cost. |
| Version Manager | Framework component maintaining the authoritative version numbering system. |
| VPS | Virtual Private Server — the current production hosting environment. |
| WAL Mode | Write-Ahead Logging — SQLite mode preventing database corruption on crash. |

---

# DOCUMENT METRICS

| Attribute | Value |
|-----------|-------|
| Document Code | IIOS-BLD-DEP-001 |
| Framework Version | 1.0.0 |
| Document Status | Active |
| Total Parts | 10 |
| Total Supplements | 10 (A through J) |
| Build Types Defined | 25 |
| Architecture Components | 18 |
| Environments Defined | 16 |
| Deployment Lifecycle Stages | 12 |
| Constitution Rules | 110 |
| Constitution Categories | 13 |
| Readiness Domains | 11 |
| Readiness Checks (HARD) | 79 |
| Readiness Checks (SOFT) | 17 |
| Readiness Checks (Total) | 96 |
| Deployment Patterns | 4 |
| Rollback Patterns | 4 |
| Operational Runbook Scenarios | 5 |
| Anti-Patterns | 8 |
| Engineering Decision Records | 10 |
| Glossary Entries | 55 |

---

# AMENDMENT HISTORY

| Version | Date | Author | Change Description |
|---------|------|--------|-------------------|
| 1.0.0 | 2026-07-05 | Architecture Council | Initial publication |

---

# CLOSING STATEMENT

This document — the Build, Release, Deployment, Environment, and Delivery
Engineering Framework for the Investment Intelligence Operating System (IIOS),
bearing document code IIOS-BLD-DEP-001 — is the complete, authoritative
engineering specification for how the platform transitions from source code to
a running production system that manages real capital.

The framework rests on five foundational commitments:

**Reproducibility:** The same source always produces the same artifact. There
are no surprises in the build.

**Safety:** No deployment makes the system worse than it was. Rollback is always
available, always tested, always fast.

**Zero data loss:** Financial records survive every deployment, every rollback,
every recovery. The data volume is never the container.

**Full auditability:** Every decision about what runs in production is recorded,
authorized, and traceable.

**Operability:** The system can be deployed, rolled back, monitored, and recovered
by a single on-call engineer following documented procedures, at any time, under
any conditions.

These commitments are not aspirational — they are enforced by 110 constitutional
rules, 18 framework components, 16 managed environments, 12 lifecycle stages,
96 readiness checks, and the Architecture Council's unanimous authorization
requirement for every production deployment.

This is how IIOS earns the right to be trusted with real capital.

---

*IIOS-BLD-DEP-001 / Version 1.0.0 / Status: Active*
*Build, Release, Deployment, Environment, and Delivery Engineering Framework*
*Investment Intelligence Operating System*
*Architecture Council Approved*

---

# EXTENDED SUPPLEMENT — IIOS LAYER-SPECIFIC DEPLOYMENT SPECIFICATIONS

## EX.1 Purpose

This supplement provides deployment-specific specifications for each of the 17
IIOS layers. For every layer, it defines: the deployment order, initialization
requirements, startup verification, configuration parameters, health indicators,
and failure handling during deployment.

---

## EX.2 Layer Deployment Order

`
SHUTDOWN ORDER (before new deployment)
  Layer 17 -> 16 -> 15 -> 14 -> 13 -> 12 -> 11 -> 10 ->
  9 -> 8 -> 7 -> 6 -> 5 -> 4 -> 3 -> 2 -> 1

STARTUP ORDER (after new deployment)
  Layer 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7 -> 8 ->
  9 -> 10 -> 11 -> 12 -> 13 -> 14 -> 15 -> 16 -> 17
`

Layers are initialized in ascending order because each layer depends on the
layers below it. ControlTower (Layer 17) is the last to start because it
monitors all other layers.

---

## EX.3 Layer 1 — GlobalIntelligence Deployment Spec

**Module:** global_intelligence/global_data_ai.py
**Startup time:** <= 60 seconds (including cache pre-warm thread start)
**Health indicator:** GlobalDataAI.fetch(force=False) returns a non-None GlobalSnapshot
**Latency baseline:** 17ms p99 (cache hit path)
**Critical threshold:** 12,000ms (CRIT OVERRIDE from system_monitor)

**Deployment check:** After startup, one fetch() call must complete within
12,000ms with no exception.

**Configuration verified at deployment:**
- LAYER_LATENCY_WARN_OVERRIDES: GlobalIntelligence -> 5,000ms
- LAYER_LATENCY_CRIT_OVERRIDES: GlobalIntelligence -> 12,000ms
- Cache TTL: 300 seconds (5 minutes)

**Failure at deployment:** If GlobalIntelligence fails to initialize within
60 seconds, the container is not READY. Health check fails. Rollback is initiated.

---

## EX.4 Layer 2 — MarketIntelligence Deployment Spec

**Module:** market_intelligence/market_monitor.py
**Startup time:** <= 45 seconds
**Health indicator:** Market monitor reports regime classification without error
**Latency baseline:** 19ms p99

**Deployment check:** One market intelligence cycle must complete within 19,000ms.

**Continuous scan verification:** 30-second interval confirmed active in logs.

---

## EX.5 Layer 3 — MetaLearning Deployment Spec

**Module:** meta_learning/regime_strategy_map.py
**Startup time:** <= 30 seconds
**Health indicator:** get_regime_strategy_map() returns valid map; k-NN model loaded
**State restoration:** Regime strategy weights are loaded from data/ on startup

**Deployment check:** Strategy map initialization completes; at least one regime
has a strategy weight assigned.

---

## EX.6 Layer 4 — OpportunityEngine Deployment Spec

**Module:** opportunity_engine/
**Startup time:** <= 30 seconds
**Health indicator:** Scanner initializes without error; symbol list loaded
**Configuration check:** NIFTY and BANKNIFTY symbols confirmed bare (no .NS suffix)

---

## EX.7 Layer 5 — StrategyLab Deployment Spec

**Module:** strategy_lab/strategy_generator_ai.py
**Startup time:** <= 45 seconds (evolved strategies loaded from JSON)
**Health indicator:** At least one strategy in active pool after initialization
**Critical deployment check:** min_signal_rr filtering verified active

**Evolved strategy verification:** After startup, the strategy pool must contain
at least one strategy with status=ACTIVE. An empty strategy pool is a FAIL.

**Security note:** Evolved strategy JSON files are integrity-checked against
their last-known hashes after deployment. A modified evolved strategy file
triggers a security alert.

---

## EX.8 Layer 6 — CapitalRiskEngine Deployment Spec

**Module:** capital_risk_engine/
**Startup time:** <= 20 seconds
**Health indicator:** Position sizing computes a non-zero allocation for a
test position input
**Safety check:** Maximum position limit enforced at configured value

---

## EX.9 Layer 7 — RiskControl Deployment Spec

**Module:** risk_control/risk_manager_ai.py
**Startup time:** <= 20 seconds
**Health indicator:** Risk check completes for a test portfolio without error
**Safety check:** Stress test threshold confirmed at configured value

---

## EX.10 Layer 8 — MarketSimulation Deployment Spec

**Module:** market_simulation/
**Startup time:** <= 30 seconds
**Health indicator:** Monte Carlo engine accepts inputs and returns simulation results
**Scenario count verification:** All 14 scenario definitions confirmed present

---

## EX.11 Layer 9 — RiskGuardian Deployment Spec

**Module:** risk_guardian/risk_guardian.py
**Startup time:** <= 15 seconds
**Health indicator:** RiskGuardian initializes; kill switch state loaded correctly

**CRITICAL deployment check:**
This is the most safety-critical component. The following must be verified at
every deployment:

1. Kill switch state loaded from data/kill_switch.json correctly.
2. VIX threshold confirmed at 45.0.
3. Daily loss threshold confirmed at 2.0%.
4. Kill switch triggers when VIX=45.1 in the post-deployment test.
5. Kill switch does not trigger when VIX=44.9 in the post-deployment test.
6. Kill switch state persistence: write to data/kill_switch.json confirmed.

If any of these checks fails, the deployment is immediately rolled back.
No exception. No override.

---

## EX.12 Layer 10 — DebateAndDecision Deployment Spec

**Module:** debate_and_decision/decision_engine.py
**Startup time:** <= 30 seconds
**Health indicator:** All 5 debate agents initialize; decision threshold confirmed at 6.5
**Decision threshold verification:** Threshold 6.5 confirmed in initialization log

---

## EX.13 Layer 11 — ExecutionEngine Deployment Spec

**Module:** execution_engine/order_manager.py
**Startup time:** <= 20 seconds
**Health indicator:** OrderManager initializes; paper_trades.csv accessible
**CRITICAL check:** PAPER_TRADING flag confirmed true in deployment

**Safety-critical deployment check:**
After startup, the first check is always: is PAPER_TRADING=true? If PAPER_TRADING
is false and live trading is not explicitly authorized, the deployment is rolled
back immediately. This check is automatic and non-bypassable.

**Position journal check:** data/paper_trades.csv is readable; record count
consistent with last known value before deployment.

---

## EX.14 Layer 12 — TradeMonitoring Deployment Spec

**Module:** trade_monitoring/trade_monitor.py
**Startup time:** <= 20 seconds
**Health indicator:** TradeMonitor initializes; StrategyHealthMonitor reports
at least one monitored strategy
**Active trade check:** Any open paper positions are correctly loaded from journal

---

## EX.15 Layer 13 — LearningSystem Deployment Spec

**Module:** learning_system/learning_engine.py
**Startup time:** <= 30 seconds
**Health indicator:** LearningEngine initializes; StrategyPerformanceTracker loaded
**State restoration:** Win rates and performance history loaded from data/ on startup

**EOD check:** After deployment, verify that the EOD learning cycle can execute
without error on a test run.

---

## EX.16 Layer 14 — PerformanceAnalytics Deployment Spec

**Module:** performance_analytics/
**Startup time:** <= 20 seconds
**Health indicator:** DrawdownAnalyzer and WalkForwardTester initialize
**Historical data check:** Performance history accessible from data/

---

## EX.17 Layer 15 — ResearchLab Deployment Spec

**Module:** research_lab/
**Startup time:** <= 20 seconds
**Health indicator:** ResearchLab initializes; promotion gates confirmed at:
WinRate >= 50%, Sharpe > 0.8, MaxDD < 15%

**Gate verification:** After deployment, promotion gate thresholds are confirmed
in initialization log. Any deviation from the configured values is a deployment
failure.

---

## EX.18 Layer 16 — ValidationEngine Deployment Spec

**Module:** validation_engine/
**Startup time:** <= 30 seconds
**Health indicator:** All 6 validation stages initialized:
Backtest -> WFT -> CrossMarket -> MC -> Sensitivity -> Regime

**Stage count verification:** After startup, confirm all 6 stages are active.
A ValidationEngine with fewer than 6 stages is a deployment failure.

---

## EX.19 Layer 17 — ControlTower Deployment Spec

**Module:** control_tower/
**Startup time:** <= 45 seconds (dashboard startup)
**Health indicator:** SQLite telemetry database accessible; EventBus operational;
Streamlit dashboard HTTP health endpoint responds

**ControlTower is the last layer to start.** Its health indicates that the
entire system is operational.

**Post-deployment verification via ControlTower:**
1. Streamlit dashboard loads at http://localhost:8501.
2. Dashboard shows all 17 layers with HEALTHY status.
3. Telegram /status command returns system state.
4. EventBus delivers a test event to all subscribers.
5. Telemetry database logs a test event with correct timestamp.

---

## EX.20 Full-System Post-Deployment Verification Matrix

| Check | Component | Pass Criteria | Failure Action |
|-------|---------|--------------|---------------|
| Container health | Docker | Both containers (healthy) | Rollback |
| Layer 9 kill switch | RiskGuardian | State loaded, thresholds correct | Rollback |
| Paper trading flag | ExecutionEngine | PAPER_TRADING=true | Rollback |
| Strategy pool | StrategyLab | >= 1 active strategy | Alert, investigate |
| Cycle execution | MasterOrchestrator | Full cycle <= 200ms | Alert, monitor |
| GlobalIntel latency | GlobalIntelligence | <= 17ms (cache hit) | Alert, monitor |
| Dashboard response | ControlTower | HTTP 200 from Streamlit | Alert, investigate |
| Telegram /status | TelegramBot | Response within 5s | Alert, investigate |
| Database access | ControlTower | All DBs respond | Rollback |
| Journal integrity | ExecutionEngine | Record count unchanged | Rollback |
| Promotion gates | ResearchLab | WinRate >= 50%, Sharpe > 0.8 | Alert, review |
| Kill switch VIX test | RiskGuardian | Triggers at 45.1, not 44.9 | Rollback |

---

## EX.21 Build Troubleshooting Guide

### Problem 1: Build fails with dependency hash mismatch

**Symptom:** Build output includes Hash mismatch for package X.

**Cause:** A dependency version was updated upstream and the new version has
a different hash than recorded in requirements.lock.

**Resolution:**
1. Identify which package has changed: pip install --dry-run -r requirements.txt
2. Investigate whether the version change is expected.
3. If expected: update requirements.lock with new hash after security review.
4. If unexpected: the upstream package may have been compromised. Treat as
   a security incident.

---

### Problem 2: Container fails to start after deployment

**Symptom:** docker compose ps shows container in Restarting or Exited state.

**Cause:** Startup error in Python application code.

**Resolution:**
1. Check container logs: docker logs ai-trading-brain
2. Identify the import error or initialization error.
3. If a missing dependency: update requirements.txt and rebuild.
4. If a code error: rollback; fix in new PR; re-deploy.

---

### Problem 3: Health check never reaches (healthy)

**Symptom:** Container starts but shows (health: starting) for > 60 seconds.

**Cause:** Application is running but health check script is failing.

**Resolution:**
1. Execute health check script manually: docker exec ai-trading-brain python /app/healthcheck.py
2. Check error output.
3. Common causes: database not accessible; last cycle timestamp too old.
4. If database: verify data volume is mounted correctly.

---

### Problem 4: Cycle latency exceeds baseline after deployment

**Symptom:** Post-deployment monitoring shows cycle latency > 200ms.

**Cause:** New code path is slower; dependency change introduced overhead;
data volume I/O slower (disk contention).

**Resolution:**
1. Compare cycle component timing in logs vs pre-deployment baseline.
2. Identify which layer has increased latency.
3. If GlobalIntelligence > 17ms on cache hit: investigate cache initialization.
4. If multiple layers slow: investigate system resource contention.
5. If unresolvable within 30 minutes: rollback.

---

### Problem 5: Post-deployment database migration fails

**Symptom:** Migration Manager reports migration failure. Containers not started.

**Cause:** Migration script incompatible with actual production schema state.

**Resolution:**
1. Do not start the new containers.
2. Restore pre-migration snapshot.
3. Verify snapshot integrity.
4. Start previous version containers.
5. Investigate migration script against production schema copy.
6. Fix migration; test against copy; re-deploy.

---

## EX.22 Production Configuration Reference

All production environment variables with their required values:

| Variable | Required Value | Description |
|---------|---------------|-----------|
| PAPER_TRADING | true | Paper trading mode (mandatory for all deployments) |
| CONTINUOUS_SCAN_INTERVAL | 30 | Market monitoring interval in seconds |
| LAYER_LATENCY_WARN_MS | 2000 | Default per-layer warning threshold |
| LAYER_LATENCY_CRIT_MS | 5000 | Default per-layer critical threshold |
| DB_WAL_MODE | true | Enables WAL mode on all SQLite databases |
| LOG_LEVEL | INFO | Production logging level |
| TELEGRAM_ENABLED | true | Enable Telegram bot notifications |
| ENABLE_LIVE_TRADING | false | Must be false unless Council explicitly authorized |
| ENABLE_DHAN_FEED | false | Dhan feed (disabled when token unavailable) |
| ENABLE_CONTINUOUS_SCAN | true | Market monitoring active |

---

## EX.23 Deployment Infrastructure Specification

**Production Host:**
- Address: 178.18.252.24
- OS: Linux (distribution per VPS provider)
- Docker Engine: current stable version
- docker-compose: v2.x
- CPU: as provisioned
- Memory: sufficient for two containers plus OS overhead
- Disk: minimum 40GB allocated; 20% free required before deployment

**Network Configuration:**
- SSH port: 22 (key-based only; password disabled)
- Streamlit dashboard: port 8501
- No other ports exposed to public network

**Data Volume Configuration:**
- Mount: ./data:/app/data
- Mode: read-write
- Backup: daily snapshot to off-site storage

**Container Configuration:**
- ai-trading-brain: restart=unless-stopped; health check active
- trading-dashboard: restart=unless-stopped; health check active

---

*End of Extended Supplement*

---
---

# EXTENDED SUPPLEMENT 2 — IIOS BUILD ENGINEERING DECISION MATRIX

## ED2.1 Purpose

This supplement provides additional Engineering Decision Records and a complete
deployment decision matrix for operational use during incidents and audits.

---

## ED2.2 Additional Engineering Decision Records

### EDR-BLD-011 — Ordered Layer Shutdown and Startup

**Decision:** Layers are shut down in reverse order (17 to 1) before deployment
and started in forward order (1 to 17) after deployment.

**Rationale:** Higher-numbered layers depend on lower-numbered layers. Shutting
down Layer 17 (ControlTower) first ensures that monitoring stops cleanly before
the monitored components shut down. Starting Layer 1 (GlobalIntelligence) first
ensures that data dependencies are available before the layers that consume
them initialize.

**Date:** Inception
**Status:** Active

---

### EDR-BLD-012 — Single Production Instance

**Decision:** IIOS runs as a single process on a single VPS host with no
horizontal replication.

**Rationale:** Trading systems require consistent state. Horizontal replication
introduces distributed state management complexity (split-brain, consensus
protocols, distributed locking) that is architecturally disproportionate to
current trading volume. The single-instance model provides simpler, more
auditable behavior. Availability is addressed through restart policies and
fast rollback, not replication.

**Review trigger:** Horizontal scaling is reconsidered when trading volume
requires more than one instance to handle cycle processing within latency budgets.

**Date:** Inception
**Status:** Active

---

### EDR-BLD-013 — GitHub Actions for Cloud CI/CD

**Decision:** GitHub Actions provides the cloud CI/CD pipeline for IIOS.

**Rationale:** GitHub Actions integrates natively with the git repository,
provides the build environment, and requires no additional infrastructure.
The build configuration is version-controlled alongside the application code,
ensuring that CI/CD changes go through the same review process as code changes.

**Date:** Inception
**Status:** Active

---

### EDR-BLD-014 — Environment Variables for All Configuration

**Decision:** All environment-specific configuration is provided to containers
via environment variables. No environment-specific configuration is baked into
the container image.

**Rationale:** Environment variables allow the same container image to be used
in all environments by supplying different configuration at runtime. An image
that contains environment-specific configuration requires a separate build per
environment, reducing reproducibility.

**Date:** Inception
**Status:** Active

---

### EDR-BLD-015 — Paper Trading as Default Production Mode

**Decision:** The production system operates in paper trading mode (PAPER_TRADING=true)
by default. Enabling live trading (PAPER_TRADING=false) requires an explicit
Architecture Council unanimous vote.

**Rationale:** Paper trading mode provides all the system's analytical and
decision-making capabilities while eliminating the risk of unintended live order
execution during development, testing, and early operation. The default-safe
posture means that any configuration error defaults to the safer behavior.

**Date:** Inception
**Status:** Active

---

## ED2.3 Deployment Decision Matrix — Incident Scenarios

| Scenario | Decision | Authorization | Rollback | Escalation |
|---------|---------|--------------|---------|-----------|
| Container fails to start after deployment | Immediate rollback | On-call engineer | Auto | Architecture Council if rollback fails |
| Kill switch triggers within 30 min of deployment | Rollback after market close | Architecture Council | Manual | None additional |
| Cycle latency doubles after deployment | Monitor 30 min; rollback if persistent | On-call | Manual | Architecture Council if not resolved |
| Data feed unavailable after deployment | Stay on yfinance; investigate Dhan | On-call | None | Architecture Council if both feeds fail |
| Database access fails after deployment | Immediate rollback | Auto (health check) | Auto | Architecture Council |
| One container healthy, one not | Rollback | Architecture Council | Manual | Platform Team |
| Telegram bot unresponsive after deployment | Investigate 30 min; if persistent rollback | Architecture Council | Manual | None additional |
| Strategy pool empty after deployment | Alert; investigate; don't trade | Architecture Council | Manual | Research Lab |

---

## ED2.4 Deployment Governance Compliance Checklist

The following compliance items are verified at each quarterly governance review:

| Item | Review Frequency | Compliance Owner |
|------|-----------------|-----------------|
| All deployments had written authorization | Quarterly | Architecture Council |
| No deployment occurred during market hours | Quarterly | Platform Team |
| All rollbacks completed within 5-minute SLA | Quarterly | Platform Team |
| All P0 incidents have post-mortem | Quarterly | Architecture Council |
| All P0 incidents have improvement actions closed | Quarterly | Architecture Council |
| DR environment tested within 90 days | Quarterly | Platform Team |
| Artifact retention policy followed | Quarterly | Governance Manager |
| Audit trail complete (no gaps) | Quarterly | Governance Manager |
| CVE resolution SLAs met | Quarterly | Security Team |
| Feature flag changes authorized | Quarterly | Governance Manager |

---

## ED2.5 IIOS Build Pipeline Metrics (Target Values)

| Metric | Target | Alert Threshold | Period |
|--------|-------|----------------|-------|
| Build success rate | >= 95% | < 90% | Weekly |
| Mean build duration | <= 20 min | > 25 min | Weekly |
| Deployment success rate | >= 98% | < 95% | Monthly |
| Rollback rate | <= 5% | > 10% | Monthly |
| Time to detect failure | <= 5 min | > 10 min | Per incident |
| Time to rollback | <= 5 min | > 10 min | Per incident |
| MTTR (all severity) | <= 60 min | > 120 min | Monthly |
| CVE resolution (CRITICAL) | <= 24 hours | > 48 hours | Per CVE |
| DR activation success | 100% | < 100% | Per test |

---

## ED2.6 Deployment Engineering Principles Summary

The following 10 principles summarize the IIOS deployment engineering philosophy
in order of priority. When two principles conflict, the higher-priority principle
takes precedence.

**Priority 1 — Safety First:**
No deployment creates a condition that could result in uncontrolled financial
risk. Safety checks are non-bypassable.

**Priority 2 — Zero Data Loss:**
Data written to persistent storage is never lost as a result of any deployment
operation.

**Priority 3 — Rollback Always Available:**
Every deployment must be reversible. A deployment for which rollback cannot be
demonstrated is not authorized.

**Priority 4 — No Deployment During Market Hours:**
Production systems are not modified during live market operation. The market
hours guard is enforced by tooling.

**Priority 5 — Architecture Council Authorization:**
Production deployments require unanimous Architecture Council written authorization.

**Priority 6 — Reproducible Builds:**
The same source produces the same artifact. Build outputs are deterministic.

**Priority 7 — Artifact Integrity:**
Every artifact is hashed, signed, and verified. Unverified artifacts are never
deployed.

**Priority 8 — Full Auditability:**
Every governed action is recorded. The audit trail is complete and permanent.

**Priority 9 — Operational Continuity:**
Trading operations are disrupted for the minimum necessary duration.

**Priority 10 — Continuous Improvement:**
Every incident and every deployment produces learning that improves the process.

---

*IIOS-BLD-DEP-001 / Version 1.0.0 — Extended Supplements Added*
*Build, Release, Deployment, Environment, and Delivery Engineering Framework*

---

# EXTENDED SUPPLEMENT 3 — DEPLOYMENT INTEGRITY VERIFICATION SUMMARY

## ED3.1 Complete Deployment Integrity Chain

Every IIOS production deployment is verified at every link of the following
chain. A failure at any link blocks the deployment or triggers rollback.

`
SOURCE INTEGRITY
  Git commit SHA matches release tag
  No uncommitted changes on release branch
  Release branch is frozen
         |
         v
BUILD INTEGRITY
  Clean build from pinned dependencies
  Dependency hashes match requirements.lock
  CVE scan complete and clean
  Build manifest generated
         |
         v
ARTIFACT INTEGRITY
  SHA256 hash computed and stored in Artifact Registry
  Artifact signed by Build Infrastructure
  Signature verified after signing
  Container image vulnerability scan clean
         |
         v
DELIVERY INTEGRITY
  Image referenced by digest (not mutable tag)
  Hash verified at pull time
  Signature verified at deployment time
         |
         v
DEPLOYMENT INTEGRITY
  Kill switch verified INACTIVE
  Market hours guard confirmed
  Rollback artifact verified
  Database snapshot taken and verified
         |
         v
RUNTIME INTEGRITY
  All containers report (healthy)
  Kill switch thresholds confirmed correct
  PAPER_TRADING=true confirmed
  Strategy pool non-empty
  Full cycle executes within latency budget
  Telegram /status responds
`

This chain is the definition of a correct IIOS production deployment. A
deployment for which any link cannot be verified is not a complete deployment.

---

*IIOS-BLD-DEP-001 v1.0.0 — Deployment Integrity Supplement*
