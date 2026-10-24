---
title: Tap in at a session
sidebar_position: 4
description: Check in with an NFC sticker or QR code and leave a one-line note.
---

Each session door has a Crew sticker holding `https://<crew>/tap?s=<session id>`. Phones open NFC URLs and QR codes
natively, so there's no app to install.

## What happens on a tap

1. The first time on a phone, Crew asks **Who are you?** and remembers the answer on that phone.
2. Crew records `Person -ATTENDED-> Session` and shows:
   - whether the session was on your plan, someone else's, or nobody's ("You just closed a blind spot"),
   - **why it matters to you**, as graph paths.
3. **One line from the room** saves a note about that session. Crew extracts the packages it mentions, fetches the
   release notes or docs, links them, and flags breaking changes with the repos and owners they affect.

The graph view lights up the check-in and, after a note, the note's links.

:::note Verification
Check-ins and notes, including fetching their sources through Bright Data, are tested.
:::

## Demo without stickers: `/sim`

`/sim` shows the doors, a phone and the live graph side by side. Pick whose phone it is, then click a door or press
**1–9**. The phone shows "Crew tag detected" and opens the same `/tap` URL a sticker would. Everything after the
tap is the real flow.

## From an agent

Saying "I'm in the MCP talk" to your TrueForge agent calls the `check_in` tool, which does the same as a tap.
