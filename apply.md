---
description: Tailor a resume for a job posting URL, compile the PDF, and log it to applications.md
---

The user gives a job-posting URL (or pasted JD text) as: $ARGUMENTS

Run this pipeline:

1. **Fetch the JD.** WebFetch the URL (fall back to `curl -sL` if blocked).
   Extract: company, exact role title, location, cycle/season, required
   qualifications, preferred qualifications, any short-answer/essay questions.
   **Confirm the cycle is Summer 2027** before going further — if the posting is
   another cycle, say so and stop rather than tailoring for the wrong one.

2. **Load context.** Read `applications.md` (any integrity notes at the top are
   binding) and skim the relevant parts of `career-history.md`.
   **NEVER fabricate metrics, titles, dates or claims.** If a preferred
   qualification is almost-true, tell John the small concrete task that would
   make it true instead of writing it as though it already is.

   Style rules: keep bullets to exactly one or exactly two rendered lines,
   plain human voice, no filler. If `writing-style.md` exists in the repo, its
   rules override these — read it first.

3. **Pick the base resume** from `resumes/` by lane: `swe`, `ai-ml`, `cyber`,
   `quant`, `startup`. Ask John only if genuinely ambiguous. For a
   high-priority role, confirm the local `.tex` is current — his editor copy may
   be ahead of the repo.

4. **Tailor with minimal targeted edits** — reorder, bold, and swap bullets
   rather than rewriting. Cover every preferred qualification that is truthfully
   claimable and **bold** those phrases. His strongest reusable material:
   RISEE Finance (nonprofit iOS financial-management app, Swift/SwiftUI, in
   beta, co-founder), Volee (iOS tennis matchmaking app, co-founder), Python GUI
   automation tooling built solo for engineering teams at John Deere and still
   in use, plus GreyHat / CP@GT / DIB Cyber Compliance VIP for the security and
   algorithms lanes. Pick the two or three that match the JD; don't cram in all
   of them.

   Save as `resumes/out/Dsouza_John_<Company>_<Role>.tex` — never overwrite the
   base version.

5. **Compile:** `tectonic <file>.tex` in `resumes/out/`. Fix LaTeX errors
   (common: a bare `&` must be `\&`). Verify it stays ONE page (`pdfinfo`, or a
   page count via python). Open the PDF for review.

6. **Report a coverage table:** each JD requirement / preferred qualification →
   where the resume now addresses it, or "gap (honest)" / "gap (30-min task
   would fix it)".

7. **Draft any short-answer/essay questions** in John's voice. Show them as
   drafts for his edit — never auto-submit prose.

8. **Check eligibility explicitly.** Many defense, national-lab and federal
   postings in this watcher require US citizenship, and some require an active
   clearance. Flag the requirement and let John confirm — do not assume a
   citizenship or clearance status on his behalf.

9. **Log it:** add or update the entry in `applications.md` with status
   `prepared`, the resume filename, the date, and any deadline found in the JD.
   When John later says "sent" / "applied", flip the status to `applied`.

10. **Hand off:** tell John the PDF path. If he wants wording changes he edits
    the `.tex` directly and says "recompile", or tells you the change.
