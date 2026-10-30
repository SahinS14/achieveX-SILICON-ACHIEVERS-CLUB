-- Run once in your Supabase SQL editor, then set server-only credentials in .env.
create table if not exists public.participants (
 sic text primary key check (sic ~ '^[a-z0-9]{5,24}$'),
 full_name text not null,
 email text not null,
 contact text not null,
 gender text not null default '',
 year integer not null check (year between 1 and 4),
 branch text not null,
 track text not null check (track in ('junior','cs','core')),
 week1 numeric(5,2) check (week1 between 0 and 100),
 week2 numeric(5,2) check (week2 between 0 and 100),
 week3 numeric(5,2) check (week3 between 0 and 100),
 week4 numeric(5,2) check (week4 between 0 and 100),
 week5 numeric(5,2) check (week5 between 0 and 100),
 total numeric(6,2) generated always as (coalesce(week1,0)+coalesce(week2,0)+coalesce(week3,0)+coalesce(week4,0)+coalesce(week5,0)) stored,
 check ((year=1 and track='junior') or (year>1 and track in ('cs','core')))
);
create table if not exists public.competition_settings (
 id integer primary key check (id=1),
 published_week integer not null default 0 check (published_week between 0 and 5)
);
insert into public.competition_settings values(1,0) on conflict do nothing;
alter table public.participants enable row level security;
alter table public.competition_settings enable row level security;
revoke all on public.participants,public.competition_settings from anon,authenticated;
grant all on public.participants,public.competition_settings to service_role;
-- One transaction for a complete validated CSV import; on conflict the same SIC is updated.
create or replace function public.import_participants(records jsonb) returns void
language sql security invoker set search_path=public as $$
 insert into public.participants(sic,full_name,email,contact,gender,year,branch,track,week1,week2,week3,week4,week5)
 select sic,full_name,email,contact,gender,year,branch,track,week1,week2,week3,week4,week5
 from jsonb_to_recordset(records) as r(sic text,full_name text,email text,contact text,gender text,year integer,branch text,track text,week1 numeric,week2 numeric,week3 numeric,week4 numeric,week5 numeric)
 on conflict(sic) do update set full_name=excluded.full_name,email=excluded.email,contact=excluded.contact,gender=excluded.gender,year=excluded.year,branch=excluded.branch,track=excluded.track,week1=excluded.week1,week2=excluded.week2,week3=excluded.week3,week4=excluded.week4,week5=excluded.week5;
$$;
revoke all on function public.import_participants(jsonb) from public,anon,authenticated;
grant execute on function public.import_participants(jsonb) to service_role;

-- AchieveX Achievement Badges System
create table if not exists public.badge_definitions (
 id text primary key,
 name text not null,
 icon text not null,
 description text not null,
 category text not null check (category in ('ranking','milestone')),
 criteria text not null,
 image_url text not null
);

create table if not exists public.student_badge_awards (
 student_sic text not null references public.participants(sic) on delete cascade,
 badge_id text not null references public.badge_definitions(id) on delete cascade,
 award_date text not null,
 qualifying_exam_id text not null default '',
 evidence text not null default '',
 is_active boolean not null default true,
 primary key (student_sic, badge_id, qualifying_exam_id)
);

create index if not exists idx_student_badge_awards_student on public.student_badge_awards(student_sic);
create index if not exists idx_student_badge_awards_badge on public.student_badge_awards(badge_id);

alter table public.badge_definitions enable row level security;
alter table public.student_badge_awards enable row level security;
revoke all on public.badge_definitions, public.student_badge_awards from anon, authenticated;
grant all on public.badge_definitions, public.student_badge_awards to service_role;

insert into public.badge_definitions (id, name, icon, description, category, criteria, image_url) values
 ('the-main-character', 'The Main Character', '👑', 'Overall AchieveX champion with the highest cumulative performance across weekly exams.', 'ranking', 'Highest average percentage across all eligible, finalized exams (all published exams required).', '/assets/badges/the-main-character.png'),
 ('the-ace', 'The Ace', '⚡', 'Highest scorer in an individual weekly exam.', 'ranking', 'Attain the highest normalized score in an individual weekly exam.', '/assets/badges/the-ace.png'),
 ('the-glow-up', 'The Glow Up', '📈', 'Biggest improvement compared with the previous weekly exam.', 'ranking', 'Greatest positive improvement in percentage points between consecutive finalized weekly exams.', '/assets/badges/the-glow-up.png'),
 ('on-fire', 'On Fire', '🔥', 'Consistently scores at least 80% across three consecutive weekly exams.', 'milestone', 'Score 80% or higher in any three consecutive finalized weekly exams.', '/assets/badges/on-fire.png'),
 ('flawless', 'Flawless', '💎', 'Achieved a perfect score in a weekly exam.', 'milestone', 'Achieve a perfect 100% score in any verified weekly exam.', '/assets/badges/flawless.png'),
 ('the-comeback-arc', 'The Comeback Arc', '🚀', 'Makes a remarkable recovery after a low scoring exam.', 'milestone', 'Score strictly below 50% in one exam and improve by at least 20 percentage points in the next exam.', '/assets/badges/the-comeback-arc.png'),
 ('the-unlocked-five', 'The Unlocked Five', '🔒', 'Participated in all five required weekly exams.', 'milestone', 'Complete verified participation or submission across all five designated championship exams.', '/assets/badges/the-unlocked-five.png')
on conflict (id) do update set
 name = excluded.name,
 icon = excluded.icon,
 description = excluded.description,
 category = excluded.category,
 criteria = excluded.criteria,
 image_url = excluded.image_url;

