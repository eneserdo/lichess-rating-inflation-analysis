
# Variables related to the prepare.py
EVERY_N_MONTHS = 6
NUM_GAMES_PER_MONTH = 250
RATING_BIN_MEANS = [1400, 1600, 1800, 2000, 2200, 2400]
RATING_BINS = [(mean - 50, mean + 50) for mean in RATING_BIN_MEANS]
TIME_CONTROL = {"blitz": (180, 300), "rapid": (600, 900)}

# Variables related to the analyze.py
STOCKFISH_PATH = "./stockfish/stockfish-ubuntu-x86-64-avx2"
STOCKFISH_DEPTH = 20

