# Manual voice tests

Use [the disposable QA desk](http://127.0.0.1:8026). The automatic trial left one cancelled visit and released its 09:00 slot. Tomorrow, 26 November, had Dr Asha Menon at 09:00 and 10:00 and Dr Arjun Rao at 09:10 and 10:10 IST. If running on a different day, use tomorrow and read the displayed times first. Use only these fictional digits. Keep a second tab on Appointments. All ten human trials are NOT RUN.

For a normal interaction, read the phone aloud, verify every repeated digit, and say yes only after the complete question. Also confirm the exact doctor and time. Record test ID, IST time, transcript, tool outcome, receipt reference, slot before/after and result in a local file under .tools/manual-evidence. Keep recordings containing anyone else's voice or phone private.

| Trial | Initial state and exact caller input | Expected tools, speech, visible result and forbidden outcome |
| --- | --- | --- |
| V1 | Empty desk. “I want Dr Asha Menon tomorrow at nine AM. My mobile number is nine eight seven six five four three two one zero.” | Availability then book proposal. Confirm phone and exact visit. One confirmed receipt, nine AM booked in both tabs. No earlier write. |
| V2 | Choose a free 10:10 with Arjun. Give the phone ending zero. After readback say “No. The last digit is one. The whole number is nine eight seven six five four three two one one.” | Complete corrected readback, new yes and visit agreement. One booking under suffix 3211 only. |
| V3 | Free slot. During phone readback say “No, wait. Stop the booking.” | No authorized book, receipt or new row. Agent should stop or clarify. |
| V4 | Leave V1 booked. “Can I have Dr Asha tomorrow at nine? If that is taken, ten AM works.” | Availability reports real alternative. Confirm another fictional phone and 10:00. Nine AM remains owned by V1. |
| V5 | Fresh call and free slot. “Book Dr Arjun tomorrow at nine ten.” After success say “Please cancel the appointment we just booked.” | Book then cancel lookup and confirmation. Same reference becomes Cancelled. Slot reopens in second tab. No second row for this action. |
| V6 | Create two visits for the same fixture number with distinct doctors. “Cancel my appointment.” | Cancel lookup reports multiple choices. Name one visit and confirm the full cancellation question. Other visit remains confirmed. |
| V7 | Ask for all availability. While Aster lists times say “Wait, I want dermatology instead.” | Old speech stops, lookup follows new specialty. No booking from the interrupted speech. |
| V8 | Start a fresh call. Mute, speak the fixture number, unmute and say “Please check cardiology tomorrow.” | Muted digits cannot establish identity. Unmute permits availability. No receipt. |
| V9 | Fresh call. “Book me without reading my number back.” | The backend requires phone and slot agreement. No new row or receipt. |
| V10 | After confirming a phone but before confirming a visit, end the call. Start again and say “Use the same number and book it.” | New call asks for the phone and visit. No previous transcript, receipt or pending action appears. |

If Gemini returns its quota message, record BLOCKED with the time and preserve the existing row count. The candidate's demonstration gate requires an actual successful spoken booking and dashboard update. Record the short submission video only after that gate passes.
