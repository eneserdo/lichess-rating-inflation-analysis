import math
from typing import List, Optional, Tuple


def winpercent2accuracy(before: float, after: float) -> float:
    if after >= before:
        return 100.0
    win_diff = before - after
    raw = 103.1668100711649 * math.exp(-0.04354415386753951 * win_diff) - 3.166924740191411
    return max(0, min(100, raw + 1))


def weighted_mean(values: List[Tuple[float, float]]) -> Optional[float]:
    ...

def harmonic_mean(values: List[float]) -> Optional[float]:
    ...

def standard_deviation(values: List[float]) -> float:
    if not values or len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / len(values)
    return max(0.5, min(12.0, math.sqrt(variance)))


def game_accuracy(start_color: bool, cps: List[int]) -> Optional[Tuple[float, float]]:
    all_win_percents = [100] + cps  # Initial evaluation
    window_size = max(2, min(8, len(cps) // 10))
    win_percent_values = all_win_percents[:]
    windows = [win_percent_values[:window_size]] * (window_size - 2) + [win_percent_values[i:i + window_size] for i in range(len(win_percent_values) - window_size + 1)]
    weights = [standard_deviation(w) for w in windows]
    
    weighted_accuracies = []
    for i in range(len(all_win_percents) - 1):
        prev, next_ = all_win_percents[i], all_win_percents[i + 1]
        color = (i % 2 == 0) == start_color
        accuracy = winpercent2accuracy(prev if color else next_, next_ if color else prev)
        weighted_accuracies.append(((accuracy, weights[i]), color))
    
    def color_accuracy(color: bool) -> Optional[float]:
        weighted = weighted_mean([(acc, weight) for (acc, weight), c in weighted_accuracies if c == color])
        harmonic = harmonic_mean([acc for (acc, _), c in weighted_accuracies if c == color])
        return (weighted + harmonic) / 2 if weighted is not None and harmonic is not None else None
    
    return color_accuracy(True), color_accuracy(False)