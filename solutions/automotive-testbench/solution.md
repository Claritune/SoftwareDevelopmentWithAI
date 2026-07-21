# ECU Test Bench Management System — Reference Solution

## Module Decomposition

**ECU Registry** — Manages the catalog of known ECU types, tracks individual ECU instances and their current firmware/calibration versions.

**Bench Registry** — Manages the inventory of physical test benches, their hardware channel capabilities, supported ECU types, and current operational status.

**Signal Configuration Manager** — Stores and versions the mapping definitions between ECU signal interfaces and bench hardware channels, including conversion formulas and timing parameters.

**Test Case Repository** — Handles creation, versioning, storage, and retrieval of test case definitions and their organization into test suites.

**Traceability Manager** — Maintains the bidirectional links between external requirement IDs and test cases, and provides coverage queries ("which requirements are verified, by what, with what result").

**Bench Scheduler** — Manages reservation requests, detects and resolves time conflicts, enforces priority rules, and designates automated regression windows.

**Session Controller** — Orchestrates the lifecycle of a single test session: validates inputs, sequences test case execution, delegates to the signal layer, collects results, and updates session status.

**Signal Translation Layer** — Translates abstract stimulus actions ("set speed to 60 km/h") into bench-specific hardware commands using signal configurations, and translates raw hardware readings back into named signal values.

**Signal Monitor & Evaluator** — Records time-series trace data from ECU outputs during execution and evaluates observed signals against expected results, applying tolerances and time windows to produce per-test-case verdicts.

**Results Repository** — Persistently stores all test results with full version context (firmware, calibration, signal config, test case version) and serves structured queries and comparisons.

**Notification Service** — Accepts event triggers from other modules (session complete, regression detected, bench available, conflict) and dispatches alerts through configured channels.

**Batch Runner / Simulation Engine** — Coordinates execution of multiple sessions across available benches, feeding the session controller and aggregating cross-session metrics like suite pass rates over time.

---

## Sequence Diagram — Test Session Execution Flow

```mermaid
sequenceDiagram
    actor Engineer
    participant BR as Batch Runner
    participant BS as Bench Scheduler
    participant SC as Session Controller
    participant BenchReg as Bench Registry
    participant ECUReg as ECU Registry
    participant TCR as Test Case Repository
    participant SCM as Signal Config Manager
    participant STL as Signal Translation Layer
    participant SME as Signal Monitor & Evaluator
    participant RR as Results Repository
    participant NS as Notification Service

    Engineer->>BS: Request bench reservation<br/>(ECU type, time window, priority)
    BS->>BenchReg: Find compatible bench
    BenchReg-->>BS: Bench #3 available
    BS-->>Engineer: Reservation confirmed<br/>(Bench #3, 14:00-16:00)

    Note over Engineer,NS: Session Start

    Engineer->>SC: Create test session<br/>(Bench #3, ECU instance, suite ID)
    SC->>BenchReg: Validate bench status & compatibility
    BenchReg-->>SC: Bench #3 OK, supports Braking ECU
    SC->>ECUReg: Get ECU firmware & calibration versions
    ECUReg-->>SC: FW 3.2.1, Cal dataset D-0089
    SC->>TCR: Resolve test suite → test case list
    TCR-->>SC: [TC-0041 v2, TC-0042 v3, TC-0043 v1]
    SC->>SCM: Get signal config<br/>(Braking ECU + Bench #3)
    SCM-->>SC: Signal config v4 with channel mappings
    SC->>BenchReg: Set bench status → Occupied

    Note over Engineer,NS: Test Case Execution Loop

    loop For each test case in suite
        SC->>STL: Load signal config & preconditions
        STL-->>SC: Bench configured, preconditions set

        SC->>STL: Execute stimulus sequence
        STL->>SME: Stream raw signal traces

        Note right of SME: Records time-series data,<br/>evaluates expected results

        SME-->>SC: Verdict (Pass/Fail/Error)<br/>+ trace log + timing measurements
        SC->>RR: Store test result<br/>(verdict, traces, versions)
    end

    Note over Engineer,NS: Session Complete

    SC->>BenchReg: Set bench status → Available
    SC->>RR: Finalize session record<br/>(3 passed, 0 failed)
    SC->>NS: Trigger session-complete event
    NS-->>Engineer: Notification: session complete,<br/>all tests passed

    Note over Engineer,NS: Post-Session Queries

    Engineer->>RR: Query: "All results for FW 3.2.1"
    RR-->>Engineer: Results with trace logs & verdicts
    Engineer->>TCR: Query traceability for REQ-1234
    TCR->>RR: Get latest results for linked test cases
    RR-->>Engineer: Coverage report with verdicts
```
