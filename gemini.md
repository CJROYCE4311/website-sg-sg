# Project: SG@SG Website Automation

## 🧠 Memory & Context
- **User:** Chris Royce (Wife: Miki).
- **Project:** Golf Tournament Dashboard (SG@SG).
- **Workflow:** **Screenshots -> AI Extraction -> Python Pipeline -> Netlify**.
- **Key Constants:**
    - Course Rating: 70.5
    - Slope: 124
    - Par: 72
- **Data Conventions:**
    - Plus Handicaps are stored as **NEGATIVE** numbers (e.g., -1.7).
    - Excel Column: `HI` or `Handicap`.
    - Script Lookback: 13 Months.
- **Data Schema:** `scores.csv` includes `Partner`, `Team_Rank`, and `Individual_Rank`.
- **Visuals:** PlayerStats uses a Green/Yellow/Red gauge segment system.

## ✅ Completed Tasks
- [x] Standardized `update_site.py` to handle `HI`/`Handicap` columns.
- [x] Implemented 13-month lookback filter.
- [x] Implemented "Handicap Analysis" logic (Best 3/6 Implied Index).
- [x] **Refined "Handicap Detail":** Gap = `Diff - Index`. Red/Bold = Beat Index (Audit Alert).
- [x] **Fixed:** `index.html` regex logic to prevent duplicate "Latest Results" blocks.
- [x] Updated SOP to reflect Image-based workflow.
- [x] **Backfill:** Backfilled Team/Rank/Partner data for Nov 2025, Dec 2025, Jan 2026.
- [x] **Pipeline:** Implemented `upsert` and `batch` logic in `ingest_data.py`.
- [x] **Data Hygiene:** Normalized player names (Mc/Mac) and merged duplicate records.
- [x] **UX:** Enhanced PlayerStats visualization (3-segment gauge).
- [x] **Fix:** Fixed Index.html 'Latest Results' layout and duplicate Log entries.

## 📋 To-Do / Backlog
- [ ] **Monitor:** Watch for name duplication in future ingests (auto-normalization feature?).
- [ ] **Feature:** Add specific "Most Improved" badge to the Analysis page?