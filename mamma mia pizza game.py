# main.py
# Improved "Mamma Mia Pizza Game" visuals and enemy variety.
# - Better human-like drawings for Mom and mafia (hair, faces, clothes, accessories)
# - Walk bob, arm/rolling-pin swing, knockback and daze effects
# - Multiple mafia types with different looks
# - Slap, gun & grenade hooks retained from prior version
#
# Controls:
#  - Arrow keys / WASD: Move
#  - Space: Slap with rolling pin
#  - F: Shoot (if you have a gun powerup)
#  - G: Throw grenade (if you have grenades)
#  - R: Restart (after game over)
#  - Esc / Close window: Quit
#
# Run: python main.py
# Requirements: pygame

import pygame
import random
import math
import sys
from collections import deque

# ---------------- Configuration ----------------
SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 680
FPS = 60

MOM_SPEED = 4.2
MAFIA_MIN_SPEED = 0.9
MAFIA_MAX_SPEED = 2.3
MAFIA_SPAWN_INTERVAL = 1400  # ms base
SLAP_COOLDOWN = 520  # ms
SLAP_DURATION = 140
SLAP_RANGE = 78
SLAP_WIDTH = 44

STARTING_LIVES = 3

# Powerup defaults (kept small; extend later)
POWERUP_SPAWN_INTERVAL = 13000
POWERUP_TYPES = ["gun", "grenade"]
GUN_DURATION = 15000
GUN_FIRE_COOLDOWN = 200
GRENADE_COUNT = 2
GRENADE_FUSE = 1000
GRENADE_RADIUS = 84

# Colors
BG_COLOR = (246, 222, 179)
KITCHEN_COUNTER = (228, 200, 150)
TEXT_COLOR = (28, 28, 28)
SLAP_COLOR = (220, 180, 100)
BULLET_COLOR = (20, 20, 20)
GRENADE_COLOR = (80, 120, 40)
EXPLOSION_COLOR = (255, 200, 80)
SCORE_POP_COLOR = (255, 60, 60)

pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Mamma Mia — Improved")
clock = pygame.time.Clock()
font = pygame.font.SysFont("arial", 20)
big_font = pygame.font.SysFont("arial", 48)

# ---------------- Helpers ----------------
def draw_text(surface, text, x, y, font_obj, color=TEXT_COLOR, center=False):
    surf = font_obj.render(text, True, color)
    rect = surf.get_rect()
    if center:
        rect.center = (x, y)
    else:
        rect.topleft = (x, y)
    surface.blit(surf, rect)

def clamp(v, a, b):
    return max(a, min(b, v))

def lerp(a, b, t):
    return a + (b - a) * t

# small utility to create varied skin tones
SKIN_TONES = [
    (241, 194, 125),
    (224, 172, 105),
    (198, 134, 66),
    (150, 101, 50),
    (255, 224, 189),
    (205, 133, 63),
]

CLOTHING_COLORS = [
    (40, 40, 60),
    (60, 20, 20),
    (10, 60, 30),
    (50, 30, 80),
    (100, 60, 10),
    (80, 80, 80),
]

HAIR_COLORS = [
    (20, 20, 20),
    (60, 30, 10),
    (120, 80, 40),
    (200, 180, 150),
    (80, 30, 20),
]

