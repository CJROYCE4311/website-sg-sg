# Golf Performance Analysis Methodology
**Purpose:** To evaluate player performance relative to their handicap on a hole-by-hole basis.

## 1. Data Requirements
To reproduce this analysis for any player, you need:
*   **Player Info:** Handicap Index (HI).
*   **Course Info:** Course Rating, Slope Rating, Par (Total), and Hole-by-Hole "Stroke Index" (the 'HCP' row on scorecard).
*   **Score Data:** Gross score for each hole.

## 2. The Algorithm

### Step A: Calculate Course Handicap (CH)
Determine how many strokes the player receives for the specific set of tees.
*   **Formula:** `CH = (Handicap Index * (Slope / 113)) + (Course Rating - Par)`
*   **Rounding:** Round to the nearest whole number (.5 rounds up).

### Step B: Allocate Strokes (Net Score Calculation)
Distribute the Course Handicap strokes across the 18 holes based on the course's Stroke Index (SI).
1.  **Base Strokes:** Every player gets `CH // 18` strokes per hole (e.g., a 20 handicap gets 1 stroke on every hole automatically).
2.  **Extra Strokes:** Calculate the remainder `CH % 18`. The holes with a Stroke Index less than or equal to this remainder get +1 extra stroke.
    *   *Example:* A 20 Handicap gets 1 stroke everywhere. The remaining 2 strokes (20-18) go to hole SI #1 and SI #2.
3.  **Calculate Net Score:** `Net Score = Gross Score - Strokes Received`

### Step C: Performance Metrics
Compare the Net Score to the Hole Par.
*   **Metric:** `Net Differential = Net Score - Hole Par`
    *   **0 (Even):** Player played exactly to their handicap.
    *   **Negative (-):** Player beat their handicap (Net Birdie/Eagle).
    *   **Positive (+):** Player played worse than handicap (Net Bogey+).

### Step D: Aggregation (The Report)
For a tournament or multi-round analysis:
1.  **Avg Gross:** Sum of Gross Scores / Number of Rounds.
2.  **Avg Net:** Sum of Net Scores / Number of Rounds.
3.  **Net +/-:** `Avg Net - Par`.

## 3. Interpretation Key
*   **<-0.5:** **Major Strength.** The player dominates this hole.
*   **-0.5 to +0.5:** **Neutral.** Expected performance.
*   **>+0.5:** **Weakness/Leak.** The player is losing strokes here relative to their potential.

---

## Python Implementation
(See accompanying script `tournament_analyzer.py` for the code to run this on your tournament data).
