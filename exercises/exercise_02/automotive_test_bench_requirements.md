# ECU Test Bench Management System

## Requirements and Guidelines

You are requested to design and implement a **Test Bench Management System** for managing Hardware-in-the-Loop (HIL) testing of automotive Electronic Control Units (ECUs).

If this is the first time you encounter the term "HIL testing" don't worry — it is standard practice in automotive development. After working through these requirements you should feel comfortable reasoning about how cars are tested before they hit the road.

The project deals with organizing, executing, and tracking tests of car computer components (ECUs) on specialized laboratory equipment (test benches).

To get a glimpse into the domain of automotive ECU testing, you can read and watch the following:

- https://en.wikipedia.org/wiki/Hardware-in-the-loop_simulation
- https://en.wikipedia.org/wiki/Electronic_control_unit
- https://en.wikipedia.org/wiki/CAN_bus
- https://www.youtube.com/watch?v=wJXbnsOs3RQ (What is an ECU?)
- https://www.youtube.com/watch?v=gqNxRINbkOc (HIL Testing Explained)

---

## General Instructions

### Background: What is an ECU?

A modern car contains dozens of Electronic Control Units — small computers that control specific vehicle functions. Examples include: the Engine Control Module (managing fuel injection and ignition timing), the Braking Control Unit (managing ABS and stability control), the ADAS Controller (managing driver assistance features like lane keeping and adaptive cruise control), and the Body Control Module (managing lights, wipers, windows, and door locks).

Each ECU communicates with other ECUs and with physical sensors and actuators through vehicle communication buses, primarily CAN bus (Controller Area Network). An ECU expects to receive signals from sensors and other ECUs, processes them according to its software, and sends commands to actuators and other ECUs.

### Background: What is a Test Bench?

Before an ECU is installed in a real car, it must be thoroughly tested. A test bench is a laboratory setup that allows engineers to test an ECU in isolation by simulating the rest of the vehicle around it.

The test bench "tricks" the ECU into thinking it is installed in a real car. It generates the electrical signals the ECU expects from sensors (temperature, pressure, wheel speed, etc.), simulates messages from other ECUs on the communication bus, and monitors the ECU's outputs to verify it behaves correctly.

This approach is called Hardware-in-the-Loop (HIL) because real hardware (the ECU) is placed "in the loop" of a simulation that replaces the rest of the vehicle.

---

### ECU (Device Under Test)

An ECU has the following properties:

- **ECU Type**: a classification indicating the vehicle domain (e.g. Powertrain, Braking, ADAS, Body Electronics, Infotainment)
- **Part Number**: manufacturer's identifier for the hardware unit
- **Firmware Version**: the software version currently flashed on the ECU (format: major.minor.patch, e.g. 3.2.1)
- **Calibration Dataset ID**: identifier for the parameter/calibration set loaded alongside the firmware
- **Signal Interface Specification**: the set of input signals the ECU expects and output signals it produces, including signal names, types (analog, digital, CAN message), value ranges, and timing requirements

An ECU's firmware version may change over the course of a project as developers release updates. The system must track which firmware version is installed on an ECU at any given time.


### Test Bench (Physical Equipment)

A test bench has the following properties:

- **Bench ID**: unique identifier
- **Bench Name**: human-readable name (e.g. "Powertrain HIL Bench #3")
- **Supported ECU Types**: list of ECU types this bench is configured to test (a bench configured for Braking ECUs cannot test an ADAS ECU without reconfiguration)
- **Hardware Channels**: the set of physical I/O channels available on the bench. Each channel has a name, a type (analog output, analog input, digital output, digital input, CAN port, LIN port), and a physical range (e.g. 0-5V, 0-12V, 0-1000 ohm)
- **Status**: one of Available, Occupied, Under Maintenance, or Offline

A test bench is a shared resource. Multiple engineers may need access to the same bench, but only one test session can run on a bench at any given time.


### Signal Configuration (Mapping Virtual Car to Physical Bench)

When an ECU is placed on a test bench, the system needs a mapping between the ECU's expected signals and the bench's physical hardware channels. This mapping is called the Signal Configuration.

For example, if the Braking ECU expects an analog input called "FrontLeftWheelSpeed" with a range of 0-250 km/h, the signal configuration specifies which physical analog output channel on the bench generates that signal and how the km/h value translates to a voltage level.

A Signal Configuration has:

- **ECU Type** it applies to
- **Bench ID** it applies to
- **Version**: configurations evolve as bench hardware or ECU interfaces change
- **Channel Mappings**: list of entries, each containing: ECU signal name, bench channel name, conversion formula (e.g. "voltage = speed_kmh * 0.02"), and any timing parameters

A signal configuration is specific to the combination of ECU type and bench. The same ECU type may have different signal configurations on different benches.


### Test Case

