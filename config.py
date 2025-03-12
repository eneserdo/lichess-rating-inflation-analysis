
# Variables related to the prepare.py
NUM_GAMES_PER_MONTH = 250
RATING_BIN_MEANS = [1300, 1500, 1700, 1900, 2100, 2300]
RATING_BINS = [(mean - 50, mean + 50) for mean in RATING_BIN_MEANS]
TIME_CONTROL = {"blitz": (180, 300), "rapid": (600, 900)} # time_control: (min_sec, max_sec)

TOTAL_NUM_GAMES = NUM_GAMES_PER_MONTH * len(TIME_CONTROL.keys()) * len(RATING_BIN_MEANS)

EVERY_N_MONTHS = 6
DATES = [f"{year}-{month:02d}" for year in range(2018, 2025) for month in range(1, 13, EVERY_N_MONTHS)]

# Variables related to the analyze.py
STOCKFISH_PATH = "./stockfish/stockfish-ubuntu-x86-64-avx2"
STOCKFISH_DEPTH = 20


# Variables related to the single_run.py
PLAYERS = [
    "enerd", # Me :D, An average amateur player
    "DrNykterstein", # The legend himself, Magnus Carlsen
    "guki1124", # The current World Champion, Gukesh Dommaraju
    "SVODMEVKO", # Danil Dubov, A Russian GM
    "Ediz_Gurel", # Ediz Gurel, A Turkish GM
    "thibault", # The developer of Lichess
]
