import sqlite3
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

import config as cfg
from analyse import centipawn_to_winpercent, winpercents_to_accuracy

sns.set_theme()

#### Plots of Formulas ####
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

#### Plots of Data ####
"""
This is the schema of the sqlite database:
Table name: game_metrics
Columns:
- id: integer
- date: text ("2017-01", "2017-07", ..., "2025-01", "2025-07")
- game_id: text
- w_elo: integer
- b_elo: integer
- bin: text (rating bin, e.g. "1300", "1500", ..., "2300")
- game_result text
- time_control text
- tempo text ("rapid", "blitz", "bullet")
- w_acpl real
- w_accuracy real
- w_inaccuracies integer
- w_mistakes integer
- w_blunders integer
- b_acpl real
- b_accuracy real
- b_inaccuracies integer
- b_mistakes integer
- b_blunders integer
"""

# Error means: blunder, mistake, inaccuracy.

def get_data(select: list[str], where: dict[str, str]) -> List[Tuple]:
    # A generic function to get data from the database
    # select: list of columns to select
    # where: dictionary of column names and values to filter by
    # returns a list of tuples, each tuple contains the values of the selected columns

    keys, values = zip(*where.items())
    query = "SELECT " + ", ".join(select) + " FROM game_metrics WHERE " + " AND ".join([f"{k} = ?" for k in keys])

    conn = sqlite3.connect("chess_metrics.db")
    cursor = conn.cursor()
    cursor.execute(query, values)
    data = cursor.fetchall()
    conn.close()

    return data

def plot_errors_per_bin(date, tempo):
    raw_data = get_data(select=["w_blunders", "b_blunders", "w_mistakes", "b_mistakes", "w_inaccuracies", "b_inaccuracies", "w_elo", "b_elo"], where={"date": date, "tempo": tempo})

    _w_blunders, _b_blunders, _w_mistakes, _b_mistakes, _w_inaccuracies, _b_inaccuracies, _w_elo, _b_elo = zip(*raw_data)

    blunders = np.array(_w_blunders + _b_blunders)
    mistakes = np.array(_w_mistakes + _b_mistakes)
    inaccuracies = np.array(_w_inaccuracies + _b_inaccuracies)
    elo = np.array(_w_elo + _b_elo)

    # grouped bar plots with standard deviation error bars 
    # for blunders, mistakes, and inaccuracies 
    # seperate each group by rating bin, for each rating bin, plot the mean and standard deviation error bars for blunders, mistakes, and inaccuracies
    
    # Calculate statistics for each rating bin
    bin_labels = []
    blunders_means = []
    blunders_stds = []
    mistakes_means = []
    mistakes_stds = []
    inaccuracies_means = []
    inaccuracies_stds = []
    
    for i, bin_range in enumerate(cfg.RATING_BINS):
        # Create mask for current rating bin
        mask = (elo >= bin_range[0]) & (elo <= bin_range[1])
        
        # Skip if no data in this bin
        if not np.any(mask):
            continue
            
        bin_labels.append(str(cfg.RATING_BIN_MEANS[i]))
        
        # Calculate means and standard deviations for each error type
        blunders_means.append(np.mean(blunders[mask]))
        blunders_stds.append(np.std(blunders[mask]))
        
        mistakes_means.append(np.mean(mistakes[mask]))
        mistakes_stds.append(np.std(mistakes[mask]))
        
        inaccuracies_means.append(np.mean(inaccuracies[mask]))
        inaccuracies_stds.append(np.std(inaccuracies[mask]))
    
    # Convert to numpy arrays for easier manipulation
    blunders_means = np.array(blunders_means)
    blunders_stds = np.array(blunders_stds)
    mistakes_means = np.array(mistakes_means)
    mistakes_stds = np.array(mistakes_stds)
    inaccuracies_means = np.array(inaccuracies_means)
    inaccuracies_stds = np.array(inaccuracies_stds)
    
    # Create the grouped bar plot
    plt.figure(figsize=(12, 8), dpi=100)
    
    x = np.arange(len(bin_labels))  # Label locations
    width = 0.25  # Width of bars
    
    # Create bars with error bars
    bars1 = plt.bar(x - width, blunders_means, width, yerr=blunders_stds, 
                   label='Blunders', capsize=5, alpha=0.8)
    bars2 = plt.bar(x, mistakes_means, width, yerr=mistakes_stds, 
                   label='Mistakes', capsize=5, alpha=0.8)
    bars3 = plt.bar(x + width, inaccuracies_means, width, yerr=inaccuracies_stds, 
                   label='Inaccuracies', capsize=5, alpha=0.8)
    
    # Customize the plot
    plt.title(f'Average Errors per Game by Rating Bin ({tempo}, {date})', 
             fontsize=14, pad=15)
    plt.xlabel('Rating Bin', fontsize=12)
    plt.ylabel('Average Number of Errors per Game', fontsize=12)
    plt.xticks(x, bin_labels)
    plt.legend()
    plt.grid(True, linestyle='-', alpha=0.3, axis='y')
    
    # Adjust layout to prevent label cutoff
    plt.tight_layout()
    
    # Save the plot
    plt.savefig(f"errors_by_rating_bin_{tempo}_{date}.png", 
                bbox_inches='tight', 
                facecolor='white', 
                edgecolor='none')
    plt.close()