A test case defines a single test to be performed on an ECU. It is authored by engineers and stored in the system for repeated execution.

A test case has:

- **Test Case ID**: unique identifier
- **Test Case Name**: human-readable description (e.g. "ABS activation on ice surface at 60 km/h")
- **Target ECU Type**: which type of ECU this test applies to
- **Preconditions**: the state the ECU and simulation must be in before the test begins (e.g. "ECU powered on, engine running at idle, vehicle speed = 0")
- **Stimulus Sequence**: an ordered list of actions to perform during the test. Each action has a timestamp (relative to test start, in milliseconds), a target signal name, and a target value. For example: at T=0ms set vehicle speed to 60 km/h, at T=500ms set road surface friction to 0.1 (ice), at T=500ms inject a fault on the front-left wheel speed sensor.
- **Expected Results**: an ordered list of conditions to verify. Each condition has a signal name to observe, an expected value or range, a time window within which the condition must be met, and a tolerance. For example: within 200ms of the friction change, the CAN message "ABS_Active" must be set to 1.
- **Pass/Fail Criteria**: overall rules for determining the test outcome, including whether all expected results must pass or a subset is sufficient, and any timing tolerance on the overall test duration.
- **Timeout**: maximum allowed duration for the test execution in milliseconds.

Test cases are versioned. When a test case is modified, a new version is created. Previous versions are retained.


### Test Suite

A test suite is a named, ordered collection of test cases intended to be run together. For example, "Braking ECU Full Regression" might contain 200 test cases covering all aspects of the braking system.

A test suite has:

- **Suite ID**: unique identifier
- **Suite Name**: human-readable name
- **Target ECU Type**: the ECU type all contained test cases must target
- **Test Case List**: ordered list of test case IDs (with specific versions)
- **Execution Mode**: Sequential (run one after another, stop on first failure or continue all) or Independent (each test case resets the bench to initial state before running)


### Test Session (Execution)

A test session represents a single execution event — one engineer running one or more test cases on one bench with one ECU.

A test session has:

- **Session ID**: unique identifier
- **Bench ID**: which bench is being used
- **ECU instance identifier**: which specific physical ECU is being tested (Part Number + serial)
- **Firmware Version**: the firmware version on the ECU at the time of the session (captured at session start)
- **Signal Configuration Version**: which version of the signal configuration was used
- **Test Cases**: the list of test cases (with versions) to be executed, either specified individually or via a test suite reference
- **Session Status**: one of Scheduled, Running, Completed, Aborted, or Failed
- **Operator**: the engineer who initiated the session

When a session runs, each test case produces a **Test Result**:

- **Test Case ID and version**
- **Verdict**: Pass, Fail, Error (execution problem, not a test logic failure), or Skipped
- **Signal Trace Log**: time-series recording of all input and output signals during the test execution
- **Timing Measurements**: actual timestamps of when expected conditions were met (or not met)
- **Failure Details**: if the verdict is Fail, which specific expected results were not met and what the actual observed values were


### Bench Scheduling

Engineers need to reserve bench time in advance. The scheduling system must handle:

- **Reservation requests**: an engineer requests a specific bench (or any bench compatible with a given ECU type) for a time window
- **Conflict resolution**: two engineers cannot reserve the same bench for overlapping time windows
- **Priority levels**: some test sessions are higher priority than others. For example, a test needed to investigate a blocking defect discovered in vehicle testing has higher priority than routine weekly regression. Priority levels are: Critical, High, Normal, Low.
- **Automated regression windows**: certain time slots (e.g. nightly between 22:00 and 06:00) can be designated for automated regression runs. During these windows, the system should automatically initiate scheduled test suite executions without an operator present.
- **Bench unavailability**: when a bench goes Under Maintenance or Offline, all future reservations for that bench must be flagged and affected engineers notified.


### Results Repository and Querying

All test results must be stored persistently and be queryable. Typical queries include:

- "Show me all test results for the Braking ECU firmware version 3.2.1 in the last two weeks."
- "Show me all failures for test case TC-0042 across all firmware versions."
- "What is the pass rate for the ADAS Full Regression suite over the last 10 runs?"
- "Compare signal trace logs for test case TC-0042 between firmware 3.2.0 (passing) and 3.2.1 (failing)."

Results must be linked to the exact firmware version, calibration dataset, signal configuration version, and test case version used. This chain must be maintained for auditing purposes.


### Traceability

The automotive industry operates under functional safety standards (ISO 26262). The system must support bidirectional traceability:

- Each **requirement** (managed externally, referenced by a Requirement ID string) can be linked to one or more test cases that verify it.
- Each **test case** can be linked to one or more requirements it verifies.
- Each **test result** is linked to the test case version, ECU firmware version, and session in which it was produced.

The system must be able to answer: "For requirement REQ-1234, which test cases verify it, and what was the most recent test result for each?"


