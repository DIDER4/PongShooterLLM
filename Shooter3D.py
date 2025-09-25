"""
3D Shooter Game
- Based on the 2D shooter from Shooter.py
- Using PyGame with OpenGL for 3D rendering
"""

import pygame
import pygame.locals as pl
from pygame.locals import *
import sys
import math
import random
import os

print("Initializing game...")

# Initialize pygame first before doing anything else
pygame.init()
print("Pygame initialized")

# Set up display early
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 900
print(f"Setting up display: {SCREEN_WIDTH}x{SCREEN_HEIGHT}")

# Try to import OpenGL (use module aliases to avoid wildcard unresolved references)
try:
    import OpenGL.GL as gl
    import OpenGL.GLU as glu
    has_opengl = True
    print("OpenGL support enabled")
except Exception:
    print("WARNING: PyOpenGL not available. Running in compatibility mode.")
    gl = None
    glu = None
    has_opengl = False

# Set up screen (needs to be done before any texture loading)
if has_opengl:
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), DOUBLEBUF | OPENGL)
else:
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    
pygame.display.set_caption("3D FPS Shooter")
print("Display initialized")

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
YELLOW = (255, 255, 0)
BLUE = (0, 0, 255)
PURPLE = (128, 0, 128)
ORANGE = (255, 165, 0)
GRAY = (100, 100, 100)
DARK_GRAY = (50, 50, 50)
LIGHT_GRAY = (200, 200, 200)

# 3D environment constants
WORLD_SIZE = 50.0
FLOOR_Y = -1.0
CEILING_Y = 5.0
WALL_HEIGHT = CEILING_Y - FLOOR_Y
FOV = 60  # Field of view in degrees

# Textures and resources
SPRITES_DIR = os.path.join(os.path.dirname(__file__), 'sprites')

def load_image(filename, size=None):
    try:
        path = os.path.join(SPRITES_DIR, filename)
        print(f"Loading image: {path}")
        image = pygame.image.load(path)
        image = image.convert_alpha() if image.get_flags() & pygame.SRCALPHA else image.convert()
        if size:
            image = pygame.transform.scale(image, size)
        print(f"Image loaded successfully: {filename}")
        return image
    except Exception as e:
        print(f"Error loading image {filename}: {e}")
        return None

print("Loading textures...")
# Load textures (display is initialized so convert_alpha works)
wall_texture = load_image('vaeg.jpg', (256, 256))
weapon_texture = load_image('skud.png', (128, 128))
enemy_texture = load_image('fjende.png', (128, 128))
player_texture = load_image('Spiller.png', (128, 128))
print("Textures loaded")

# Sound effects
def load_sound(path):
    try:
        return pygame.mixer.Sound(path)
    except Exception as e:
        print(f"Error loading sound {path}: {e}")
        return None

shoot_sound = load_sound('shoot.wav')
hit_sound = load_sound('hit.wav')
gameover_sound = load_sound('gameover.wav')

class Vector3:
    """Simple 3D vector class"""
    def __init__(self, x=0, y=0, z=0):
        self.x = x
        self.y = y
        self.z = z

    def __add__(self, other):
        return Vector3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other):
        return Vector3(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, scalar):
        return Vector3(self.x * scalar, self.y * scalar, self.z * scalar)

    def magnitude(self):
        return math.sqrt(self.x**2 + self.y**2 + self.z**2)

    def normalize(self):
        mag = self.magnitude()
        if mag > 0:
            return Vector3(self.x/mag, self.y/mag, self.z/mag)
        return Vector3()

    def dot(self, other):
        return self.x*other.x + self.y*other.y + self.z*other.z

    def cross(self, other):
        return Vector3(
            self.y*other.z - self.z*other.y,
            self.z*other.x - self.x*other.z,
            self.x*other.y - self.y*other.x
        )

