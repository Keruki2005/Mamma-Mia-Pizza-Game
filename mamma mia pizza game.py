# A simple "Mamma Mia Pizza Game" written with pygame.
# You are an Italian mom who slaps mafia people with a rolling pin.
#
# Controls:
#  - Arrow keys / WASD to move
#  - Space to slap with the rolling pin
#  - Esc to quit
#
# Requirements: pygame
# Run: python main.py

import pygame
import random
import math
import sys

# ------ Configuration ------
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60

MOM_SPEED = 4
MAFIA_MIN_SPEED = 1.0
MAFIA_MAX_SPEED = 2.5
MAFIA_SPAWN_INTERVAL = 1500  # milliseconds
SLAP_COOLDOWN = 600  # milliseconds
SLAP_DURATION = 120  # ms during which the slap is active
SLAP_RANGE = 70
SLAP_WIDTH = 40

STARTING_LIVES = 3

# Colors
BG_COLOR = (246, 222, 179)  # warm kitchen-ish
MOM_COLOR = (205, 92, 92)
MAFIA_COLOR = (40, 40, 40)
SLAP_COLOR = (194, 154, 85)
TEXT_COLOR = (20, 20, 20)

pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Mamma Mia Pizza Game")
clock = pygame.time.Clock()
font = pygame.font.SysFont("arial", 24)
big_font = pygame.font.SysFont("arial", 48)


# ------ Helper functions ------
def draw_text(surface, text, x, y, font_obj, color=TEXT_COLOR, center=False):
    surf = font_obj.render(text, True, color)
    rect = surf.get_rect()
    if center:
        rect.center = (x, y)
    else:
        rect.topleft = (x, y)
    surface.blit(surf, rect)


