import sqlite3
from typing import List, Tuple

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

import config as cfg
from analyse import centipawn_to_winpercent, winpercents_to_accuracy

sns.set_theme()


def plot_winpercent_formula():
    # Create figure with seaborn styling
    plt.figure(figsize=(10, 6), dpi=100)  # Larger, higher resolution figure
    
    # Create the plot
    x = np.linspace(-1500, 1500, 1000)
    sns.lineplot(x=x, 
                y=[centipawn_to_winpercent(cp) for cp in x],
                linewidth=2,
                color='#2166ac')  # Professional blue color
    
    # Customize the plot
    plt.title('Centipawns to Win Percentage', 
             fontsize=14, 
             pad=15)
    plt.xlabel('Centipawns', fontsize=12)
    plt.ylabel('Win Percent (%)', fontsize=12)

    # add formula, right bottom corner
    plt.text(1400, 10, r'$Win\% = 50 + 50 \cdot \left( \frac{2}{1 + e^{k \cdot cp}} - 1 \right)$', 
             fontsize=12, 
             ha='right', 
             va='bottom')
    plt.text(1400, 4, r'$k = -0.00368208$', 
             fontsize=9, 
             ha='right', 
             va='bottom')
    
    # Add grid (though seaborn includes this by default)
    plt.grid(True, linestyle='-', alpha=0.7)
    
    # Adjust layout to prevent label cutoff
    plt.tight_layout()
    
    # Save with white background and higher quality
    plt.savefig("winpercent.png", 
                bbox_inches='tight', 
                facecolor='white', 
                edgecolor='none')

def plot_accuracy_formula():
    # Create figure with seaborn styling
    plt.figure(figsize=(10, 6), dpi=100)  # Larger, higher resolution figure
    
    # Create the plot
    x = np.linspace(-100, 100, 1000)
    sns.lineplot(x=x, 
                y=[winpercents_to_accuracy(0, cp) for cp in x],
                linewidth=2,
                color='#2166ac')  # Professional blue color

    # Customize the plot
    plt.title('Accuracy Percentage', 
             fontsize=14, 
             pad=15)
    plt.xlabel('Centipawns', fontsize=12)
    plt.ylabel('Accuracy (%)', fontsize=12)

    # add formula, right bottom corner  
    plt.text(1400, 10, r'$A(\Delta cp) = 100 - 103.1668100711649 \cdot e^{0.04354415386753951 \cdot \Delta cp} + 3.166924740191411$', 
             fontsize=12, 
             ha='right', 
             va='bottom')
    
    # Add grid (though seaborn includes this by default)
    plt.grid(True, linestyle='-', alpha=0.7)
    
    # Adjust layout to prevent label cutoff
    plt.tight_layout()
    
    # Save with white background and higher quality
    plt.savefig("accuracy.png", 
                bbox_inches='tight', 
                facecolor='white', 
                edgecolor='none')

"""
This is the schema of the database:
        CREATE TABLE IF NOT EXISTS game_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            game_id TEXT NOT NULL,
            w_elo INTEGER NOT NULL,
            b_elo INTEGER NOT NULL,
            bin TEXT NOT NULL,
            game_result TEXT NOT NULL,
            time_control TEXT NOT NULL,
            tempo TEXT,
            w_acpl REAL,
            w_accuracy REAL,
            w_inaccuracies INTEGER,
            w_mistakes INTEGER,
            w_blunders INTEGER,
            b_acpl REAL,
            b_accuracy REAL,
            b_inaccuracies INTEGER,
            b_mistakes INTEGER,
            b_blunders INTEGER,
            UNIQUE(game_id)
        )

"""

def get_accuracy_rating_data(year: str, tempo: str) -> List[Tuple[float, float]]:
    # Connects to database, for each game, gets the game accuracy and rating for each side
    # I am aware that repeatedly calling this function will be inefficient, but it is what it is

    conn = sqlite3.connect("chess_metrics.db")
    cursor = conn.cursor()
    cursor.execute("SELECT w_accuracy, w_elo, b_accuracy, b_elo FROM game_metrics WHERE date LIKE ? AND tempo = ?", (f"{year}%", tempo))
    data = cursor.fetchall()
    conn.close()

    games = []
    for datum in data:
        w_accuracy, w_elo, b_accuracy, b_elo = datum
        games.append((w_accuracy, w_elo))
        games.append((b_accuracy, b_elo))

    return np.array(games)


def plot1():
    # calculate the correlation between accuracy and rating for each year and plot a line plot
    # repeat for each tempo so that we have N lines
    
    corr_coeffs = {tempo: [] for tempo in cfg.TIME_CONTROL.keys()}

    for tempo in cfg.TIME_CONTROL.keys():
        for year in cfg.EVERY_N_MONTHS:
            data = get_accuracy_rating_data(year, tempo)
            plt.figure(figsize=(10, 6), dpi=100)
            plt.scatter(data[:, 0], data[:, 1])
            plt.grid(True, linestyle='-', alpha=0.7)
            plt.tight_layout()

            # fit a line
            slope, intercept = np.polyfit(data[:, 0], data[:, 1], 1)
            plt.plot(data[:, 0], slope * data[:, 0] + intercept, color='red')

            plt.title(f"Accuracy vs Rating for {tempo} in {year}")
            plt.xlabel("Accuracy")
            plt.ylabel("Rating")
            plt.savefig(f"accuracy_rating_correlation_{tempo}_{year}.png", 
                        bbox_inches='tight', 
                        facecolor='white', 
                        edgecolor='none')

            plt.close()

            corr_coeffs[tempo].append(np.corrcoef(data[:, 0], data[:, 1])[0, 1])


    plt.figure(figsize=(10, 6), dpi=100)
    plt.title("Accuracy vs Rating Correlation")
    plt.xlabel("Year")
    plt.ylabel("Correlation Coefficient")
    for tempo in cfg.TIME_CONTROL.keys():
        plt.plot(cfg.EVERY_N_MONTHS, corr_coeffs[tempo], label=tempo)
    plt.legend()
    plt.show()

    plt.savefig("accuracy_rating_correlation.png", 
                bbox_inches='tight', 
                facecolor='white', 
                edgecolor='none')




if __name__ == '__main__':
    # plot_winpercent_formula()
    # plot_accuracy_formula()
    g1=get_accuracy_rating_data("2017-01", "bullet")
    g2=get_accuracy_rating_data("2017-01", "blitz")

    # read json file and load: game accuracy, error counts, acpl
    # json[tempo][rating][game_identifier] = {
    #     "accuracy": (float, float),
    #     "error_counts": ((int,int,int), (int,int,int)),
    #     "acpl": (float, float)
    # }
        
    