class Camera:
    """Camera for 3D rendering"""
    def __init__(self):
        self.position = Vector3(0, 0, 0)
        self.forward = Vector3(0, 0, -1)  # Looking down -Z initially
        self.up = Vector3(0, 1, 0)  # Y is up
        self.right = Vector3(1, 0, 0)  # X is right
        self.yaw = 0  # Rotation around Y axis (left/right)
        self.pitch = 0  # Rotation around X axis (up/down)
        self.speed = 0.2

    def update_vectors(self):
        # Compute the forward vector based on yaw and pitch
        yaw_rad = math.radians(self.yaw)
        pitch_rad = math.radians(self.pitch)

        # Forward vector components
        self.forward.x = -math.sin(yaw_rad) * math.cos(pitch_rad)
        self.forward.y = math.sin(pitch_rad)
        self.forward.z = -math.cos(yaw_rad) * math.cos(pitch_rad)

        # Right vector (cross product of forward and world up)
        world_up = Vector3(0, 1, 0)
        self.right = self.forward.cross(world_up).normalize()

        # Up vector (cross product of right and forward)
        self.up = self.right.cross(self.forward).normalize()

    def move(self, keys):
        # Update camera vectors
        self.update_vectors()

        # Movement based on key presses
        move_speed = self.speed

        if keys[K_w] or keys[K_UP]:  # Move forward
            self.position = self.position + self.forward * move_speed
        if keys[K_s] or keys[K_DOWN]:  # Move backward
            self.position = self.position - self.forward * move_speed
        if keys[K_a] or keys[K_LEFT]:  # Strafe left
            self.position = self.position - self.right * move_speed
        if keys[K_d] or keys[K_RIGHT]:  # Strafe right
            self.position = self.position + self.right * move_speed
        if keys[K_SPACE]:  # Move up
            self.position.y += move_speed
        if keys[K_LSHIFT]:  # Move down
            self.position.y -= move_speed

        # Constrain to world boundaries
        self.position.x = max(-WORLD_SIZE/2, min(WORLD_SIZE/2, self.position.x))
        self.position.y = max(FLOOR_Y + 0.5, min(CEILING_Y - 0.5, self.position.y))
        self.position.z = max(-WORLD_SIZE/2, min(WORLD_SIZE/2, self.position.z))

    def look(self, dx, dy):
        # Update yaw and pitch based on mouse movement
        sensitivity = 0.2
        self.yaw += dx * sensitivity
        self.pitch -= dy * sensitivity

        # Constrain pitch to avoid gimbal lock
        self.pitch = max(-89, min(89, self.pitch))

class Wall:
    """Wall in 3D space"""
    def __init__(self, start_pos, end_pos, height=WALL_HEIGHT, texture=None):
        self.start = start_pos  # Vector3 for start position
        self.end = end_pos  # Vector3 for end position
        self.height = height
        self.texture = texture or wall_texture
        # Calculate wall normal (perpendicular to wall)
        wall_vector = Vector3(end_pos.x - start_pos.x, 0, end_pos.z - start_pos.z)
        self.normal = Vector3(-wall_vector.z, 0, wall_vector.x).normalize()

    def draw(self):
        if not has_opengl:
            return

        gl.glPushMatrix()

        texture_id = None
        # Apply texture if available
        if self.texture is not None:
            try:
                texture_data = pygame.image.tostring(self.texture, "RGBA", True)
                texture_id = gl.glGenTextures(1)
                gl.glBindTexture(gl.GL_TEXTURE_2D, texture_id)
                gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
                gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
                gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA, self.texture.get_width(),
                            self.texture.get_height(), 0, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, texture_data)
                gl.glEnable(gl.GL_TEXTURE_2D)
            except Exception as e:
                texture_id = None
                gl.glDisable(gl.GL_TEXTURE_2D)
                gl.glColor3f(0.7, 0.7, 0.7)
        else:
            gl.glDisable(gl.GL_TEXTURE_2D)
            gl.glColor3f(0.7, 0.7, 0.7)  # Gray color if no texture

        # Draw wall as a quad
        gl.glBegin(gl.GL_QUADS)

        # Calculate wall length for proper texture mapping
        wall_length = math.sqrt((self.end.x - self.start.x)**2 + (self.end.z - self.start.z)**2)

        # Bottom left
        gl.glTexCoord2f(0, 0)
        gl.glVertex3f(self.start.x, FLOOR_Y, self.start.z)

        # Bottom right
        gl.glTexCoord2f(wall_length/2, 0)
        gl.glVertex3f(self.end.x, FLOOR_Y, self.end.z)

        # Top right
        gl.glTexCoord2f(wall_length/2, 1)
        gl.glVertex3f(self.end.x, CEILING_Y, self.end.z)

        # Top left
        gl.glTexCoord2f(0, 1)
        gl.glVertex3f(self.start.x, CEILING_Y, self.start.z)

        gl.glEnd()

        if texture_id is not None:
            gl.glDisable(gl.GL_TEXTURE_2D)
            try:
                gl.glDeleteTextures([texture_id])
            except Exception:
                pass

        gl.glPopMatrix()

    def collides_with_point(self, point, radius=0.5):
        """Check if a point (with radius) collides with this wall"""
        # Vector from wall start to point
        start_to_point = Vector3(
            point.x - self.start.x,
            0,  # Ignore Y for now
            point.z - self.start.z
        )

        # Vector representing the wall
        wall_vector = Vector3(
            self.end.x - self.start.x,
            0,
            self.end.z - self.start.z
        )

        # Wall length squared
        wall_length_sq = wall_vector.x**2 + wall_vector.z**2

        # If wall has zero length, return distance to start point
        if wall_length_sq == 0:
            dist_sq = start_to_point.x**2 + start_to_point.z**2
            return math.sqrt(dist_sq) <= radius

        # Calculate how far along the wall the closest point is (0 to 1)
        t = max(0, min(1, (start_to_point.x * wall_vector.x + start_to_point.z * wall_vector.z) / wall_length_sq))

        # Calculate the closest point on the wall
        closest_x = self.start.x + t * wall_vector.x
        closest_z = self.start.z + t * wall_vector.z

        # Calculate distance from the point to the closest point on the wall
        dist_sq = (point.x - closest_x)**2 + (point.z - closest_z)**2

        # Return true if the distance is less than or equal to the radius
        return math.sqrt(dist_sq) <= radius

