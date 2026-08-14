---
name: app-instructbrain
description: instructBrain / instructsurvey / site-sentinel / V4: invariants, survey types, architecture and branding.
---

# App: instructBrain

Use when: reading or writing anything to do with instructBrain, instructsurvey,
site-sentinel, the V4 merge, or the instructReport Supabase project.

## What it is

AI-powered construction report generator. Photos in, client-ready reports out.
Live at instructbrain.com. Sits in the Instruct suite as "An instructSite Company".
The working name "Report Ready" is retired — don't use it in code, copy or commits.

## Current shape

- Three report types only: **Site Walk**, **Snag Identifier**, **Weatherproofing survey**.
  Don't add a fourth without being asked. "Site condition report" is a banned label —
  it collides with condition survey in UK usage.
- Fire-stopping / compartmentation was deliberately dropped as too dangerous to
  automate. If you see it in old code or docs, it's dead — don't revive it.
- Supabase project `instructReport`, ref `krwphsejinmlwvtwugwk`, eu-west-2.
- Built on TanStack Start. Not connected to Lovable Cloud — it uses the external
  Supabase deliberately. Don't propose wiring it to Lovable Cloud.
- Pricing is in reports, not tokens: 3 free, £49/mo for 10, £99/mo for 30, custom above.
- Stripe not connected yet.

## Core architecture decision

**Survey Type Definitions.** Discipline-specific statuses, capture fields, AI guidance,
severity scales, trades and output sections are all held as data (jsonb) against a
generic engine. New disciplines are data, not code.

If a change adds a hardcoded `if surveyType === 'weatherproofing'` branch, it's wrong.
Push the difference into the definition.

## Invariants — a change that breaks one of these is a failed change

1. AI failure sets `not_assessed`. Never a passing status. `not_assessed` is
   first-class and blocks export.
2. Status ids come from `survey_type_snapshot`, not from live config.
3. Images are persisted from day one. No ephemeral upload paths.
4. Full-resolution images (1500px+) go to the AI. Never the thumbnail.
5. Reference IDs are stable and never recomputed once issued.
6. No cross-discipline text leakage between survey types.
7. Trade attribution is always a human-confirmed suggestion. Nothing is ever sent
   automatically.
8. People in photos are handled confidentially — face blurring, supervisor-only path.

The canonical list lives in the Lovable project knowledge block. If your reading of
one conflicts with that, the knowledge block wins — flag the conflict.

## Production requirements easily forgotten

- HEIC handling. Golden-set photos came off Android, but users are on iPhones.
- Server-side PDF rendering, not client-side.
- RLS with SECURITY DEFINER role checks on every table.
- Private storage bucket for report photos. Never public.

## Branding

Match instructSite exactly: blue, orange and white, dark navy console styling.
Blue/purple was tried on 6 Aug and reverted the same day — don't reintroduce it.

## UI direction

- The three action buttons (Project report / Quick report / My reports) live on the
  authenticated dashboard, not the landing page.
- Selecting a mode *reveals* the three survey types rather than showing everything at
  once — built for one-handed thumb reach.
- Explanatory text is stripped from app screens. Short silent how-to clips sit behind
  a persistent Help button instead. Don't add instructional paragraphs to screens.

## Open questions — don't invent answers

- What a "Quick report" actually is: whether it can later attach to a project,
  whether it supports distribution.

## V4 merge context

V4 is a merge of three existing builds — `instructbrain`, `instructsurvey`,
`site-sentinel` (all under github.com/darrenhopwood13-maker) — into one app, built as
a fresh Lovable project against a new GitHub repo, with GitHub as source of truth and
one consolidated Supabase project. It is not a fourth separate app.

`site-sentinel` has had a live `.env` committed. Treat everything in that repo's
history as compromised until Dal confirms rotation.
