import math
import random
import time

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

sns.set_theme()

def clip(value: int) -> int:
    return min(max(value, -1000), 1000)

# [0, 100]
def centipawn_to_winpercent(cp: int) -> float:
    return 50 + 50 * centipawn_to_winchance(clip(cp))


# [-1, 1]
def centipawn_to_winchance(cp: int) -> float:
    MULTIPLIER = -0.00368208
    return max(min(2 / (1 + math.exp(MULTIPLIER * cp)) - 1, 1), -1)

# Based on https://github.com/lichess-org/lila/blob/4336bf020e746413e0039f1583a186442084bafa/modules/analyse/src/main/AccuracyPercent.scala#L47-L55
def winpercents_to_accuracy(before_winpercent: float, after_winpercent: float) -> float:
    # Accuracy per move
    diff = after_winpercent - before_winpercent
    if diff >= 0:
        return 100.0
    raw = 103.1668100711649 * math.exp(0.04354415386753951 * diff) - 3.166924740191411
    raw += 1  # // uncertainty bonus (due to imperfect analysis)
    return max(0, min(100, raw))


def plot_winpercent():
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

def plot_accuracy():
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

if __name__ == '__main__':
    # plot_winpercent()
    # plot_accuracy()
    from utils import PrintInLine
    PrintInLine.reset()
    pbar = PrintInLine.get_pbar_function()
    pbar2 = PrintInLine.get_pbar_function()

    for i in range(100):
        if i == 50:
            pbar2 = PrintInLine.get_pbar_function()
        pbar(i, 100, "Hello World", 4, update_period=0)
        time.sleep(random.random() * 0.1)
        pbar2(2*i, 100, "Hello", 5, update_period=0)
        time.sleep(random.random() * 0.1)