if __name__ == '__main__':
    # plot_winpercent_formula()
    # plot_accuracy_formula()

    #############################################################
    date = "2022-01"
    tempo = "rapid"
    # g1=get_accuracy_rating_data(date, tempo)
    raw_data = get_data(select=["w_accuracy", "b_accuracy", "w_elo", "b_elo"], where={"tempo": tempo, "date": date})
    _w_accuracy, _b_accuracy, _w_elo, _b_elo = zip(*raw_data)

    accuracy = np.array(_w_accuracy + _b_accuracy)
    elo = np.array(_w_elo + _b_elo)

    # draw kde plot for each rating bin in the same figure
    plt.figure(figsize=(10, 6), dpi=100)
    for i, bin in enumerate(cfg.RATING_BINS):
        mask = (elo >= bin[0]) & (elo <= bin[1])
        bin_mean = cfg.RATING_BIN_MEANS[i]
        sns.kdeplot(data=accuracy[mask], label=f"Rating Bin {bin_mean}")
    plt.legend()
    plt.title(f"KDE Plot for {tempo} in {date}")
    plt.xlabel("Accuracy")
    plt.ylabel("Density")
    plt.savefig(f"accuracy_kde_plot_{tempo}_{date}.png", 
                bbox_inches='tight', 
                facecolor='white', 
                edgecolor='none')
    plt.close()

    #############################################################

    tempo = "rapid"
    rating_bin = "2100"
    # accuracy_data_ = get_accuracy_data_v2(tempo, rating_bin)
    accuracy_data = get_data(select=["w_accuracy", "b_accuracy", "date"], where={"tempo": tempo, "bin": rating_bin})
    _w_accuracy, _b_accuracy, _date = zip(*accuracy_data)

    accuracy_data = {}
    for dt, w_a, b_a in zip(_date, _w_accuracy, _b_accuracy):
        if dt not in accuracy_data:
            accuracy_data[dt] = []
        accuracy_data[dt].extend([w_a, b_a])

    # plot game accuracies for each date
    plt.figure(figsize=(10, 6), dpi=100)
    # make the color intensity increase with the date
    colors = sns.color_palette("viridis", len(accuracy_data))[::-1]
    for i, date in enumerate(sorted(accuracy_data.keys())):
        sns.kdeplot(data=accuracy_data[date], label=date, color=colors[i])

    plt.legend()
    plt.title(f"{tempo} {rating_bin} Rating Bin Accuracy")
    plt.xlabel("Accuracy")
    plt.ylabel("Density")
    plt.savefig(f"{tempo}_{rating_bin}_accuracy.png", 
                bbox_inches='tight', 
                facecolor='white',
                edgecolor='none')

    plt.close()

    # ############################################################

    raw_data = get_data(select=["w_acpl", "b_acpl", "w_elo", "b_elo"], where={"date": "2025-01"})
    _w_acpl, _b_acpl, _w_elo, _b_elo = zip(*raw_data)

    acpl = np.array(_w_acpl + _b_acpl)
    elo = np.array(_w_elo + _b_elo)


    plt.figure(figsize=(10, 6), dpi=100)
    plt.scatter(acpl, elo, alpha=0.5, s=5)
    plt.grid(True, linestyle='-', alpha=0.7)
    plt.tight_layout()
    plt.title("ACPL vs Rating")
    plt.xlabel("ACPL")
    plt.ylabel("Rating")
    plt.savefig("acpl_rating_2025_01.png", 
                bbox_inches='tight', 
                facecolor='white', 
                edgecolor='none')
    plt.close()

    ############################################################

    plot_errors_per_bin("2025-01", "rapid")
    plot_errors_per_bin("2025-01", "blitz")
    plot_errors_per_bin("2025-01", "bullet")

    plot_errors_per_bin("2020-01", "rapid")
    plot_errors_per_bin("2020-01", "blitz")
    plot_errors_per_bin("2020-01", "bullet")


