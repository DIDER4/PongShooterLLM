"""
Shoote game project. October 2024.
- Programming a Shooter game using an LLM
- Dynamisk banegenerering og avancerede spilelementer
"""

# -*- coding: utf-8 -*-
"""
Created on Thu Oct 24 11:41:14 2024

@author: sila
"""


import pygame
import math
import random
import sys
import os
import time

# Initialize pygame
pygame.init()

# Screen dimensions (larger map)
SCREEN_WIDTH, SCREEN_HEIGHT = 1200, 900
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Advanced FPS Shooter")

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
YELLOW = (255, 255, 0)
BLUE = (0, 0, 255)
PURPLE = (128, 0, 128)
ORANGE = (255, 165, 0)

# Load sprites
SPRITES_DIR = os.path.join(os.path.dirname(__file__), 'sprites')
def load_image(filename, size=None):
    try:
        path = os.path.join(SPRITES_DIR, filename)
        image = pygame.image.load(path).convert_alpha()
        if size:
            image = pygame.transform.scale(image, size)
        return image
    except Exception as e:
        print(f"Error loading image {filename}: {e}")
        return None

# Sizes for our game objects
PLAYER_SIZE = (40, 40)
ENEMY_SIZE = (50, 50)
BULLET_SIZE = (60, 60)  # Store skud for bedre synlighed
POWERUP_SIZE = (30, 30)

# Load all sprite images
player_img = load_image('Spiller.png', PLAYER_SIZE)
enemy_img = load_image('fjende.png', ENEMY_SIZE)
bullet_img = load_image('skud.png', BULLET_SIZE)
wall_img = load_image('vaeg.jpg')

# Font
font = pygame.font.Font(None, 36)
large_font = pygame.font.Font(None, 72)
small_font = pygame.font.Font(None, 24)

# Sound effects (optional, fallback if not found)
def load_sound(path):
    try:
        return pygame.mixer.Sound(path)
    except:
        return None

shoot_sound = load_sound('shoot.wav')
hit_sound = load_sound('hit.wav')
gameover_sound = load_sound('gameover.wav')
powerup_sound = load_sound('powerup.wav')

# Våbentyper
WEAPON_TYPES = {
    "pistol": {"damage": 1, "cooldown": 300, "bullet_speed": 12, "bullet_size": BULLET_SIZE},
    "shotgun": {"damage": 1, "cooldown": 800, "bullet_speed": 10, "bullet_size": (50, 50), "spread": 3},
    "machine_gun": {"damage": 0.5, "cooldown": 100, "bullet_speed": 15, "bullet_size": (40, 40)},
    "sniper": {"damage": 3, "cooldown": 1200, "bullet_speed": 20, "bullet_size": (70, 70)}
}

# Powerup typer
POWERUP_TYPES = ["health", "speed", "shield", "weapon", "score_multiplier"]

class Obstacle:
    def __init__(self, x, y, w, h):
        self.rect = pygame.Rect(x, y, w, h)
        # Create a scaled copy of the wall image for this specific obstacle
        if wall_img:
            self.image = pygame.transform.scale(wall_img, (w, h))
        else:
            self.image = None

    def draw(self, surface):
        if self.image:
            surface.blit(self.image, self.rect.topleft)
        else:
            pygame.draw.rect(surface, (80, 80, 80), self.rect)

    def collides(self, x, y, radius):
        # Circle-rectangle collision
        circle_dist_x = abs(x - self.rect.centerx)
        circle_dist_y = abs(y - self.rect.centery)
        if circle_dist_x > (self.rect.width/2 + radius): return False
        if circle_dist_y > (self.rect.height/2 + radius): return False
        if circle_dist_x <= (self.rect.width/2): return True
        if circle_dist_y <= (self.rect.height/2): return True
        corner_dist_sq = (circle_dist_x - self.rect.width/2)**2 + (circle_dist_y - self.rect.height/2)**2
        return corner_dist_sq <= radius**2