class Enemy:
    """Enemy in 3D space"""
    def __init__(self, position=None, health=3, speed=0.05):
        if position is None:
            # Randomly place enemy on the map, not too close to player
            angle = random.uniform(0, 2*math.pi)
            distance = random.uniform(10, WORLD_SIZE/2)
            self.position = Vector3(
                math.cos(angle) * distance,
                FLOOR_Y + 0.5,  # Slightly above ground
                math.sin(angle) * distance
            )
        else:
            self.position = position

        self.health = health
        self.speed = speed
        self.radius = 0.5
        self.height = 1.8
        self.texture = enemy_texture
        self.last_attack_time = 0
        self.attack_cooldown = 1000  # ms
        self.behavior_type = random.choice(["chaser", "flanker", "ambusher"])
        self.aggression = random.uniform(0.3, 0.8)

    def update(self, player_pos, walls, current_time):
        # Different behavior types
        target_pos = Vector3(player_pos.x, self.position.y, player_pos.z)

        # Calculate distance and direction to player
        to_player = Vector3(
            player_pos.x - self.position.x,
            0,  # Ignore Y for now
            player_pos.z - self.position.z
        )
        distance = to_player.magnitude()

        # Modify target position based on behavior
        if self.behavior_type == "flanker" and distance < 10:
            # Try to circle around the player
            perp_dir = Vector3(-to_player.z, 0, to_player.x).normalize()
            flank_dist = 5.0
            target_pos = Vector3(
                player_pos.x + perp_dir.x * flank_dist,
                self.position.y,
                player_pos.z + perp_dir.z * flank_dist
            )
        elif self.behavior_type == "ambusher" and distance < 8:
            # Stay in place if close
            return False

        # Calculate movement direction
        direction = Vector3(
            target_pos.x - self.position.x,
            0,  # Ignore Y for now
            target_pos.z - self.position.z
        )

        if direction.magnitude() > 0:
            direction = direction.normalize()

            # Calculate new position
            new_pos = Vector3(
                self.position.x + direction.x * self.speed,
                self.position.y,
                self.position.z + direction.z * self.speed
            )

            # Check wall collisions
            collision = False
            for wall in walls:
                if wall.collides_with_point(new_pos, self.radius):
                    collision = True
                    break

            # Update position if no collision
            if not collision:
                self.position = new_pos

        # Check if enemy can attack
        can_attack = (current_time - self.last_attack_time > self.attack_cooldown) and \
                    (distance < 3.0) and (random.random() < self.aggression)

        if can_attack:
            self.last_attack_time = current_time
            return True

        return False

    def draw(self):
        if not has_opengl:
            return

        gl.glPushMatrix()

        gl.glDisable(gl.GL_LIGHTING)
        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)

        modelview = gl.glGetDoublev(gl.GL_MODELVIEW_MATRIX)

        camera_right = Vector3(modelview[0][0], modelview[0][1], modelview[0][2])
        camera_up = Vector3(modelview[1][0], modelview[1][1], modelview[1][2])

        texture_id = None
        if self.texture is not None:
            try:
                texture_data = pygame.image.tostring(self.texture, "RGBA", True)
                texture_id = gl.glGenTextures(1)
                gl.glBindTexture(gl.GL_TEXTURE_2D, texture_id)
                gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
                gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
                gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA, self.texture.get_width(),
                                self.texture.get_height(), 0, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, texture_data)
                gl.glEnable(gl.GL_TEXTURE_2D)
            except Exception:
                texture_id = None
                gl.glDisable(gl.GL_TEXTURE_2D)
                gl.glColor3f(1.0, 0.0, 0.0)
        else:
            gl.glDisable(gl.GL_TEXTURE_2D)
            gl.glColor3f(1.0, 0.0, 0.0)

        half_width = self.radius
        half_height = self.height / 2

        p1 = Vector3(
            self.position.x - camera_right.x * half_width + camera_up.x * half_height,
            self.position.y - camera_right.y * half_width + camera_up.y * half_height,
            self.position.z - camera_right.z * half_width + camera_up.z * half_height
        )

        p2 = Vector3(
            self.position.x + camera_right.x * half_width + camera_up.x * half_height,
            self.position.y + camera_right.y * half_width + camera_up.y * half_height,
            self.position.z + camera_right.z * half_width + camera_up.z * half_height
        )

        p3 = Vector3(
            self.position.x + camera_right.x * half_width - camera_up.x * half_height,
            self.position.y + camera_right.y * half_width - camera_up.y * half_height,
            self.position.z + camera_right.z * half_width - camera_up.z * half_height
        )

        p4 = Vector3(
            self.position.x - camera_right.x * half_width - camera_up.x * half_height,
            self.position.y - camera_right.y * half_width - camera_up.y * half_height,
            self.position.z - camera_right.z * half_width - camera_up.z * half_height
        )

        gl.glBegin(gl.GL_QUADS)
        gl.glTexCoord2f(0, 0); gl.glVertex3f(p1.x, p1.y, p1.z)
        gl.glTexCoord2f(1, 0); gl.glVertex3f(p2.x, p2.y, p2.z)
        gl.glTexCoord2f(1, 1); gl.glVertex3f(p3.x, p3.y, p3.z)
        gl.glTexCoord2f(0, 1); gl.glVertex3f(p4.x, p4.y, p4.z)
        gl.glEnd()

        if texture_id is not None:
            gl.glDisable(gl.GL_TEXTURE_2D)
            try:
                gl.glDeleteTextures([texture_id])
            except Exception:
                pass

        gl.glDisable(gl.GL_BLEND)
        gl.glEnable(gl.GL_LIGHTING)

        gl.glPopMatrix()

    def hit(self):
        self.health -= 1
        if hit_sound:
            hit_sound.play()
        return self.health <= 0

