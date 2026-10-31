# AchieveX — Silicon Achievers’ Club

A responsive academic championship dashboard with light/dark themes, animated standings, team profiles, exam schedules, and a PIN-protected administration panel.

## Quick start

Requires Python 3.9+ and Node.js/npm for the development scripts. No package installation is needed.

```bash
git clone https://github.com/SahinS14/achieveX-SILICON-ACHIEVERS-CLUB.git
cd achieveX-SILICON-ACHIEVERS-CLUB
npm run dev
```

Open http://localhost:4173. Alternatively run `python3 server.py` without Node.js. Local SQLite storage is ready immediately; Supabase is optional and can be configured later. No credentials or participant records are included in this repository.

## Admin

Open http://localhost:4173/admin. The requested initial PIN is **135790**. Change it using `ADMIN_PIN` in an untracked `.env` file. Server-checked PIN, an HttpOnly SameSite cookie, an 8-hour session, origin checks, and login rate limits protect the admin API. The development server binds to localhost.

Add or edit participants and their five scores (0–100 inclusive, up to two decimals). Blank is ungraded; zero is a graded zero. SIC is unique and case-insensitive. Editing locks the SIC to prevent accidental duplicates. CSV imports are validated first, then confirmed: existing SICs are updated, including clearing scores when the CSV cells are blank. Invalid imports save nothing. Download the header-only CSV template from the panel; maximum 1,000 rows per file.

Use “Publish results through” to choose the latest visible week. Future scores stay server-side. Overall scores are out of 500; cumulative ranks compare only published weeks, exclude participants with no graded published scores, and assign equal ranks to ties (1,1,3). No committee tie-break is invented. Junior and Senior Core/CS are ranked separately. Student data starts empty; the demo roster is removed. The public page checks for updates every 30 seconds and when focused.

Names, SICs, year, track, and published scores are public. Emails, contact numbers, gender, branch, unpublished scores, and the admin roster are never included in the public results API. Store personal data only on a machine/project you control. No signup is required.

## Storage and Supabase setup

Without Supabase settings, the app saves to `.data/achievex.sqlite3`, an ignored local SQLite database outside the served directory. It survives server restarts. Back up this file as needed.

1. Create/select your Supabase project. Run `supabase/schema.sql` in its SQL editor. This creates participant/settings tables and an atomic import function. RLS is enabled; anonymous and authenticated browser roles receive no access.
2. Copy `.env.example` to `.env` in this project directory.
3. Set `SUPABASE_URL` and `SUPABASE_SECRET_KEY` to your project URL and server secret key (Settings → API Keys). A legacy service-role key is also accepted. Never put this key into `dist/`, browser JavaScript, screenshots, or Git.
4. Restart `npm run dev`. After unlocking Admin, the status must read **SUPABASE CONNECTED**. Verify by saving one participant and checking the table in Supabase.

Supabase is the sole data source whenever configured. A failing Supabase connection returns an error; the app never silently writes to SQLite instead. Existing local records are not copied automatically: retain your CSV and import it in the connected panel. The SQL schema's total column also calculates the five-week total in Postgres.

Do not expose this development server publicly. For public deployment, use HTTPS, Secure cookies, durable shared sessions/rate-limiting, and a private backend; keep secrets server-side. The PIN requested for this local application is not an identity system.

## Verification

`npm run check` checks JavaScript syntax and runs backend integration tests covering authentication, rate limits, cross-origin requests, scoring bounds, totals, privacy, publishing, CSV validation/rollback, duplicate SICs, and category rules. Tests use a temporary database, not real participants.

## Design assets

Outfit and Plus Jakarta Sans are stored locally with SIL Open Font License notices. Generated avatars illustrate leaderboard profiles, not actual student photos. Faculty/member photographs and confirmed exam dates are awaited. The achievement cutout was generated with the built-in image tool from the supplied illustration. The interface honours reduced motion.

## Vercel deployment

The repository includes `vercel.json` and `api/index.py` for Vercel's Python Functions. Static assets come from `dist/`. The project can be deployed before database setup: the public leaderboard is empty, and admin writes stay disabled until configured. SQLite is only used locally, never on Vercel.

When ready, run `supabase/schema.sql` and add these **server-side Vercel environment variables**, then redeploy:

- `SUPABASE_URL`
- `SUPABASE_SECRET_KEY`
- `ADMIN_PIN` (your chosen six-digit PIN)
- `SESSION_SECRET` (a long random secret; generate with `python3 -c "import secrets; print(secrets.token_urlsafe(48))"`)

Cloud sessions are signed and checked across function instances, with Secure HttpOnly cookies. Logout clears the browser cookie; signed tokens expire after eight hours. Rotate SESSION_SECRET to revoke all cloud sessions. Login throttling is per function instance; configure durable edge rate limits before a wider admin rollout.

## Calendar reveals and club page

Our Team is removed. About now describes Silicon Achievers’ Club using the supplied club guidelines; it flags the document’s conflicting CGPA thresholds instead of inventing one.

Admin → **Schedule & subject reveals** manages five rounds per Junior, Senior CS, and Senior Core. Edit the subject, assessment scope, HTTPS syllabus reference, and optional date. Save with the reveal switch off for a private draft; reveal only when ready. The public API omits hidden subjects, scope, and references. Revealed calendar rows open an accessible syllabus dialog with a university PDF link. Presets use the CSE 2025–26 curriculum; they are not guaranteed exam scope, and no unrelated course is substituted for missing references.

## Seven Achievement Badges

AchieveX features seven automated achievement badges calculated directly from verified exam results and participation data:
1. **The Main Character 👑** (Ranking): Overall AchieveX champion with highest cumulative average percentage across finalized exams (requires completion of all published exams).
2. **The Ace ⚡** (Ranking): Highest scorer in an individual weekly exam (evaluates each exam independently; multiple Ace awards preserved).
3. **The Glow Up 📈** (Ranking): Greatest positive improvement in percentage points between consecutive finalized weekly exams.
4. **On Fire 🔥** (Milestone): Consistently scores 80% or higher across three consecutive weekly exams.
5. **Flawless 💎** (Milestone): Achieved a perfect 100% score in any verified weekly exam.
6. **The Comeback Arc 🚀** (Milestone): Scores strictly below 50% in one exam and improves by at least 20 percentage points in the next exam.
7. **The Unlocked Five 🔒** (Milestone): Verified participation or submission across all five designated championship exams.

Badge assignment is 100% automated and transparent. There is no manual assignment by administrators or developers.


### Audit and cloud admin sessions

See [AUDIT.md](AUDIT.md) for verified rules, test coverage and operational limits. Cloud admin sessions and atomic login attempt slots use the existing **private** `achievex-config` bucket under `security/`; no additional SQL migration is needed. Keep this bucket private. Periodically delete expired security objects. Logout revokes a durable session; changing `SESSION_SECRET` invalidates all existing sessions. Public badges are calculated on the server from published results, rather than optional award-table records.

### Student UI checks

See [UI_AUDIT.md](UI_AUDIT.md) for the student usability pass and remaining rendered/device checks. Run `npm ci` then `npm run check` to include DOM interaction regression tests alongside Python API tests. DOM tests do not replace visual browser or real-phone testing.
