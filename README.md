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