class Bullet:
    """Bullet in 3D space"""
    def __init__(self, position, direction, speed=0.5, damage=1):
        self.position = position
        self.direction = direction.normalize()
        self.speed = speed
        self.damage = damage
        self.radius = 0.1
        self.active = True
        self.distance_traveled = 0
        self.max_distance = 100  # Maximum travel distance

    def update(self, walls):
        # Calculate new position
        movement = self.direction * self.speed
        new_pos = Vector3(
            self.position.x + movement.x,
            self.position.y + movement.y,
            self.position.z + movement.z
        )

        # Update distance traveled
        self.distance_traveled += movement.magnitude()

        # Check for max distance
        if self.distance_traveled > self.max_distance:
            self.active = False
            return

        # Check wall collisions
        for wall in walls:
            if wall.collides_with_point(new_pos, self.radius):
                self.active = False
                return

        # Update position if still active
        self.position = new_pos

    def draw(self):
        if not has_opengl:
            return

        gl.glPushMatrix()
        gl.glTranslatef(self.position.x, self.position.y, self.position.z)
        gl.glColor3f(1.0, 1.0, 0.0)
        sphere = glu.gluNewQuadric()
        glu.gluSphere(sphere, self.radius, 8, 8)
        glu.gluDeleteQuadric(sphere)
        gl.glPopMatrix()

