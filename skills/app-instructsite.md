---
name: app-instructsite
description: instructSite, instructSiteEnterprise and ScopeGuard: features, demo assets and taxonomy rules.
---

# App: instructSite

Use when: reading or writing anything to do with instructSite, instructSiteEnterprise,
ScopeGuard, or the wider Instruct suite structure.

## What it is

B2B construction SaaS. Automates subcontractor weekly compliance packs, risk
assessments and technical drawing analysis. instructSite is the parent brand —
instructBrain sits under it as "An instructSite Company".

Branding: blue, orange and white. instructBrain matches this exactly, so a palette
change here is a change to both. Don't make one unilaterally.

## instructSiteEnterprise

Lovable project. Test project is Willow Bank House.

Live feature area: short-term programmes — PM seats, upload/accept/lock flow, private
programmes, a 5-cap, and a PM-seat gate. If you touch programme code, check all five
of those still hold.

## Demo and onboarding assets — don't break these

A full rehearsal environment exists and doubles as source material for the onboarding
manual:

- Test project "Kingsgate House — CAT A/CAT B Office Refurbishment", org Hopwood
  Construction
- 4 subcontractors (strip-out, steelwork, M&E, plastering) plus project admin, site
  manager and QS
- All on `darrenhopwood13+label@gmail.com` style addresses
- A live in-app guided tour: floating "Start Tour" button, spotlight highlights on
  real buttons, no zoom or pan
- An onboarding manual, both standalone and in-app at `/manual`

Treat the tour and `/manual` as production surfaces. A change that moves or renames a
button breaks the tour's spotlight targets — check and update both together.

## ScopeGuard

Separate product, not a feature of instructSite. UK construction scope-gap detection SaaS.

Non-negotiables:
- **Uniclass codes as the shared taxonomy.** Never free text. This is what makes the
  later handoff possible.
- Built as its own Lovable/Supabase product with its own login.
- Sold later as a paid instructSiteEnterprise add-on via a **token-based data handoff**,
  not a shared login. Don't propose SSO or a merged auth model.
- Phase 0 scope: Uniclass-seeded schema, document ingestion, citation-backed gap and
  conflict detection. Detection must cite its source — an uncited gap is a bug.

The Phase 0 build brief is written and waiting on Lovable credits in the instructBrain
workspace. Check credits before proposing work there.

## Suite-level rules

- One Supabase project per product. Don't cross-wire databases between Instruct products.
- Product names in code and copy: instructSite, instructSiteEnterprise, instructBrain,
  ScopeGuard. Never "Report Ready".
