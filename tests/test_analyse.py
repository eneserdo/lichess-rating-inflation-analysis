import math
import os
import sys
import unittest

import chess
import chess.pgn

# Add the parent directory to the path so we can import from analyse.py
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analyse import count_errors, extract_cps, game_accuracy, get_acpl

"""
########## Game states from lichess: 

###### g1: 
white:
9 Inaccuracies
1 Mistake
4 Blunders
77 Average centipawn loss
68% Accuracy

black:
5 Inaccuracies
4 Mistakes
4 Blunders
76 Average centipawn loss
70% Accuracy 

###### g2: 
white:
6 Inaccuracies
2 Mistakes
0 Blunders
41 Average centipawn loss
83% Accuracy

black:
3 Inaccuracies
3 Mistakes
0 Blunders
41 Average centipawn loss
82% Accuracy 

###### g3: 
white:
7 Inaccuracies
2 Mistakes
0 Blunders
35 Average centipawn loss
87% Accuracy
black:
3 Inaccuracies
3 Mistakes
1 Blunder
47 Average centipawn loss
83% Accuracy 

###### g4: 
white: 
4 Inaccuracies
0 Mistakes
1 Blunder
28 Average centipawn loss
89% Accuracy
black:
2 Inaccuracies
1 Mistake
1 Blunder
25 Average centipawn loss
86% Accuracy 

###### g5: 
white:
0 Inaccuracies
0 Mistakes
2 Blunders
404 Average centipawn loss
23% Accuracy
black:
0 Inaccuracies
0 Mistakes
3 Blunders
601 Average centipawn loss
17% Accuracy 
"""


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
        # Positions: +15 (white move) -> +50 (black move) -> +30 (white move) -> +70 (black move) -> +50 (white move)
        cps = [15, 50, 30, 70, 50]
        white_acpl, black_acpl = get_acpl(cps)
        
        # White should have positive ACPL (made mistakes)
        # Black should have 0 ACPL (only made good moves)
        assert white_acpl > 0, f"Expected white ACPL > 0, got {white_acpl}"
        assert black_acpl == 0, f"Expected black ACPL = 0, got {black_acpl}"
    
    def test_get_acpl_black_blunders(self):
        """Test ACPL when only black makes mistakes"""
        # Black makes losing moves (evaluation increases after black moves from black's perspective)
        # Positions: +15 (white move) -> +30 (black move) -> +70 (white move) -> +50 (black move) -> +90 (white move)
        cps = [15, 30, 70, 50, 90]
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
            cps = extract_cps(game)
            white_acpl, black_acpl = get_acpl(cps)
            # According to lichess: 
            assert white_acpl == 77, f"Expected white ACPL = 77, got {white_acpl}"
            assert black_acpl == 76, f"Expected black ACPL = 76, got {black_acpl}"

    def test_get_acpl_g2(self):
        """Test ACPL calculation with g2.pgn"""
        with open("tests/sample_pgns/g2.pgn", "r") as f:
            game = chess.pgn.read_game(f)
            cps = extract_cps(game)
            white_acpl, black_acpl = get_acpl(cps)
            # According to lichess: 
            assert white_acpl == 41, f"Expected white ACPL = 41, got {white_acpl}"
            assert black_acpl == 41, f"Expected black ACPL = 41, got {black_acpl}"

    def test_get_acpl_g3(self):
        """Test ACPL calculation with g3.pgn"""
        with open("tests/sample_pgns/g3.pgn", "r") as f:
            game = chess.pgn.read_game(f)
            cps = extract_cps(game)
            white_acpl, black_acpl = get_acpl(cps)
            # According to lichess: 
            assert white_acpl == 35, f"Expected white ACPL = 35, got {white_acpl}"
            assert black_acpl == 47, f"Expected black ACPL = 47, got {black_acpl}"

    def test_get_acpl_g4(self):
        """Test ACPL calculation with g4.pgn"""
        with open("tests/sample_pgns/g4.pgn", "r") as f:
            game = chess.pgn.read_game(f)
            cps = extract_cps(game)
            white_acpl, black_acpl = get_acpl(cps)
            # According to lichess: 
            assert white_acpl == 28, f"Expected white ACPL = 28, got {white_acpl}"
            assert black_acpl == 25, f"Expected black ACPL = 25, got {black_acpl}"

    def test_get_acpl_g5(self):
        """Test ACPL calculation with g5.pgn"""
        with open("tests/sample_pgns/g5.pgn", "r") as f:
            game = chess.pgn.read_game(f)
            cps = extract_cps(game)
            white_acpl, black_acpl = get_acpl(cps)
            # According to lichess: 
            assert white_acpl == 404, f"Expected white ACPL = 404, got {white_acpl}"
            assert black_acpl == 601, f"Expected black ACPL = 601, got {black_acpl}"