class Powerup:
    def __init__(self, x, y, type_name):
        self.x = x
        self.y = y
        self.type = type_name
        self.radius = POWERUP_SIZE[0] // 2
        self.active = True
        self.pulse = 0
        self.colors = {
            "health": RED,
            "speed": YELLOW,
            "shield": BLUE,
            "weapon": ORANGE,
            "score_multiplier": PURPLE
        }

    def update(self):
        self.pulse = (self.pulse + 0.05) % (2 * math.pi)

    def draw(self, surface):
        color = self.colors.get(self.type, WHITE)
        size_mod = math.sin(self.pulse) * 3
        pygame.draw.circle(surface, color, (int(self.x), int(self.y)), int(self.radius + size_mod))

        # Draw icon based on type
        text = small_font.render(self.type[0].upper(), True, WHITE)
        text_rect = text.get_rect(center=(int(self.x), int(self.y)))
        surface.blit(text, text_rect)

class Player:
    def __init__(self, obstacles=None):
        self.obstacles = obstacles or []

        # Forsøg at finde en sikker spawn position for spilleren
        self.radius = PLAYER_SIZE[0] // 2
        safe_spawn = False
        attempts = 0
        self.x = SCREEN_WIDTH // 2
        self.y = SCREEN_HEIGHT // 2

        # Prøv at finde en sikker position, start med centrum og udvid gradvist
        while not safe_spawn and attempts < 20:
            safe_spawn = True
            # Check om positionen kolliderer med nogen forhindringer
            for obs in self.obstacles:
                if obs.collides(self.x, self.y, self.radius):
                    safe_spawn = False
                    # Prøv en ny position
                    offset = 100 * (attempts + 1)
                    self.x = SCREEN_WIDTH // 2 + random.randint(-offset, offset)
                    self.y = SCREEN_HEIGHT // 2 + random.randint(-offset, offset)
                    # Hold positionen inden for skærmen
                    self.x = max(self.radius, min(SCREEN_WIDTH - self.radius, self.x))
                    self.y = max(self.radius, min(SCREEN_HEIGHT - self.radius, self.y))
                    attempts += 1
                    break

        self.angle = 0
        self.speed = 5
        self.base_speed = 5
        self.turn_speed = 5
        self.health = 1000
        self.max_health = 1000
        self.last_shot = 0
        self.image = player_img

        # Nye variabler
        self.shield = 0
        self.max_shield = 50
        self.weapon = "pistol"
        self.weapons_owned = ["pistol"]
        self.score_multiplier = 1
        self.score_multiplier_time = 0
        self.speed_boost_time = 0

    def move(self, keys):
        old_x, old_y = self.x, self.y

        # Check for speed boost timeout
        current_time = pygame.time.get_ticks()
        if current_time > self.speed_boost_time and self.speed > self.base_speed:
            self.speed = self.base_speed

        if keys[pygame.K_LEFT]:
            self.angle -= self.turn_speed
        if keys[pygame.K_RIGHT]:
            self.angle += self.turn_speed
        if keys[pygame.K_UP]:
            self.x += self.speed * math.cos(math.radians(self.angle))
            self.y += self.speed * math.sin(math.radians(self.angle))
        if keys[pygame.K_DOWN]:
            self.x -= self.speed * math.cos(math.radians(self.angle))
            self.y -= self.speed * math.sin(math.radians(self.angle))

        # Weapon switching
        if keys[pygame.K_1] and "pistol" in self.weapons_owned:
            self.weapon = "pistol"
        if keys[pygame.K_2] and "shotgun" in self.weapons_owned:
            self.weapon = "shotgun"
        if keys[pygame.K_3] and "machine_gun" in self.weapons_owned:
            self.weapon = "machine_gun"
        if keys[pygame.K_4] and "sniper" in self.weapons_owned:
            self.weapon = "sniper"

        # Keep player on screen
        self.x = max(self.radius, min(SCREEN_WIDTH - self.radius, self.x))
        self.y = max(self.radius, min(SCREEN_HEIGHT - self.radius, self.y))
        # Prevent moving through obstacles
        for obs in self.obstacles:
            if obs.collides(self.x, self.y, self.radius):
                self.x, self.y = old_x, old_y
                break

    def draw(self, surface):
        if self.image:
            # Rotate the player image
            rotated = pygame.transform.rotate(self.image, -self.angle)
            # Get the rectangle of the rotated image
            rect = rotated.get_rect()
            # Position the rectangle centered on the player's position
            rect.center = (int(self.x), int(self.y))
            # Draw the rotated image
            surface.blit(rotated, rect.topleft)
        else:
            # Fallback to circle if image loading failed
            pygame.draw.circle(surface, GREEN, (int(self.x), int(self.y)), self.radius)
            end_x = self.x + self.radius * math.cos(math.radians(self.angle))
            end_y = self.y + self.radius * math.sin(math.radians(self.angle))
            pygame.draw.line(surface, WHITE, (self.x, self.y), (end_x, end_y), 4)

        # Draw shield if active
        if self.shield > 0:
            pygame.draw.circle(surface, BLUE, (int(self.x), int(self.y)),
                              int(self.radius + 5), 2)

        # Draw current weapon icon
        weapon_text = small_font.render(self.weapon, True, WHITE)
        surface.blit(weapon_text, (self.x - 20, self.y - self.radius - 20))

        # Draw multiplier if active
        if pygame.time.get_ticks() < self.score_multiplier_time:
            mult_text = small_font.render(f"{self.score_multiplier}x", True, PURPLE)
            surface.blit(mult_text, (self.x + 20, self.y - self.radius - 20))

    def can_shoot(self):
        weapon_cooldown = WEAPON_TYPES[self.weapon]["cooldown"]
        return pygame.time.get_ticks() - self.last_shot > weapon_cooldown

    def shoot(self):
        self.last_shot = pygame.time.get_ticks()
        if shoot_sound:
            shoot_sound.play()

        weapon_data = WEAPON_TYPES[self.weapon]

        if self.weapon == "shotgun":
            bullets = []
            for i in range(-1, 2):  # -1, 0, 1
                spread_angle = self.angle + (i * 15)  # 15-degree spread
                bullets.append(Bullet(
                    self.x, self.y, spread_angle, self.obstacles,
                    damage=weapon_data["damage"],
                    speed=weapon_data["bullet_speed"],
                    size=weapon_data["bullet_size"]
                ))
            return bullets
        else:
            return [Bullet(
                self.x, self.y, self.angle, self.obstacles,
                damage=weapon_data["damage"],
                speed=weapon_data["bullet_speed"],
                size=weapon_data["bullet_size"]
            )]

    def collect_powerup(self, powerup):
        if powerup.type == "health":
            self.health = min(self.max_health, self.health + 25)
        elif powerup.type == "speed":
            self.speed = self.base_speed * 1.5
            self.speed_boost_time = pygame.time.get_ticks() + 10000  # 10 seconds
        elif powerup.type == "shield":
            self.shield = min(self.max_shield, self.shield + 30)
        elif powerup.type == "weapon":
            available_weapons = [w for w in WEAPON_TYPES.keys() if w not in self.weapons_owned]
            if available_weapons:
                new_weapon = random.choice(available_weapons)
                self.weapons_owned.append(new_weapon)
                self.weapon = new_weapon
        elif powerup.type == "score_multiplier":
            self.score_multiplier = 2
            self.score_multiplier_time = pygame.time.get_ticks() + 15000  # 15 seconds

        if powerup_sound:
            powerup_sound.play()

    def take_damage(self, amount):
        # First reduce shield, then health
        if self.shield > 0:
            if amount <= self.shield:
                self.shield -= amount
                amount = 0
            else:
                amount -= self.shield
                self.shield = 0

        if amount > 0:
            self.health -= amount

        return self.health <= 0

