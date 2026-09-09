---
description: Tailor John's resume for a job posting, produce the PDF, and log it to applications.md
---

# /apply — how it works for John (chat version, .docx base)

John runs this in a Claude chat, not a terminal. He pastes a posting URL (or the
JD text) and, the first time in a session, attaches his base resume `.docx`.
Claude does the rest and sends back a tailored `.docx` + PDF.

**Inputs Claude needs in the session:**
- The job posting URL or pasted JD text
- The base resume `.docx` (attach it, or Claude reads it from the "Future"
  project if John has uploaded it there)
- `career-history.md` and `applications.md` — both private; John keeps them in
  the watcher folder (gitignored) or the Future project. If absent, Claude
  proceeds from the resume alone and says so.

## Pipeline

1. **Fetch the JD.** WebFetch the URL (fall back to the pasted text). Extract:
   company, exact title, location, cycle, required qualifications, preferred
   qualifications, any short-answer questions, and eligibility lines
   (citizenship, sponsorship, clearance, major, class year).
   **Stop if it's not Summer 2027** and say so.

2. **Load context.** Read `applications.md` (skip if already applied there)
   and `career-history.md` for the long-form facts and numbers.
   **Never fabricate** a metric, title, date, tool, or claim. If a preferred
   qualification is almost true, say what small task would make it true.

3. **Pick the lane** from the JD — `swe`, `ai-ml`, `cyber`, `quant`,
   `startup` — and use it to decide what moves up. There is one base resume;
   lane changes ordering and emphasis, not content.

4. **Tailor with minimal edits** to the `.docx` (use the docx skill):
   - Reorder sections/entries so the lane-relevant ones come first.
   - Swap in bullets from `career-history.md` that hit the JD's preferred
     qualifications; swap out the weakest bullets to keep one page.
   - Mirror the JD's own terms where they are truthfully applicable
     (e.g. "NIST 800-171", "incident response", "Core ML").
   - Keep John's style: every bullet 1–2 lines, plain voice, real numbers.
   - Do not touch the header, education block, or dates.
   Save as `Dsouza_John_<Company>_<Role>.docx`; export PDF; verify ONE page.

5. **Coverage table.** Each JD requirement / preferred qualification → where
   the resume now addresses it, or "gap (honest)" / "gap (30-min task fixes)".

6. **Draft short-answer questions** in John's voice, as drafts for his edit.
   Never submit anything.

7. **Eligibility check.** Restate every eligibility line from the JD
   (citizenship, sponsorship, clearance, major, class year, location) and let
   John confirm. Do not assume his status.

8. **Log it** in `applications.md` with status `prepared`, the filename, the
   date, and any deadline. When John says "applied", flip to `applied`.

9. **Hand off.** Send the `.docx` and PDF. John edits the `.docx` directly
   for wording changes and re-attaches, or tells Claude the change.

## Base resume facts (from the Sept 2026 general version)
GT CS, AI + Cybersecurity threads, Leadership Studies minor, May 2029, GPA 3.65.
Experience: Volee (co-founder, Jan 2026–), Biofilter intern (Budapest, summer
2026), Walmart. Projects: John Deere Python GUI tools, RISEE Finance,
Congressional Bill Outcome Predictor. Leadership: Study Abroad Peer Advisor,
DIB Cyber Compliance VIP, AI Safety Initiative Fellowship, CP@GT, GreyHat.
Details and extra bullets live in `career-history.md`.
