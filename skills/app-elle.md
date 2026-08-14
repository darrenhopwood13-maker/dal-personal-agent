---
name: app-elle
description: Elle Inventory Solutions: the four report modes, photo grouping logic and strict report format rules.
---

# App: Elle Inventory Solutions

Use when: reading or writing anything to do with Elle Inventory Solutions, the
property inventory app, or inventory / check-in / check-out / update reports.

## What it is

Property inventory SaaS for Dal's mother's business. The whole point is removing
manual work — she currently uploads photos, dictates reports and types them up. The
app should leave her doing none of that.

Branded for Elle Inventory Solutions. Visual language is minimalist "quiet luxury"
editorial. Not construction-styled, not the instructSite palette.

## Four report modes

| Mode | Compares against |
|---|---|
| Inventory | Nothing — it's the baseline |
| Check In | The existing Inventory, reviewed with the new tenant present |
| Check Out | The existing Inventory for that property |
| Update | The most recent report of **any** type for that property |

Two rules people get wrong:

- **Check Out is built from the existing Inventory**, not generated from scratch. It
  starts from the baseline and adds check-out condition and comments against it.
- **A second Update compares against the first Update**, not the original Inventory.

**Check In disagreements:** when a tenant disagrees with an item, record both
positions side by side — the original inventory position and the tenant's position.
Do not flag it for resolution. Do not pick one. Do not average them.

## Photo grouping logic

A room starts with 3 wide-angle shots. Every photo after that belongs to that room
until the next set of 3 wide shots begins a new room.

## Room decks

- AI identifies each item (what it is, colour, condition) and auto-allocates it to a
  room-based scrollable deck — toaster goes to the kitchen deck.
- Items that could plausibly belong to more than one room go to an **unallocated**
  deck for manual allocation. Don't guess to avoid the unallocated deck.
- Every photo/AI result in a deck can be opened, edited, deleted or moved to another room.
- The user can always overwrite an AI response. Manual items (photos + details) are
  added on a separate page.

## Per-photo box format — strict

Show **only** the photo number and the item description. That's it.

Do not include:
- a status badge ("Damaged / Patch Required", "Intact / No Action")
- a "Finding:" prefix
- a Severity line
- a Fix line

Descriptions must not begin with: **A, The, They, their, there.**

## Cover page

Title, "Property Inventory", date, prepared-by, a small cropped property photo, and
the client logo in the footer.

## Report layout

1. Title page
2. Contents page
3. Then each room, **landscape**: the room's 3 wide-angle photos across the top of the
   page, each item photo + inventory info below, fitting as many photos per page as
   possible without shrinking them too much.

Reports must be editable in Word, downloadable and shareable.

## Property files

- The property file is created by the user **before** photos are uploaded.
- Address-book-style search by property address. Every property is saved to the
  backend (Supabase) until recalled.
- On recall, the user chooses which of the four report types to view.
- The property card carries a status identifier — e.g. "Awaiting Check In",
  "Check Out Booked", "In Tenancy".

## Architecture note

Uses instructBrain-style separate AI "brains" per report type, uploaded by Dal over
time. A new report type should be a new brain, not new branching logic.
