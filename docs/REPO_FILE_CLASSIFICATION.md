# Repo File Classification

This document classifies the current repo contents by operational importance so cleanup can happen safely.

## Classification Legend

- **Keep: Canonical**
  - Source of truth for current operations.
- **Keep: Active Pipeline**
  - Required for ingest, validation, rebuild, or current runbooks.
- **Keep: Static Site Support**
  - User-facing site pages that are not regenerated from data each run.
- **Keep: Shared Agent Policy**
  - One tool-agnostic entry point for agent behavior and repo workflow.
- **Keep: Generated Output**
  - Reproducible from canonical data and scripts.
- **Keep: Historical Reference**
  - Useful context, but not part of the active runtime path.
- **Cleanup Candidate**
  - Likely redundant, stale, tool-specific, or superseded.

## Keep: Canonical

These are the operational source-of-truth files.

- `data/scores.csv`
- `data/financials.csv`
- `data/handicaps.csv`
- `data/course_info.csv`
- `data/tournaments.csv`
- `data/team_pairings.csv`
- `data/score_audit_exceptions.csv`
- `data/player_aliases.json`

## Keep: Active Pipeline

These drive the current local workflow.

- `AGENTS.md`
- `README.md`
- `INSTRUCTIONS.md`
- `docs/SGSG_Monthly_Tournament_Runbook.docx`
- `docs/SQUABBIT_CSV_IMPORT.md`
- `docs/CODEX_WORKFLOW.md`
- `docs/tournament_data.template.json`
- `scripts/import_squabbit_csv.py`
- `scripts/ingest_data.py`
- `scripts/process_tournament.py`
- `scripts/update_site.py`
- `scripts/audit_canonical_data.py`
- `scripts/generate_methodology_data.py`
- `scripts/convert_json_to_js.py`

## Keep: Static Site Support

These are active site shells or support pages and are linked from current pages.

- `website/index.html`
- `website/AdminPortal.html`
- `website/MethodologyReport.html`
- `website/HandicapProposal.html`
- `website/HandicapProbability.html`
- `website/assets/Sterling Grove Flag.png`
- `website/assets/IMGGolfCourse.jpeg`
- `website/assets/SG-SG Map.png`
- `website/assets/IMG_Sign-Ups.png`

## Keep: Shared Agent Policy

Use one shared, tool-agnostic repo policy instead of separate assistant-specific runbooks.

- `AGENTS.md`

## Keep: Generated Output

These are current outputs regenerated from canonical data.

- `website/DataAudit.html`
- `website/MoneyList2025.html`
- `website/MoneyList2026.html`
- `website/HandicapAnalysis.html`
- `website/Handicap_Detail.html`
- `website/PlayerStats.html`
- `website/AverageScore.html`
- `website/HoleIndex.html`
- `website/results_2025-11-15.html`
- `website/results_2025-12-20.html`
- `website/results_2026-01-17.html`
- `website/results_2026-02-21.html`
- `website/results_2026-03-21.html`
- `website/data/methodology_data.json`
- `website/data/methodology_data.js`

Notes:

- These should be treated as rebuildable outputs, not hand-authored operational docs.
- If you later want a leaner repo, these are good candidates for “generated on demand” policy decisions, but do not remove them until that policy is explicit.

## Keep: Historical Reference

These still provide useful context, especially for model rationale and handoff history, but they are not in the active runtime path.

- `archive/README_2026-03-25.md`
- `archive/2026-01-18_Handicap_Model_Analysis.md`
- `archive/2026_Handicap_Model_Report.pdf`
- `archive/Tournament_Analysis_Methodology.md`
- `archive/2025-12-27_Legacy_Python1.md`
- `archive/2025-12-27_Legacy_Python2.md`
- `docs/SOP_SG-SG.md`
- `docs/WORKFLOW_VISUAL.html`

Recommended action:

- Keep them in `archive/` so the repo root stays focused on active operational files.

## Cleanup Candidate

No immediate cleanup candidates remain in the active repo root.

Future policy decisions may still include:

- whether tracked generated website files should remain committed, or shift to a rebuild-on-demand model
- whether archived historical materials should eventually move to a separate history repo

## Local-Only / Ignore Area

These are important operationally but should remain local rather than being treated as durable repo assets.

- `input/`
  - Working area for Squabbit reconciliation reports, reviewed payloads, local WHS identity maps, raw CSV archives, screenshot fallbacks, and ingest history.
- `venv/`
  - Local Python environment.
- `SESSION_HANDOFF.md`
  - Local-only handoff note file, already gitignored.
- `.DS_Store`
  - Local OS metadata.

## Recommended Cleanup Order

This is the safest order for cleanup.

1. **Consolidate duplicate workflow docs**
   - Decide whether `README.md`, `AGENTS.md`, and `docs/CODEX_WORKFLOW.md` should all remain first-class.
   - My recommendation: keep all three, but make each purpose explicit:
     - `README.md`: operator quick start
     - `AGENTS.md`: repo policy and guardrails
     - `docs/CODEX_WORKFLOW.md`: compact detailed workflow

2. **Archive top-level historical analysis files**
   - Move:
     - `archive/README_2026-03-25.md`
     - `archive/2026-01-18_Handicap_Model_Analysis.md`
     - `archive/2026_Handicap_Model_Report.pdf`
     - `archive/Tournament_Analysis_Methodology.md`
   - Suggested destination: `archive/` or `docs/history/`

3. **Retire tool-specific entry docs**
   - Completed:
     - removed `CLAUDE.md`
     - removed `gemini.md`
   - Current policy:
     - use `AGENTS.md` as the canonical agent policy and workflow pointer.

4. **Retire legacy utilities**
   - Completed:
     - removed the standalone migration and analysis helpers that are not part of the live workflow
   - Result:
     - the active repo now contains only the current operational path plus a small set of historical reference documents

5. **Decide generated-output policy**
   - Either:
     - keep generated website files tracked, or
     - move toward a “rebuild on demand” model later.
   - Do not change this until you explicitly choose the policy.

## My Current Recommendation

If the goal is a cleaner operational repo without changing behavior:

- **Keep** all canonical data, active pipeline scripts, current workflow docs, static site support pages, compatibility pointer docs, and generated site outputs.
- **Archive** the historical analysis, handoff files, and legacy utilities so the repo root stays focused on the live workflow.
- **Decide later** whether generated outputs should remain tracked or move to a rebuild-on-demand policy.
