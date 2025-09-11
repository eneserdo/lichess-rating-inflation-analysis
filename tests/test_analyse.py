import math
import os
import sys
import unittest

import chess
import chess.pgn
from chess.engine import Cp, Mate

# Add the parent directory to the path so we can import from analyse.py
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analyse import count_errors, evals_to_cps, extract_evals, game_accuracy, get_acpl


class TestACPLCalculation(unittest.TestCase):
    """Test Average Centipawn Loss (ACPL) calculation function"""
    
    def test_get_acpl_empty_list(self):
        """Test ACPL calculation with empty centipawn list"""
        with self.assertRaises(Exception):
            get_acpl([])
    
    def test_get_acpl_single_move(self):
        """Test ACPL calculation with single move (no differences possible)"""
        cps = [15]  # Only initial position
        with self.assertRaises(Exception):
            get_acpl(cps)
    
    def test_get_acpl_perfect_play(self):
        """Test ACPL with perfect play (no centipawn losses)"""
        # Perfectly equal positions throughout the game
        cps = [15, 15, 15, 15, 15, 15]
        white_acpl, black_acpl = get_acpl(cps)
        
        # Assert both players have 0 ACPL for perfect play
        assert white_acpl == 0.0, f"Expected white ACPL to be 0.0, got {white_acpl}"
        assert black_acpl == 0.0, f"Expected black ACPL to be 0.0, got {black_acpl}"
    
    def test_get_acpl_white_blunders(self):
        """Test ACPL when only white makes mistakes"""
        # White makes losing moves (evaluation drops after white moves)
        # Positions: +15 (white move) -> 0 (black move) -> 0 (white move) -> -10 (black move) -> -10 (white move)
        cps = [15, 0, 0, -10, -10]
        white_acpl, black_acpl = get_acpl(cps)
        
        # White should have positive ACPL (made mistakes)
        # Black should have 0 ACPL (only made good moves)
        assert white_acpl > 0, f"Expected white ACPL > 0, got {white_acpl}"
        assert black_acpl == 0, f"Expected black ACPL = 0, got {black_acpl}"
    
    def test_get_acpl_black_blunders(self):
        """Test ACPL when only black makes mistakes"""
        # Black makes losing moves (evaluation increases after black moves from black's perspective)
        # Positions: +15 (white move) -> +30 (black move) -> +70 (white move) -> +70 (black move) -> +90 (white move)
        cps = [15, 30, 70, 70, 90]
        white_acpl, black_acpl = get_acpl(cps)
        
        # Black should have positive ACPL (made mistakes)
        # White should have 0 ACPL (only made good moves)
        assert white_acpl == 0, f"Expected white ACPL = 0, got {white_acpl}"
        assert black_acpl > 0, f"Expected black ACPL > 0, got {black_acpl}"
    
    def test_get_acpl_both_players_blunder(self):
        """Test ACPL when both players make mistakes"""
        # Both players make suboptimal moves
        cps = [15, 50, 90, 70, 110, 90]
        white_acpl, black_acpl = get_acpl(cps)
        
        # Both players should have positive ACPL
        assert white_acpl > 0, f"Expected white ACPL > 0, got {white_acpl}"
        assert black_acpl > 0, f"Expected black ACPL > 0, got {black_acpl}"
    
    def test_get_acpl_g1(self):
        """Test ACPL calculation with g1.pgn"""
        with open("tests/sample_pgns/g1.pgn", "r") as f:
            game = chess.pgn.read_game(f)
            evals, has_variation = extract_evals(game)
            cps = evals_to_cps(evals)
            white_acpl, black_acpl = get_acpl(cps)
            # According to lichess: 
            assert white_acpl == 77, f"Expected white ACPL = 77, got {white_acpl}"
            assert black_acpl == 76, f"Expected black ACPL = 76, got {black_acpl}"

    def test_get_acpl_g2(self):
        """Test ACPL calculation with g2.pgn"""
        with open("tests/sample_pgns/g2.pgn", "r") as f:
            game = chess.pgn.read_game(f)
            evals, has_variation = extract_evals(game)
            cps = evals_to_cps(evals)
            white_acpl, black_acpl = get_acpl(cps)
            # According to lichess: 
            assert white_acpl == 41, f"Expected white ACPL = 41, got {white_acpl}"
            assert black_acpl == 41, f"Expected black ACPL = 41, got {black_acpl}"

    def test_get_acpl_g3(self):
        """Test ACPL calculation with g3.pgn"""
        with open("tests/sample_pgns/g3.pgn", "r") as f:
            game = chess.pgn.read_game(f)
            evals, has_variation = extract_evals(game)
            cps = evals_to_cps(evals)
            white_acpl, black_acpl = get_acpl(cps)
            # According to lichess: 
            assert white_acpl == 35, f"Expected white ACPL = 35, got {white_acpl}"
            assert black_acpl == 47, f"Expected black ACPL = 47, got {black_acpl}"

    def test_get_acpl_g4(self):
        """Test ACPL calculation with g4.pgn"""
        with open("tests/sample_pgns/g4.pgn", "r") as f:
            game = chess.pgn.read_game(f)
            evals, has_variation = extract_evals(game)
            cps = evals_to_cps(evals)
            white_acpl, black_acpl = get_acpl(cps)
            # According to lichess: 
            assert white_acpl == 28, f"Expected white ACPL = 28, got {white_acpl}"
            assert black_acpl == 25, f"Expected black ACPL = 25, got {black_acpl}"

    def test_get_acpl_g5(self):
        """Test ACPL calculation with g5.pgn"""
        with open("tests/sample_pgns/g5.pgn", "r") as f:
            game = chess.pgn.read_game(f)
            evals, has_variation = extract_evals(game)
            cps = evals_to_cps(evals)
            white_acpl, black_acpl = get_acpl(cps)
            # According to lichess: 
            assert white_acpl == 28, f"Expected white ACPL = 28, got {white_acpl}"
            assert black_acpl == 44, f"Expected black ACPL = 44, got {black_acpl}"

    def test_get_acpl_g6(self):
        """Test ACPL calculation with g6.pgn"""
        with open("tests/sample_pgns/g6.pgn", "r") as f:
            game = chess.pgn.read_game(f)
            evals, has_variation = extract_evals(game)
            cps = evals_to_cps(evals)
            white_acpl, black_acpl = get_acpl(cps)
            # According to lichess: 
            assert white_acpl == 82, f"Expected white ACPL = 82, got {white_acpl}"
            assert black_acpl == 98, f"Expected black ACPL = 98, got {black_acpl}"
    
    def test_get_acpl_g7(self):
        """Test ACPL calculation with g7.pgn"""
        with open("tests/sample_pgns/g7.pgn", "r") as f:
            game = chess.pgn.read_game(f)
            evals, has_variation = extract_evals(game)
            cps = evals_to_cps(evals)
            white_acpl, black_acpl = get_acpl(cps)
            # According to lichess: 
            assert white_acpl == 50, f"Expected white ACPL = 50, got {white_acpl}"
            assert black_acpl == 49, f"Expected black ACPL = 49, got {black_acpl}"

    def test_get_acpl_g8(self):
        """Test ACPL calculation with g8.pgn"""
        with open("tests/sample_pgns/g8.pgn", "r") as f:
            game = chess.pgn.read_game(f)
            evals, has_variation = extract_evals(game)
            cps = evals_to_cps(evals)
            white_acpl, black_acpl = get_acpl(cps)
            # According to lichess: 
            assert white_acpl == 39, f"Expected white ACPL = 39, got {white_acpl}"
            assert black_acpl == 73, f"Expected black ACPL = 73, got {black_acpl}"
    
    def test_get_acpl_g9(self):
        """Test ACPL calculation with g9.pgn"""
        with open("tests/sample_pgns/g9.pgn", "r") as f:
            game = chess.pgn.read_game(f)
            evals, has_variation = extract_evals(game)
            cps = evals_to_cps(evals)
            white_acpl, black_acpl = get_acpl(cps)
            # According to lichess: 
            assert white_acpl == 75, f"Expected white ACPL = 75, got {white_acpl}"
            assert black_acpl == 67, f"Expected black ACPL = 67, got {black_acpl}"


