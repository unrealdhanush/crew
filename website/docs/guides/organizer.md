---
title: Publish an event
sidebar_position: 1
description: Organizers publish the agenda and print NFC/QR stickers for the session doors.
---

Organizers do two things: publish the agenda, so teams can be matched against it, and put a sticker on each
session door, so attendees can tap in.

## Publish the agenda

1. Open `/organizer`.
2. Enter the event name and the agenda page URL(s), one per line.
3. Click **Publish agenda**.

Crew scrapes each page with Bright Data, has OpenAI extract the sessions (title, time, room, speakers, topics and
the packages each session is about), and writes them to the graph. The progress feed lists each session as it's
written. If teams have already signed up, their plans are recalculated.

**Use sample agenda** loads four made-up sessions from `data/agenda.sample.json` instead, with no keys needed.

:::note Verification
Tested on Oct 24 with GitHub Universe 2026: two GitHub blog schedule posts gave 19 real sessions with speakers and
topics, and a real team's plan connected through `mcp`, `agents`, `github-actions` and `supply-chain-security`.
Scraped pages are cached for 6 hours (`WEB_CACHE_SECONDS`), so a second publish works even if the venue network drops.
:::

### Choosing agenda URLs

Point Crew at pages whose session details are in the HTML. Session catalogs that render in the browser (such as
GitHub Universe's RainFocus catalog) return only their navigation to a plain fetch, so Crew finds no sessions there.
Published schedule posts and static agenda pages work well. For GitHub Universe 2026, click **GitHub Universe 2026**
under the buttons to fill in the two schedule posts from the GitHub blog. Times and rooms are only filled in when the
page lists them.

The CLI equivalents are `crew agenda <url>... [--fresh]` and `crew agenda-file data/agenda.sample.json`.

## Print door stickers

Open `/stickers`. There's one sticker per session with the event name, title, time and room, a QR code, and the URL
to write to an NFC tag. Each URL opens `/tap?s=<session id>`.

1. Set **Address phones will open**. Phones can't reach `127.0.0.1`, so for real stickers start Crew with
   `CREW_HOST=0.0.0.0` and enter the laptop's network address, e.g. `http://192.168.1.20:8765`.
2. Click **Print**. The sheet prints two stickers per row with cut lines.
3. Write each URL to an NFC tag with any NFC writer app, and stick it on the door with its card.

:::note
QR codes are drawn by a library loaded from cdnjs. Without internet the sheet still prints, with the URL only.
:::

## Check it worked

The home page counts sessions, and `/team` stops showing its "No agenda has been published yet" banner.
