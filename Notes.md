# Research Questions

0. Rating is just an estimation of the skill. A more fine-grained estimation might be game accuracy or number of misplays/errors.
    - Formulation of centipawns -> win percentage -> accuracy per move -> accuracy per game
    -                                             -> misplay/error count (blunder, mistake, inaccuracy)

1. How ratings of the players and accuracy of games are correlated in chess?
    - How this correlation evolves over time?
    - How much the accuracy and number of mistakes differs between players with similar ratings?
    - How much the accuracy and number of mistakes differs between, for instance, players with 1500 rating and 1700 rating? Look for rating hell.

2. Is there an inflation or deflation in ratings?
    - Definition of inflation/deflation
    - show for specific rating categories how their accuracy evolves over time
    - What might be the cause of inflation/deflation?
    - The difference between ELO system and Glicko system (there is a deflation in the ELO system)

3. Choosing a sample of players, how their ratings and accuracy evolve over time?

4. Given the game thinking time, how the accuracy of the moves differs between different rating ranges?


We are omitting some nuances of the game:
- In different game phases or when there is not much time, move accuracy might change. We are basically averaging all moves assuming that in average those effects will cancel out.

# Data/Preprocessing

I used the Lichess database to get the data, which is publicly available [here](https://database.lichess.org/).

I downloaded the games from 2017 to 2025 every 6 months. 

For the analysis, I only considered rated games played by signed users. I filtered the games where rating gain/loss is less than 15, so that rating gain/loss ...


# Analysis
I used Stockfish 17 to evaluate the moves in 25 depth. I used the 



## Free form

TL;DR: There is a significant inflation in X ratings in Y tempo. and players average accuracy does not correlate with their rating for some rating ranges.

I have been playing online chess very actively last 5 years on Lichess, and I observed suspicious increase in my ratings throughout the years. Either I was actually improving my game or there is something wrong with the rating system. Due to my strong imposter syndrome, I immediately crossed the former possibility and have decided to analyze the rating system empirically.

<!-- insert a picture of the my rating changes -->

The purpose of a rating system is to estimate the *actual skill* of the players. However, for some reasons, I believe Glicko system in Lichess is not working very well. Another reasonable estimation of skill could be the average *accuracy* of the moves. The definition or formulation of accuracy might differentiate from site to site, but in Lichess, they define it as follows:

"The Accuracy metric indicates how well you play - according to Stockfish, the strongest chess engine"

And to calculate the accuracy, they use the following formula:

First,calculate Win%

Win% = 50 + 50 * (2 / (1 + exp(-0.00368208 * centipawns)) - 1)

This function is an estimation based on real data, but it has been claimed that it may not be a good estimator for high-level players: https://chessenginelab.substack.com/p/expected-score-of-grandmasters

Then, calculate Accuracy

Accuracy% = 103.1668 * exp(-0.04354 * (winPercentBefore - winPercentAfter)) - 3.1669

for a move is how your move is close to the best move determined by Stockfish. So, assuming that accuracy is a better estimator than rating to measure the skill of a player, I have decided to analyze the average accuracy of the moves for different rating ranges.

I am aware that in "masa başı" chess, there is a slight deflation in ratings. However, Me and many redditors have felt that in online chess, there is a more significant inflation.

https://zwischenzug.substack.com/p/centipawns-suck

Elo hell