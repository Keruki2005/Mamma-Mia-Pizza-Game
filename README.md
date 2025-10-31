```markdown
# Mamma Mia — Improved

This version improves the visuals and behavior so mafia enemies look like distinct people:
- Faces, hair, beards, hats, and glasses
- Clothing color variety and small health bars for tougher enemies
- Walk bobbing and rolling-pin swing animation for Mom
- Knockback & daze effect on hit, with score pop-ups
- Powerups (gun, grenade) and explosion visuals retained

How to run
1. Install dependencies:
   pip install -r requirements.txt
2. Run:
   python main.py

Controls
- Arrow keys / WASD — Move Mamma
- Space — Slap with rolling pin
- F — Shoot with gun (if you have gun powerup)
- G — Throw grenade (if you have grenades)
- R — Restart after game over
- Esc — Quit

Notes & next steps you might want
- Replace the primitive drawings with real PNG sprites: the Mom and mafia draw functions have clear places where sprites can be drawn instead. Use pygame.image.load and blit with per-pixel alpha.
- Add sounds: slap, punch, gunshot, grenade bounce/explosion. Use pygame.mixer.
- Add animation frames or sprite sheet for walking & slap for extra polish.
- Add more mafia types and attacks (throwing knives, shields).
- Tweak balance: spawn rates, health, speeds.

If you'd like, I can:
- Add placeholder PNG sprites (I can include simple SVG-to-PNG conversions or programmatic placeholder images),
- Add sound effect stubs and a small assets folder layout,
- Create a settings/constants file to make tuning easier.
