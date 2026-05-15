# Aqua Elya — Practical Shot List for Filming

Companion to `VIDEO_SCRIPT.md`. This is the day-of checklist: what to film, in what order, with what setup. Built around realistic constraints (one person, phone or laptop webcam, golden-hour Louisiana light).

---

## Before you press record

### Equipment checklist

- [ ] **Phone** for garden / hardware / talking-head shots (modern phone is fine — 1080p minimum, 4K if available)
- [ ] **Tripod or stable surface** for the talking-head shot (can improvise: stack of books, bench, etc.)
- [ ] **Laptop** with the dual-brain code working (verify with `python3 scada_loop.py --fast --once` before shoot day)
- [ ] **OBS Studio** installed for clean screen recording (preferred over GNOME Screen Recorder for higher-quality codec + multi-source flexibility)
- [ ] **External mic** if available (USB mic or even phone earbuds are better than laptop mic). If none, plan to record voiceover in a quiet room separate from the b-roll.
- [ ] **Lavalier or shotgun mic** if you have one (huge audio quality boost for talking-head)

### Pre-shoot prep (do this the day before)

- [ ] Run the dual-brain code once and screenshot the output. Make sure terminal text is large enough to read in 1080p video (font size 14-16 minimum)
- [ ] Pre-generate the 26B analyst output you want to show on-camera (it takes ~2 minutes to run live, too slow for video flow). Save the output as a text file you can `cat` on screen.
- [ ] Set terminal background to dark, high-contrast theme. Default macOS Terminal black or Linux black is fine.
- [ ] Tidy the area around your NFT system for the b-roll shots. Remove obvious clutter but DON'T over-stage — the authenticity is the point.
- [ ] Lay out the sensor components (flow meter, pH probe, ESP32, relay board) on a clean workbench surface. They can be in original packaging or unpacked — your call. Authentic > pristine.

---

## Shooting order (one day, ~3-4 hours total)

### Block 1 — Garden b-roll (golden hour, 6:30-7:30 PM Louisiana May)
~30 minutes

This is the hardest to schedule because you only get one golden hour per day. Do it FIRST so you don't miss the light.

- [ ] **Wide shot of the entire NFT system** — show the scale (108 cells, two reservoirs, channels). 5-10 seconds, slow pan.
- [ ] **Close-up of plants in the channels** — leaves, root structure visible through clear sections if your channels are translucent. 5-10 seconds.
- [ ] **Reservoir close-up** — water surface, pump submerged or visible inlet. 3-5 seconds.
- [ ] **Channel flow close-up** — actually film water flowing. The thin-film effect on roots is visually striking. 5 seconds.
- [ ] **Wide context shot** — you in frame with the system (for the talking-head bridge in Shot 5). 10 seconds.

Backup if golden hour is rained out: shoot at any daylight hour with overcast sky for diffuse light. Avoid harsh midday sun (creates ugly contrast).

### Block 2 — Hardware close-ups (any time, indoor)
~20 minutes

- [ ] **Sensor kit laid out on workbench** — pan slowly across each component as the voiceover names them (flow meter, pH probe, ESP32). 15-20 seconds total pan.
- [ ] **ESP32 in hand or close-up** — shows scale (it's tiny). 3-5 seconds.
- [ ] **Laptop running the code** — close-up of the screen showing terminal output. Combined with screen recording later. 5-10 seconds.

### Block 3 — Screen recording (any time, quiet room)
~30 minutes

OBS Studio settings: 1920×1080, 30fps, screen-region capture limited to your terminal window only (NOT full screen — keeps file size down and avoids accidentally showing personal info).

- [ ] **`scada_loop.py --fast --once` run** — one full cycle showing sensor read → Gemma function call → action. Record 2-3 takes for editing flexibility.
- [ ] **Pre-generated 26B analyst output** — `cat analysis_report.json | python3 -m json.tool` OR `cat /tmp/preformatted_analyst.txt`. Whatever looks cleanest. 15-20 second cat. Combined with read-aloud voiceover.
- [ ] **GitHub repo page** — open `https://github.com/Scottcjn/aqua-sophia` in browser, scroll slowly through README. 10-15 seconds. Use this for Shot 6.

### Block 4 — Talking-head (any time, quiet room)
~45 minutes (because re-takes)

- [ ] Set phone on tripod at eye level, ~3-4 feet from your face.
- [ ] Frame yourself with the NFT system visible in background (or use a simple background — plain wall, bookshelf, your IT workshop).
- [ ] Record Shot 5 ("Why It Matters") — read through 2-3 takes.
- [ ] Record bridge segments / pickup lines as needed.

If you're not comfortable on camera, swap talking-head for **voiceover-only**: record Shot 5 audio in a quiet room, edit over garden b-roll. Less personal but still effective.

### Block 5 — Audio cleanup (after all shots)
~30 minutes

- [ ] Listen back to all takes — flag clipping, background noise, mumbled words for re-record
- [ ] Re-record any voiceover lines that need fixing — this is faster than re-shooting video
- [ ] Note: voiceover doesn't need to perfectly match the original take's video. You can record fresh narration over existing video in the editor.

---

## Editing (Day 2)

Editor recommendation for Linux: **Kdenlive** (free, native, decent timeline editor). For more polish: **DaVinci Resolve free** (heavier, but professional-grade color + audio).

### Rough timeline structure

```
0:00–0:30   SHOT 1    Garden wide shot + you talking IN THE GARDEN (or VO over b-roll)
0:30–1:15   SHOT 2    Screen recording of scada_loop.py + your VO explaining
1:15–1:50   SHOT 3    Split-screen or sequential: E4B output, then 26B output, with VO reading the analyst
1:50–2:20   SHOT 4    Hardware pan + you holding laptop + cut to NFT system (per updated script)
2:20–2:50   SHOT 5    Talking head, NFT system in background
2:50–3:00   SHOT 6    GitHub repo page + end card
```

Total target: 2:55. Stay UNDER 3:00 — Kaggle entries cut off at the cap.

### Color / audio quick wins

- **Audio**: normalize all clips to -16 LUFS (Kdenlive: Audio Effects → Normalize)
- **Color**: bump saturation +10% on garden shots (makes plants pop), keep terminal screens neutral
- **Captions**: optional but adds accessibility. Auto-generate via Whisper (`whisper input.mp4 --language en --output_format srt`) then import into Kdenlive

---

## Common mistakes to avoid

- **Don't film vertically** if you can avoid it (Kaggle expects 16:9)
- **Don't try to record system audio + voice at the same time** — record them separately and mix in editing
- **Don't oversell deployment status** — the writeup is honest; the video should match
- **Don't film terminal text too small to read** — reviewers won't pause to squint
- **Don't forget to test export settings** — render a 30-second test before committing to the full final render

---

## Final upload

- [ ] Upload to YouTube as **Unlisted** (not Public — Kaggle expects unlisted)
- [ ] Title: "Aqua Elya — Gemma 4 Hydroponic SCADA (Kaggle Submission)"
- [ ] Description: short paragraph + GitHub link + brief tech stack list
- [ ] Get the URL → paste into your Kaggle submission form

Backup: Vimeo unlisted works equally well if YouTube is being slow on a deadline day.