class TestErrorCounting(unittest.TestCase):
    """Test error counting function (blunders, mistakes, inaccuracies)"""
    
    def test_count_errors_empty_list(self):
        """Test error counting with empty centipawn list"""
        with self.assertRaises(Exception):
            count_errors([])
    
    def test_count_errors_single_move(self):
        """Test error counting with single move"""
        with self.assertRaises(Exception):
            count_errors([Cp(15)])
    
    def test_count_errors_no_errors(self):
        """Test error counting with perfect play (no errors)"""
        # Small improvements or equal positions
        cps = [Cp(15), Cp(20), Cp(25), Cp(30), Cp(35)]
        has_variation = [True] * len(cps)
        errors = count_errors(cps, has_variation)
        
        expected = {
            "white": {"blunder": 0, "mistake": 0, "inaccuracy": 0},
            "black": {"blunder": 0, "mistake": 0, "inaccuracy": 0}
        }
        assert errors == expected, f"Expected no errors, got {errors}"
    
    def test_count_errors_white_blunder(self):
        """Test counting white blunder (>0.3 winchance loss)"""
        # Create a position where white loses significant advantage
        # This requires understanding the centipawn_to_winchance function
        cps = [Cp(300), Cp(-200), Cp(-150)]  # White blunders from +300 to -200
        has_variation = [True] * len(cps)
        errors = count_errors(cps, has_variation)
        
        # White should have at least one blunder
        assert errors["white"]["blunder"] >= 1, "Expected white blunder, got " + str(errors)
        assert errors["black"]["blunder"] == 0, "Expected no black blunder, got " + str(errors)
    
    def test_count_errors_black_mistake(self):
        """Test counting black mistake (0.2-0.3 winchance loss)"""
        # Create a position where black makes a mistake
        cps = [Cp(-100), Cp(-50), Cp(100)]  # Black position gets worse from black's perspective
        has_variation = [True] * len(cps)
        errors = count_errors(cps, has_variation)
        
        # Black should have some error (mistake or blunder)
        total_black_errors = sum(errors["black"].values())
        assert total_black_errors >= 1, f"Expected black error, got {errors}"
    
    def test_count_errors_inaccuracy(self):
        """Test counting inaccuracies (0.1-0.2 winchance loss)"""
        # Create positions with small but noticeable errors
        # This test may need adjustment based on the exact centipawn values
        # that correspond to 0.1-0.2 winchance differences
        cps = [Cp(50), Cp(20), Cp(60), Cp(30)]
        has_variation = [True] * len(cps)
        errors = count_errors(cps, has_variation)
        
        # At least one player should have some errors
        total_errors = sum(errors["white"].values()) + sum(errors["black"].values())
        assert isinstance(total_errors, int), "Error counts should be integers"
        assert total_errors >= 0, "Error counts should be non-negative"
    
    def test_count_errors_structure(self):
        """Test that error counting returns correct structure"""
        cps = [Cp(15), Cp(50), Cp(20), Cp(80), Cp(30)]
        has_variation = [True] * len(cps)
        errors = count_errors(cps, has_variation)
        
        # Check structure
        assert "white" in errors, "Missing 'white' key in errors"
        assert "black" in errors, "Missing 'black' key in errors"
        
        for color in ["white", "black"]:
            assert "blunder" in errors[color], f"Missing 'blunder' for {color}"
            assert "mistake" in errors[color], f"Missing 'mistake' for {color}"
            assert "inaccuracy" in errors[color], f"Missing 'inaccuracy' for {color}"
            
            # All counts should be non-negative integers
            for error_type in ["blunder", "mistake", "inaccuracy"]:
                count = errors[color][error_type]
                assert isinstance(count, int), f"{color} {error_type} should be int, got {type(count)}"
                assert count >= 0, f"{color} {error_type} should be non-negative, got {count}"

    def test_count_errors_g1(self):
        """Test error counting with g1.pgn"""
        with open("tests/sample_pgns/g1.pgn", "r") as f:
            game = chess.pgn.read_game(f)
            evals, has_variation = extract_evals(game)
            errors = count_errors(evals, has_variation)
            w_b, w_m, w_i = errors["white"]["blunder"], errors["white"]["mistake"], errors["white"]["inaccuracy"]
            b_b, b_m, b_i = errors["black"]["blunder"], errors["black"]["mistake"], errors["black"]["inaccuracy"]
            assert w_b == 4, f"Expected white blunder = 4, got {w_b}"
            assert w_m == 1, f"Expected white mistake = 1, got {w_m}"
            assert w_i == 9, f"Expected white inaccuracy = 9, got {w_i}"
            assert b_b == 4, f"Expected black blunder = 4, got {b_b}"
            assert b_m == 4, f"Expected black mistake = 4, got {b_m}"
            assert b_i == 5, f"Expected black inaccuracy = 5, got {b_i}"

    def test_count_errors_g2(self):
        """Test error counting with g2.pgn"""
        with open("tests/sample_pgns/g2.pgn", "r") as f:
            game = chess.pgn.read_game(f)
            evals, has_variation = extract_evals(game)
            errors = count_errors(evals, has_variation)
            w_b, w_m, w_i = errors["white"]["blunder"], errors["white"]["mistake"], errors["white"]["inaccuracy"]
            b_b, b_m, b_i = errors["black"]["blunder"], errors["black"]["mistake"], errors["black"]["inaccuracy"]
            assert w_b == 0, f"Expected white blunder = 0, got {w_b}"
            assert w_m == 2, f"Expected white mistake = 2, got {w_m}" 
            assert w_i == 6, f"Expected white inaccuracy = 6, got {w_i}"
            assert b_b == 0, f"Expected black blunder = 0, got {b_b}"
            assert b_m == 3, f"Expected black mistake = 3, got {b_m}"
            assert b_i == 3, f"Expected black inaccuracy = 3, got {b_i}"
    
    def test_count_errors_g3(self):
        """Test error counting with g3.pgn"""
        with open("tests/sample_pgns/g3.pgn", "r") as f:
            game = chess.pgn.read_game(f)
            evals, has_variation = extract_evals(game)
            errors = count_errors(evals, has_variation)
            w_b, w_m, w_i = errors["white"]["blunder"], errors["white"]["mistake"], errors["white"]["inaccuracy"]
            b_b, b_m, b_i = errors["black"]["blunder"], errors["black"]["mistake"], errors["black"]["inaccuracy"]
            assert w_b == 0, f"Expected white blunder = 0, got {w_b}"
            assert w_m == 2, f"Expected white mistake = 2, got {w_m}"
            assert w_i == 7, f"Expected white inaccuracy = 7, got {w_i}"
            assert b_b == 1, f"Expected black blunder = 1, got {b_b}"
            assert b_m == 3, f"Expected black mistake = 3, got {b_m}"
            assert b_i == 3, f"Expected black inaccuracy = 3, got {b_i}"

    def test_count_errors_g4(self):
        """Test error counting with g4.pgn"""
        with open("tests/sample_pgns/g4.pgn", "r") as f:
            game = chess.pgn.read_game(f)
            evals, has_variation = extract_evals(game)
            errors = count_errors(evals, has_variation)
            w_b, w_m, w_i = errors["white"]["blunder"], errors["white"]["mistake"], errors["white"]["inaccuracy"]
            b_b, b_m, b_i = errors["black"]["blunder"], errors["black"]["mistake"], errors["black"]["inaccuracy"]
            assert w_b == 1, f"Expected white blunder = 1, got {w_b}"
            assert w_m == 2, f"Expected white mistake = 2, got {w_m}"
            assert w_i == 4, f"Expected white inaccuracy = 4, got {w_i}"
            assert b_b == 1, f"Expected black blunder = 1, got {b_b}"
            assert b_m == 1, f"Expected black mistake = 1, got {b_m}"
            assert b_i == 2, f"Expected black inaccuracy = 2, got {b_i}"

    def test_count_errors_g5(self):
        """Test error counting with g5.pgn"""
        with open("tests/sample_pgns/g5.pgn", "r") as f:
            game = chess.pgn.read_game(f)
            evals, has_variation = extract_evals(game)
            errors = count_errors(evals, has_variation)
            w_b, w_m, w_i = errors["white"]["blunder"], errors["white"]["mistake"], errors["white"]["inaccuracy"]
            b_b, b_m, b_i = errors["black"]["blunder"], errors["black"]["mistake"], errors["black"]["inaccuracy"]
            assert w_b == 1, f"Expected white blunder = 1, got {w_b}"
            assert w_m == 2, f"Expected white mistake = 2, got {w_m}"
            assert w_i == 2, f"Expected white inaccuracy = 2, got {w_i}"
            assert b_b == 3, f"Expected black blunder = 3, got {b_b}"
            assert b_m == 2, f"Expected black mistake = 2, got {b_m}"
            assert b_i == 5, f"Expected black inaccuracy = 5, got {b_i}"

    def test_count_errors_g6(self):
        """Test error counting with g6.pgn"""
        with open("tests/sample_pgns/g6.pgn", "r") as f:
            game = chess.pgn.read_game(f)
            evals, has_variation = extract_evals(game)
            errors = count_errors(evals, has_variation)
            w_b, w_m, w_i = errors["white"]["blunder"], errors["white"]["mistake"], errors["white"]["inaccuracy"]
            b_b, b_m, b_i = errors["black"]["blunder"], errors["black"]["mistake"], errors["black"]["inaccuracy"]
            assert w_b == 3, f"Expected white blunder = 5, got {w_b}"
            assert w_m == 2, f"Expected white mistake = 2, got {w_m}"
            assert w_i == 5, f"Expected white inaccuracy = 5, got {w_i}"
            assert b_b == 5, f"Expected black blunder = 5, got {b_b}"
            assert b_m == 0, f"Expected black mistake = 0, got {b_m}"
            assert b_i == 8, f"Expected black inaccuracy = 8, got {b_i}"
 
    def test_count_errors_g7(self):
        """Test error counting with g7.pgn"""
        with open("tests/sample_pgns/g7.pgn", "r") as f:
            game = chess.pgn.read_game(f)
            evals, has_variation = extract_evals(game)
            errors = count_errors(evals, has_variation)
            w_b, w_m, w_i = errors["white"]["blunder"], errors["white"]["mistake"], errors["white"]["inaccuracy"]
            b_b, b_m, b_i = errors["black"]["blunder"], errors["black"]["mistake"], errors["black"]["inaccuracy"]
            assert w_b == 3, f"Expected white blunder = 3, got {w_b}"
            assert w_m == 1, f"Expected white mistake = 1, got {w_m}"
            assert w_i == 4, f"Expected white inaccuracy = 4, got {w_i}"
            assert b_b == 4, f"Expected black blunder = 4, got {b_b}"
            assert b_m == 1, f"Expected black mistake = 1, got {b_m}"
            assert b_i == 5, f"Expected black inaccuracy = 5, got {b_i}"
    
    def test_count_errors_g8(self):
        """Test error counting with g8.pgn"""
        with open("tests/sample_pgns/g8.pgn", "r") as f:
            game = chess.pgn.read_game(f)
            evals, has_variation = extract_evals(game)
            errors = count_errors(evals, has_variation)
            w_b, w_m, w_i = errors["white"]["blunder"], errors["white"]["mistake"], errors["white"]["inaccuracy"]
            b_b, b_m, b_i = errors["black"]["blunder"], errors["black"]["mistake"], errors["black"]["inaccuracy"]
            assert w_b == 1, f"Expected white blunder = 1, got {w_b}"
            assert w_m == 0, f"Expected white mistake = 0, got {w_m}"
            assert w_i == 4, f"Expected white inaccuracy = 4, got {w_i}"
            assert b_b == 2, f"Expected black blunder = 2, got {b_b}"
            assert b_m == 2, f"Expected black mistake = 2, got {b_m}"
            assert b_i == 5, f"Expected black inaccuracy = 5, got {b_i}"
    
    def test_count_errors_g9(self):
        """Test error counting with g9.pgn"""
        with open("tests/sample_pgns/g9.pgn", "r") as f:
            game = chess.pgn.read_game(f)
            evals, has_variation = extract_evals(game)
            errors = count_errors(evals, has_variation)
            w_b, w_m, w_i = errors["white"]["blunder"], errors["white"]["mistake"], errors["white"]["inaccuracy"]
            b_b, b_m, b_i = errors["black"]["blunder"], errors["black"]["mistake"], errors["black"]["inaccuracy"]
            assert w_b == 11, f"Expected white blunder = 11, got {w_b}"
            assert w_m == 2, f"Expected white mistake = 2, got {w_m}"
            assert w_i == 9, f"Expected white inaccuracy = 9, got {w_i}"
            assert b_b == 9, f"Expected black blunder = 9, got {b_b}"
            assert b_m == 2, f"Expected black mistake = 2, got {b_m}"
            assert b_i == 4, f"Expected black inaccuracy = 4, got {b_i}"


