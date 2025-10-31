# main.py
# "Mamma Mia Pizza Game" — procedural map + pickup-as-weapon + respawn + richer chunks
# Fix applied: replaced undefined `surface` with `screen` in the game loop (the cause of the runtime error).
# Added: ponds, fences, small interior rooms for the central house chunk,
#        persistent pickup respawns and a simple inventory for Mom.

import pygame
import random
import math
import sys
from collections import deque

# -------- Configuration --------
SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 680
FPS = 60

TILE_SIZE = 64
CHUNK_TILES = 6  # 6x6 tiles per chunk
CHUNK_SIZE = TILE_SIZE * CHUNK_TILES
VIEW_DISTANCE_CHUNKS = 2  # generate chunks in a radius

MOM_SPEED = 160  # world units per second (pixels)

MAFIA_MIN_SPEED = 35
MAFIA_MAX_SPEED = 80
MAFIA_SPAWN_INTERVAL = 1400

SLAP_COOLDOWN = 520
SLAP_DURATION = 140
SLAP_WIDTH = 44

STARTING_LIVES = 3

# respawn
PICKUP_RESPAWN_MIN_MS = 15000
PICKUP_RESPAWN_MAX_MS = 45000

# weapons (base slap as fists)
WEAPONS = {
    "fist": {"name": "Fist", "damage": 1, "range": 78, "cooldown": SLAP_COOLDOWN, "type": "melee"},
    "frying_pan": {"name": "Frying Pan", "damage": 2, "range": 96, "cooldown": 520, "type": "melee"},
    "broom": {"name": "Broom", "damage": 1, "range": 120, "cooldown": 680, "type": "melee"},
    "chair": {"name": "Chair", "damage": 3, "range": 64, "cooldown": 900, "type": "melee"},
    "tomato": {"name": "Tomato", "damage": 1, "range": 10, "cooldown": 420, "type": "throw", "speed": 280},
}

# environment tile types
TILE_COLORS = {
    "floor": (235, 210, 175),
    "kitchen_floor": (240, 220, 190),
    "grass": (150, 200, 120),
    "path": (180, 160, 120),
    "soil": (100, 70, 40),
    "water": (110, 160, 220),
    "fence": (120, 80, 40),
}

# pickup types and spawnable items
PICKUP_TYPES = ["frying_pan", "broom", "chair", "tomato"]

# colors
BG_COLOR = (200, 200, 200)
TEXT_COLOR = (28, 28, 28)

pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Mamma Mia — Procedural World & Weapons (Fixed)")
clock = pygame.time.Clock()
font = pygame.font.SysFont("arial", 20)
big_font = pygame.font.SysFont("arial", 48)

# -------- Helpers --------
def draw_text(surface, text, x, y, font_obj, color=TEXT_COLOR, center=False):
    surf = font_obj.render(text, True, color)
    rect = surf.get_rect()
    if center:
        rect.center = (x, y)
    else:
        rect.topleft = (x, y)
    surface.blit(surf, rect)

def world_to_screen(pos, cam_pos):
    return (int(pos[0] - cam_pos[0] + SCREEN_WIDTH / 2), int(pos[1] - cam_pos[1] + SCREEN_HEIGHT / 2))

def screen_to_world(pos, cam_pos):
    return (pos[0] + cam_pos[0] - SCREEN_WIDTH / 2, pos[1] + cam_pos[1] - SCREEN_HEIGHT / 2)

# deterministic RNG for chunk generation
def chunk_rng(cx, cy):
    seed = (cx * 73856093) ^ (cy * 19349663)
    return random.Random(seed)

def clamp(v, a, b):
    return max(a, min(b, v))

