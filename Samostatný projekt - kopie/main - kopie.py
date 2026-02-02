import pygame
import random
import math
import sys

pygame.init()
FPS = 60

# === SCREEN / LEVEL ===
SCREEN_W, SCREEN_H = 1920, 1080
screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
pygame.display.set_caption("Camera + Enemies + XP System")
clock = pygame.time.Clock()

# === LEVEL / CAMERA ===
class Level:
    def __init__(self, width, height, grid_size=200):
        self.width = width
        self.height = height
        self.grid_size = grid_size
        self.bg_color = (40, 40, 50)
        self.grid_color = (60, 60, 70)
        self.boundary_color = (200, 80, 80)

    def draw(self, surface, camera):
        surface.fill(self.bg_color)
        view_rect = pygame.Rect(camera.x, camera.y, camera.screen_w, camera.screen_h)
        start_x = (view_rect.left // self.grid_size) * self.grid_size
        end_x = ((view_rect.right // self.grid_size) + 1) * self.grid_size
        start_y = (view_rect.top // self.grid_size) * self.grid_size
        end_y = ((view_rect.bottom // self.grid_size) + 1) * self.grid_size

        for x in range(start_x, end_x + 1, self.grid_size):
            pygame.draw.line(surface, self.grid_color, (x - camera.x, 0), (x - camera.x, camera.screen_h))
        for y in range(start_y, end_y + 1, self.grid_size):
            pygame.draw.line(surface, self.grid_color, (0, y - camera.y), (camera.screen_w, y - camera.y))

        pygame.draw.rect(surface, self.boundary_color,
                         pygame.Rect(-camera.x, -camera.y, self.width, self.height), 4)

class Camera:
    def __init__(self, screen_w, screen_h, level_w, level_h):
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.level_w = level_w
        self.level_h = level_h
        self.x = 0
        self.y = 0

    def update(self, target_x, target_y):
        desired_x = int(target_x - self.screen_w / 2)
        desired_y = int(target_y - self.screen_h / 2)
        max_x = max(0, self.level_w - self.screen_w)
        max_y = max(0, self.level_h - self.screen_h)
        self.x = max(0, min(desired_x, max_x))
        self.y = max(0, min(desired_y, max_y))

# === CHARACTER ===
class Character:
    def __init__(self, x, y, speed=400, image_path="character.png", image_size=(128,128)):
        self.x = float(x)
        self.y = float(y)
        self.speed = speed
        self.radius = 20
        self.hp = 100
        self.max_hp = 100
        self.level = 1
        self.xp = 0
        self.xp_to_next = 100
        self.kills = 0  # kill count

        try:
            self.image = pygame.image.load(image_path).convert_alpha()
            self.image = pygame.transform.scale(self.image, image_size)
        except:
            self.image = None

    def handle_input(self, keys, dt):
        dx, dy = 0, 0
        if keys[pygame.K_w]: dy -= 1
        if keys[pygame.K_s]: dy += 1
        if keys[pygame.K_a]: dx -= 1
        if keys[pygame.K_d]: dx += 1
        if dx != 0 and dy != 0:
            dx *= 0.7071
            dy *= 0.7071
        self.x += dx * self.speed * dt
        self.y += dy * self.speed * dt

    def clamp_to_level(self, level_w, level_h):
        self.x = max(self.radius, min(self.x, level_w - self.radius))
        self.y = max(self.radius, min(self.y, level_h - self.radius))

    def draw(self, surface, camera):
        cx, cy = int(self.x - camera.x), int(self.y - camera.y)
        if self.image:
            rect = self.image.get_rect(center=(cx, cy))
            surface.blit(self.image, rect)
        else:
            pygame.draw.circle(surface, (255,0,0), (cx, cy), self.radius)

    def gain_xp(self, amount):
        self.xp += amount
        while self.xp >= self.xp_to_next:
            self.xp -= self.xp_to_next
            self.level += 1
            self.xp_to_next = int(self.xp_to_next * 1.25)

    def take_damage(self, dmg):
        self.hp -= dmg
        if self.hp < 0:
            self.hp = 0

# === ZOMBIE ===
class Zombie:
    def __init__(self, x, y, speed=250, hp=50, damage=10, image_path="zombie.png", image_size=(160,120)):
        self.x = float(x)
        self.y = float(y)
        self.speed = speed
        self.hp = hp
        self.max_hp = hp
        self.damage = damage
        self.hitbox_radius = 25
        try:
            self.image = pygame.image.load(image_path).convert_alpha()
            self.image = pygame.transform.scale(self.image, image_size)
        except:
            self.image = None
        self.cooldown = 0.0

    def update(self, dt, player):
        dx = player.x - self.x
        dy = player.y - self.y
        dist = math.hypot(dx, dy)
        if dist > 0.001:
            nx = dx / dist
            ny = dy / dist
            self.x += nx * self.speed * dt
            self.y += ny * self.speed * dt
        if self.cooldown > 0:
            self.cooldown -= dt

    def draw(self, surface, camera):
        cx, cy = int(self.x - camera.x), int(self.y - camera.y)
        if self.image:
            rect = self.image.get_rect(center=(cx, cy))
            surface.blit(self.image, rect)
        else:
            pygame.draw.circle(surface, (80,200,80), (cx, cy), self.hitbox_radius)

        hp_w, hp_h = 40, 5
        ratio = max(0, self.hp / self.max_hp)
        pygame.draw.rect(surface, (0,0,0), (cx - hp_w//2, cy - 40, hp_w, hp_h))
        pygame.draw.rect(surface, (200,50,50), (cx - hp_w//2, cy - 40, int(hp_w * ratio), hp_h))

    def collides(self, player):
        dist = math.hypot(self.x - player.x, self.y - player.y)
        return dist < (self.hitbox_radius + player.radius)

    def take_damage(self, dmg):
        self.hp -= dmg

# === FIREBALL ===
class Fireball:
    def __init__(self, x, y, target, damage=25, speed=350, image_path="fireball.png", image_size=(32,32)):
        self.x = float(x)
        self.y = float(y)
        self.target = target
        self.speed = speed
        self.damage = damage
        self.radius = 8
        self.dead = False
        try:
            self.image = pygame.image.load(image_path).convert_alpha()
            self.image = pygame.transform.scale(self.image, image_size)
        except:
            self.image = None

    def update(self, dt):
        if not self.target or self.target.hp <= 0:
            self.dead = True
            return
        dx = self.target.x - self.x
        dy = self.target.y - self.y
        dist = math.hypot(dx, dy)
        if dist > 2:
            nx, ny = dx / dist, dy / dist
            self.x += nx * self.speed * dt
            self.y += ny * self.speed * dt
        else:
            self.target.take_damage(self.damage)
            self.dead = True

    def draw(self, surface, camera):
        cx, cy = int(self.x - camera.x), int(self.y - camera.y)
        if self.image:
            rect = self.image.get_rect(center=(cx, cy))
            surface.blit(self.image, rect)
        else:
            pygame.draw.circle(surface, (255,140,0), (cx, cy), self.radius)

# === HELPERS ===
def spawn_outside_camera(level, camera):
    side = random.choice(["left","right","top","bottom"])
    margin = 100
    if side == "left":
        x = max(0, camera.x - margin)
        y = random.uniform(camera.y, camera.y + camera.screen_h)
    elif side == "right":
        x = min(level.width, camera.x + camera.screen_w + margin)
        y = random.uniform(camera.y, camera.y + camera.screen_h)
    elif side == "top":
        x = random.uniform(camera.x, camera.x + camera.screen_w)
        y = max(0, camera.y - margin)
    else:
        x = random.uniform(camera.x, camera.x + camera.screen_w)
        y = min(level.height, camera.y + camera.screen_h + margin)
    return x, y

# === DRAW MINIMAP ===
def draw_minimap(surface, level, player, camera, pos, size):
    map_surf = pygame.Surface((size, size), pygame.SRCALPHA)
    map_surf.fill((255,255,0,50))
    scale_x = size / level.width
    scale_y = size / level.height
    px = int(player.x * scale_x)
    py = int(player.y * scale_y)
    pygame.draw.circle(map_surf, (255,0,0), (px, py), 4)
    surface.blit(map_surf, pos)

# === MAIN ===
def main():
    level = Level(SCREEN_W * 10, SCREEN_H * 10)
    camera = Camera(SCREEN_W, SCREEN_H, level.width, level.height)
    player = Character(level.width/2, level.height/2)

    enemies = []
    fireballs = []

    spawn_timer = 5.0
    fire_timer = 5.0
    fire_timer_reset = 5.0  # initial spawn delay

    font = pygame.font.SysFont(None, 32)

    minimap_size = 200
    minimap_margin = 200
    minimap_pos = (SCREEN_W - minimap_size - minimap_margin, minimap_margin)

    xp_bar_width = 10
    xp_bar_margin = 200
    xp_bar_height = SCREEN_H - 2 * xp_bar_margin
    xp_bar_pos = (xp_bar_margin, xp_bar_margin)

    text_x = xp_bar_margin + xp_bar_width + 10
    text_y = xp_bar_margin
    level_text_pos = (text_x, text_y)
    hp_text_pos = (text_x, text_y + 22)
    kill_text_pos = (text_x, text_y + 44)

    running = True
    while running:
        dt = clock.tick(FPS)/1000
        for e in pygame.event.get():
            if e.type == pygame.QUIT or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
                running = False

        keys = pygame.key.get_pressed()
        player.handle_input(keys, dt)
        player.clamp_to_level(level.width, level.height)
        camera.update(player.x, player.y)

        spawn_timer -= dt
        if spawn_timer <= 0:
            spawn_timer = 5.0
            sx, sy = spawn_outside_camera(level, camera)
            enemies.append(Zombie(sx, sy))

        fire_timer -= dt
        if fire_timer <= 0:
            fire_timer = fire_timer_reset
            if enemies:
                target = min(enemies, key=lambda e: math.hypot(player.x - e.x, player.y - e.y))
                fireballs.append(Fireball(player.x, player.y, target))

        for z in enemies[:]:
            z.update(dt, player)
            if z.collides(player) and z.cooldown <= 0:
                player.take_damage(z.damage)
                z.cooldown = 0.5

                # === GAME OVER ===
                if player.hp <= 0:
                    pygame.quit()
                    sys.exit()

            if z.hp <= 0:
                enemies.remove(z)
                player.gain_xp(50)

                # === KILL COUNT & FIREBALL SPAWN SPEED ===
                player.kills += 1
                fire_timer_reset = max(0.5, 5.0 * (0.95 ** player.kills))  # spawn 2% faster per kill, min 0.5s

        for f in fireballs[:]:
            f.update(dt)
            if f.dead:
                fireballs.remove(f)

        level.draw(screen, camera)
        for z in enemies: z.draw(screen, camera)
        for f in fireballs: f.draw(screen, camera)
        player.draw(screen, camera)

        draw_minimap(screen, level, player, camera, minimap_pos, minimap_size)

        xp_surface = pygame.Surface((xp_bar_width, xp_bar_height), pygame.SRCALPHA)
        xp_surface.fill((0,0,0,120))
        fill_ratio = player.xp / player.xp_to_next
        fill_h = int(xp_bar_height * fill_ratio)
        pygame.draw.rect(xp_surface, (80,255,80), (0, xp_bar_height - fill_h, xp_bar_width, fill_h))
        screen.blit(xp_surface, xp_bar_pos)

        screen.blit(font.render(f"Level {player.level}", True, (255,255,255)), level_text_pos)
        screen.blit(font.render(f"HP: {int(player.hp)}/{player.max_hp}", True, (255,255,255)), hp_text_pos)
        screen.blit(font.render(f"Kills: {player.kills}", True, (255,255,255)), kill_text_pos)

        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
