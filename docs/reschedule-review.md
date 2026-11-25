# Reception and rescheduling review · 25 November 2026

## Incident

The original database contained two confirmed visits for the reported caller, doctor and date. The 16:10 reference was AS-D452EF90, and 15:10 was AS-24EFAB15. Inspection found no reschedule function in the original tool registry. A second booking could succeed while the first remained active.

The reported records were checked for matching ownership, doctor, date, times and confirmed status before the old visit was cancelled through the transactional service. The database then showed 15:10 booked and 16:10 open. The cancelled row remains in history. New reschedules update the slot on the original visit and preserve its reference. A failed move rolls back, retaining the original reservation.

## Prioritized design findings and changes

The forest navigation, restrained colors and serif page heading already gave Aster a recognizable clinic identity. The working dashboard still gave a promotional call card more prominence than the appointment register. The most consequential visual defect was that two receipts could communicate two active outcomes after the caller requested one change.

| Rank | Observed weakness | Implemented change |
| --- | --- | --- |
| 1 | Receipts accumulated by status, allowing obsolete visit outcomes to remain visible. | Keep one current outcome per reference. A successful move displays Rescheduled, the previous time, the new time and the same reference. |
| 2 | The transcript and confirmations shared one scroll area. A long turn could push the receipt out of view. | The companion has a separately bounded receipt area immediately above the call controls. |
| 3 | A receipt for another day could sit beside today's unrelated schedule. | The initiating dashboard selects the committed visit date and refreshes from SQLite. Other tabs retain their selected view. |
| 4 | The receptionist promotion occupied the right column while actual visits fell below the roster. | The daily active register now sits beside the schedule on desktop. Full history stays available in Appointments. |
| 5 | The receptionist card duplicated the header call action and repeated operational instructions. | Removed the card, its large headset illustration and the second launch button. |
| 6 | All unavailable times looked identical. The user could not see which future time a booking occupied. | Booked times have amber fill and a bottom rule. Elapsed times are struck through. Open times retain sage fill. |
| 7 | A generic total included cancelled visits and could look like a count of active bookings. | Label active counts explicitly and filter the front desk to confirmed visits on its selected day. |
| 8 | A disabled Companion open button competed with the running call and wrapped the mobile page heading. | Hide the launch action while the companion is open. |
| 9 | A headset illustration and large centered identity block consumed the space needed for conversation. | Compact left-aligned call header puts status, timer and measured audio level together. |
| 10 | Caller and receptionist turns looked alike apart from small speaker labels. | Add distinct left rules, caller tint and a separate treatment for interim text. |
| 11 | The transcript heading disappeared while reviewing earlier lines. | Pin the heading within the transcript scroll area. Preserve the user's scroll position when reading history. |
| 12 | The calendar date used small uppercase lettering; the selected summary date disappeared on mobile. | Use sentence-case date text and keep the summary's selected date visible at phone widths. |
| 13 | Workspace breadcrumbs repeated the active navigation item. | Use one slim clinic and synchronization line. Retain active-page navigation and keyboard controls. |
| 14 | Date arrows and phone navigation had cramped touch targets. | Enlarge calendar targets and mobile navigation buttons. |
| 15 | Try again after failure implied that the previous booking conversation would resume. Historical journal replay could also highlight old changes. | Label a fresh call explicitly, retain committed outcomes through the error state, and ignore journal IDs already included in the current snapshot when highlighting rows. |

Captured before editing and again after implementation at 1440×900, 1280×800 and 390×844. The screenshot pass checked viewport width against document width. The first receipt inspection showed an unrelated schedule date; the final implementation and browser regression cover that defect. Screenshot files beginning review-before and review-after are from the normal server. The review-rescheduled screenshot is a controlled WebRTC fixture with a real database transaction and synthetic conversation events.

[Desktop before](evidence/review-before-1440.png) · [Desktop after](evidence/review-after-1440.png) · [Phone before](evidence/review-before-call-390.png) · [Phone after](evidence/review-after-call-390.png) · [Rescheduled receipt in the browser fixture](evidence/review-rescheduled.png)

## QA results

| Requirement | Classification | Observation |
| --- | --- | --- |
| Incorrect, interrupted or unrelated phone readback; correction after confirmation | Verified | Session tests reject the mutation or require a fresh complete readback. STT frame test rejects interim/unattributed text as identity evidence. |
| Duplicate booking, repeated tool calls, delayed replay | Verified | Independent tests check one active reservation, stable reference, one journal change, rejection of reused request IDs with different arguments, and rejection of a delayed booking after cancellation. |
| Concurrent booking and stale availability | Verified | Independent SQLite writers competed for a slot. One succeeded. A stale, past or occupied destination was rejected. |
| Rescheduling | Verified | Transaction tests and a real-browser fixture moved the original reference. One reservation remained active. Both schedule slots and the receipt changed, including in a second tab. |
| Competing moves and rollback | Verified | Two writers supplied the same source slot. One move won. An injected journal failure rolled the move back. |
| Wrong cancellation ownership, ambiguous visits, stale cancellation consent | Verified | A different owner cannot cancel or move the visit. Several visits require selection. A visit that changed time requires a new cancellation question. |
| Call-session isolation and disconnection | Verified | Separate Conversation instances isolate identities. A closed session rejects a late mutation. Edge started a second call and checked that prior receipts and transcript lines were cleared. |
| Reconnection and committed dashboard updates | Verified | A second browser went offline around cancellation and recovered the committed result. The transaction journal and mutation share a commit; rollback creates no notification. |
| Microphone denial and call controls | Verified | Edge permission denial produced actionable guidance. Real WebRTC fixture exercised call start, mute/unmute and hang-up. |
| ElevenLabs STT and streaming TTS in normal execution | Verified | Normal backend constructs the actual provider adapters. An opt-in Edge call sent a synthetic spoken question through that backend. The browser received non-silent remote audio (observed peak 0.1455) and the finalized transcript matched the availability question. No browser speech synthesis or recognition is in the production path. |
| Gemini native function calling | Verified | Earlier live Gemini 3.5 Flash probe invoked check_doctor_availability and returned three SQLite slots. Normal call execution uses the same Google service and function schema; the user also supplied a spoken booking transcript with corresponding committed database records. |
| Current normal-server Gemini availability call | Failed | The independent browser probe reached Google after transcription and ended with HTTP 429. Aster displayed Gemini's usage-limit message. |
| Full post-fix reschedule spoken through all providers | Not tested | The reschedule succeeded in service and browser integration tests. The current live-provider check stopped at Gemini quota. |
| Physical microphone barge-in, device unplug, and network loss at the exact instant of commit | Not tested | Interrupted-readback, closed-session, rollback and reconnect cases have deterministic coverage. The exact physical and timing scenarios were not independently reproduced. |

## Verification boundaries

The browser acceptance suite uses a temporary database, real browser WebRTC transport and a substituted worker in tests/browser_server.py. It explicitly injects transcript and tool events for repeatability. The optional live-audio.mjs probe supplies a synthetic microphone recording only; its server is the production Aster instance and its remote audio and transcript come through the real provider path. Neither probe represents a human-spoken post-fix booking or a submission video.
