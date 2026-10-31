# AchieveX logic and access audit — 31 October 2026

## Live database verification

201 participants: 73 Junior, 64 Senior CS, 64 Senior Core. Every record passes the server's participant validator; SICs are unique; generated database totals match the five weekly scores. Published week is 3. All 15 schedule entries validate and none is revealed. Public responses exclude email, contact and gender. Anonymous Supabase requests to participants/settings and the private schedule are blocked. No participant or competition setting was changed by this audit.

## Corrections

- Public badges now come from one server evaluator for SQLite and Supabase. The browser no longer recalculates a different badge set.
- Competitive badges compare students within Junior, Senior CS or Senior Core, matching leaderboard categories. Ties share awards.
- Main Character follows published cumulative standings (missing scores count zero; an entirely ungraded student is ineligible). It denotes the current leader until Week 5, not a guaranteed final champion.
- Ace evaluates each published exam separately; Glow Up evaluates each consecutive published pair separately. Repeated awards are retained.
- Unlocked Five requires all five weeks published and all five scores graded. A zero counts as graded; a blank does not. Participation is inferred from grading because no separate attendance/submission field exists.
- Corrections, deletion and reducing the published week automatically retract affected public badges. Unpublished scores cannot generate public awards.
- Decimal scores use half-up rounding to two places, matching PostgreSQL numeric storage. Negative request lengths and non-boolean editing flags are rejected; editing a missing participant returns 404.
- Cloud sessions now have durable private records. Logout revokes the server-side session rather than only clearing the browser cookie. Atomic private Storage objects enforce six login attempts per IP per fixed ten-minute window across instances, including successful logins.
- Schedule read errors no longer silently return defaults except for a missing object.

## Verification

35 automated tests pass, including authentication, authorization, cross-origin writes, rate limits, bounds, totals, CSV preview/import validation, deletion confirmation, reveal privacy, badge boundaries/ties, category isolation, publication rollback, rounding and cloud projection parity. Live isolated private Storage objects verified atomic creation, session validity and revocation, then were removed. These tests do not constitute an independent penetration test or visual/browser review.

## Operational considerations

- Shared PIN access cannot attribute edits to individual admins; there is no edit history or recovery UI. Use individual accounts/audit logging if that becomes necessary.
- Rotate the Supabase secret previously shared in chat and choose a private admin PIN in the deployment environment. Secrets are server-only and excluded from git/static output.
- Private `achievex-config/security/` objects retain expired sessions and attempt slots; periodically remove expired entries (sessions after eight hours, attempt windows after their ten-minute window). Never make this bucket public. Changing SESSION_SECRET invalidates sessions.
- Fixed-window limits can allow attempts on either side of a window boundary; distributed IP attacks need platform-level protection. Storage errors fail closed with 503.
- Email syntax is validated; ownership and Silicon email-domain eligibility are not verified. Names/SIC/year/results are intentionally public.
- CSV imports deliberately update existing SICs. Concurrent admins can overwrite one another's edits; there is no optimistic locking.
- Optional database badge tables are not authoritative. Public awards are derived from current scores and publication settings to prevent stale results. Historical award timestamps are not tracked; evidence identifies qualifying weeks.
- Supabase backups/PITR and restoration are operational settings, not verified by the app's REST credentials. Keep backups before replacing demo data with real records.