class Enemy:
    def __init__(self, obstacles=None, difficulty=1.0):
        self.obstacles = obstacles or []
        self.radius = ENEMY_SIZE[0] // 2

        # Forsøg at finde en sikker spawn position for fjenden
        safe_spawn = False
        attempts = 0
        self.x = random.randint(50, SCREEN_WIDTH-50)
        self.y = random.randint(50, SCREEN_HEIGHT-50)

        # Prøv at finde en sikker position
        while not safe_spawn and attempts < 20:
            safe_spawn = True
            # Check om positionen kolliderer med nogen forhindringer
            for obs in self.obstacles:
                if obs.collides(self.x, self.y, self.radius):
                    safe_spawn = False
                    # Prøv en ny position
                    self.x = random.randint(50, SCREEN_WIDTH-50)
                    self.y = random.randint(50, SCREEN_HEIGHT-50)
                    attempts += 1
                    break

        self.health = 3
        self.speed = random.uniform(1.5, 2.5) * difficulty
        self.angle = random.uniform(0, 360)
        self.image = enemy_img
        self.aggression = random.uniform(0.5, 1.0) * difficulty
        self.last_shot = 0
        self.shot_cooldown = random.randint(1500, 3000) // difficulty

        # Random behavior traits
        self.behavior_type = random.choice(["chaser", "flanker", "ambusher"])

        # Visual differentiation based on behavior
        self.color_tint = {
            "chaser": (255, 100, 100),  # Reddish
            "flanker": (100, 255, 100),  # Greenish
            "ambusher": (100, 100, 255)  # Bluish
        }.get(self.behavior_type, (255, 255, 255))

    def update(self, player, game_time):
        # Move towards player, avoid obstacles
        dx = player.x - self.x
        dy = player.y - self.y
        dist = math.hypot(dx, dy)

        # Update angle to face player
        if dist > 0:
            self.angle = math.degrees(math.atan2(dy, dx))

        # Different behaviors based on type
        if self.behavior_type == "chaser":
            # Direct chase
            target_x, target_y = player.x, player.y
        elif self.behavior_type == "flanker":
            # Try to circle around player
            perp_angle = math.radians(self.angle + 90)
            circle_dist = 200
            target_x = player.x + circle_dist * math.cos(perp_angle)
            target_y = player.y + circle_dist * math.sin(perp_angle)
        elif self.behavior_type == "ambusher":
            # Hide behind obstacles and approach slowly
            if dist < 300:
                target_x, target_y = self.x, self.y  # Stay in place
            else:
                target_x, target_y = player.x, player.y

        # Calculate direction to target
        tx = target_x - self.x
        ty = target_y - self.y
        target_dist = math.hypot(tx, ty)

        if target_dist > 0:
            new_x = self.x + self.speed * tx / target_dist
            new_y = self.y + self.speed * ty / target_dist
            blocked = False
            for obs in self.obstacles:
                if obs.collides(new_x, new_y, self.radius):
                    blocked = True
                    break
            if not blocked:
                self.x, self.y = new_x, new_y

        # Maybe shoot at player
        can_shoot = game_time - self.last_shot > self.shot_cooldown
        if can_shoot and dist < 400 and random.random() < self.aggression:
            self.last_shot = game_time
            return True

        return False

    def draw(self, surface):
        if self.image:
            # Apply color tint to differentiate enemy types
            tinted_img = self.image.copy()
            tinted_img.fill(self.color_tint, special_flags=pygame.BLEND_RGBA_MULT)

            # Rotate the enemy image to face player
            rotated = pygame.transform.rotate(tinted_img, -self.angle)
            rect = rotated.get_rect()
            rect.center = (int(self.x), int(self.y))
            surface.blit(rotated, rect.topleft)
        else:
            # Fallback to circle if image loading failed
            pygame.draw.circle(surface, RED, (int(self.x), int(self.y)), self.radius)

        # Health bar
        health_bar_len = int(30 * self.health / 3)
        pygame.draw.rect(surface, GREEN, (self.x-15, self.y-self.radius-10, health_bar_len, 5))

        # Behavior type indicator
        type_text = small_font.render(self.behavior_type[0], True, WHITE)
        surface.blit(type_text, (self.x-5, self.y-5))

    def hit(self, damage=1):
        self.health -= damage
        if hit_sound:
            hit_sound.play()
        return self.health <= 0

