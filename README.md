# mlb-underdogs

## Methodology:

This model aims to find valuable MLB underdog moneylines by generating its own moneylines for every game each day and comparing those against the lines
offered by DraftKings, in real time. It uses the two teams run differentials over the last five games, and the dollar value of a singular run, to construct its own
moneyline for each game. Underdogs which have at least +10pts of value are returned - meaning the line offered on DraftKings is at least 10pts above the generated
moneyline, suggesting the line has good value. The model tends to perform better picking "small upsets" than "large upsets".

## Two Models:

#### last_five_games.py:
- Uses a fixed lookback window of last five games
- Outputs underdogs whose lines show "good value" based on L5 games ML

#### last_n_games.py:
- Creates eight moneylines for each game, one for each lookback window from 3 games - 10 games
- Outputs a plot for each game, overlaying the DraftKings moneyline, the models L5 game moneyline, and how the models moneyline changes by lookback window

## Model Picks & Performance: [Link](https://www.jacktonina.com/mlb-underdog-tracker.html)

## Inspiration:
"Betting on Major League Baseball" by Ken Osterman