class WeaponViewModel:
    """First-person weapon view"""
    def __init__(self):
        self.texture = weapon_texture
        self.weapon_type = "pistol"
        self.last_shot_time = 0
        self.cooldown = 300  # ms
        self.is_shooting = False
        self.shoot_animation = 0  # 0 to 1 for animation

    def update(self, current_time):
        # Update shooting animation
        if self.is_shooting:
            time_since_shot = current_time - self.last_shot_time
            if time_since_shot < 150:  # Animation duration
                self.shoot_animation = 1.0 - (time_since_shot / 150)
            else:
                self.shoot_animation = 0
                self.is_shooting = False

    def can_shoot(self, current_time):
        return current_time - self.last_shot_time > self.cooldown

    def shoot(self, current_time):
        self.last_shot_time = current_time
        self.is_shooting = True
        self.shoot_animation = 1.0
        if shoot_sound:
            shoot_sound.play()

    def draw(self, screen_width, screen_height):
        if self.texture is None:
            return

        # Draw 2D weapon overlay
        weapon_width = 200
        weapon_height = 150

        # Position at bottom right, with offset for shooting animation
        anim_offset = int(20 * self.shoot_animation)
        x_pos = screen_width - weapon_width - 50
        y_pos = screen_height - weapon_height + anim_offset

        # Create scaled weapon image
        weapon_img = pygame.transform.scale(self.texture, (weapon_width, weapon_height))

        # Draw to screen
        screen = pygame.display.get_surface()
        screen.blit(weapon_img, (x_pos, y_pos))

