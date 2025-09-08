
# Variables related to the prepare.py
NUM_GAMES_PER_CONFIG = 250
RATING_BIN_MEANS = [1300, 1500, 1700, 1900, 2100, 2300]
RATING_BINS = [(mean - 50, mean + 50) for mean in RATING_BIN_MEANS]
TIME_CONTROL = {"blitz": (180, 300), "rapid": (600, 900)} # time_control: (min_sec, max_sec)

MAX_GAMES_PER_PLAYER = 5 # limit the number of games per player per month

TOTAL_NUM_GAMES = NUM_GAMES_PER_CONFIG * len(TIME_CONTROL.keys()) * len(RATING_BIN_MEANS)

EVERY_N_MONTHS = 6
DATES = [f"{year}-{month:02d}" for year in range(2017, 2026) for month in range(1, 13, EVERY_N_MONTHS)]

# Variables related to the evaluate.py
STOCKFISH_PATH = "./stockfish/stockfish-ubuntu-x86-64-avx2"
STOCKFISH_LIMIT_DEPTH = 25 # depth (aka ply) per move
STOCKFISH_LIMIT_TIME = None # seconds per move
STOCKFISH_HASH_SIZE = None # None means use the default hash size
STOCKFISH_THREADS = 3 # None means use the default threads

# Variables related to the single_run.py
PLAYERS = [
    "enerd", # Me :D, An average amateur player
    "DrNykterstein", # The legend himself, Magnus Carlsen
    "guki1124", # The current World Champion, Gukesh Dommaraju
    "SVODMEVKO", # Danil Dubov, A Russian GM
    "Ediz_Gurel", # Ediz Gurel, A Turkish GM
    "thibault", # The developer of Lichess
]
