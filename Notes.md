# Research Questions

1. How ratings of the players and accuracy of moves are correlated in chess?
    - How this correlation evolves over time?
    - Average move accuracy and rating which is the best estimator for player's strength?
2. Is there an inflation or deflation in ratings?
    - Definition of inflation/deflation
    - show for specific rating categories how their accuracy evolves over time
    - What might be the cause of inflation/deflation?
    - The difference between ELO system and Glicko system (there is a deflation in the ELO system)

3. Choosing a sample of players, how their ratings and accuracy evolve over time?

We are omitting some nuances of the game:
- In different game phases or when there is not much time, move accuracy might change. We are basically averaging all moves hoping that in average those effects will cancel out.

# Data/Preprocessing

I used the Lichess database to get the data, which is publicly available [here](https://database.lichess.org/).

I downloaded the games from 2015 to 2024 every 6 months. 

For the analysis, I only considered rated games played by signed users. I filtered the games where rating gain/loss is less than 15, so that rating gain/loss ...


# Analysis
I used Stockfish 17 to evaluate the moves in 20 depth. I used the 


Website: deployment? extra visualizations 