class Bullet:
    def __init__(self, x, y, angle, obstacles=None, damage=1, speed=12, size=BULLET_SIZE):
        self.x = x
        self.y = y
        self.angle = angle
        self.speed = speed
        self.damage = damage
        self.radius = size[0] // 2
        self.active = True
        self.obstacles = obstacles or []
        self.image = bullet_img
        if size != BULLET_SIZE and bullet_img:
            self.image = pygame.transform.scale(bullet_img, size)

        # Trail effect
        self.trail = []
        self.max_trail_length = 5

    def update(self):
        # Save position for trail
        self.trail.append((self.x, self.y))
        if len(self.trail) > self.max_trail_length:
            self.trail.pop(0)

        new_x = self.x + self.speed * math.cos(math.radians(self.angle))
        new_y = self.y + self.speed * math.sin(math.radians(self.angle))
        for obs in self.obstacles:
            if obs.collides(new_x, new_y, self.radius):
                self.active = False
                return
        self.x, self.y = new_x, new_y
        if self.x < 0 or self.x > SCREEN_WIDTH or self.y < 0 or self.y > SCREEN_HEIGHT:
            self.active = False

    def draw(self, surface):
        # Draw trail
        for i, pos in enumerate(self.trail):
            alpha = int(255 * (i / len(self.trail)))
            size = int(self.radius * 0.7 * (i / len(self.trail)))
            pygame.draw.circle(surface, (255, 255, 0, alpha),
                              (int(pos[0]), int(pos[1])), size)

        if self.image:
            # Rotate the bullet image
            rotated = pygame.transform.rotate(self.image, -self.angle)
            rect = rotated.get_rect()
            rect.center = (int(self.x), int(self.y))
            surface.blit(rotated, rect.topleft)
        else:
            # Fallback to circle if image loading failed
            pygame.draw.circle(surface, YELLOW, (int(self.x), int(self.y)), self.radius)

