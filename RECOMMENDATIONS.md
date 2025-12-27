### 1) Recommendation

Refactor **yt-factory** from “generic compilation generator” into a **channel-driven publishing system**. Add channel profiles, conversion assets, and a minimal curation gate. Then add batch mode so you can run overnight without babysitting. 

---

### 2) Why this is the best move

Right now the pipeline optimizes for “it uploads.” Your actual business goals are: repeat listeners (brand consistency + correct format per channel) and app signups (CTAs everywhere, consistently), while keeping the factory stable (QC + batching). The current implementation has the right backbone (step-based, resumable, project.json), it just needs **productization around channels + funnel**. 

---

### 3) Execution plan

#### A. Make “Channel” a first-class concept (highest leverage)

**Deliverables**

* `channels/` directory with 6 configs: `fantasy_tavern.yaml`, `fantasy_reading.yaml`, `dnb_focus.yaml`, `lofi_study.yaml`, `cafe_jazz.yaml`, `sleep_ambience.yaml`
* Add `project.channel_id` + `project.intent` into `project.json` schema
* Update `ytf new` to require `--channel <id>` (or interactive pick)

**What goes into each channel profile**

* Default duration and track count rules (Sleep targets 8h, Jazz/Lo-fi 2–4h, Fantasy/DnB 60–120m)
* Prompt constraints (instrumental/vocals defaults, energy level, “no medical claims” enforcement for DnB Focus)
* Title templates (2–3 variants) and description template
* Tag whitelist + banned terms list (critical for policy risk)
* Thumbnail style preset (font, layout variant, safe words)
* Upload defaults: privacy, category, language, made-for-kids flag

**Agent implementation notes**

* Keep it boring. Load YAML into Pydantic models.
* Channel config drives `plan`, `render`, and `upload`. One source of truth.

#### B. Bake the app funnel into outputs (no more “add CTA later”)

**Deliverables**

* Generate these files in `output/` every run:

  * `youtube_description.txt` (already exists) but now templated + includes CTA block + UTM link placeholders
  * `pinned_comment.txt` (new) with 2 variants (short and long)
  * `shorts_script.txt` (optional, simple 5-line template to cut later)
* Add `project.funnel` section:

  * `landing_url`, `utm_source`, `utm_campaign`, `cta_variant_id`

**Behavior changes**

* `plan` step chooses a CTA variant from channel profile (A/B test friendly) and writes it into the funnel fields.
* Description always includes a “Use these mixes inside Focus Sessions” style CTA, channel-specific wording, and a single primary link.
* Don’t attempt comment pinning via API. Just output `pinned_comment.txt` and copy/paste. (You can automate posting a comment via API, but pinning is not reliably supported in the Data API docs, so keep it manual for now.) ([Google for Developers][1])

#### C. Add a curation gate + auto QC (prevents garbage uploads)

**Deliverables**

* New step: `review` (between generate and render)
* Support `approved.txt` and `rejected.txt` inside project folder
* Auto QC report: `qc_report.json` + `qc_report.txt`

**Auto QC checks (minimum viable)**

* Reject too-short tracks (e.g., < 60s or < configured min)
* Detect long leading silence (FFmpeg silencedetect)
* Reject corrupted downloads / missing audio
* Optional: loudness outliers (basic RMS/peak check, not perfect)

**Render behavior**

* If `approved.txt` exists, only use approved tracks.
* Else use “all OK tracks that pass QC.”
* If not enough tracks to hit target duration, fail fast with a clear error that says what’s missing.

#### D. Batch mode for throughput (overnight factory)

**Deliverables**

* `ytf batch --channel cafe_jazz --count 3 --mode full`
  Creates N projects then runs steps sequentially with resumability.
* `ytf run <project_id> --to upload` convenience command

**Behavior changes**

* Standardize retry/backoff across *all* provider calls (Gemini, Suno, YouTube). This is explicitly listed as missing today. 
* Batch runner logs summary: `batch_summary.json` with pass/fail per project.

#### E. Branding consistency without “visual overbuild”

**Deliverables**

* Thumbnail templates per channel (2 layouts max): “big title + small subtitle” variants.
* Lock typography and phrasing per channel config.
* Store channel brand assets under `assets/brand/<channel_id>/`

**Postpone**

* Runway intro, Creatomate title card. These are nice-to-haves until the funnel and batching are working. 

---

### 4) Success metrics

**Per channel (weekly)**

* Upload reliability: ≥ 95% of projects reach upload without manual fixes
* Output cadence: hit your target schedule (whatever you set) with batch mode
* Viewer signals: returning viewers, average view duration, and repeat listens (watch time per viewer)
* Funnel: description link CTR, app signup conversion rate, paid conversion rate (track via UTMs)

**Factory health**

* Median end-to-end runtime per project
* % tracks failing QC
* % projects blocked by “not enough approved tracks”

---

### 5) Risks + mitigations

**Risk: Monetization/policy hits from repetitive AI compilation patterns**

* Mitigation: channel profiles enforce variety within constraints (multiple title templates, multiple CTA variants, prompt variation). Add banned-term lists (especially “medical” terms for Focus). Keep “Focus” language non-medical.

**Risk: Uploading low-quality tracks kills retention**

* Mitigation: review step + QC. Fail fast if insufficient good tracks. Don’t “ship trash.”

**Risk: Overbuilding visuals instead of funnel + throughput**

* Mitigation: keep visuals to thumbnails + static background for now. Ship batching + CTA + QC first.

**Risk: API brittleness**

* Mitigation: unified retry/backoff, better error surfaces in `project.json.status.last_error`, batch summary for quick triage. 

---

### 6) Next actions (checklist)

* [ ] Add `channels/` configs (6 files) with duration rules, templates, banned terms, upload defaults
* [ ] Extend `project.json` schema: `channel_id`, `intent`, `funnel` section
* [ ] Update `ytf new` and `plan` to be channel-driven
* [ ] Implement `review` step with `approved.txt` + QC checks + reports
* [ ] Update `render` to honor approvals/QC and fail fast when underfilled
* [ ] Add `pinned_comment.txt` output + CTA variants + UTM fields
* [ ] Implement `ytf batch` + `ytf run --to`
* [ ] Standardize retry/backoff across all providers

If you want this to be easy for the Cursor agent, tell them to implement it in this order: **Channel profiles → Funnel outputs → Review/QC → Batch mode → Branding templates**.

[1]: https://developers.google.com/youtube/v3/docs/commentThreads/insert?utm_source=chatgpt.com "CommentThreads: insert | YouTube Data API - Google Developers"
