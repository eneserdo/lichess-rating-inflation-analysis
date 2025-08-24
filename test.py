import math
from typing import Dict, List, Optional, Union

import chess.pgn
from chess.engine import Cp, Mate

from analyse import extract_evals

Eval = Union[Cp, Mate]

def clip(value: float, min_val: float, max_val: float) -> float:
    return min(max(value, min_val), max_val)

def centipawn_to_winchance(cp: int) -> float:
    MULTIPLIER = -0.00368208
    value = 2.0 / (1.0 + math.exp(MULTIPLIER * float(cp))) - 1.0
    return clip(value, -1.0, 1.0)



def count_errors(evals: List[Eval], verbose: bool = False) -> Dict[str, Dict[str, int]]:
    """
    Count blunders, mistakes, and inaccuracies for White and Black.

    The logic follows Lichess advice rules:
    - CP advice: use changes in winning chances derived from centipawns with
      thresholds 0.3 (blunder), 0.2 (mistake), 0.1 (inaccuracy). The delta is
      measured from White's winning-chance perspective and flipped for the mover
      so that positive values indicate the mover made the position worse.
    - Mate advice: detect transitions creating a forced mate for the opponent
      or losing one's own forced mate. The severity depends on the position
      evaluation (in centipawns) relative to the mover's POV:
        MateCreated: prev Cp, next Mate against the mover
          prev_pov_cp < -999: Inaccuracy
          prev_pov_cp < -700: Mistake
          else: Blunder
        MateLost: prev Mate for mover, next Cp or Mate for opponent
          curr_pov_cp > 999: Inaccuracy
          curr_pov_cp > 700: Mistake
          else: Blunder

    Assumptions:
    - `evals[i]` is the engine evaluation after the i-th ply, starting with
      White having just moved at index 0. Therefore, the mover for the pair
      (evals[i-1] -> evals[i]) is White if i is even, else Black.
    """

    assert isinstance(evals, list) and all(isinstance(e, (Cp, Mate)) for e in evals), (
        "Evals must be a list of chess.engine.Cp or chess.engine.Mate"
    )
    if len(evals) <= 1:
        raise Exception("Not enough moves to count errors")

    errors: Dict[str, Dict[str, int]] = {
        "white": {"blunder": 0, "mistake": 0, "inaccuracy": 0},
        "black": {"blunder": 0, "mistake": 0, "inaccuracy": 0},
    }

    def get_cp(eval_obj: Eval) -> Optional[int]:
        return int(eval_obj.score()) if isinstance(eval_obj, Cp) else None

    def get_mate(eval_obj: Eval) -> Optional[int]:
        return int(eval_obj.mate()) if isinstance(eval_obj, Mate) else None

    for i in range(1, len(evals)):
        prev_eval = evals[i - 1]
        curr_eval = evals[i]

        mover = "white" if (i % 2 == 1) else "black"

        prev_cp = get_cp(prev_eval)
        curr_cp = get_cp(curr_eval)

        # CP advice when both evaluations are centipawn scores
        if prev_cp is not None and curr_cp is not None:
            prev_wc = centipawn_to_winchance(prev_cp)
            curr_wc = centipawn_to_winchance(curr_cp)
            delta = curr_wc - prev_wc
            # Flip for White so that positive means "worse for mover"
            badness = -delta if mover == "white" else delta

            if badness >= 0.3:
                errors[mover]["blunder"] += 1
                if verbose:
                    print(f"Ply {i}: {mover} blunder (Δ={badness:.3f})")
            elif badness >= 0.2:
                errors[mover]["mistake"] += 1
                if verbose:
                    print(f"Ply {i}: {mover} mistake (Δ={badness:.3f})")
            elif badness >= 0.1:
                errors[mover]["inaccuracy"] += 1
                if verbose:
                    print(f"Ply {i}: {mover} inaccuracy (Δ={badness:.3f})")
            continue

        # Mate advice
        prev_mate = get_mate(prev_eval)
        curr_mate = get_mate(curr_eval)

        # Helper: centipawn value from mover's POV (positive is good for mover)
        def pov_cp(value: Optional[int]) -> int:
            if value is None:
                return 0
            return value if mover == "white" else -value

        # Helper: mate sign from mover's POV (positive is mate for mover)
        def pov_mate(value: Optional[int]) -> Optional[int]:
            if value is None:
                return None
            return value if mover == "white" else -value

        # MateCreated: prev Cp, next Mate against mover
        if prev_cp is not None and curr_mate is not None:
            curr_pov_mate = pov_mate(curr_mate)
            assert curr_pov_mate is not None
            if curr_pov_mate < 0:
                prev_pov_cp = pov_cp(prev_cp)
                if prev_pov_cp < -999:
                    errors[mover]["inaccuracy"] += 1
                    if verbose:
                        print(f"Ply {i}: {mover} inaccuracy (mate created; prev={prev_pov_cp})")
                elif prev_pov_cp < -700:
                    errors[mover]["mistake"] += 1
                    if verbose:
                        print(f"Ply {i}: {mover} mistake (mate created; prev={prev_pov_cp})")
                else:
                    errors[mover]["blunder"] += 1
                    if verbose:
                        print(f"Ply {i}: {mover} blunder (mate created; prev={prev_pov_cp})")
            continue

        # MateLost: prev Mate for mover, next Cp or Mate for opponent
        if prev_mate is not None and pov_mate(prev_mate) is not None and pov_mate(prev_mate) > 0:
            judgement_recorded = False
            if curr_cp is not None:
                curr_pov_cp = pov_cp(curr_cp)
                if curr_pov_cp > 999:
                    errors[mover]["inaccuracy"] += 1
                elif curr_pov_cp > 700:
                    errors[mover]["mistake"] += 1
                else:
                    errors[mover]["blunder"] += 1
                judgement_recorded = True
                if verbose:
                    print(f"Ply {i}: {mover} {'inaccuracy' if curr_pov_cp > 999 else 'mistake' if curr_pov_cp > 700 else 'blunder'} (mate lost; curr={curr_pov_cp})")
            else:
                curr_pov_mate = pov_mate(curr_mate)
                if curr_pov_mate is not None and curr_pov_mate < 0:
                    # No CP available; treat as 0 for judgement thresholds
                    errors[mover]["blunder"] += 1
                    judgement_recorded = True
                    if verbose:
                        print(f"Ply {i}: {mover} blunder (mate lost; now mated)")

            if judgement_recorded:
                continue

        # Other mate-to-mate transitions (e.g., delaying mate) are ignored per reference

    return errors


if __name__ == "__main__":
    # Example usage
    with open("tests/sample_pgns/g7.pgn", "r") as f:
        game = chess.pgn.read_game(f)
        evals = extract_evals(game)
    result = count_errors(evals, verbose=True)
    print(result)