# -------- World & Map --------
class Chunk:
    def __init__(self, cx, cy):
        self.cx = cx
        self.cy = cy
        self.tiles = [["grass" for _ in range(CHUNK_TILES)] for _ in range(CHUNK_TILES)]
        self.pickups = []  # items placed in this chunk
        self.features = []  # decorative features (type, x, y)
        self.generated = False
        self.generate()

    def generate(self):
        r = chunk_rng(self.cx, self.cy)
        # central chunk (0,0) -> house / kitchen with simple interior walls
        if self.cx == 0 and self.cy == 0:
            for tx in range(CHUNK_TILES):
                for ty in range(CHUNK_TILES):
                    self.tiles[ty][tx] = "kitchen_floor"
            # add a simple interior partition "wall" (visual) and a few pickups
            # partition: vertical wall at tile column 2 (makes a small room)
            for ty in range(1, CHUNK_TILES - 1):
                self.features.append(("wall", self.cx * CHUNK_SIZE + 2 * TILE_SIZE + TILE_SIZE//2,
                                      self.cy * CHUNK_SIZE + ty * TILE_SIZE + TILE_SIZE//2))
            # place kitchen counters and items
            for i in range(4):
                px = (self.cx * CHUNK_SIZE) + r.randint(1, CHUNK_TILES - 2) * TILE_SIZE + TILE_SIZE // 2
                py = (self.cy * CHUNK_SIZE) + r.randint(1, CHUNK_TILES - 2) * TILE_SIZE + TILE_SIZE // 2
                self.pickups.append(PickUp(px, py, r.choice(PICKUP_TYPES)))
        else:
            t = r.random()
            if t < 0.12:
                # garden/soil with plants and occasional tomato
                for tx in range(CHUNK_TILES):
                    for ty in range(CHUNK_TILES):
                        self.tiles[ty][tx] = "soil"
                for i in range(r.randint(1, 5)):
                    fx = (self.cx * CHUNK_SIZE) + r.randint(0, CHUNK_TILES - 1) * TILE_SIZE + TILE_SIZE // 2
                    fy = (self.cy * CHUNK_SIZE) + r.randint(0, CHUNK_TILES - 1) * TILE_SIZE + TILE_SIZE // 2
                    self.features.append(("plant", fx, fy))
                if r.random() < 0.45:
                    px = (self.cx * CHUNK_SIZE) + r.randint(0, CHUNK_TILES - 1) * TILE_SIZE + TILE_SIZE // 2
                    py = (self.cy * CHUNK_SIZE) + r.randint(0, CHUNK_TILES - 1) * TILE_SIZE + TILE_SIZE // 2
                    self.pickups.append(PickUp(px, py, "tomato"))
            elif t < 0.30:
                # path and benches
                for tx in range(CHUNK_TILES):
                    for ty in range(CHUNK_TILES):
                        self.tiles[ty][tx] = "path" if r.random() < 0.7 else "grass"
                if r.random() < 0.45:
                    px = (self.cx * CHUNK_SIZE) + r.randint(0, CHUNK_TILES - 1) * TILE_SIZE + TILE_SIZE // 2
                    py = (self.cy * CHUNK_SIZE) + r.randint(0, CHUNK_TILES - 1) * TILE_SIZE + TILE_SIZE // 2
                    self.pickups.append(PickUp(px, py, "chair"))
            elif t < 0.45:
                # small pond
                for tx in range(CHUNK_TILES):
                    for ty in range(CHUNK_TILES):
                        self.tiles[ty][tx] = "grass"
                # add water at center and some around it
                cxw = self.cx * CHUNK_SIZE + (CHUNK_TILES // 2) * TILE_SIZE
                cyw = self.cy * CHUNK_SIZE + (CHUNK_TILES // 2) * TILE_SIZE
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        self.features.append(("pond", cxw + dx * TILE_SIZE, cyw + dy * TILE_SIZE))
                # maybe a few pickups near pond
                if r.random() < 0.3:
                    px = cxw + r.randint(-1, 1) * TILE_SIZE
                    py = cyw + r.randint(-1, 1) * TILE_SIZE
                    self.pickups.append(PickUp(px, py, r.choice(PICKUP_TYPES)))
            elif t < 0.65:
                # fenced yard
                for tx in range(CHUNK_TILES):
                    for ty in range(CHUNK_TILES):
                        self.tiles[ty][tx] = "grass"
                # create fence segments along edges with some openings
                for i in range(CHUNK_TILES):
                    # top and bottom
                    if r.random() < 0.9:
                        self.features.append(("fence", self.cx * CHUNK_SIZE + i * TILE_SIZE + TILE_SIZE//2,
                                              self.cy * CHUNK_SIZE + 0 * TILE_SIZE + TILE_SIZE//2))
                    if r.random() < 0.9:
                        self.features.append(("fence", self.cx * CHUNK_SIZE + i * TILE_SIZE + TILE_SIZE//2,
                                              self.cy * CHUNK_SIZE + (CHUNK_TILES - 1) * TILE_SIZE + TILE_SIZE//2))
                for i in range(CHUNK_TILES):
                    if r.random() < 0.9:
                        self.features.append(("fence", self.cx * CHUNK_SIZE + 0 * TILE_SIZE + TILE_SIZE//2,
                                              self.cy * CHUNK_SIZE + i * TILE_SIZE + TILE_SIZE//2))
                    if r.random() < 0.9:
                        self.features.append(("fence", self.cx * CHUNK_SIZE + (CHUNK_TILES - 1) * TILE_SIZE + TILE_SIZE//2,
                                              self.cy * CHUNK_SIZE + i * TILE_SIZE + TILE_SIZE//2))
                if r.random() < 0.25:
                    px = (self.cx * CHUNK_SIZE) + r.randint(1, CHUNK_TILES - 2) * TILE_SIZE + TILE_SIZE // 2
                    py = (self.cy * CHUNK_SIZE) + r.randint(1, CHUNK_TILES - 2) * TILE_SIZE + TILE_SIZE // 2
                    self.pickups.append(PickUp(px, py, "broom"))
            else:
                # mostly grass, some trees and occasional pickup
                for tx in range(CHUNK_TILES):
                    for ty in range(CHUNK_TILES):
                        self.tiles[ty][tx] = "grass"
                for i in range(r.randint(0, 2)):
                    fx = (self.cx * CHUNK_SIZE) + r.randint(0, CHUNK_TILES - 1) * TILE_SIZE + TILE_SIZE // 2
                    fy = (self.cy * CHUNK_SIZE) + r.randint(0, CHUNK_TILES - 1) * TILE_SIZE + TILE_SIZE // 2
                    self.features.append(("tree", fx, fy))
                if r.random() < 0.18:
                    px = (self.cx * CHUNK_SIZE) + r.randint(0, CHUNK_TILES - 1) * TILE_SIZE + TILE_SIZE // 2
                    py = (self.cy * CHUNK_SIZE) + r.randint(0, CHUNK_TILES - 1) * TILE_SIZE + TILE_SIZE // 2
                    self.pickups.append(PickUp(px, py, r.choice(PICKUP_TYPES)))
        self.generated = True

    def draw(self, surface, cam_pos):
        base_x = self.cx * CHUNK_SIZE
        base_y = self.cy * CHUNK_SIZE
        for ty in range(CHUNK_TILES):
            for tx in range(CHUNK_TILES):
                tile = self.tiles[ty][tx]
                color = TILE_COLORS.get(tile, TILE_COLORS["grass"])
                world_x = base_x + tx * TILE_SIZE
                world_y = base_y + ty * TILE_SIZE
                sx, sy = world_to_screen((world_x, world_y), cam_pos)
                pygame.draw.rect(surface, color, (sx, sy, TILE_SIZE, TILE_SIZE))
        # draw features
        for f in self.features:
            kind, fx, fy = f
            sx, sy = world_to_screen((fx, fy), cam_pos)
            if kind == "plant":
                pygame.draw.circle(surface, (40, 160, 40), (sx, sy), 6)
            elif kind == "tree":
                pygame.draw.circle(surface, (80, 50, 20), (sx, sy + 6), 12)
                pygame.draw.circle(surface, (40, 120, 40), (sx, sy - 8), 22)
            elif kind == "pond":
                pygame.draw.circle(surface, TILE_COLORS["water"], (sx, sy), TILE_SIZE//2 - 4)
            elif kind == "fence":
                # simple fence post
                pygame.draw.rect(surface, TILE_COLORS["fence"], (sx - 4, sy - 10, 8, 16))
            elif kind == "wall":
                # interior simple wall tile
                pygame.draw.rect(surface, (100, 100, 100), (sx - TILE_SIZE//2 + 6, sy - TILE_SIZE//2 + 6, TILE_SIZE - 12, 6))

        for p in list(self.pickups):
            p.draw(surface, cam_pos)

class World:
    def __init__(self):
        self.chunks = {}
        # respawn queue: list of (respawn_time_ms, chunk_key, x, y, ptype)
        self.respawn_queue = []

    def ensure_chunks_around(self, cx, cy, radius=VIEW_DISTANCE_CHUNKS):
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                key = (cx + dx, cy + dy)
                if key not in self.chunks:
                    self.chunks[key] = Chunk(key[0], key[1])

    def draw_near(self, surface, cam_pos):
        cam_cx = int(math.floor(cam_pos[0] / CHUNK_SIZE))
        cam_cy = int(math.floor(cam_pos[1] / CHUNK_SIZE))
        for dx in range(-VIEW_DISTANCE_CHUNKS, VIEW_DISTANCE_CHUNKS + 1):
            for dy in range(-VIEW_DISTANCE_CHUNKS, VIEW_DISTANCE_CHUNKS + 1):
                key = (cam_cx + dx, cam_cy + dy)
                chunk = self.chunks.get(key)
                if chunk:
                    chunk.draw(surface, cam_pos)

    def get_pickups_near(self, rect_world):
        found = []
        for chunk in self.chunks.values():
            for p in list(chunk.pickups):
                if p.collides_world_rect(rect_world):
                    found.append((p, chunk))
        return found

    def remove_pickup(self, pickup):
        # remove a pickup from its chunk and schedule respawn
        for key, chunk in self.chunks.items():
            if pickup in chunk.pickups:
                chunk.pickups.remove(pickup)
                # schedule respawn at a random delay
                delay = random.randint(PICKUP_RESPAWN_MIN_MS, PICKUP_RESPAWN_MAX_MS)
                respawn_time = pygame.time.get_ticks() + delay
                # store world coords and type
                self.respawn_queue.append((respawn_time, key, pickup.x, pickup.y, pickup.ptype))
                return

    def update(self):
        now = pygame.time.get_ticks()
        remaining = []
        for item in self.respawn_queue:
            respawn_time, key, x, y, ptype = item
            if now >= respawn_time:
                # only respawn if chunk still exists; otherwise it will be created later and we'll add it lazily
                chunk = self.chunks.get(key)
                if chunk:
                    chunk.pickups.append(PickUp(x, y, ptype))
            else:
                remaining.append(item)
        self.respawn_queue = remaining

# -------- Entities: pickups & players & enemies --------
class PickUp:
    def __init__(self, x, y, ptype):
        self.x = x
        self.y = y
        self.ptype = ptype
        self.radius = 14

    def draw(self, surface, cam_pos):
        sx, sy = world_to_screen((self.x, self.y), cam_pos)
        if self.ptype == "frying_pan":
            pygame.draw.circle(surface, (170, 120, 60), (sx, sy), 8)
            pygame.draw.rect(surface, (120, 80, 40), (sx - 10, sy + 6, 20, 4))
        elif self.ptype == "broom":
            pygame.draw.line(surface, (180, 140, 90), (sx - 10, sy - 6), (sx + 10, sy + 6), 4)
        elif self.ptype == "chair":
            pygame.draw.rect(surface, (120, 90, 70), (sx - 10, sy - 6, 20, 12), border_radius=3)
        elif self.ptype == "tomato":
            pygame.draw.circle(surface, (220, 30, 30), (sx, sy), 6)
        # small shadow (non-alpha fallback)
        pygame.draw.circle(surface, (0, 0, 0), (sx + 2, sy + 8), 5)

    def collides_world_rect(self, rect_world):
        rx, ry, rw, rh = rect_world
        if (self.x >= rx - self.radius and self.x <= rx + rw + self.radius and
                self.y >= ry - self.radius and self.y <= ry + rh + self.radius):
            return True
        return False

class Mom:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.radius = 18
        self.facing = "right"
        self.slapping = False
        self.slap_start = 0
        self.last_slap = -SLAP_COOLDOWN
        self.weapon = "fist"  # key
        self.weapon_hold = None  # not strictly needed, we store inventory instead
        self.inventory = []  # list of pickup types carried
        self.vx = 0
        self.vy = 0
        self.bob = 0.0

    def world_rect(self):
        return (self.x - self.radius, self.y - self.radius, self.radius * 2, self.radius * 2)

    def try_pickup(self, world):
        rect = self.world_rect()
        found = world.get_pickups_near(rect)
        if found:
            p, chunk = found[0]
            # add to inventory
            self.inventory.append(p.ptype)
            # auto-equip if fists
            if self.weapon == "fist":
                self.weapon = p.ptype
            # remove from world and schedule respawn
            world.remove_pickup(p)
            return True
        return False

    def try_slap(self):
        now = pygame.time.get_ticks()
        wconf = WEAPONS.get(self.weapon, WEAPONS["fist"])
        if now - self.last_slap >= wconf.get("cooldown", SLAP_COOLDOWN):
            self.slapping = True
            self.slap_start = now
            self.last_slap = now
            return True
        return False

    def update(self, dt, keys):
        speed = MOM_SPEED * (dt / 1000.0)
        dx = dy = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            dx -= 1
            self.facing = "left"
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            dx += 1
            self.facing = "right"
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            dy -= 1
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            dy += 1
        mag = math.hypot(dx, dy)
        if mag > 0:
            dx /= mag; dy /= mag
        self.x += dx * speed
        self.y += dy * speed
        self.bob += 0.08 * (1 + mag)
        if self.bob > 9999:
            self.bob = 0
        if self.slapping and pygame.time.get_ticks() - self.slap_start > SLAP_DURATION:
            self.slapping = False

    def draw(self, surface, cam_pos):
        sx, sy = world_to_screen((self.x, self.y), cam_pos)
        bob_y = int(math.sin(self.bob) * 3)
        pygame.draw.ellipse(surface, (200, 80, 80), (sx - 18, sy - 10 + bob_y, 36, 46))
        pygame.draw.circle(surface, (245, 210, 175), (sx, sy - 28 + bob_y), 12)
        pygame.draw.circle(surface, (100, 50, 20), (sx + 10, sy - 36 + bob_y), 6)
        if self.weapon:
            draw_text(surface, WEAPONS[self.weapon]["name"], sx - 32, sy + 34, font)
        if self.slapping:
            wconf = WEAPONS.get(self.weapon, WEAPONS["fist"])
            rng = wconf.get("range", 78)
            if self.facing == "right":
                pygame.draw.rect(surface, (170, 120, 60), (sx + 8, sy - 4 + bob_y, rng // 2, 10), border_radius=6)
            else:
                pygame.draw.rect(surface, (170, 120, 60), (sx - 8 - rng // 2, sy - 4 + bob_y, rng // 2, 10), border_radius=6)

class Mafia:
    def __init__(self, x, y, speed):
        self.x = x
        self.y = y
        self.radius = 16
        self.speed = speed
        self.health = 1
        self.color = (30, 30, 50)
        self.stagger_till = 0
        self.knock_vx = 0
        self.knock_vy = 0

    def world_rect(self):
        return (self.x - self.radius, self.y - self.radius, self.radius * 2, self.radius * 2)

    def update(self, dt, mom_x, mom_y):
        now = pygame.time.get_ticks()
        if now < self.stagger_till:
            self.x += self.knock_vx * (dt / 16.0)
            self.y += self.knock_vy * (dt / 16.0)
            self.knock_vx *= 0.92
            self.knock_vy *= 0.92
            return
        dx = mom_x - self.x
        dy = mom_y - self.y
        dist = math.hypot(dx, dy) + 0.01
        nx = dx / dist
        ny = dy / dist
        self.x += nx * self.speed * (dt / 1000.0)
        self.y += ny * self.speed * (dt / 1000.0)

    def draw(self, surface, cam_pos):
        sx, sy = world_to_screen((self.x, self.y), cam_pos)
        pygame.draw.rect(surface, self.color, (sx - 12, sy - 20, 24, 36), border_radius=6)
        pygame.draw.circle(surface, (210, 180, 150), (sx, sy - 28), 10)

    def apply_hit(self, dmg, knockx, knocky, stagger_ms=220):
        self.health -= dmg
        self.knock_vx += knockx
        self.knock_vy += knocky
        self.stagger_till = pygame.time.get_ticks() + stagger_ms

class Projectile:
    def __init__(self, x, y, vx, vy, damage, ttl=3000):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.damage = damage
        self.ttl = ttl
        self.spawn = pygame.time.get_ticks()
        self.radius = 6

    def update(self, dt):
        self.x += self.vx * (dt / 1000.0)
        self.y += self.vy * (dt / 1000.0)
        # gravity for thrown heavy items
        self.vy += 240 * (dt / 1000.0) * 0.12

    def draw(self, surface, cam_pos):
        sx, sy = world_to_screen((self.x, self.y), cam_pos)
        pygame.draw.circle(surface, (220, 30, 30), (sx, sy), self.radius)

    def expired(self):
        return pygame.time.get_ticks() - self.spawn > self.ttl

# -------- Game class --------
class Game:
    def __init__(self):
        self.world = World()
        self.mom = Mom(0 + CHUNK_SIZE // 2, 0 + CHUNK_SIZE // 2)
        self.world.ensure_chunks_around(0, 0)
        self.mafias = []
        self.bullets = []
        self.score = 0
        self.lives = STARTING_LIVES
        self.last_spawn = 0
        self.running = True
        self.game_over = False

    def spawn_mafia_near(self):
        angle = random.random() * math.tau
        dist = CHUNK_SIZE * (VIEW_DISTANCE_CHUNKS + 0.5)
        x = self.mom.x + math.cos(angle) * dist
        y = self.mom.y + math.sin(angle) * dist
        speed = random.uniform(MAFIA_MIN_SPEED, MAFIA_MAX_SPEED)
        m = Mafia(x, y, speed)
        self.mafias.append(m)

    def update(self, dt):
        if self.game_over:
            return
        keys = pygame.key.get_pressed()
        self.mom.update(dt, keys)
        cam_cx = int(math.floor(self.mom.x / CHUNK_SIZE))
        cam_cy = int(math.floor(self.mom.y / CHUNK_SIZE))
        self.world.ensure_chunks_around(cam_cx, cam_cy)
        # world respawn processing
        self.world.update()

        for m in list(self.mafias):
            m.update(dt, self.mom.x, self.mom.y)
            if rects_collide(m.world_rect(), self.mom.world_rect()):
                self.lives -= 1
                try:
                    self.mafias.remove(m)
                except ValueError:
                    pass
                if self.lives <= 0:
                    self.game_over = True

        for p in list(self.bullets):
            p.update(dt)
            for m in list(self.mafias):
                if point_in_rect((p.x, p.y), m.world_rect()):
                    m.apply_hit(p.damage, p.vx * 0.02, p.vy * 0.02)
                    self.score += p.damage
                    try:
                        self.mafias.remove(m)
                    except ValueError:
                        pass
                    if p in self.bullets:
                        self.bullets.remove(p)
            if p.expired():
                if p in self.bullets:
                    self.bullets.remove(p)

        now = pygame.time.get_ticks()
        if now - self.last_spawn > MAFIA_SPAWN_INTERVAL:
            self.spawn_mafia_near()
            self.last_spawn = now

    def handle_input_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                did = self.mom.try_slap()
                if did:
                    wconf = WEAPONS.get(self.mom.weapon, WEAPONS["fist"])
                    if wconf.get("type") == "melee":
                        rng = wconf.get("range", 78)
                        dmg = wconf.get("damage", 1)
                        rect_world = self.get_slap_world_rect(rng)
                        for m in list(self.mafias):
                            if rects_collide(m.world_rect(), rect_world):
                                dx = m.x - self.mom.x
                                dy = m.y - self.mom.y
                                dist = math.hypot(dx, dy) + 0.01
                                kx = (dx / dist) * 120
                                ky = (dy / dist) * 120
                                m.apply_hit(dmg, kx, ky)
                                self.score += dmg
                                if m.health <= 0 and m in self.mafias:
                                    self.mafias.remove(m)
                    else:
                        w = WEAPONS.get(self.mom.weapon)
                        if w:
                            speed = w.get("speed", 240)
                            dirx = 1 if self.mom.facing == "right" else -1
                            vx = dirx * speed
                            vy = -40
                            proj = Projectile(self.mom.x + dirx * 16, self.mom.y - 6, vx, vy, w.get("damage", 1))
                            self.bullets.append(proj)
                            # remove one tomato from inventory if present (tomato is single-use)
                            if self.mom.weapon == "tomato":
                                # remove one tomato from inventory
                                try:
                                    self.mom.inventory.remove("tomato")
                                except ValueError:
                                    pass
                                self.mom.weapon = "fist"

            elif event.key == pygame.K_e:
                picked = self.mom.try_pickup(self.world)
                # picked returns True if picked up; world.remove_pickup handled scheduling of respawn

            elif event.key == pygame.K_f:
                # throw currently equipped heavy item
                if self.mom.weapon in ["chair", "broom", "frying_pan"]:
                    dirx = 1 if self.mom.facing == "right" else -1
                    vx = dirx * 260
                    vy = -120
                    dmg = WEAPONS.get(self.mom.weapon, WEAPONS["fist"]).get("damage", 1) + 1
                    proj = Projectile(self.mom.x + dirx * 20, self.mom.y - 6, vx, vy, dmg)
                    self.bullets.append(proj)
                    # consume the item from inventory (if present)
                    try:
                        self.mom.inventory.remove(self.mom.weapon)
                    except ValueError:
                        pass
                    self.mom.weapon = "fist"

    def get_slap_world_rect(self, rng):
        if self.mom.facing == "right":
            left = self.mom.x + 10
            top = self.mom.y - SLAP_WIDTH
            return (left, top, rng, SLAP_WIDTH * 2)
        else:
            right = self.mom.x - 10
            left = right - rng
            top = self.mom.y - SLAP_WIDTH
            return (left, top, rng, SLAP_WIDTH * 2)

    def draw(self, surface):
        cam = (self.mom.x, self.mom.y)
        surface.fill(BG_COLOR)
        self.world.draw_near(surface, cam)
        for m in sorted(self.mafias, key=lambda x: x.y):
            m.draw(surface, cam)
        for p in list(self.bullets):
            p.draw(surface, cam)
        self.mom.draw(surface, cam)
        draw_text(surface, f"Score: {self.score}", 14, 8, font)
        draw_text(surface, f"Lives: {self.lives}", 14, 34, font)
        draw_text(surface, f"Weapon: {WEAPONS[self.mom.weapon]['name']}", SCREEN_WIDTH - 240, 8, font)
        # inventory compact
        invtext = "Inv: " + ",".join(self.mom.inventory[-6:]) if self.mom.inventory else "Inv: (empty)"
        draw_text(surface, invtext, SCREEN_WIDTH - 420, 34, font)
        draw_text(surface, "E: Pick up   F: Throw held   Space: Use/Slap", SCREEN_WIDTH - 420, 56, font)
        if self.game_over:
            draw_text(surface, "GAME OVER", SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 30, big_font, center=True)
            draw_text(surface, f"Final Score: {self.score}", SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 20, font, center=True)

    def run_frame(self, dt):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_r and self.game_over:
                    self.__init__()
                else:
                    self.handle_input_event(event)
        self.update(dt)
        # FIX: use the global screen variable (previous code used an undefined `surface` here)
        self.draw(screen)
        pygame.display.flip()

    def run(self):
        while self.running:
            dt = clock.tick(FPS)
            self.run_frame(dt)
        pygame.quit()
        sys.exit()

# -------- Utility functions --------
def rects_collide(a, b):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return not (ax + aw < bx or ax > bx + bw or ay + ah < by or ay > by + bh)

def point_in_rect(p, r):
    x, y = p
    rx, ry, rw, rh = r
    return x >= rx and x <= rx + rw and y >= ry and y <= ry + rh

# -------- Entry Point --------
if __name__ == "__main__":
    g = Game()
    try:
        g.run()
    except Exception as e:
        print("Error running game:", e)
        pygame.quit()
        raise
