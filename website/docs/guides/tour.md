---
title: Take the guided tour
sidebar_position: 0
description: A spotlight walk through the app that highlights each button and field you need, from publishing an agenda to a tap check-in.
---

The tour dims the page and rings the real button or field it's explaining, with a short note beside it. It takes about
a minute and walks through the pages in the order you'd use them.

## Start it

- Choose **Tour** in the top bar, on any page. It starts at the first step of the page you're on.
- On the home page, choose **Take the 1-minute tour**.
- Add `?tour=1` to any page address, for example `/team?tour=1`. This is handy for sharing a link to a specific page's tour.

## What it covers

| Page | What it highlights |
|---|---|
| Home | Where to start, the setup status and its next-step button, and the example questions |
| Organizer | Event name, agenda links, **Publish agenda**, the sample agenda, and the live graph |
| Door stickers | The address phones open, **Print stickers**, and the sticker sheet |
| Team | Team name, adding a teammate, **Find repos**, private repos, **Build the team graph**, and the live graph |
| Tap demo | Choosing a phone, tapping a door, the check-in screen, and the highlighted path |
| Graph | The colour legend, bridges versus everything, and the latest answer |

The last step of each page reads **Next: \<page\>** and carries on to that page.

## Controls

| Action | How |
|---|---|
| Next or back | **Next** and **Back**, or the right and left arrow keys |
| Leave the tour | **Skip tour**, or **Esc** |
| Finish | **Finish** on the last step, or **Next** through the whole walk |

While the tour is open the rest of the page is switched off, so clicks and Tab stay inside the tour card. On a phone
the card sits at the bottom of the screen and the highlighted item scrolls into view above it.

Where you are in the tour is kept in the browser, which is how it follows you from page to page. If the browser blocks
storage, the next page still starts its own tour. Leaving the tour with **Skip tour** or **Esc** forgets your place.

If a step's target isn't on the page (for example, you removed it), the tour shows the note in the middle of the
screen without a highlight.

## Change the steps

The steps live in `web/tour.js`, in the `PAGES` list: a page path, a name, and steps with a CSS selector, a title and
the text. `crew.js` loads the file only when the tour starts, and `crew/server.py` lists it in `ASSETS`.

:::note Verification
Tested on Oct 24 in a browser against a stand-in for the Crew API, at desktop and phone sizes: every step's highlight,
moving between pages, **Back** across a page boundary, **Esc**, the arrow keys, Tab staying inside the card, blocked
browser storage, an empty graph, and a missing target. It has not been run against a live `crew serve` with FalkorDB.
:::