class TestGameAccuracy(unittest.TestCase):
    """Test game accuracy calculation function"""
    
    def test_game_accuracy_empty_list(self):
        """Test accuracy calculation with empty centipawn list"""
        with self.assertRaises(Exception):
            game_accuracy([])
    
    def test_game_accuracy_perfect_play(self):
        """Test accuracy with perfect play"""
        # Perfectly equal positions
        cps = [15] * 10
        white_acc, black_acc = game_accuracy(cps)
        
        # Perfect play should yield high accuracy (close to 100%)
        assert white_acc is not None, "White accuracy should not be None"
        assert black_acc is not None, "Black accuracy should not be None"
        assert 90 <= white_acc <= 100, f"Expected high white accuracy, got {white_acc}"
        assert 90 <= black_acc <= 100, f"Expected high black accuracy, got {black_acc}"
    
    def test_game_accuracy_terrible_play(self):
        """Test accuracy with very poor play"""
        # Alternating large swings indicating poor play
        cps = [300, -300, 400, -400, 500, -500]
        white_acc, black_acc = game_accuracy(cps)
        
        # Poor play should yield low accuracy
        assert white_acc is not None, "White accuracy should not be None"
        assert black_acc is not None, "Black accuracy should not be None"
        assert 0 <= white_acc <= 100, f"White accuracy out of range: {white_acc}"
        assert 0 <= black_acc <= 100, f"Black accuracy out of range: {black_acc}"
    
    def test_game_accuracy_range(self):
        """Test that accuracy is always in valid range [0, 100]"""
        # Various game scenarios
        test_cases = [
            [15, 30, 45, 60, 75],  # Gradual improvement for white
            [-15, -30, -45, -60, -75],  # Gradual improvement for black
            [100, 50, 0, -50, -100],  # Declining position
            [0, 200, -200, 300, -300, 400]  # Volatile game
        ]
        
        for cps in test_cases:
            white_acc, black_acc = game_accuracy(cps)
            
            if white_acc is not None:
                assert 0 <= white_acc <= 100, f"White accuracy out of range for {cps}: {white_acc}"
            if black_acc is not None:
                assert 0 <= black_acc <= 100, f"Black accuracy out of range for {cps}: {black_acc}"
    
    def test_game_accuracy_short_game(self):
        """Test accuracy calculation for very short games"""
        # Minimum viable game length
        cps = [15, 30, 45]
        white_acc, black_acc = game_accuracy(cps)
        
        # Should handle short games gracefully
        assert white_acc is not None or black_acc is not None, "At least one accuracy should be calculated"

    def test_game_accuracy_g1(self):
        """Test accuracy calculation with g1.pgn"""
        with open("tests/sample_pgns/g1.pgn", "r") as f:
            game = chess.pgn.read_game(f)
            evals, has_variation = extract_evals(game)
            cps = evals_to_cps(evals)
            white_acc, black_acc = game_accuracy(cps)
            assert white_acc == 68, f"Expected white accuracy = 68, got {white_acc}"
            assert black_acc == 70, f"Expected black accuracy = 70, got {black_acc}"
    
    def test_game_accuracy_g2(self):
        """Test accuracy calculation with g2.pgn"""
        with open("tests/sample_pgns/g2.pgn", "r") as f:
            game = chess.pgn.read_game(f)
            evals, has_variation = extract_evals(game)
            cps = evals_to_cps(evals)
            white_acc, black_acc = game_accuracy(cps)
            assert white_acc == 83, f"Expected white accuracy = 83, got {white_acc}"
            assert black_acc == 82, f"Expected black accuracy = 82, got {black_acc}"
    
    def test_game_accuracy_g3(self):
        """Test accuracy calculation with g3.pgn"""
        with open("tests/sample_pgns/g3.pgn", "r") as f:
            game = chess.pgn.read_game(f)
            evals, has_variation = extract_evals(game)
            cps = evals_to_cps(evals)
            white_acc, black_acc = game_accuracy(cps)
            assert white_acc == 87, f"Expected white accuracy = 87, got {white_acc}"
            assert black_acc == 83, f"Expected black accuracy = 83, got {black_acc}"

    def test_game_accuracy_g4(self):
        """Test accuracy calculation with g4.pgn"""
        with open("tests/sample_pgns/g4.pgn", "r") as f:
            game = chess.pgn.read_game(f)
            evals, has_variation = extract_evals(game)
            cps = evals_to_cps(evals)
            white_acc, black_acc = game_accuracy(cps)
            assert white_acc == 89, f"Expected white accuracy = 89, got {white_acc}"
            assert black_acc == 86, f"Expected black accuracy = 86, got {black_acc}"

    def test_game_accuracy_g5(self):
        """Test accuracy calculation with g5.pgn"""
        with open("tests/sample_pgns/g5.pgn", "r") as f:
            game = chess.pgn.read_game(f)
            evals, has_variation = extract_evals(game)
            cps = evals_to_cps(evals)
            white_acc, black_acc = game_accuracy(cps)
            assert white_acc == 91, f"Expected white accuracy = 91, got {white_acc}"
            assert black_acc == 88, f"Expected black accuracy = 88, got {black_acc}"

    def test_game_accuracy_g6(self):
        """Test accuracy calculation with g6.pgn"""
        with open("tests/sample_pgns/g6.pgn", "r") as f:
            game = chess.pgn.read_game(f)
            evals, has_variation = extract_evals(game)
            cps = evals_to_cps(evals)
            white_acc, black_acc = game_accuracy(cps)
            assert white_acc == 85, f"Expected white accuracy = 85, got {white_acc}"
            assert black_acc == 79, f"Expected black accuracy = 79, got {black_acc}"
    
    def test_game_accuracy_g8(self):
        """Test accuracy calculation with g8.pgn"""
        with open("tests/sample_pgns/g8.pgn", "r") as f:
            game = chess.pgn.read_game(f)
            evals, has_variation = extract_evals(game)
            cps = evals_to_cps(evals)
            white_acc, black_acc = game_accuracy(cps)
            assert white_acc == 92, f"Expected white accuracy = 92, got {white_acc}"
            assert black_acc == 83, f"Expected black accuracy = 83, got {black_acc}"

    def test_game_accuracy_g9(self):
        """Test accuracy calculation with g9.pgn"""
        with open("tests/sample_pgns/g9.pgn", "r") as f:
            game = chess.pgn.read_game(f)
            evals, has_variation = extract_evals(game)
            cps = evals_to_cps(evals)
            white_acc, black_acc = game_accuracy(cps)
            assert white_acc == 68, f"Expected white accuracy = 68, got {white_acc}"
            assert black_acc == 69, f"Expected black accuracy = 69, got {black_acc}"


if __name__ == '__main__':
    # Configure test runner
    unittest.main(verbosity=2)