def generate_random_map(min_obstacles=5, max_obstacles=10, min_size=50, max_size=250):
    """Genererer en tilfældig bane med forhindringer"""
    obstacles = []
    num_obstacles = random.randint(min_obstacles, max_obstacles)

    # Grid-based placement to avoid complete overlap
    grid_size = 200
    grid_cols = SCREEN_WIDTH // grid_size
    grid_rows = SCREEN_HEIGHT // grid_size

    # Create a grid to track used cells
    used_cells = set()

    # Ensure center area is clear for player spawn
    center_x = SCREEN_WIDTH // 2
    center_y = SCREEN_HEIGHT // 2
    center_cell_x = center_x // grid_size
    center_cell_y = center_y // grid_size
    used_cells.add((center_cell_x, center_cell_y))

    for _ in range(num_obstacles):
        attempts = 0
        while attempts < 10:  # Prøv 10 gange at placere en forhindring
            cell_x = random.randint(0, grid_cols-1)
            cell_y = random.randint(0, grid_rows-1)

            # Skip if cell is already used
            if (cell_x, cell_y) in used_cells:
                attempts += 1
                continue

            # Randomize obstacle properties
            w = random.randint(min_size, max_size)
            h = random.randint(min_size, max_size)
            x = cell_x * grid_size + random.randint(0, grid_size - min_size)
            y = cell_y * grid_size + random.randint(0, grid_size - min_size)

            # Constrain to screen
            x = min(max(0, x), SCREEN_WIDTH - w)
            y = min(max(0, y), SCREEN_HEIGHT - h)

            # Add obstacle and mark cell as used
            obstacles.append(Obstacle(x, y, w, h))
            used_cells.add((cell_x, cell_y))
            break

        attempts += 1

    return obstacles

class Minimap:
    def __init__(self, width=200, height=150):
        self.width = width
        self.height = height
        self.surface = pygame.Surface((width, height))
        self.scale_x = width / SCREEN_WIDTH
        self.scale_y = height / SCREEN_HEIGHT

    def update(self, player, obstacles, enemies):
        self.surface.fill((0, 0, 0))

        # Draw border
        pygame.draw.rect(self.surface, (100, 100, 100), (0, 0, self.width, self.height), 2)

        # Draw obstacles
        for obs in obstacles:
            x = obs.rect.x * self.scale_x
            y = obs.rect.y * self.scale_y
            w = obs.rect.width * self.scale_x
            h = obs.rect.height * self.scale_y
            pygame.draw.rect(self.surface, (150, 150, 150), (x, y, w, h))

        # Draw enemies
        for enemy in enemies:
            x = enemy.x * self.scale_x
            y = enemy.y * self.scale_y
            pygame.draw.circle(self.surface, (255, 0, 0), (int(x), int(y)), 3)

        # Draw player
        px = player.x * self.scale_x
        py = player.y * self.scale_y
        pygame.draw.circle(self.surface, (0, 255, 0), (int(px), int(py)), 4)

    def draw(self, surface, x, y):
        surface.blit(self.surface, (x, y))

