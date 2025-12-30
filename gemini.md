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

## ✅ Completed Tasks
- [x] Standardized `update_site.py` to handle `HI`/`Handicap` columns.
- [x] Implemented 13-month lookback filter.
- [x] Implemented "Handicap Analysis" logic (Best 3/6 Implied Index).
- [x] **Refined "Handicap Detail":** Gap = `Diff - Index`. Red/Bold = Beat Index (Audit Alert).
- [x] **Fixed:** `index.html` regex logic to prevent duplicate "Latest Results" blocks.
- [x] Updated SOP to reflect Image-based workflow.

## 📋 To-Do / Backlog
- [ ] **Monitor:** Ensure next month's screenshots are processed correctly by the Agent.
- [ ] **Feature:** Add specific "Most Improved" badge to the Analysis page?