# ---------------- Game Objects ----------------
class Mom(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.radius = 24
        self.rect = pygame.Rect(0, 0, self.radius * 2, self.radius * 2)
        self.rect.center = (x, y)
        self.vel = pygame.Vector2(0, 0)
        self.facing = "right"
        self.slapping = False
        self.slap_start_time = 0
        self.last_slap_time = -SLAP_COOLDOWN

        # powerups
        self.has_gun = False
        self.gun_end_time = 0
        self.last_shot_time = -GUN_FIRE_COOLDOWN
        self.grenades = 0

        # animation
        self.bob_phase = 0.0
        self.slap_progress = 0.0  # 0..1 when slapping for smooth arm swing
        self.slap_active = False

    def update(self, dt, keys):
        dx = dy = 0
        moving = False
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            dx -= MOM_SPEED
            self.facing = "left"
            moving = True
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            dx += MOM_SPEED
            self.facing = "right"
            moving = True
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            dy -= MOM_SPEED
            moving = True
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            dy += MOM_SPEED
            moving = True

        # smooth velocity (small inertia)
        target = pygame.Vector2(dx, dy)
        self.vel = lerp(self.vel, target, 0.25)
        self.rect.x += int(self.vel.x)
        self.rect.y += int(self.vel.y)

        # bounds
        self.rect.left = clamp(self.rect.left, 6, SCREEN_WIDTH - self.rect.width - 6)
        self.rect.top = clamp(self.rect.top, 6, SCREEN_HEIGHT - self.rect.height - 86)

        # bob when moving or breathing when idle
        self.bob_phase += (0.02 + (0.06 if moving else 0.01)) * (abs(self.vel.x) + abs(self.vel.y) + 1)
        if self.bob_phase > 99999:
            self.bob_phase = 0.0

        # update slap smooth progress
        now = pygame.time.get_ticks()
        if self.slapping:
            # measure elapsed fraction of SLAP_DURATION for animation progress
            elapsed = now - self.slap_start_time
            self.slap_progress = clamp(elapsed / SLAP_DURATION, 0.0, 1.0)
            if elapsed >= SLAP_DURATION:
                self.slapping = False
                self.slap_progress = 0.0
        else:
            self.slap_progress = 0.0

        # gun expiration
        if self.has_gun and now > self.gun_end_time:
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
        offset = int(self.radius * 0.9)
        if self.facing == "right":
            slap_rect = pygame.Rect(cx + offset, cy - SLAP_WIDTH // 2, SLAP_RANGE, SLAP_WIDTH)
        else:
            slap_rect = pygame.Rect(cx - SLAP_RANGE - offset, cy - SLAP_WIDTH // 2, SLAP_RANGE, SLAP_WIDTH)
        return slap_rect

    def draw(self, surface):
        cx, cy = self.rect.center
        bob = int(math.sin(self.bob_phase) * 4)

        # legs
        pygame.draw.rect(surface, (70, 40, 40), (cx - 12, cy + 12 + bob, 24, 20), border_radius=6)
        # dress/body
        pygame.draw.ellipse(surface, (200, 80, 80), (cx - 22, cy - 6 + bob, 44, 56))
        # apron (little detail)
        pygame.draw.rect(surface, (240, 240, 240), (cx - 14, cy + 6 + bob, 28, 26), border_radius=6)
        pygame.draw.line(surface, (220, 200, 180), (cx - 14, cy + 6 + bob), (cx + 14, cy + 6 + bob), 2)

        # head
        head_y = cy - 30 + bob
        pygame.draw.circle(surface, (245, 210, 175), (cx, head_y), 14)

        # hair (bun)
        pygame.draw.ellipse(surface, (100, 50, 20), (cx - 18, head_y - 18, 36, 14))
        pygame.draw.circle(surface, (100, 50, 20), (cx + 10, head_y - 20), 6)

        # eyes and smile
        eye_y = head_y - 4
        eye_x_offset = 6
        pygame.draw.circle(surface, (255, 255, 255), (cx - eye_x_offset, eye_y), 3)
        pygame.draw.circle(surface, (255, 255, 255), (cx + eye_x_offset, eye_y), 3)
        pygame.draw.circle(surface, (20, 20, 20), (cx - eye_x_offset, eye_y), 1)
        pygame.draw.circle(surface, (20, 20, 20), (cx + eye_x_offset, eye_y), 1)
        pygame.draw.arc(surface, (140, 30, 30), (cx - 7, head_y - 6, 14, 10), math.pi, 2 * math.pi, 2)

        # rolling pin: when slapping, show arc/rect in front
        # animate arm swing: use slap_progress to rotate the pin visual
        arm_swing = math.sin(self.slap_progress * math.pi) if self.slapping else 0.0
        pin_len = 48
        if self.facing == "right":
            pin_x = cx + 14 + int(arm_swing * 22)
            pin_y = head_y + 6 + int(arm_swing * 6)
            pygame.draw.rect(surface, (170, 120, 60), (pin_x - 6, pin_y - 4, pin_len, 8), border_radius=6)
        else:
            pin_x = cx - 14 - int(arm_swing * 22) - pin_len
            pin_y = head_y + 6 + int(arm_swing * 6)
            pygame.draw.rect(surface, (170, 120, 60), (pin_x, pin_y - 4, pin_len, 8), border_radius=6)

        # slap visual if active
        if self.slapping:
            sr = self.get_slap_rect()
            pygame.draw.rect(surface, SLAP_COLOR, sr, border_radius=8)

        # gun/grenade indicators (small)
        if self.has_gun:
            pygame.draw.rect(surface, (60, 60, 60), (self.rect.centerx - 8, self.rect.top - 20, 16, 6))
        if self.grenades > 0:
            draw_text(surface, f"G:{self.grenades}", self.rect.right + 4, self.rect.top - 20, font)

# ---------------- Mafia variations ----------------
class Mafia(pygame.sprite.Sprite):
    TYPE_DEFS = [
        {"hat": True, "glasses": False, "beard": False, "tough": False},
        {"hat": False, "glasses": True, "beard": False, "tough": False},
        {"hat": False, "glasses": False, "beard": True, "tough": True},
        {"hat": True, "glasses": True, "beard": False, "tough": True},
        {"hat": False, "glasses": False, "beard": False, "tough": False},
    ]

    def __init__(self, x, y, speed):
        super().__init__()
        self.width = 34
        self.height = 50
        self.rect = pygame.Rect(0, 0, self.width, self.height)
        self.rect.center = (x, y)
        self.base_speed = speed
        self.speed = speed
        self.health = 1
        self.max_health = 1
        self.jitter_phase = random.random() * math.pi * 2
        self.skin = random.choice(SKIN_TONES)
        self.hair = random.choice(HAIR_COLORS)
        self.cloth = random.choice(CLOTHING_COLORS)
        self.type = random.choice(Mafia.TYPE_DEFS)
        # tougher mafias have more health and slightly slower movement
        if self.type["tough"]:
            self.max_health = 2
            self.health = 2
            self.speed = max(0.7, self.base_speed * 0.9)

        # daze/knockback
        self.knockback = pygame.Vector2(0, 0)
        self.stagger_till = 0
        self.hit_flash = 0  # ms flash indicating recently hit

    def update(self, dt, mom_pos):
        now = pygame.time.get_ticks()
        # knockback applied as negative movement for a short while
        if now < self.stagger_till:
            # apply knockback; reduce over time
            self.rect.centerx += int(self.knockback.x * (dt / 16))
            self.rect.centery += int(self.knockback.y * (dt / 16))
            # decay
            self.knockback *= 0.9
            return

        # normal movement towards mom with slight wobble
        direction = pygame.Vector2(mom_pos) - pygame.Vector2(self.rect.center)
        if direction.length() != 0:
            direction = direction.normalize()
        wobble = pygame.Vector2(
            math.cos(self.jitter_phase + pygame.time.get_ticks() / 400.0),
            math.sin(self.jitter_phase + pygame.time.get_ticks() / 550.0)
        ) * 0.5
        move_vec = (direction + wobble) * self.speed
        self.rect.centerx += int(move_vec.x)
        self.rect.centery += int(move_vec.y)

        # top/bottom clamp
        self.rect.left = clamp(self.rect.left, -40, SCREEN_WIDTH + 40)
        self.rect.top = clamp(self.rect.top, -40, SCREEN_HEIGHT + 40)

        # decrease hit flash
        if self.hit_flash > 0:
            self.hit_flash = max(0, self.hit_flash - dt)

    def draw(self, surface):
        cx, cy = self.rect.center

        # body (suit) with lapel
        suit_rect = pygame.Rect(cx - 16, cy - 8, 32, 40)
        pygame.draw.rect(surface, self.cloth, suit_rect, border_radius=6)

        # shirt
        pygame.draw.rect(surface, (240, 240, 240), (cx - 8, cy - 4, 16, 12), border_radius=2)

        # tie or scarf
        pygame.draw.polygon(surface, (160, 30, 30), [(cx, cy - 2), (cx - 5, cy + 8), (cx + 5, cy + 8)])

        # head
        head_y = cy - 26
        pygame.draw.circle(surface, self.skin, (cx, head_y), 12)

        # hair top
        pygame.draw.ellipse(surface, self.hair, (cx - 14, head_y - 14, 28, 14))
        # hat if type
        if self.type["hat"]:
            pygame.draw.rect(surface, (20, 20, 20), (cx - 16, head_y - 26, 32, 8), border_radius=6)
            pygame.draw.rect(surface, (40, 40, 40), (cx - 12, head_y - 22, 24, 6), border_radius=4)

        # beard
        if self.type["beard"]:
            pygame.draw.ellipse(surface, (80, 60, 40), (cx - 10, head_y - 2, 20, 12))

        # glasses
        if self.type["glasses"]:
            pygame.draw.rect(surface, (30, 30, 30), (cx - 10, head_y - 5, 8, 6), border_radius=2)
            pygame.draw.rect(surface, (30, 30, 30), (cx + 2, head_y - 5, 8, 6), border_radius=2)
            pygame.draw.line(surface, (30, 30, 30), (cx - 2, head_y - 2), (cx + 2, head_y - 2), 2)

        # eyes (if no glasses, show small eyes)
        if not self.type["glasses"]:
            pygame.draw.circle(surface, (255, 255, 255), (cx - 5, head_y - 3), 2)
            pygame.draw.circle(surface, (255, 255, 255), (cx + 5, head_y - 3), 2)
            pygame.draw.circle(surface, (10, 10, 10), (cx - 5, head_y - 3), 1)
            pygame.draw.circle(surface, (10, 10, 10), (cx + 5, head_y - 3), 1)

        # mouth
        pygame.draw.line(surface, (120, 20, 20), (cx - 5, head_y + 6), (cx + 5, head_y + 6), 2)

        # hit flash or daze
        if self.hit_flash > 0:
            s = pygame.Surface((self.width + 8, self.height + 8), pygame.SRCALPHA)
            alpha = int(180 * (self.hit_flash / 200.0))
            s.fill((255, 255, 255, alpha))
            surface.blit(s, (self.rect.left - 4, self.rect.top - 4))

        # small health bar
        if self.max_health > 1:
            bar_w = 28
            bar_h = 6
            frac = self.health / self.max_health
            pygame.draw.rect(surface, (50, 50, 50), (cx - bar_w // 2, cy - 40, bar_w, bar_h), border_radius=3)
            pygame.draw.rect(surface, (60, 200, 80), (cx - bar_w // 2 + 2, cy - 40 + 2, int((bar_w - 4) * frac), bar_h - 4), border_radius=3)

    def apply_hit(self, knock_vec, stagger_ms=280):
        # reduce health and apply knockback & stun
        self.health -= 1
        self.hit_flash = 220
        self.knockback = pygame.Vector2(knock_vec) * 0.9
        self.stagger_till = pygame.time.get_ticks() + stagger_ms

# ---------------- Projectile & Utility classes ----------------
class Bullet(pygame.sprite.Sprite):
    def __init__(self, x, y, vx, vy):
        super().__init__()
        self.rect = pygame.Rect(0, 0, 10, 6)
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
        pygame.draw.rect(surface, BULLET_COLOR, self.rect, border_radius=3)

class Grenade(pygame.sprite.Sprite):
    def __init__(self, x, y, vx, vy):
        super().__init__()
        self.rect = pygame.Rect(0, 0, 12, 12)
        self.rect.center = (x, y)
        self.vx = vx
        self.vy = vy
        self.spawn_time = pygame.time.get_ticks()
        self.exploded = False

    def update(self, dt):
        self.vy += 0.22
        self.rect.x += int(self.vx * dt / (1000 / FPS))
        self.rect.y += int(self.vy * dt / (1000 / FPS))
        if self.rect.top > SCREEN_HEIGHT + 200:
            self.kill()
        if not self.exploded and pygame.time.get_ticks() - self.spawn_time >= GRENADE_FUSE:
            self.exploded = True

    def draw(self, surface):
        if not self.exploded:
            pygame.draw.circle(surface, GRENADE_COLOR, self.rect.center, 6)

class Powerup(pygame.sprite.Sprite):
    def __init__(self, x, y, ptype):
        super().__init__()
        self.rect = pygame.Rect(0, 0, 22, 22)
        self.rect.center = (x, y)
        self.ptype = ptype
        self.spawn_t = pygame.time.get_ticks()

    def draw(self, surface):
        colors = {"gun": (60, 60, 200), "grenade": (80, 160, 40)}
        pygame.draw.rect(surface, colors.get(self.ptype, (150, 150, 150)), self.rect, border_radius=6)
        draw_text(surface, self.ptype[0].upper(), self.rect.centerx - 6, self.rect.centery - 10, font)

# ---------------- The Game ----------------
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

        # ephemeral score pop-ups
        self.score_pops = deque()  # list of (x,y, value, expiry)

        # explosion visuals
        self.explosions = []

    def spawn_mafia(self):
        side = random.choice(["top", "bottom", "left", "right"])
        if side == "top":
            x = random.randint(30, SCREEN_WIDTH - 30)
            y = -40
        elif side == "bottom":
            x = random.randint(30, SCREEN_WIDTH - 30)
            y = SCREEN_HEIGHT + 40
        elif side == "left":
            x = -40
            y = random.randint(30, SCREEN_HEIGHT - 150)
        else:
            x = SCREEN_WIDTH + 40
            y = random.randint(30, SCREEN_HEIGHT - 150)
        speed = random.uniform(MAFIA_MIN_SPEED, MAFIA_MAX_SPEED + (self.spawned_count * 0.02))
        m = Mafia(x, y, speed)
        self.mafia_group.add(m)
        self.all_sprites.add(m)
        self.spawned_count += 1

    def spawn_powerup(self):
        x = random.randint(70, SCREEN_WIDTH - 70)
        y = random.randint(70, SCREEN_HEIGHT - 180)
        ptype = random.choice(POWERUP_TYPES)
        p = Powerup(x, y, ptype)
        self.powerups.add(p)
        self.all_sprites.add(p)

    def handle_collisions(self):
        now = pygame.time.get_ticks()
        # slap collisions: apply knockback depending on facing & distance
        if self.mom.slapping:
            sr = self.mom.get_slap_rect()
            hits = [m for m in self.mafia_group if sr.colliderect(m.rect)]
            for m in hits:
                # knockback vector away from mom
                dx = m.rect.centerx - self.mom.rect.centerx
                dy = m.rect.centery - self.mom.rect.centery
                dist = math.hypot(dx, dy) + 0.1
                knock_dir = (dx / dist, dy / dist)
                # if already staggered, still apply but smaller impact
                m.apply_hit(knock_dir, stagger_ms=280)
                # slight score pop and increment
                self.score += 1
                self.score_pops.append([m.rect.centerx, m.rect.top - 6, "+1", now + 700])
                if m.health <= 0:
                    m.kill()

        # bullets vs mafia
        for b in list(self.bullets):
            hits = [m for m in self.mafia_group if b.rect.colliderect(m.rect)]
            for m in hits:
                # bullets do instant damage
                self.score += 1
                self.score_pops.append([m.rect.centerx, m.rect.top - 6, "+1", now + 700])
                m.apply_hit((b.vx * 0.15, b.vy * 0.15), stagger_ms=160)
                b.kill()
                if m.health <= 0:
                    m.kill()

        # grenades: explode when flagged
        for g in list(self.grenades):
            if g.exploded:
                x, y = g.rect.center
                self.explosions.append([x, y, GRENADE_RADIUS, now + 380])
                # damage mafia within radius
                for m in list(self.mafia_group):
                    dx = m.rect.centerx - x
                    dy = m.rect.centery - y
                    if dx * dx + dy * dy <= GRENADE_RADIUS * GRENADE_RADIUS:
                        m.apply_hit((dx * 0.02, dy * 0.02), stagger_ms=260)
                        self.score += 1
                        self.score_pops.append([m.rect.centerx, m.rect.top - 6, "+1", now + 700])
                        if m.health <= 0:
                            m.kill()
                g.kill()

        # mafia touching mom
        for m in list(self.mafia_group):
            if self.mom.rect.colliderect(m.rect):
                # small knockback to mom (visual)
                self.lives -= 1
                # remove enemy
                m.kill()
                # brief hit popup
                self.score_pops.append([self.mom.rect.centerx, self.mom.rect.top - 10, "-1L", now + 900])
                if self.lives <= 0:
                    self.game_over = True

        # powerup pick-up
        for p in list(self.powerups):
            if self.mom.rect.colliderect(p.rect):
                if p.ptype == "gun":
                    self.mom.has_gun = True
                    self.mom.gun_end_time = pygame.time.get_ticks() + GUN_DURATION
                elif p.ptype == "grenade":
                    self.mom.grenades += GRENADE_COUNT
                p.kill()

        # clean expired score pops
        while self.score_pops and self.score_pops[0][3] < now:
            self.score_pops.popleft()

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
        if now - self.last_spawn_time >= max(420, self.spawn_interval - (self.spawned_count * 12)):
            self.spawn_mafia()
            self.last_spawn_time = now

        if now - self.difficulty_timer > 11000:
            self.spawn_interval = max(600, int(self.spawn_interval * 0.92))
            self.difficulty_timer = now

        if now - self.last_powerup_time >= POWERUP_SPAWN_INTERVAL:
            self.spawn_powerup()
            self.last_powerup_time = now

        # tidy explosions
        self.explosions = [e for e in self.explosions if e[3] > now]

    def draw(self, surface):
        surface.fill(BG_COLOR)
        pygame.draw.rect(surface, KITCHEN_COUNTER, (0, SCREEN_HEIGHT - 86, SCREEN_WIDTH, 86))

        # draw powerups (under layer)
        for p in self.powerups:
            p.draw(surface)

        # draw mafia and bullets/grenades
        for m in sorted(self.mafia_group, key=lambda x: x.rect.centery):
            m.draw(surface)
        for b in self.bullets:
            b.draw(surface)
        for g in self.grenades:
            g.draw(surface)

        # explosions visuals
        for e in self.explosions:
            now = pygame.time.get_ticks()
            remaining = e[3] - now
            alpha = max(30, min(210, int(255 * (remaining / 380.0))))
            rad = e[2]
            s = pygame.Surface((rad * 2, rad * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (*EXPLOSION_COLOR, alpha), (rad, rad), rad)
            surface.blit(s, (e[0] - rad, e[1] - rad))

        # draw mom last so she appears forward
        self.mom.draw(surface)

        # HUD
        draw_text(surface, f"Score: {self.score}", 14, 8, font)
        draw_text(surface, f"Lives: {self.lives}", 14, 34, font)
        weapon = "None"
        if self.mom.has_gun:
            weapon = "Gun"
        if self.mom.grenades > 0:
            weapon += (" + Grenades" if weapon != "None" else "Grenades")
        draw_text(surface, f"Weapon: {weapon}", SCREEN_WIDTH - 260, 8, font)
        draw_text(surface, "F: Shoot  G: Throw grenade", SCREEN_WIDTH - 320, 34, font)

        # score pops
        for pop in list(self.score_pops):
            x, y, text, expiry = pop
            # fade out
            remain = expiry - pygame.time.get_ticks()
            alpha = clamp(int(255 * (remain / 900.0)), 0, 255)
            surf = font.render(str(text), True, SCORE_POP_COLOR)
            surf.set_alpha(alpha)
            surface.blit(surf, (x - surf.get_width() // 2, y - (900 - remain)/7))

        # game over
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
                    if self.mom.has_gun and pygame.time.get_ticks() - self.mom.last_shot_time >= GUN_FIRE_COOLDOWN:
                        cx, cy = self.mom.rect.center
                        speed = 10
                        if self.mom.facing == "right":
                            vx, vy = speed, 0
                            bx = cx + 22
                        else:
                            vx, vy = -speed, 0
                            bx = cx - 22
                        b = Bullet(bx, cy - 4, vx, vy)
                        self.bullets.add(b)
                        self.all_sprites.add(b)
                        self.mom.last_shot_time = pygame.time.get_ticks()
                if not self.game_over and event.key == pygame.K_g:
                    if self.mom.grenades > 0:
                        cx, cy = self.mom.rect.center
                        vel = 6.5
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