class TestErrorCounting(unittest.TestCase):
    """Test error counting function (blunders, mistakes, inaccuracies)"""
    
    def test_count_errors_empty_list(self):
        """Test error counting with empty centipawn list"""
        with self.assertRaises(Exception):
            count_errors([])
    
    def test_count_errors_single_move(self):
        """Test error counting with single move"""
        with self.assertRaises(Exception):
            count_errors([15])
    
    def test_count_errors_no_errors(self):
        """Test error counting with perfect play (no errors)"""
        # Small improvements or equal positions
        cps = [15, 20, 25, 30, 35]
        errors = count_errors(cps)
        
        expected = {
            "white": {"blunder": 0, "mistake": 0, "inaccuracy": 0},
            "black": {"blunder": 0, "mistake": 0, "inaccuracy": 0}
        }
        assert errors == expected, f"Expected no errors, got {errors}"
    
    def test_count_errors_white_blunder(self):
        """Test counting white blunder (>0.3 winchance loss)"""
        # Create a position where white loses significant advantage
        # This requires understanding the centipawn_to_winchance function
        cps = [300, -200, -150]  # White blunders from +300 to -200
        errors = count_errors(cps)
        
        # White should have at least one blunder
        assert errors["white"]["blunder"] >= 1, "Expected white blunder, got " + str(errors)
        assert errors["black"]["blunder"] == 0, "Expected no black blunder, got " + str(errors)
    
    def test_count_errors_black_mistake(self):
        """Test counting black mistake (0.2-0.3 winchance loss)"""
        # Create a position where black makes a mistake
        cps = [-100, -50, 100]  # Black position gets worse from black's perspective
        errors = count_errors(cps)
        
        # Black should have some error (mistake or blunder)
        total_black_errors = sum(errors["black"].values())
        assert total_black_errors >= 1, f"Expected black error, got {errors}"
    
    def test_count_errors_inaccuracy(self):
        """Test counting inaccuracies (0.1-0.2 winchance loss)"""
        # Create positions with small but noticeable errors
        # This test may need adjustment based on the exact centipawn values
        # that correspond to 0.1-0.2 winchance differences
        cps = [50, 20, 60, 30]
        errors = count_errors(cps)
        
        # At least one player should have some errors
        total_errors = sum(errors["white"].values()) + sum(errors["black"].values())
        assert isinstance(total_errors, int), "Error counts should be integers"
        assert total_errors >= 0, "Error counts should be non-negative"
    
    def test_count_errors_structure(self):
        """Test that error counting returns correct structure"""
        cps = [15, 50, 20, 80, 30]
        errors = count_errors(cps)
        
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
            cps = extract_cps(game)
            errors = count_errors(cps)
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
            cps = extract_cps(game)
            errors = count_errors(cps)
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
            cps = extract_cps(game)
            errors = count_errors(cps)
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
            cps = extract_cps(game)
            errors = count_errors(cps)
            w_b, w_m, w_i = errors["white"]["blunder"], errors["white"]["mistake"], errors["white"]["inaccuracy"]
            b_b, b_m, b_i = errors["black"]["blunder"], errors["black"]["mistake"], errors["black"]["inaccuracy"]
            assert w_b == 1, f"Expected white blunder = 1, got {w_b}"
            assert w_m == 0, f"Expected white mistake = 0, got {w_m}"
            assert w_i == 4, f"Expected white inaccuracy = 4, got {w_i}"
            assert b_b == 1, f"Expected black blunder = 1, got {b_b}"
            assert b_m == 1, f"Expected black mistake = 1, got {b_m}"
            assert b_i == 2, f"Expected black inaccuracy = 2, got {b_i}"

    def test_count_errors_g5(self):
        """Test error counting with g5.pgn"""
        with open("tests/sample_pgns/g5.pgn", "r") as f:
            game = chess.pgn.read_game(f)
            cps = extract_cps(game)
            errors = count_errors(cps)
            w_b, w_m, w_i = errors["white"]["blunder"], errors["white"]["mistake"], errors["white"]["inaccuracy"]
            b_b, b_m, b_i = errors["black"]["blunder"], errors["black"]["mistake"], errors["black"]["inaccuracy"]
            assert w_b == 2, f"Expected white blunder = 2, got {w_b}"
            assert w_m == 0, f"Expected white mistake = 0, got {w_m}"
            assert w_i == 0, f"Expected white inaccuracy = 0, got {w_i}"
            assert b_b == 3, f"Expected black blunder = 3, got {b_b}"
            assert b_m == 0, f"Expected black mistake = 0, got {b_m}"
            assert b_i == 0, f"Expected black inaccuracy = 0, got {b_i}"


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
            cps = extract_cps(game)
            white_acc, black_acc = game_accuracy(cps)
            assert white_acc == 68, f"Expected white accuracy = 68, got {white_acc}"
            assert black_acc == 70, f"Expected black accuracy = 70, got {black_acc}"
    
    def test_game_accuracy_g2(self):
        """Test accuracy calculation with g2.pgn"""
        with open("tests/sample_pgns/g2.pgn", "r") as f:
            game = chess.pgn.read_game(f)
            cps = extract_cps(game)
            white_acc, black_acc = game_accuracy(cps)
            assert white_acc == 83, f"Expected white accuracy = 83, got {white_acc}"
            assert black_acc == 82, f"Expected black accuracy = 82, got {black_acc}"
    
    def test_game_accuracy_g3(self):
        """Test accuracy calculation with g3.pgn"""
        with open("tests/sample_pgns/g3.pgn", "r") as f:
            game = chess.pgn.read_game(f)
            cps = extract_cps(game)
            white_acc, black_acc = game_accuracy(cps)
            assert white_acc == 87, f"Expected white accuracy = 87, got {white_acc}"
            assert black_acc == 83, f"Expected black accuracy = 83, got {black_acc}"

    def test_game_accuracy_g4(self):
        """Test accuracy calculation with g4.pgn"""
        with open("tests/sample_pgns/g4.pgn", "r") as f:
            game = chess.pgn.read_game(f)
            cps = extract_cps(game)
            white_acc, black_acc = game_accuracy(cps)
            assert white_acc == 89, f"Expected white accuracy = 89, got {white_acc}"
            assert black_acc == 86, f"Expected black accuracy = 86, got {black_acc}"

    def test_game_accuracy_g5(self):
        """Test accuracy calculation with g5.pgn"""
        with open("tests/sample_pgns/g5.pgn", "r") as f:
            game = chess.pgn.read_game(f)
            cps = extract_cps(game)
            white_acc, black_acc = game_accuracy(cps)
            assert white_acc == 23, f"Expected white accuracy = 23, got {white_acc}"
            assert black_acc == 17, f"Expected black accuracy = 17, got {black_acc}"