class Shooter3D:
    """Main 3D shooter game class"""
    def __init__(self):
        # Initialize Pygame
        pygame.init()

        # Set up display
        self.screen_width = SCREEN_WIDTH
        self.screen_height = SCREEN_HEIGHT
        if has_opengl:
            self.screen = pygame.display.set_mode((self.screen_width, self.screen_height), DOUBLEBUF | OPENGL)
        else:
            self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))

        pygame.display.set_caption("3D FPS Shooter")

        # Set up OpenGL if available
        # Now that display is initialized, load textures
        self.load_textures()

        if has_opengl:
            self.setup_opengl()

        # Initialize clock
        self.clock = pygame.time.Clock()
        self.fps = 60

        # Game state
        self.running = True
        self.game_over = False
        self.score = 0
        self.high_score = self.load_high_score()

        # Camera and player
        self.camera = Camera()
        self.health = 100
        self.max_health = 100
        self.shield = 0
        self.max_shield = 50

        # Mouse look
        pygame.mouse.set_visible(False)
        pygame.event.set_grab(True)

        # Weapon
        self.weapon = WeaponViewModel()
        self.bullets = []

        # Level elements
        self.walls = self.generate_level()
        self.enemies = [Enemy() for _ in range(5)]

        # UI font
        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 24)

        # Initialize minimap
        self.minimap_size = 150
        self.minimap_surface = pygame.Surface((self.minimap_size, self.minimap_size))

        # Game difficulty settings
        self.difficulty = 1.0
        self.level = 1
        self.next_level_score = 10


    def load_textures(self):
        # Load game textures after display is initialized
        global wall_texture, weapon_texture, enemy_texture, player_texture
        wall_texture = load_image('vaeg.jpg', (256, 256))
        weapon_texture = load_image('skud.png', (128, 128))
        enemy_texture = load_image('fjende.png', (128, 128))
        player_texture = load_image('Spiller.png', (128, 128))
    def setup_opengl(self):
        # Set up the projection matrix
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glLoadIdentity()
        glu.gluPerspective(FOV, self.screen_width / self.screen_height, 0.1, 100.0)

        # Set up the modelview matrix
        gl.glMatrixMode(gl.GL_MODELVIEW)
        gl.glLoadIdentity()

        # Enable depth testing
        gl.glEnable(gl.GL_DEPTH_TEST)

        # Set up lighting
        gl.glEnable(gl.GL_LIGHTING)
        gl.glEnable(gl.GL_LIGHT0)
        gl.glEnable(gl.GL_COLOR_MATERIAL)
        gl.glColorMaterial(gl.GL_FRONT_AND_BACK, gl.GL_AMBIENT_AND_DIFFUSE)

        # Set light position and properties
        gl.glLightfv(gl.GL_LIGHT0, gl.GL_POSITION, (0, 10, 0, 1))
        gl.glLightfv(gl.GL_LIGHT0, gl.GL_DIFFUSE, (1.0, 1.0, 1.0, 1.0))
        gl.glLightfv(gl.GL_LIGHT0, gl.GL_AMBIENT, (0.3, 0.3, 0.3, 1.0))

    def generate_level(self):
        """Generate walls for the level"""
        walls = []

        # Outer walls
        half_size = WORLD_SIZE / 2

        # North wall
        walls.append(Wall(Vector3(-half_size, FLOOR_Y, -half_size), Vector3(half_size, FLOOR_Y, -half_size)))

        # East wall
        walls.append(Wall(Vector3(half_size, FLOOR_Y, -half_size), Vector3(half_size, FLOOR_Y, half_size)))

        # South wall
        walls.append(Wall(Vector3(half_size, FLOOR_Y, half_size), Vector3(-half_size, FLOOR_Y, half_size)))

        # West wall
        walls.append(Wall(Vector3(-half_size, FLOOR_Y, half_size), Vector3(-half_size, FLOOR_Y, -half_size)))

        # Add some internal walls
        walls.append(Wall(Vector3(-5, FLOOR_Y, -5), Vector3(5, FLOOR_Y, -5)))
        walls.append(Wall(Vector3(-5, FLOOR_Y, 5), Vector3(5, FLOOR_Y, 5)))
        walls.append(Wall(Vector3(-5, FLOOR_Y, -5), Vector3(-5, FLOOR_Y, 5)))
        walls.append(Wall(Vector3(5, FLOOR_Y, -5), Vector3(5, FLOOR_Y, 5)))

        # Add some obstacles
        walls.append(Wall(Vector3(-10, FLOOR_Y, -10), Vector3(-5, FLOOR_Y, -10)))
        walls.append(Wall(Vector3(10, FLOOR_Y, 10), Vector3(15, FLOOR_Y, 10)))
        walls.append(Wall(Vector3(-15, FLOOR_Y, 10), Vector3(-15, FLOOR_Y, 15)))
        walls.append(Wall(Vector3(15, FLOOR_Y, -15), Vector3(15, FLOOR_Y, -10)))

        return walls

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

    def handle_events(self):
        # Mouse movement for looking around
        dx, dy = pygame.mouse.get_rel()
        self.camera.look(dx, dy)

        # Process events
        for event in pygame.event.get():
            if event.type == QUIT:
                self.running = False
            elif event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    self.running = False
                elif event.key == K_r and self.game_over:
                    self.reset_game()

        # Get pressed keys for movement
        keys = pygame.key.get_pressed()
        self.camera.move(keys)

        # Handle shooting
        current_time = pygame.time.get_ticks()
        if pygame.mouse.get_pressed()[0] and self.weapon.can_shoot(current_time) and not self.game_over:
            self.weapon.shoot(current_time)

            # Create a bullet from camera position in the direction the camera is facing
            bullet_pos = Vector3(self.camera.position.x, self.camera.position.y, self.camera.position.z)
            bullet_dir = Vector3(self.camera.forward.x, self.camera.forward.y, self.camera.forward.z)
            self.bullets.append(Bullet(bullet_pos, bullet_dir))

    def update(self):
        if self.game_over:
            return

        current_time = pygame.time.get_ticks()

        # Update weapon
        self.weapon.update(current_time)

        # Update bullets
        for bullet in self.bullets:
            bullet.update(self.walls)

        self.bullets = [b for b in self.bullets if b.active]

        # Update enemies
        for enemy in self.enemies:
            # Check if enemy attacks player
            if enemy.update(self.camera.position, self.walls, current_time):
                # Calculate damage based on difficulty
                damage = 5 * self.difficulty
                self.take_damage(damage)

        # Check bullet-enemy collisions
        for bullet in self.bullets:
            for enemy in self.enemies:
                # Simple distance-based collision
                distance = math.sqrt(
                    (bullet.position.x - enemy.position.x) ** 2 +
                    (bullet.position.y - enemy.position.y) ** 2 +
                    (bullet.position.z - enemy.position.z) ** 2
                )

                if distance < enemy.radius + bullet.radius:
                    bullet.active = False
                    if enemy.hit():
                        self.enemies.remove(enemy)
                        self.score += int(10 * self.difficulty)
                        self.check_level_up()

                        # Spawn a new enemy
                        self.enemies.append(Enemy())

                        # Check for high score
                        if self.score > self.high_score:
                            self.high_score = self.score
                    break

        # Remove inactive bullets
        self.bullets = [b for b in self.bullets if b.active]

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

            # Check for game over
            if self.health <= 0:
                self.health = 0
                self.game_over = True
                if gameover_sound:
                    gameover_sound.play()
                self.save_high_score()

    def check_level_up(self):
        if self.score >= self.next_level_score:
            self.level += 1
            self.difficulty += 0.2
            self.next_level_score *= 2

            # Add more enemies
            for _ in range(2):
                self.enemies.append(Enemy())

            # Increase max health
            self.max_health += 20
            self.health = self.max_health

    def reset_game(self):
        self.game_over = False
        self.score = 0
        self.health = 100
        self.max_health = 100
        self.shield = 0
        self.level = 1
        self.difficulty = 1.0
        self.next_level_score = 10

        # Reset camera position
        self.camera.position = Vector3(0, 0, 0)
        self.camera.yaw = 0
        self.camera.pitch = 0

        # Reset enemies
        self.enemies = [Enemy() for _ in range(5)]

        # Clear bullets
        self.bullets = []

    def render_scene(self):
        # Clear the screen and depth buffer
        if has_opengl:
            gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
            gl.glClearColor(0.5, 0.5, 1.0, 1.0)  # Sky blue color

            # Set camera position and orientation
            gl.glLoadIdentity()
            glu.gluLookAt(
                self.camera.position.x, self.camera.position.y, self.camera.position.z,  # Camera position
                self.camera.position.x + self.camera.forward.x,  # Look at point
                self.camera.position.y + self.camera.forward.y,
                self.camera.position.z + self.camera.forward.z,
                self.camera.up.x, self.camera.up.y, self.camera.up.z  # Up vector
            )

            # Draw floor
            gl.glBegin(gl.GL_QUADS)
            gl.glColor3f(0.3, 0.3, 0.3)  # Dark gray
            gl.glVertex3f(-WORLD_SIZE/2, FLOOR_Y, -WORLD_SIZE/2)
            gl.glVertex3f(WORLD_SIZE/2, FLOOR_Y, -WORLD_SIZE/2)
            gl.glVertex3f(WORLD_SIZE/2, FLOOR_Y, WORLD_SIZE/2)
            gl.glVertex3f(-WORLD_SIZE/2, FLOOR_Y, WORLD_SIZE/2)
            gl.glEnd()

            # Draw ceiling
            gl.glBegin(gl.GL_QUADS)
            gl.glColor3f(0.5, 0.5, 0.5)  # Light gray
            gl.glVertex3f(-WORLD_SIZE/2, CEILING_Y, -WORLD_SIZE/2)
            gl.glVertex3f(WORLD_SIZE/2, CEILING_Y, -WORLD_SIZE/2)
            gl.glVertex3f(WORLD_SIZE/2, CEILING_Y, WORLD_SIZE/2)
            gl.glVertex3f(-WORLD_SIZE/2, CEILING_Y, WORLD_SIZE/2)
            gl.glEnd()

            # Draw walls
            for wall in self.walls:
                wall.draw()

            # Draw enemies
            for enemy in self.enemies:
                enemy.draw()

            # Draw bullets
            for bullet in self.bullets:
                bullet.draw()
        else:
            # Compatibility mode (2D only)
            self.screen.fill((100, 100, 100))  # Gray background

        # Draw 2D elements (UI, weapon view, etc.)
        self.draw_ui()

    def draw_ui(self):
        # Health bar
        health_pct = max(0, self.health / self.max_health)
        health_width = 200 * health_pct
        pygame.draw.rect(self.screen, (50, 50, 50), (10, 10, 200, 20))
        pygame.draw.rect(self.screen, (255, 0, 0), (10, 10, health_width, 20))
        health_text = self.font.render(f"Health: {int(self.health)}", True, WHITE)
        self.screen.blit(health_text, (220, 10))

        # Shield bar
        if self.shield > 0:
            shield_pct = self.shield / self.max_shield
            shield_width = 200 * shield_pct
            pygame.draw.rect(self.screen, (0, 0, 255), (10, 40, shield_width, 10))

        # Score & level
        score_text = self.font.render(f"Score: {self.score}", True, WHITE)
        self.screen.blit(score_text, (10, 50))
        high_score_text = self.font.render(f"High Score: {self.high_score}", True, WHITE)
        self.screen.blit(high_score_text, (10, 80))
        level_text = self.font.render(f"Level: {self.level}", True, YELLOW)
        self.screen.blit(level_text, (220, 50))

        # Draw weapon view
        self.weapon.draw(self.screen_width, self.screen_height)

        # Draw minimap
        self.update_minimap()
        self.screen.blit(self.minimap_surface, (self.screen_width - self.minimap_size - 10, 10))

        # Game over screen
        if self.game_over:
            # Create a semi-transparent overlay
            overlay = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 150))  # Black with 60% opacity
            self.screen.blit(overlay, (0, 0))

            # Game over text
            game_over_text = pygame.font.Font(None, 72).render("GAME OVER", True, RED)
            self.screen.blit(game_over_text,
                (self.screen_width//2 - game_over_text.get_width()//2,
                self.screen_height//2 - 60))

            # Score text
            score_text = self.font.render(f"Final Score: {self.score}", True, WHITE)
            self.screen.blit(score_text,
                (self.screen_width//2 - score_text.get_width()//2,
                self.screen_height//2))

            # High score text
            if self.score >= self.high_score:
                high_text = self.font.render("NEW HIGH SCORE!", True, YELLOW)
                self.screen.blit(high_text,
                    (self.screen_width//2 - high_text.get_width()//2,
                    self.screen_height//2 + 40))

            # Restart text
            restart_text = self.font.render("Press R to Restart", True, WHITE)
            self.screen.blit(restart_text,
                (self.screen_width//2 - restart_text.get_width()//2,
                self.screen_height//2 + 80))

        # Draw crosshair
        pygame.draw.line(self.screen, WHITE,
                        (self.screen_width//2 - 10, self.screen_height//2),
                        (self.screen_width//2 + 10, self.screen_height//2), 2)
        pygame.draw.line(self.screen, WHITE,
                        (self.screen_width//2, self.screen_height//2 - 10),
                        (self.screen_width//2, self.screen_height//2 + 10), 2)

        # FPS counter
        fps_text = self.small_font.render(f"FPS: {int(self.clock.get_fps())}", True, WHITE)
        self.screen.blit(fps_text, (self.screen_width - 100, self.screen_height - 30))

    def update_minimap(self):
        # Clear minimap
        self.minimap_surface.fill((0, 0, 0))

        # Draw border
        pygame.draw.rect(self.minimap_surface, (100, 100, 100),
                        (0, 0, self.minimap_size, self.minimap_size), 2)

        # Calculate scale factors
        scale_x = self.minimap_size / WORLD_SIZE
        scale_z = self.minimap_size / WORLD_SIZE

        # Calculate offset to center map
        offset_x = self.minimap_size / 2
        offset_z = self.minimap_size / 2

        # Draw walls
        for wall in self.walls:
            # Convert 3D coordinates to 2D minimap coordinates
            start_x = int(wall.start.x * scale_x + offset_x)
            start_z = int(wall.start.z * scale_z + offset_z)
            end_x = int(wall.end.x * scale_x + offset_x)
            end_z = int(wall.end.z * scale_z + offset_z)

            # Draw line representing wall
            pygame.draw.line(self.minimap_surface, (150, 150, 150),
                            (start_x, start_z), (end_x, end_z), 2)

        # Draw enemies
        for enemy in self.enemies:
            # Convert 3D coordinates to 2D minimap coordinates
            x = int(enemy.position.x * scale_x + offset_x)
            z = int(enemy.position.z * scale_z + offset_z)

            # Draw dot representing enemy
            pygame.draw.circle(self.minimap_surface, RED, (x, z), 3)

        # Draw player
        player_x = int(self.camera.position.x * scale_x + offset_x)
        player_z = int(self.camera.position.z * scale_z + offset_z)
        pygame.draw.circle(self.minimap_surface, GREEN, (player_x, player_z), 4)

        # Draw player direction
        direction_x = player_x + int(self.camera.forward.x * 10)
        direction_z = player_z + int(self.camera.forward.z * 10)
        pygame.draw.line(self.minimap_surface, GREEN, (player_x, player_z),
                        (direction_x, direction_z), 2)

    def run(self):
        # Main game loop
        while self.running:
            # Process events and input
            self.handle_events()

            # Update game state
            self.update()

            # Render the scene
            self.render_scene()

            # Update display
            pygame.display.flip()

            # Limit frame rate
            self.clock.tick(self.fps)

        # Clean up
        pygame.quit()
        sys.exit()

# Run the game if this script is executed
if __name__ == "__main__":
    game = Shooter3D()
    game.run()