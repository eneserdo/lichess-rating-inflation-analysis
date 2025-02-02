import chess
import chess.pgn

fname = "./sample/lichess_pgn_2025.02.01_enerd_vs_Ivan_Umpelev.1dE5J3x7.pgn"

with open(fname, "r") as f:
    game = chess.pgn.read_game(f)

evals = []
while not game.is_end():
    game = game.next()
    evals.append(game.eval().white().score(mate_score=1000))


from test import game_accuracy

with open(fname, "r") as f:
    game = chess.pgn.read_game(f)

wa, ba = game_accuracy(evals)
print(f"{wa=}, {ba=}")
print("ok")