class Game:
    def __init__(self):
        # Dynamisk banegenerering ved hver ny spil
        self.obstacles = generate_random_map()

        self.player = Player(self.obstacles)
        self.bullets = []
        self.enemy_bullets = []
        self.enemies = [Enemy(self.obstacles) for _ in range(5)]
        self.powerups = []
        self.score = 0
        self.high_score = self.load_high_score()
        self.running = True
        self.game_over = False
        self.clock = pygame.time.Clock()
        self.minimap = Minimap()
        self.level = 1
        self.next_level_score = 10
        self.difficulty = 1.0
        self.last_powerup_time = 0
        self.powerup_interval = 10000  # 10 seconds between powerups

    def load_high_score(self):
        try:
            with open("highscore.txt", "r") as f:
                return int(f.read().strip())
        except:
            return 0

    def save_high_score(self):
        try:
            with open("highscore.txt", "w") as f:
                f.write(str(max(self.high_score, self.score)))
        except:
            pass

    def spawn_enemy(self):
        self.enemies.append(Enemy(self.obstacles, self.difficulty))

    def spawn_powerup(self):
        # Don't spawn too many powerups
        if len(self.powerups) > 3:
            return

        # Find a valid position away from obstacles
        valid_pos = False
        tries = 0
        while not valid_pos and tries < 20:
            x = random.randint(50, SCREEN_WIDTH - 50)
            y = random.randint(50, SCREEN_HEIGHT - 50)

            # Check if position is clear of obstacles
            clear = True
            for obs in self.obstacles:
                if obs.collides(x, y, 20):
                    clear = False
                    break

            if clear:
                powerup_type = random.choice(POWERUP_TYPES)
                self.powerups.append(Powerup(x, y, powerup_type))
                valid_pos = True

            tries += 1

    def check_level_up(self):
        if self.score >= self.next_level_score:
            self.level += 1
            self.difficulty += 0.2
            self.next_level_score = self.next_level_score * 2

            # Spawn additional enemies
            for _ in range(2):
                self.spawn_enemy()

            # Increase player max health
            self.player.max_health += 20
            self.player.health = self.player.max_health

    def update(self):
        game_time = pygame.time.get_ticks()

        # Check for powerup spawn
        if game_time - self.last_powerup_time > self.powerup_interval:
            self.spawn_powerup()
            self.last_powerup_time = game_time

        keys = pygame.key.get_pressed()
        if not self.game_over:
            self.player.move(keys)

            # Shooting
            if keys[pygame.K_SPACE] and self.player.can_shoot():
                new_bullets = self.player.shoot()
                self.bullets.extend(new_bullets)

            # Update bullets
            for bullet in self.bullets:
                bullet.update()
            self.bullets = [b for b in self.bullets if b.active]

            # Update enemy bullets
            for bullet in self.enemy_bullets:
                bullet.update()

                # Check for collision with player
                if math.hypot(bullet.x - self.player.x, bullet.y - self.player.y) < self.player.radius + bullet.radius:
                    bullet.active = False
                    game_over = self.player.take_damage(1)
                    if game_over:
                        self.game_over = True
                        if gameover_sound:
                            gameover_sound.play()

            self.enemy_bullets = [b for b in self.enemy_bullets if b.active]

            # Update powerups
            for powerup in self.powerups:
                powerup.update()

                # Check if player collected powerup
                if math.hypot(powerup.x - self.player.x, powerup.y - self.player.y) < self.player.radius + powerup.radius:
                    self.player.collect_powerup(powerup)
                    powerup.active = False

            self.powerups = [p for p in self.powerups if p.active]

            # Update enemies
            for enemy in self.enemies:
                should_shoot = enemy.update(self.player, game_time)

                # Enemy may shoot at player
                if should_shoot:
                    enemy_bullet = Bullet(
                        enemy.x, enemy.y, enemy.angle, self.obstacles,
                        damage=1, speed=8, size=(40, 40)
                    )
                    self.enemy_bullets.append(enemy_bullet)

            # Bullet-enemy collision
            for bullet in self.bullets:
                for enemy in self.enemies:
                    if math.hypot(bullet.x - enemy.x, bullet.y - enemy.y) < enemy.radius + bullet.radius:
                        bullet.active = False
                        if enemy.hit(bullet.damage):
                            self.enemies.remove(enemy)
                            score_gain = int(10 * self.player.score_multiplier)
                            self.score += score_gain
                            self.check_level_up()

                            # Update high score
                            if self.score > self.high_score:
                                self.high_score = self.score

                            # Chance to spawn powerup
                            if random.random() < 0.2:
                                self.powerups.append(Powerup(enemy.x, enemy.y,
                                                     random.choice(POWERUP_TYPES)))

                            self.spawn_enemy()
                        break

            # Enemy-player collision
            for enemy in self.enemies:
                if math.hypot(self.player.x - enemy.x, self.player.y - enemy.y) < enemy.radius + self.player.radius:
                    game_over = self.player.take_damage(5)  # Reduced damage
                    if game_over:
                        self.game_over = True
                        if gameover_sound:
                            gameover_sound.play()
                        self.save_high_score()

            # Update minimap
            self.minimap.update(self.player, self.obstacles, self.enemies)

        else:
            # Restart on Enter
            if keys[pygame.K_RETURN]:
                self.__init__()

    def draw(self):
        screen.fill(BLACK)

        # Draw obstacles
        for obs in self.obstacles:
            obs.draw(screen)

        # Draw powerups
        for powerup in self.powerups:
            powerup.draw(screen)

        # Draw enemy bullets
        for bullet in self.enemy_bullets:
            bullet.draw(screen)

        # Draw player
        self.player.draw(screen)

        # Draw bullets
        for bullet in self.bullets:
            bullet.draw(screen)

        # Draw enemies
        for enemy in self.enemies:
            enemy.draw(screen)

        # Draw UI
        # Health bar
        health_pct = max(0, self.player.health / self.player.max_health)
        health_width = 200 * health_pct
        pygame.draw.rect(screen, (50, 50, 50), (10, 10, 200, 20))
        pygame.draw.rect(screen, (255, 0, 0), (10, 10, health_width, 20))
        health_text = font.render(f"Health: {self.player.health}", True, WHITE)
        screen.blit(health_text, (220, 10))

        # Shield bar
        if self.player.shield > 0:
            shield_pct = self.player.shield / self.player.max_shield
            shield_width = 200 * shield_pct
            pygame.draw.rect(screen, (0, 0, 255), (10, 40, shield_width, 10))

        # Score & level
        score_text = font.render(f"Score: {self.score}", True, WHITE)
        screen.blit(score_text, (10, 40))
        high_score_text = font.render(f"High Score: {self.high_score}", True, WHITE)
        screen.blit(high_score_text, (10, 70))
        level_text = font.render(f"Level: {self.level}", True, YELLOW)
        screen.blit(level_text, (220, 40))

        # Weapons
        weapon_text = font.render(f"Weapon: {self.player.weapon}", True, ORANGE)
        screen.blit(weapon_text, (220, 70))

        # Weapons owned
        y_offset = 100
        weapons_text = font.render("Weapons:", True, WHITE)
        screen.blit(weapons_text, (10, y_offset))
        for i, weapon in enumerate(self.player.weapons_owned):
            key_num = i + 1
            w_text = small_font.render(f"{key_num}-{weapon}", True,
                         YELLOW if weapon == self.player.weapon else WHITE)
            screen.blit(w_text, (10, y_offset + 30 + i * 20))

        # Minimap
        self.minimap.draw(screen, SCREEN_WIDTH - 220, 20)

        # Game over screen
        if self.game_over:
            # Semi-transparent overlay
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 150))
            screen.blit(overlay, (0, 0))

            over_text = large_font.render("GAME OVER", True, RED)
            screen.blit(over_text, (SCREEN_WIDTH//2 - 180, SCREEN_HEIGHT//2 - 60))

            score_text = font.render(f"Final Score: {self.score}", True, WHITE)
            screen.blit(score_text, (SCREEN_WIDTH//2 - 100, SCREEN_HEIGHT//2))

            if self.score >= self.high_score:
                new_high_text = font.render("NEW HIGH SCORE!", True, YELLOW)
                screen.blit(new_high_text, (SCREEN_WIDTH//2 - 120, SCREEN_HEIGHT//2 + 40))

            restart_text = font.render("Press Enter to Restart", True, WHITE)
            screen.blit(restart_text, (SCREEN_WIDTH//2 - 120, SCREEN_HEIGHT//2 + 80))

        # Draw frames per second
        fps_text = small_font.render(f"FPS: {int(self.clock.get_fps())}", True, WHITE)
        screen.blit(fps_text, (SCREEN_WIDTH - 100, SCREEN_HEIGHT - 30))

        pygame.display.flip()

    def run(self):
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    self.save_high_score()
                    pygame.quit()
                    sys.exit()
            self.update()
            self.draw()
            self.clock.tick(60)

if __name__ == "__main__":
    Game().run()