# ------ Game objects ------
class Mom(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.radius = 24
        self.image = pygame.Surface((self.radius * 2, self.radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(self.image, MOM_COLOR, (self.radius, self.radius), self.radius)
        self.rect = self.image.get_rect(center=(x, y))
        self.vel = pygame.Vector2(0, 0)
        self.facing = "right"  # "left" or "right"
        self.slapping = False
        self.slap_start_time = 0
        self.last_slap_time = -SLAP_COOLDOWN

    def update(self, dt, keys):
        dx = dy = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            dx -= MOM_SPEED
            self.facing = "left"
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            dx += MOM_SPEED
            self.facing = "right"
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            dy -= MOM_SPEED
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            dy += MOM_SPEED

        self.rect.x += dx
        self.rect.y += dy

        # Keep inside screen
        self.rect.left = max(0, self.rect.left)
        self.rect.right = min(SCREEN_WIDTH, self.rect.right)
        self.rect.top = max(0, self.rect.top)
        self.rect.bottom = min(SCREEN_HEIGHT, self.rect.bottom)

        # Update slap state (duration)
        if self.slapping and pygame.time.get_ticks() - self.slap_start_time > SLAP_DURATION:
            self.slapping = False

    def try_slap(self):
        now = pygame.time.get_ticks()
        if now - self.last_slap_time >= SLAP_COOLDOWN:
            self.slapping = True
            self.slap_start_time = now
            self.last_slap_time = now
            return True
        return False

    def get_slap_rect(self):
        # Create a rectangle in front of mom representing the rolling pin swing
        cx, cy = self.rect.center
        if self.facing == "right":
            slap_rect = pygame.Rect(cx + self.radius // 2, cy - SLAP_WIDTH // 2, SLAP_RANGE, SLAP_WIDTH)
        else:
            slap_rect = pygame.Rect(cx - SLAP_RANGE - self.radius // 2, cy - SLAP_WIDTH // 2, SLAP_RANGE, SLAP_WIDTH)
        return slap_rect

    def draw(self, surface):
        surface.blit(self.image, self.rect)
        # Draw a simple rolling pin when slapping (a rectangle)
        if self.slapping:
            sr = self.get_slap_rect()
            pygame.draw.rect(surface, SLAP_COLOR, sr)
        # small detail: draw eyes indicating facing
        eye_y = self.rect.top + 12
        if self.facing == "right":
            left_eye = (self.rect.centerx + 6, eye_y)
            right_eye = (self.rect.centerx + 12, eye_y)
        else:
            left_eye = (self.rect.centerx - 12, eye_y)
            right_eye = (self.rect.centerx - 6, eye_y)
        pygame.draw.circle(surface, (255, 255, 255), left_eye, 3)
        pygame.draw.circle(surface, (255, 255, 255), right_eye, 3)


class Mafia(pygame.sprite.Sprite):
    def __init__(self, x, y, speed):
        super().__init__()
        self.width = 28
        self.height = 36
        self.image = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        pygame.draw.rect(self.image, MAFIA_COLOR, (0, 0, self.width, self.height), border_radius=6)
        # draw a small hat
        pygame.draw.rect(self.image, (20, 20, 20), (0, -6, self.width, 8))
        self.rect = self.image.get_rect(center=(x, y))
        self.speed = speed
        self.health = 1  # can be extended for tougher enemies
        # random jitter to make them more lively
        self.jitter_phase = random.random() * math.pi * 2

    def update(self, dt, mom_pos):
        # Move towards mom
        direction = pygame.Vector2(mom_pos) - pygame.Vector2(self.rect.center)
        if direction.length() != 0:
            direction = direction.normalize()
        # add slight wobble
        wobble = pygame.Vector2(math.cos(self.jitter_phase + pygame.time.get_ticks() / 300.0),
                                math.sin(self.jitter_phase + pygame.time.get_ticks() / 500.0)) * 0.4
        self.rect.centerx += int((direction.x + wobble.x) * self.speed)
        self.rect.centery += int((direction.y + wobble.y) * self.speed)

    def draw(self, surface):
        surface.blit(self.image, self.rect)


# ------ Game class ------
class Game:
    def __init__(self):
        self.all_sprites = pygame.sprite.Group()
        self.mafia_group = pygame.sprite.Group()
        self.mom = Mom(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
        self.all_sprites.add(self.mom)
        self.score = 0
        self.lives = STARTING_LIVES
        self.last_spawn_time = 0
        self.running = True
        self.game_over = False
        self.spawn_interval = MAFIA_SPAWN_INTERVAL
        self.difficulty_timer = pygame.time.get_ticks()
        # for increasing difficulty over time
        self.spawned_count = 0

    def spawn_mafia(self):
        # Spawn at a random edge
        side = random.choice(["top", "bottom", "left", "right"])
        if side == "top":
            x = random.randint(20, SCREEN_WIDTH - 20)
            y = -30
        elif side == "bottom":
            x = random.randint(20, SCREEN_WIDTH - 20)
            y = SCREEN_HEIGHT + 30
        elif side == "left":
            x = -30
            y = random.randint(20, SCREEN_HEIGHT - 20)
        else:
            x = SCREEN_WIDTH + 30
            y = random.randint(20, SCREEN_HEIGHT - 20)
        speed = random.uniform(MAFIA_MIN_SPEED, MAFIA_MAX_SPEED + (self.spawned_count * 0.03))
        m = Mafia(x, y, speed)
        self.all_sprites.add(m)
        self.mafia_group.add(m)
        self.spawned_count += 1

    def handle_collisions(self):
        # If mom slaps and slap rect intersects mafia, remove mafia / increase score
        if self.mom.slapping:
            slap_rect = self.mom.get_slap_rect()
            hit_list = [m for m in self.mafia_group if slap_rect.colliderect(m.rect)]
            for m in hit_list:
                # Knockback effect: push them away a bit, or remove them
                # We'll remove them and increment score
                self.score += 1
                m.kill()

        # If mafia touches mom, lose a life and remove that mafia
        for m in self.mafia_group:
            if self.mom.rect.colliderect(m.rect):
                self.lives -= 1
                m.kill()
                if self.lives <= 0:
                    self.game_over = True

    def update(self, dt):
        if self.game_over:
            return

        keys = pygame.key.get_pressed()
        self.mom.update(dt, keys)
        for m in list(self.mafia_group):
            m.update(dt, self.mom.rect.center)

        self.handle_collisions()

        # Spawn mafia periodically; spawning accelerates slowly
        now = pygame.time.get_ticks()
        if now - self.last_spawn_time >= max(400, self.spawn_interval - (self.spawned_count * 10)):
            self.spawn_mafia()
            self.last_spawn_time = now

        # Very simple difficulty ramp: every 10 seconds reduce spawn interval a bit
        if now - self.difficulty_timer > 10000:
            self.spawn_interval = max(600, int(self.spawn_interval * 0.92))
            self.difficulty_timer = now

    def draw(self, surface):
        surface.fill(BG_COLOR)
        # draw kitchen counters or simple decorations (optional)
        pygame.draw.rect(surface, (228, 200, 150), (0, SCREEN_HEIGHT - 80, SCREEN_WIDTH, 80))
        # draw sprites
        for m in self.mafia_group:
            m.draw(surface)
        self.mom.draw(surface)

        # HUD
        draw_text(surface, f"Score: {self.score}", 10, 10, font)
        draw_text(surface, f"Lives: {self.lives}", 10, 40, font)

        if self.game_over:
            draw_text(surface, "GAME OVER", SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 30, big_font, center=True)
            draw_text(surface, f"Final Score: {self.score}", SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 20, font, center=True)
            draw_text(surface, "Press R to restart or Esc to quit", SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 60, font, center=True)

    def run_frame(self, dt):
        # Event handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                if not self.game_over and event.key == pygame.K_SPACE:
                    slapped = self.mom.try_slap()
                    # Optional: play sound if available
                    # if slapped and hasattr(self, "slap_sound"): self.slap_sound.play()
                if self.game_over and event.key == pygame.K_r:
                    self.__init__()  # simple restart

        # Update game state
        self.update(dt)

        # Draw
        self.draw(screen)
        pygame.display.flip()

    def run(self):
        while self.running:
            dt = clock.tick(FPS)
            self.run_frame(dt)
        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    Game().run()