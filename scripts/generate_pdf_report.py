from fpdf import FPDF
import datetime

class HandicapReport(FPDF):
    def header(self):
        self.set_font('Helvetica', 'B', 16)
        self.cell(0, 10, 'Handicap Model Analysis: 2026 Season', new_x="LMARGIN", new_y="NEXT", align='C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}/{{nb}}', align='C')

def create_report():
    pdf = HandicapReport()
    pdf.alias_nb_pages()
    
    # --- PAGE 1: Last 2 (Trend) ---
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 14)
    pdf.cell(0, 10, 'Model 1: Last 2 Rounds (The "Trend" Model)', new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_font('Helvetica', '', 11)
    pdf.multi_cell(0, 6, "Methodology:\nCalculates a player's Implied Index by averaging the differentials of their two most recent tournament rounds. If this Implied Index is lower than their current Handicap Index, the player is adjusted downward. No upward revisions are permitted.")
    pdf.ln(3)
    
    pdf.multi_cell(0, 6, "Rationale:\nDesigned to prioritize current form over historical ability. This model aggressively targets players on a 'hot streak' or those who have recently found improvement, ensuring they do not carry an outdated high handicap into the next event.")
    pdf.ln(5)
    
    pdf.set_font('Helvetica', 'B', 12)
    pdf.cell(0, 10, 'Impact Analysis: Downward Adjustments Only', new_x="LMARGIN", new_y="NEXT")
    
    # Table Header
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font('Helvetica', 'B', 10)
    pdf.cell(50, 8, 'Player', border=1, fill=True)
    pdf.cell(25, 8, 'Current', border=1, align='C', fill=True)
    pdf.cell(25, 8, 'Trend (New)', border=1, align='C', fill=True)
    pdf.cell(25, 8, 'Adjustment', border=1, align='C', fill=True)
    pdf.cell(65, 8, 'Gross Scores (Last 2)', border=1, align='C', fill=True)
    pdf.ln()
    
    # Table Data (Hardcoded from previous analysis step)
    data_last2 = [
        ('Scott Lucas', 11.8, 7.7, -4.1, '77, 81'),
        ('Ben Magnone', 10.4, 7.3, -3.1, '78, 79'),
        ('Stewart Polakov', 4.9, 3.2, -1.7, '74'),
        ('Eric Lamb', 24.0, 23.2, -0.8, '96'),
        ('Scott Bracken', 9.8, 9.6, -0.2, '77, 85')
    ]
    
    pdf.set_font('Helvetica', '', 10)
    for row in data_last2:
        pdf.cell(50, 8, row[0], border=1)
        pdf.cell(25, 8, str(row[1]), border=1, align='C')
        pdf.cell(25, 8, str(row[2]), border=1, align='C')
        
        # Color the adjustment red if heavy
        if row[3] < -2:
            pdf.set_text_color(220, 50, 50)
            pdf.set_font('Helvetica', 'B', 10)
        else:
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Helvetica', '', 10)
            
        pdf.cell(25, 8, f"{row[3]:.1f}", border=1, align='C')
        
        pdf.set_text_color(0, 0, 0)
        pdf.set_font('Helvetica', '', 10)
        pdf.cell(65, 8, row[4], border=1, align='C')
        pdf.ln()

    pdf.ln(10)
    pdf.set_font('Helvetica', 'I', 10)
    pdf.multi_cell(0, 6, "Observation:\nOnly 5 players are affected. However, the impact on Scott Lucas (-4.1) and Ben Magnone (-3.1) is severe. This model effectively assumes their most recent good rounds are their permanent new standard.")


    # --- PAGE 2: Best 3 (Potential) ---
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 14)
    pdf.cell(0, 10, 'Model 2: Best 3 Rounds (The "Potential" Model)', new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_font('Helvetica', '', 11)
    pdf.multi_cell(0, 6, "Methodology:\nCalculates a player's Implied Index by averaging the lowest 3 differentials from the last 13 months. If this Implied Index is lower than their current Handicap Index, the player is adjusted downward.")
    pdf.ln(3)
    
    pdf.multi_cell(0, 6, "Rationale:\nDesigned to identify a player's ceiling. By focusing on the best 3 rounds, this model filters out inconsistent 'bad days' and anchors the handicap to the best golf the player has proven they can play. It is the industry standard for preventing sandbagging.")
    pdf.ln(5)
    
    pdf.set_font('Helvetica', 'B', 12)
    pdf.cell(0, 10, 'Impact Analysis: Downward Adjustments Only', new_x="LMARGIN", new_y="NEXT")
    
    # Table Header
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font('Helvetica', 'B', 10)
    pdf.cell(50, 8, 'Player', border=1, fill=True)
    pdf.cell(25, 8, 'Current', border=1, align='C', fill=True)
    pdf.cell(25, 8, 'Potential', border=1, align='C', fill=True)
    pdf.cell(25, 8, 'Adjustment', border=1, align='C', fill=True)
    pdf.cell(65, 8, 'Best 3 Gross Scores', border=1, align='C', fill=True)
    pdf.ln()
    
    # Table Data (Hardcoded from previous analysis step)
    data_best3 = [
        ('Kevin Barber', 16.4, 13.5, -2.9, '83, 84, 89'),
        ('Ben Magnone', 10.4, 7.7, -2.7, '78, 79, 80'),
        ('Greg Funk', 5.5, 3.2, -2.3, '72, 74, 76'),
        ('Joe Sepessy', 6.1, 3.8, -2.3, '73, 74, 77'),
        ('Scott Bracken', 9.8, 7.7, -2.1, '77, 80, 80'),
        ('Korey Jerome', 10.6, 8.7, -1.9, '78, 81, 81'),
        ('Scott Lucas', 11.8, 9.9, -1.9, '77, 81, 86'),
        ('Frank Angeloro', 8.6, 6.8, -1.8, '76, 78, 80'),
        ('Stewart Polakov', 4.9, 3.2, -1.7, '74 (1 Rd Only)'),
        ('Clark Koch', 8.8, 7.4, -1.4, '78, 78, 80'),
        ('Ron Amstutz', 12.4, 11.1, -1.3, '81, 83, 84'),
        ('Kiernan Mattson', 2.8, 1.7, -1.1, '71, 72, 74'),
        ('Matt Neimeier', 12.2, 11.1, -1.1, '82, 83, 83'),
        ('Eric Weiss', 0.5, -0.5, -1.0, '67, 71, 72'),
        ('Jeff Cloepfil', 12.0, 11.1, -0.9, '82, 83, 83')
    ]
    
    pdf.set_font('Helvetica', '', 9)  # Smaller font for longer list
    for row in data_best3:
        pdf.cell(50, 7, row[0], border=1)
        pdf.cell(25, 7, str(row[1]), border=1, align='C')
        pdf.cell(25, 7, str(row[2]), border=1, align='C')
        
        if row[3] < -2:
            pdf.set_text_color(220, 50, 50)
            pdf.set_font('Helvetica', 'B', 9)
        else:
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Helvetica', '', 9)
            
        pdf.cell(25, 7, f"{row[3]:.1f}", border=1, align='C')
        
        pdf.set_text_color(0, 0, 0)
        pdf.set_font('Helvetica', '', 9)
        pdf.cell(65, 7, row[4], border=1, align='C')
        pdf.ln()

    pdf.ln(5)
    pdf.set_font('Helvetica', 'I', 10)
    pdf.multi_cell(0, 6, "Observation:\nThis model affects significantly more players (24 total downward adjustments vs. 5). However, the adjustments are generally milder and more distributed. It successfully catches 'Grinders' like Greg Funk (-2.3) and Joe Sepessy (-2.3) who are consistently good but not necessarily trending 'hot' right now.")

    pdf.output("2026_Handicap_Model_Report.pdf")

if __name__ == "__main__":
    create_report()
