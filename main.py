# A more advanced "Mamma Mia Pizza Game" with powerups (gun and grenade), bullets, and grenade explosions.
# You are an Italian mom who protects the kitchen! Use your rolling pin or powerups to keep the mafiosi away.
# Controls:
#  - Arrow keys / WASD to move
#  - Space to slap with rolling pin
#  - F to shoot (when you have a gun)
#  - G to throw a grenade (if you have grenades)
#  - Esc to quit
#  - R restart after game over

import pygame
import random
import math
import sys

# Configuration
SCREEN_WIDTH = 900
SCREEN_HEIGHT = 640
FPS = 60
MOM_SPEED = 4
MAFIA_MIN_SPEED = 1.0
MAFIA_MAX_SPEED = 2.2
MAFIA_SPAWN_INTERVAL = 1500
SLAP_COOLDOWN = 600
SLAP_DURATION = 120
SLAP_RANGE = 70
SLAP_WIDTH = 40
STARTING_LIVES = 3

# Powerup settings
POWERUP_SPAWN_INTERVAL = 12000  # ms
POWERUP_TYPES = ["gun", "grenade"]
GUN_DURATION = 15000  # ms
GUN_FIRE_COOLDOWN = 220  # ms
GRENADE_COUNT = 2  # grenades granted by pick-up
GRENADE_FUSE = 1100  # ms
GRENADE_RADIUS = 90

# Colors
BG_COLOR = (246, 222, 179)
MOM_COLOR = (200, 140, 120)
MOM_CLOTHES = (205, 92, 92)
MAFIA_SKIN = (190, 150, 120)
MAFIA_SUIT = (30, 30, 40)
MAFIA_TIE = (150, 20, 20)
MAFIA_HAT = (15, 15, 20)
MAFIA_COLOR = (40, 40, 40)
SLAP_COLOR = (194, 154, 85)
POWERUP_COLOR = {"gun": (60, 60, 200), "grenade": (80, 160, 40)}
TEXT_COLOR = (20, 20, 20)
BULLET_COLOR = (10, 10, 10)
GRENADE_COLOR = (70, 120, 40)
EXPLOSION_COLOR = (255, 200, 80)

pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Mamma Mia Pizza Game - Powerups Added")
clock = pygame.time.Clock()
font = pygame.font.SysFont("arial", 22)
big_font = pygame.font.SysFont("arial", 48)

# Helper

def draw_text(surface, text, x, y, font_obj, color=TEXT_COLOR, center=False):
    surf = font_obj.render(text, True, color)
    rect = surf.get_rect()
    if center:
        rect.center = (x, y)
    else:
        rect.topleft = (x, y)
    surface.blit(surf, rect)

