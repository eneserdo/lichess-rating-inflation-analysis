from pprint import pprint
import chess
import chess.pgn

import config as cfg
from prepare import get_rating_bin, get_time_control

def count_games(pgn_file_path: str):
    counter = {tempo: {mean: 0 for mean in cfg.RATING_BIN_MEANS} for tempo in cfg.TIME_CONTROL.keys()}

    with open(pgn_file_path, "r") as f:
        count = 0
        while True:
            game_header = chess.pgn.read_headers(f)
            if game_header is None:
                break
            bin = get_rating_bin((int(game_header["WhiteElo"]) + int(game_header["BlackElo"])) / 2)
            tempo = get_time_control(game_header["TimeControl"])
            if tempo is not None and bin is not None:
                counter[tempo][bin] += 1
            count += 1
    
    print(f"Total games: {count}")
    pprint(counter)


if __name__ == "__main__":
    count_games("lichess_db/lichess_db_standard_rated_2020-01_filtered.pgn")