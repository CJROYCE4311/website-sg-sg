
import pandas as pd
import numpy as np

class GolfTournamentAnalyzer:
    def __init__(self, course_data_file, tees_rating, tees_slope, tees_par):
        """
        Initialize with course details.
        course_data_file: CSV with columns 'Hole', 'Par', 'HI' (Stroke Index)
        """
        self.course = pd.read_csv(course_data_file)
        self.rating = tees_rating
        self.slope = tees_slope
        self.par = tees_par

    def calculate_course_handicap(self, index):
        """Calculates Course Handicap using WHS formula."""
        if pd.isna(index) or index == '':
            return 0
        val = float(index) * (self.slope / 113) + (self.rating - self.par)
        return int(round(val))

    def calculate_net_score(self, gross, hole_si, course_handicap):
        """Calculates single hole net score."""
        strokes = course_handicap // 18
        remainder = course_handicap % 18
        
        # Stroke Allocation
        if remainder >= hole_si:
            strokes += 1
            
        return gross - strokes

    def analyze_player(self, player_name, handicap_index, gross_scores_1_to_18):
        """
        Analyzes a single round or average of rounds for a player.
        gross_scores_1_to_18: Dictionary or List of gross scores {1: 4, 2: 5...}
        """
        ch = self.calculate_course_handicap(handicap_index)
        
        results = []
        
        # Ensure scores is a dict keyed by hole number
        if isinstance(gross_scores_1_to_18, list):
            scores = {i+1: s for i, s in enumerate(gross_scores_1_to_18)}
        else:
            scores = gross_scores_1_to_18

        total_gross = 0
        total_net = 0
        
        for h in range(1, 19):
            hole_info = self.course[self.course['Hole'] == h].iloc[0]
            par = hole_info['Par']
            si = hole_info['HI']
            
            gross = scores.get(h, 0) # Handle missing
            net = self.calculate_net_score(gross, si, ch)
            net_diff = net - par
            
            total_gross += gross
            total_net += net
            
            results.append({
                'Hole': h,
                'Par': par,
                'SI': si,
                'Gross': gross,
                'Net': net,
                'Net +/-': net_diff
            })
            
        return {
            'Player': player_name,
            'CH': ch,
            'Total Gross': total_gross,
            'Total Net': total_net,
            'Net +/-': total_net - self.par,
            'Hole Data': results
        }

# Example Usage Block (can be copied to your own script)
if __name__ == "__main__":
    # 1. Setup
    # Ensure you have 'Sterling_Grove_Course_Data.csv' available
    analyzer = GolfTournamentAnalyzer(
        '40-Recreation/Sterling_Grove_Course_Data.csv', 
        tees_rating=70.5, 
        tees_slope=124, 
        tees_par=72
    )

    # 2. Example Data (Simulating a player in your tournament)
    sample_player = "Jim Smith"
    sample_hi = 15.4
    # Jim's Scores for holes 1-18
    sample_scores = [5, 5, 4, 6, 5, 5, 3, 5, 6, 5, 6, 5, 4, 5, 5, 5, 4, 6] 

    # 3. Run Analysis
    report = analyzer.analyze_player(sample_player, sample_hi, sample_scores)

    # 4. Output
    print(f"Player: {report['Player']} (CH: {report['CH']})")
    print(f"Gross: {report['Total Gross']} | Net: {report['Total Net']} ({report['Net +/-']:+})")
    print("-" * 40)
    print(f"{'Hole':<5} {'Par':<5} {'Gross':<8} {'Net':<8} {'Net +/-':<8}")
    for row in report['Hole Data']:
        print(f"{row['Hole']:<5} {row['Par']:<5} {row['Gross']:<8} {row['Net']:<8} {row['Net +/-']:<+8}")