### Notifications and Alerts

The system should be able to notify relevant parties when:

- A scheduled session is about to start (configurable lead time)
- A bench becomes available after maintenance
- A test session completes (with summary of pass/fail counts)
- A previously passing test case starts failing on a new firmware version (regression detection)
- A bench reservation conflict arises from a priority override

The notification mechanism itself is not prescribed — it may be email, messaging integration, or dashboard alerts.


---

## Parts of the Project

### Simulation / Orchestration Engine

A central program that coordinates all activity. It must:

- Manage the registry of benches, their configurations, and their availability status.
- Manage the library of test cases and test suites, including versioning.
- Accept and validate test session requests, matching them against bench capabilities and scheduling constraints.
- Manage the execution lifecycle of test sessions: initiate signal configuration loading, sequence test case execution, collect results, and update session status.
- Provide the results repository for storage and querying.
- Enforce that no test session runs on a bench that is not configured for the target ECU type.
- Handle error cases gracefully. Error cases shall never lead to a system crash and should not be silently ignored. Examples of error cases: requesting execution of a test case on a bench that doesn't support the target ECU type; a stimulus sequence referencing a signal name not present in the signal configuration; a test case targeting an ECU type different from the session's ECU.

### Signal Generation and Monitoring Layer

The component responsible for translating test case stimulus sequences into physical bench operations and monitoring ECU responses:

- Load the appropriate signal configuration for the ECU type and bench combination.
- Translate stimulus actions (e.g. "set vehicle speed to 60 km/h") into hardware channel commands using the conversion formulas from the signal configuration.
- Monitor ECU output signals and record time-series trace data.
- Evaluate expected results against observed signals, applying tolerances and time windows.
- Report verdicts and trace logs back to the orchestration engine.

### Test Authoring Interface

The component through which engineers create and manage test cases:

- Create, edit, and version test cases.
- Organize test cases into test suites.
- Define and edit signal configurations for ECU type / bench combinations.
- View and query test results.
- Link test cases to requirement IDs.
- Reserve bench time.


---

## Part 1

For the first iteration, we need:

**API and Data Model Design**

- Design the core data structures (classes/entities) for: ECU, Test Bench, Signal Configuration, Test Case, Test Suite, Test Session, and Test Result.
- Define the interfaces between the major system components: how the orchestration engine communicates with the signal generation layer, and how the test authoring interface communicates with the orchestration engine.
- Define the input/output formats for test case definitions and test results.

**Orchestration Engine (Simplified)**

- Implement a simulation that can run a batch of test sessions against a set of benches.
- The signal generation layer should have the proper API but can be simulated: instead of driving real hardware, it generates mock signal traces and produces pass/fail verdicts based on simple rules (e.g. randomly, or based on a predefined outcome file).
- Bench scheduling in Part 1 can be simplified: single-threaded sequential execution, no concurrent sessions, no priority preemption. Reservations are respected in order of request.
- Maintain the results repository. All results from simulated sessions must be stored and queryable.

**Test Case Management**

- Implement the ability to create, version, and retrieve test cases.
- Implement test suite creation (ordered list of test case references).
- Implement basic traceability linking (test case ↔ requirement ID).

**Error Handling**

- You should decide on a strategy for error cases. Error cases shall never lead to a program crash and should not be treated as OK (i.e. silently ignored). Example error cases: a test case references a signal not in the signal configuration; a session targets a bench that doesn't support the ECU type; a test suite contains test cases for different ECU types.

**Data and Reporting**

- Data collected by the simulation: you should decide what metrics to track.
- Implement at least the following queries: results by ECU firmware version, results by test case across versions, pass rate for a test suite over multiple runs.


**Items that you may want to consider:**

- What data is managed centrally vs. what belongs to individual bench controllers?
- Input and output formats — configuration files, result files, APIs?
- How does the system discover which benches exist and what their capabilities are?
- How are signal configurations validated before a test session starts?
- The test authoring interface: is it a separate application, a CLI, or part of the orchestration engine's API?


**Additional requirements that may become relevant in future iterations (may be ignored at this point, or noted where relevant):**

- Real hardware integration via standard protocols (ASAM XiL API, VISA instrument control).
- Firmware flashing management — the ability to flash new firmware onto an ECU as part of a test session setup.
- Environment simulation models — integration with Simulink or similar model-in-the-loop simulation engines for complex scenarios (e.g. ADAS radar/camera simulation).
- Multi-bench orchestration — distributing a large test suite across multiple compatible benches running in parallel.
- Continuous Integration pipeline integration — automatically triggering regression test suites when a new firmware build is produced.
- Support for different ECU communication protocols beyond CAN (LIN, FlexRay, Automotive Ethernet).
- Detailed weight and power supply simulation for ECU power consumption testing.
