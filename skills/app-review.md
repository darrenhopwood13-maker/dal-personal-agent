---
name: app-review
description: Reviewing a whole application - UI, UX, functionality, code, database, security, performance, mobile, positioning. Load before any app or product review.
---

# App review

You are reviewing the whole application, not a screen. A review that only
comments on what's on the page in front of you is the review Dal can do
himself.

## Before you start

Ask for whatever you're missing, but only if it actually blocks you:
what the app is for, who pays for it, and where the source is. If you can
reach the repo, read it. If you can only see screenshots, say so up front and
scope the review honestly rather than guessing at the code.

## What to cover

Work through these. Skip any where you genuinely have nothing, and say why.

- **UI and visual hierarchy.** Does the eye land where the value is. Spacing,
  typography, contrast, consistency across screens.
- **UX, navigation and journeys.** Walk the actual journeys end to end. Where
  does a user stall, backtrack, or have to remember something the app should
  have held for them.
- **Functionality.** Does each feature do what it claims, and does it behave
  sensibly when the input is wrong, empty, huge, or offline.
- **Code and architecture.** Where source is available: structure, duplication,
  error handling, anything that will hurt at ten times the usage.
- **Database and data flow.** Schema sense, relationships, what happens to a
  record's history, what is recomputed that should be stored.
- **Security.** Auth, access control, what an authenticated user could reach
  that isn't theirs, secrets in the wrong place, unvalidated input.
- **Performance.** What's slow, what's slow *at scale*, what loads that
  needn't.
- **Mobile and responsive.** Assume site use: one hand, gloves, bright sun,
  bad signal. Thumb reach matters.
- **Positioning.** What is this competing with, and why would someone pick it.

## What to look for that others miss

- Features that exist but shouldn't. Unnecessary features cost maintenance,
  confuse users and dilute the pitch. Say which ones to cut.
- The missing thing. What would a real user reach for that isn't there.
- The gap between what the app does and what it says it does.

## Output

1. **Verdict.** Two or three sentences. Would you ship it, and what's the one
   thing standing in the way.
2. **Scorecard.** Each area above scored out of 10 with a one-line reason.
   No score without a reason.
3. **Prioritised fixes.** Ordered by impact over effort. For each: what's
   wrong, what to do, and what it buys. Small number of high-impact items
   beats a long list of cosmetic tweaks — that ordering is the point of the
   review.
4. **Cut list.** Anything to remove.

## After fixes

If Dal comes back saying something is fixed, re-check it rather than taking
his word for it. Report whether it's actually resolved, partly resolved, or
looks resolved but has moved the problem somewhere else. Never confirm a fix
you haven't verified.