# Game objects
class Mom(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.radius = 22
        self.rect = pygame.Rect(0, 0, self.radius * 2, self.radius * 2)
        self.rect.center = (x, y)
        self.facing = "right"
        self.slapping = False
        self.slap_start_time = 0
        self.last_slap_time = -SLAP_COOLDOWN
        # powerups
        self.has_gun = False
        self.gun_end_time = 0
        self.last_shot_time = -GUN_FIRE_COOLDOWN
        self.grenades = 0

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

        # Update slap state
        if self.slapping and pygame.time.get_ticks() - self.slap_start_time > SLAP_DURATION:
            self.slapping = False

        # Gun duration check
        if self.has_gun and pygame.time.get_ticks() > self.gun_end_time:
            self.has_gun = False

    def try_slap(self):
        now = pygame.time.get_ticks()
        if now - self.last_slap_time >= SLAP_COOLDOWN:
            self.slapping = True
            self.slap_start_time = now
            self.last_slap_time = now
            return True
        return False

    def get_slap_rect(self):
        cx, cy = self.rect.center
        if self.facing == "right":
            slap_rect = pygame.Rect(cx + self.radius // 2, cy - SLAP_WIDTH // 2, SLAP_RANGE, SLAP_WIDTH)
        else:
            slap_rect = pygame.Rect(cx - SLAP_RANGE - self.radius // 2, cy - SLAP_WIDTH // 2, SLAP_RANGE, SLAP_WIDTH)
        return slap_rect

    def draw(self, surface):
        # Draw body (simple human-like)
        cx, cy = self.rect.center
        # legs
        pygame.draw.rect(surface, (80, 40, 40), (cx - 10, cy + 10, 20, 18))
        # body
        pygame.draw.ellipse(surface, MOM_CLOTHES, (cx - 18, cy - 6, 36, 40))
        # head
        pygame.draw.circle(surface, MOM_COLOR, (cx, cy - 24), 14)
        # eyes
        eye_offset_x = 6 if self.facing == "right" else -6
        pygame.draw.circle(surface, (255, 255, 255), (cx + eye_offset_x - 4, cy - 26), 3)
        pygame.draw.circle(surface, (255, 255, 255), (cx + eye_offset_x + 2, cy - 26), 3)
        # mouth
        pygame.draw.line(surface, (150, 0, 0), (cx - 6, cy - 18), (cx + 6, cy - 18), 2)
        # rolling pin held behind when not slapping
        px = cx + (self.radius + 6) if self.facing == "right" else cx - (self.radius + 6)
        pygame.draw.rect(surface, (160, 110, 60), (px - 12, cy - 4, 24, 6))

        # draw slap visual if active
        if self.slapping:
            sr = self.get_slap_rect()
            pygame.draw.rect(surface, SLAP_COLOR, sr)
        # weapon indicator (small)
        if self.has_gun:
            pygame.draw.rect(surface, (60, 60, 60), (self.rect.centerx - 6, self.rect.top - 18, 12, 6))
        if self.grenades > 0:
            draw_text(surface, f"O:{self.grenades}", self.rect.right + 6, self.rect.top - 18, font)


class Mafia(pygame.sprite.Sprite):
    def __init__(self, x, y, speed):
        super().__init__()
        self.width = 30
        self.height = 44
        self.rect = pygame.Rect(0, 0, self.width, self.height)
        self.rect.center = (x, y)
        self.speed = speed
        self.health = 1
        self.jitter_phase = random.random() * math.pi * 2

    def update(self, dt, mom_pos):
        direction = pygame.Vector2(mom_pos) - pygame.Vector2(self.rect.center)
        if direction.length() != 0:
            direction = direction.normalize()
        wobble = pygame.Vector2(math.cos(self.jitter_phase + pygame.time.get_ticks() / 300.0),
                                math.sin(self.jitter_phase + pygame.time.get_ticks() / 500.0)) * 0.4
        self.rect.centerx += int((direction.x + wobble.x) * self.speed)
        self.rect.centery += int((direction.y + wobble.y) * self.speed)

    def draw(self, surface):
        cx, cy = self.rect.center
        # suit body
        pygame.draw.rect(surface, MAFIA_SUIT, (cx - 12, cy - 6, 24, 34), border_radius=4)
        # shirt
        pygame.draw.rect(surface, (220, 220, 220), (cx - 8, cy - 2, 16, 12))
        # tie
        pygame.draw.polygon(surface, MAFIA_TIE, [(cx, cy - 2), (cx - 4, cy + 8), (cx + 4, cy + 8)])
        # head
        pygame.draw.circle(surface, MAFIA_SKIN, (cx, cy - 22), 12)
        # hat
        pygame.draw.rect(surface, MAFIA_HAT, (cx - 16, cy - 34, 32, 8))
        pygame.draw.rect(surface, (0, 0, 0), (cx - 12, cy - 30, 24, 4))


class Bullet(pygame.sprite.Sprite):
    def __init__(self, x, y, vx, vy):
        super().__init__()
        self.rect = pygame.Rect(0, 0, 8, 4)
        self.rect.center = (x, y)
        self.vx = vx
        self.vy = vy

    def update(self, dt):
        self.rect.x += int(self.vx * dt / (1000 / FPS))
        self.rect.y += int(self.vy * dt / (1000 / FPS))
        if (self.rect.right < 0 or self.rect.left > SCREEN_WIDTH or
                self.rect.bottom < 0 or self.rect.top > SCREEN_HEIGHT):
            self.kill()

    def draw(self, surface):
        pygame.draw.rect(surface, BULLET_COLOR, self.rect)


class Grenade(pygame.sprite.Sprite):
    def __init__(self, x, y, vx, vy):
        super().__init__()
        self.rect = pygame.Rect(0, 0, 10, 10)
        self.rect.center = (x, y)
        self.vx = vx
        self.vy = vy
        self.spawn_time = pygame.time.get_ticks()
        self.exploded = False

    def update(self, dt):
        # simple physics
        self.vy += 0.22  # gravity
        self.rect.x += int(self.vx * dt / (1000 / FPS))
        self.rect.y += int(self.vy * dt / (1000 / FPS))
        # keep in bounds tolerance
        if self.rect.top > SCREEN_HEIGHT + 200:
            self.kill()
        if not self.exploded and pygame.time.get_ticks() - self.spawn_time >= GRENADE_FUSE:
            self.explode()

    def explode(self):
        self.exploded = True
        # create an explosion circle check will be handled by Game

    def draw(self, surface):
        if not self.exploded:
            pygame.draw.circle(surface, GRENADE_COLOR, self.rect.center, 6)


class Powerup(pygame.sprite.Sprite):
    def __init__(self, x, y, ptype):
        super().__init__()
        self.rect = pygame.Rect(0, 0, 22, 22)
        self.rect.center = (x, y)
        self.ptype = ptype

    def draw(self, surface):
        pygame.draw.rect(surface, POWERUP_COLOR[self.ptype], self.rect, border_radius=6)
        draw_text(surface, self.ptype[0].upper(), self.rect.centerx - 6, self.rect.centery - 10, font)

# Game
class Game:
    def __init__(self):
        self.all_sprites = pygame.sprite.Group()
        self.mafia_group = pygame.sprite.Group()
        self.bullets = pygame.sprite.Group()
        self.grenades = pygame.sprite.Group()
        self.powerups = pygame.sprite.Group()
        self.mom = Mom(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
        self.all_sprites.add(self.mom)
        self.score = 0
        self.lives = STARTING_LIVES
        self.last_spawn_time = 0
        self.running = True
        self.game_over = False
        self.spawn_interval = MAFIA_SPAWN_INTERVAL
        self.difficulty_timer = pygame.time.get_ticks()
        self.spawned_count = 0
        self.last_powerup_time = 0
        self.explosions = []  # list of tuples (x,y,radius,expiry)

    def spawn_mafia(self):
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
        speed = random.uniform(MAFIA_MIN_SPEED, MAFIA_MAX_SPEED + (self.spawned_count * 0.02))
        m = Mafia(x, y, speed)
        self.all_sprites.add(m)
        self.mafia_group.add(m)
        self.spawned_count += 1

    def spawn_powerup(self):
        # spawn somewhere inside the play area
        x = random.randint(60, SCREEN_WIDTH - 60)
        y = random.randint(60, SCREEN_HEIGHT - 140)
        ptype = random.choice(POWERUP_TYPES)
        p = Powerup(x, y, ptype)
        self.all_sprites.add(p)
        self.powerups.add(p)

    def handle_collisions(self):
        # slap collisions
        if self.mom.slapping:
            slap_rect = self.mom.get_slap_rect()
            hit_list = [m for m in self.mafia_group if slap_rect.colliderect(m.rect)]
            for m in hit_list:
                self.score += 1
                m.kill()

        # bullets
        for b in list(self.bullets):
            hit_list = [m for m in self.mafia_group if b.rect.colliderect(m.rect)]
            for m in hit_list:
                self.score += 1
                m.kill()
                b.kill()

        # grenade explosions
        # process any grenade that exploded
        for g in list(self.grenades):
            if g.exploded:
                # register explosion for a short visual
                x, y = g.rect.center
                now = pygame.time.get_ticks()
                self.explosions.append([x, y, GRENADE_RADIUS, now + 350])
                # damage mafia in radius
                for m in list(self.mafia_group):
                    dx = m.rect.centerx - x
                    dy = m.rect.centery - y
                    if dx * dx + dy * dy <= GRENADE_RADIUS * GRENADE_RADIUS:
                        self.score += 1
                        m.kill()
                g.kill()

        # mafia touches mom
        for m in list(self.mafia_group):
            if self.mom.rect.colliderect(m.rect):
                self.lives -= 1
                m.kill()
                if self.lives <= 0:
                    self.game_over = True

        # powerup pickups
        for p in list(self.powerups):
            if self.mom.rect.colliderect(p.rect):
                if p.ptype == "gun":
                    self.mom.has_gun = True
                    self.mom.gun_end_time = pygame.time.get_ticks() + GUN_DURATION
                elif p.ptype == "grenade":
                    self.mom.grenades += GRENADE_COUNT
                p.kill()

    def update(self, dt):
        if self.game_over:
            return
        keys = pygame.key.get_pressed()
        self.mom.update(dt, keys)
        for m in list(self.mafia_group):
            m.update(dt, self.mom.rect.center)

        for b in list(self.bullets):
            b.update(dt)
        for g in list(self.grenades):
            g.update(dt)

        self.handle_collisions()

        now = pygame.time.get_ticks()
        if now - self.last_spawn_time >= max(400, self.spawn_interval - (self.spawned_count * 10)):
            self.spawn_mafia()
            self.last_spawn_time = now

        if now - self.difficulty_timer > 10000:
            self.spawn_interval = max(600, int(self.spawn_interval * 0.92))
            self.difficulty_timer = now

        if now - self.last_powerup_time >= POWERUP_SPAWN_INTERVAL:
            self.spawn_powerup()
            self.last_powerup_time = now

        # tidy explosions
        self.explosions = [e for e in self.explosions if e[3] > now]

    def draw(self, surface):
        surface.fill(BG_COLOR)
        pygame.draw.rect(surface, (228, 200, 150), (0, SCREEN_HEIGHT - 80, SCREEN_WIDTH, 80))

        for p in self.powerups:
            p.draw(surface)
        for m in self.mafia_group:
            m.draw(surface)
        for b in self.bullets:
            b.draw(surface)
        for g in self.grenades:
            g.draw(surface)
        for e in self.explosions:
            # draw expanding faded circle
            now = pygame.time.get_ticks()
            remaining = e[3] - now
            alpha = max(30, min(200, int(255 * (remaining / 350))))
            s = pygame.Surface((GRENADE_RADIUS * 2, GRENADE_RADIUS * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (*EXPLOSION_COLOR, alpha), (GRENADE_RADIUS, GRENADE_RADIUS), GRENADE_RADIUS)
            surface.blit(s, (e[0] - GRENADE_RADIUS, e[1] - GRENADE_RADIUS))

        self.mom.draw(surface)

        # HUD
        draw_text(surface, f"Score: {self.score}", 12, 8, font)
        draw_text(surface, f"Lives: {self.lives}", 12, 34, font)
        weapon = "None"
        if self.mom.has_gun:
            weapon = "Gun"
        if self.mom.grenades > 0:
            weapon += (" + Grenades" if weapon != "None" else "Grenades")
        draw_text(surface, f"Weapon: {weapon}", SCREEN_WIDTH - 240, 8, font)
        draw_text(surface, "F: Shoot (gun)  G: Throw grenade", SCREEN_WIDTH - 320, 34, font)

        if self.game_over:
            draw_text(surface, "GAME OVER", SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 30, big_font, center=True)
            draw_text(surface, f"Final Score: {self.score}", SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 20, font, center=True)
            draw_text(surface, "Press R to restart or Esc to quit", SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 60, font, center=True)

    def run_frame(self, dt):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                if not self.game_over and event.key == pygame.K_SPACE:
                    self.mom.try_slap()
                if not self.game_over and event.key == pygame.K_f:
                    # fire bullet if have gun
                    if self.mom.has_gun and pygame.time.get_ticks() - self.mom.last_shot_time >= GUN_FIRE_COOLDOWN:
                        # spawn bullet from mom facing
                        cx, cy = self.mom.rect.center
                        speed = 8
                        if self.mom.facing == "right":
                            vx, vy = speed, 0
                            bx = cx + 18
                        else:
                            vx, vy = -speed, 0
                            bx = cx - 18
                        b = Bullet(bx, cy - 6, vx, vy)
                        self.bullets.add(b)
                        self.all_sprites.add(b)
                        self.mom.last_shot_time = pygame.time.get_ticks()
                if not self.game_over and event.key == pygame.K_g:
                    if self.mom.grenades > 0:
                        # throw grenade
                        cx, cy = self.mom.rect.center
                        vel = 6
                        if self.mom.facing == "right":
                            vx, vy = vel, -5
                        else:
                            vx, vy = -vel, -5
                        gr = Grenade(cx, cy - 6, vx, vy)
                        self.grenades.add(gr)
                        self.all_sprites.add(gr)
                        self.mom.grenades -= 1
                if self.game_over and event.key == pygame.K_r:
                    self.__init__()

        self.update(dt)
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