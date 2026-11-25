# Invariant evidence

The last column identifies the tested boundary and any outstanding release gate.

| ID | Invariant | Evidence and scope |
| --- | --- | --- |
| I01 | A doctor slot never has more than one active booking. | SQL unique index, 2/10/50 writers, state machine |
| I02 | A booking is never created without valid phone confirmation for the current session and the agreed appointment. | Phone and exact slot challenges, raw SQL in test_release and conversations |
| I03 | A cancellation is never performed against an appointment that does not match the current confirmed phone number. | Owner predicates, fixture cancellation and concurrency tests |
| I04 | Changing the phone number invalidates its previous confirmation. | Correction and number replacement tests |
| I05 | Changing the selected doctor, time or appointment invalidates any stale action-specific confirmation. | Slot substitution and moved-visit cancellation tests |
| I06 | Replaying the same booking operation cannot create an additional appointment. | Replay/duplicate/restart cases |
| I07 | Replaying the same cancellation cannot produce an additional mutation or conflicting result. | Cancellation replay and simultaneous cancellation |
| I08 | A failed transaction leaves no partial appointment state. | SQL trigger rollback and subprocess exit immediately before commit |
| I09 | A confirmed booking survives process restart. | Reopen and post-commit process exit |
| I10 | A cancellation restores a future slot to the appropriate available state. | Future slot reopened in snapshot and browser |
| I11 | Past slots cannot be booked. | Frozen local clock and past-slot tests |
| I12 | Appointment references uniquely identify real persisted appointments. | SQLite-backed receipt reference compared to browser fixture ledger |
| I13 | The AI never announces a successful booking unless the corresponding operation actually committed. | Structured results verified; one spoken success and cancellation matched the same database reference; other conversations unverified |
| I14 | Dashboard availability and appointment state agree with the database. | Browser independent ledger, initiating tab and second tab |
| I15 | A receipt is never generated for an unsuccessful operation. | No structured receipt on rejected action in simulations |
| I16 | A new call never inherits the previous caller's confirmed phone number, transcript or pending action. | Fresh Conversation, callback guards and browser call restart |
| I17 | Delayed events from an old session cannot modify a new session's state. | Closed session and old receipt tested; arbitrary delayed messages from old peers NOT RUN |
| I18 | A cancelled or interrupted tool operation cannot cause a misleading success response. | Interrupted turn and closed session tested; overlapping live speech/tool result BLOCKED |
| I19 | Failed, duplicated or out-of-order frontend events cannot permanently corrupt displayed state. | Late receipt version, duplicate, offline snapshot and browser tests |
| I20 | No API credentials or unnecessary sensitive data appear in client bundles, public logs or committed files. | Recognizable key formats scanned; comprehensive ordinary-log retention audit NOT RUN |
| I21 | Every recoverable failure eventually reaches an explicit recoverable state or clean termination. | Preflight timeout, denied mic and quota recovery UI tested; all provider failure permutations NOT RUN |
| I22 | Ending a call releases its audio, transport, task and timer resources. | Fixture hangup completes; physical track and long-run resource census NOT RUN |
| I23 | The agent never invents doctors, available slots, existing appointments or booking references. | Returned database slots tested; the final live call spoke the real committed reference; broader model behavior unverified |
| I24 | Mutating operations are authorized and validated by trusted backend code, not merely by the LLM prompt. | Business authorization tests, backend schema validation and ownership checks |
| I25 | The assignment's phone-only identification requirement remains intact. | Only phone challenge in production pipeline. Knowledge of a phone permits impersonation. |
