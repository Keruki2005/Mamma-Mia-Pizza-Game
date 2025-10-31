# Mamma Mia Pizza Game (Python)

You are Mamma Mia — an Italian mom who protects the kitchen! Use your rolling pin to slap the mafia before they reach you.

This is a small, self-contained game written with pygame. It uses simple shapes so you don't need external assets. Feel free to modify and extend it.

## Requirements

- Python 3.8+
- pygame

Install pygame with pip:

pip install -r requirements.txt

## Running

python main.py

## Controls

- Arrow keys / WASD — Move Mamma
- Space — Slap with rolling pin (has a cooldown)
- R — Restart after game over
- Esc — Quit

## Gameplay

- Mafia spawn from the edges and move toward Mamma.
- Slap them with your rolling pin to score points.
- If a mafia reaches Mamma, you lose a life.
- Game over when lives run out.

## Ideas for improvements

- Add images and sound effects (place them in an `assets/` folder and load with pygame.mixer).
- Add different mafia types (faster, tougher).
- Add power-ups (pizza power, temporary speed boost, area slap).
- Add a high-score save file.

Have fun! If you'd like, I can:
- Add graphics or place-holder images,
- Add sound effects and music hooks,
- Turn this into a package with assets,
- Add levels, boss mafia, or animations.