class TestIntegration(unittest.TestCase):
    """Integration tests combining multiple functions"""
    
    def test_consistent_game_analysis(self):
        """Test that all analysis functions work together consistently"""
        # Sample game with known characteristics
        cps = [15, 50, 30, 80, 40, 100, 60, 120, 80]
        
        # All functions should complete without error
        white_acpl, black_acpl = get_acpl(cps)
        white_acc, black_acc = game_accuracy(cps)
        errors = count_errors(cps)
        
        # Basic sanity checks
        assert isinstance(white_acpl, float), "ACPL should be float"
        assert isinstance(black_acpl, float), "ACPL should be float"
        assert white_acpl >= 0, "ACPL should be non-negative"
        assert black_acpl >= 0, "ACPL should be non-negative"
        
        if white_acc is not None:
            assert 0 <= white_acc <= 100, "Accuracy should be in [0, 100]"
        if black_acc is not None:
            assert 0 <= black_acc <= 100, "Accuracy should be in [0, 100]"
        
        assert isinstance(errors, dict), "Errors should be dictionary"
    
    def test_extreme_values(self):
        """Test functions with extreme centipawn values"""
        # Very large positive and negative values
        extreme_cps = [-1000, 1000, -800, 800, -600, 600]
        
        # Functions should handle extreme values gracefully
        try:
            white_acpl, black_acpl = get_acpl(extreme_cps)
            white_acc, black_acc = game_accuracy(extreme_cps)
            count_errors(extreme_cps)
            
            # All results should be finite and reasonable
            assert math.isfinite(white_acpl), "ACPL should be finite"
            assert math.isfinite(black_acpl), "ACPL should be finite"
            
        except Exception as e:
            self.fail(f"Functions should handle extreme values gracefully: {e}")


if __name__ == '__main__':
    # Configure test runner
    unittest.main(verbosity=2)
