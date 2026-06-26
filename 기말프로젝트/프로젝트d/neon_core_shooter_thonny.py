import math
import random
import time
import tkinter as tk
from pathlib import Path


WIDTH = 1120
HEIGHT = 720
WORLD_W = 1680
WORLD_H = 1040
TAU = math.pi * 2


def clamp(value, low, high):
    return max(low, min(high, value))


def dist(a, b):
    return math.hypot(a["x"] - b["x"], a["y"] - b["y"])


def rotated_box(cx, cy, w, h, angle):
    points = []
    ca = math.cos(angle)
    sa = math.sin(angle)
    for px, py in [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]:
        points.extend([cx + px * ca - py * sa, cy + px * sa + py * ca])
    return points


class NeonCoreTank:
    def __init__(self, root):
        self.root = root
        self.root.title("Neon Core Tank - Thonny Edition")
        self.canvas = tk.Canvas(root, width=WIDTH, height=HEIGHT, bg="#03050a", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.focus_set()

        self.keys = set()
        self.buttons = []
        self.mouse = {"x": WIDTH // 2, "y": HEIGHT // 2, "world_x": WORLD_W // 2, "world_y": WORLD_H // 2}
        self.last_time = time.perf_counter()
        self.scene = "title"
        self.difficulty = 1
        self.effects = True
        self.camera_shake = 0
        self.flash = 0
        self.high_score = 0
        self.asset_images = self.load_asset_images()
        self.sprite_frames = self.load_sprite_frames()

        self.stages = [
            {
                "name": "Stage 1 - Neon Depot",
                "asset": "stage_neon_depot",
                "subtitle": "보급 기지를 습격한 정찰 전차를 정리하세요.",
                "time": 70,
                "target": 10,
                "color": "#00e5ff",
                "floor": "#08101a",
                "accent": "#16364a",
                "spawn": ["scout", "raider"],
                "obstacles": [(290, 260, 210, 76), (1190, 770, 250, 92), (1260, 240, 160, 68)],
            },
            {
                "name": "Stage 2 - Crimson Yard",
                "asset": "stage_crimson_yard",
                "subtitle": "좁은 산업 구역에서 중형 전차가 합류합니다.",
                "time": 78,
                "target": 14,
                "color": "#ff3b6b",
                "floor": "#100912",
                "accent": "#4a1627",
                "spawn": ["scout", "raider", "heavy"],
                "obstacles": [(260, 740, 230, 86), (760, 280, 260, 80), (1240, 560, 230, 92), (1380, 200, 160, 64)],
            },
            {
                "name": "Stage 3 - Core Gate",
                "asset": "stage_core_gate",
                "subtitle": "코어 게이트를 지키는 지휘 전차를 격파하세요.",
                "time": 95,
                "target": 18,
                "color": "#ffd166",
                "floor": "#0f1118",
                "accent": "#53451f",
                "spawn": ["raider", "heavy", "warden"],
                "obstacles": [(300, 300, 220, 78), (760, 780, 300, 96), (1170, 340, 250, 82), (1340, 790, 180, 74)],
            },
        ]

        self.root.bind("<KeyPress>", self.on_key_down)
        self.root.bind("<KeyRelease>", self.on_key_up)
        self.canvas.bind("<Motion>", self.on_mouse_move)
        self.canvas.bind("<Button-1>", self.on_mouse_down)

        self.new_campaign()
        self.loop()

    def load_asset_images(self):
        asset_dir = Path(__file__).resolve().parent / "assets"
        files = {
            "title": "title-art.png",
            "stage_neon_depot": "stage-neon-depot.png",
            "stage_crimson_yard": "stage-crimson-yard.png",
            "stage_core_gate": "stage-core-gate.png",
            "effect_explosion": "effects/explosion.png",
            "effect_hit_spark": "effects/hit-spark.png",
            "effect_dust_puff": "effects/dust-puff.png",
            "effect_shield_ring": "effects/shield-ring.png",
            "effect_power_ring": "effects/power-ring.png",
            "effect_artillery_warning": "effects/artillery-warning.png",
            "effect_friendly_warning": "effects/friendly-warning.png",
            "effect_bomb_impact": "effects/bomb-impact.png",
            "effect_emp_field": "effects/emp-field.png",
            "effect_relay_zone": "effects/relay-zone.png",
            "effect_relay_core": "effects/relay-core.png",
        }
        images = {}
        for key, filename in files.items():
            path = asset_dir / filename
            if path.exists():
                try:
                    images[key] = tk.PhotoImage(file=str(path))
                except tk.TclError:
                    pass
        return images

    def load_sprite_frames(self):
        sprite_dir = Path(__file__).resolve().parent / "assets" / "sprites" / "tk"
        names = [
            "tank-player",
            "tank-scout",
            "tank-raider",
            "tank-heavy",
            "tank-warden",
            "projectile-player",
            "projectile-enemy",
            "strike-plane",
            "pickup-supply",
            "effect-muzzle-flash",
        ]
        frames = {}
        for name in names:
            frame_dir = sprite_dir / name
            if name.startswith("effect-"):
                frame_dir = Path(__file__).resolve().parent / "assets" / "effects" / "tk" / name.replace("effect-", "")
            if not frame_dir.exists():
                continue
            loaded = []
            for path in sorted(frame_dir.glob("*.png")):
                try:
                    loaded.append(tk.PhotoImage(file=str(path)))
                except tk.TclError:
                    loaded = []
                    break
            if loaded:
                frames[name] = loaded
        return frames

    def new_campaign(self):
        self.stage_index = 0
        self.total_score = 0
        self.player = self.make_player()
        self.load_stage()

    def make_player(self):
        return {
            "x": WORLD_W / 2,
            "y": WORLD_H / 2,
            "r": 28,
            "hp": 100,
            "max_hp": 100,
            "speed": 245,
            "invuln": 0,
            "dash": 0,
            "hull": 0,
            "turret": 0,
            "color": "#00d9ff",
            "accent": "#e8fbff",
        }

    def load_stage(self):
        stage = self.stages[self.stage_index]
        self.score = 0
        self.combo = 1
        self.combo_timer = 0
        self.kills = 0
        self.time_left = float(stage["time"])
        self.fire_cooldown = 0
        self.reload_timer = 0
        self.reload_time = 1.45
        self.max_ammo = 9 + self.stage_index
        self.ammo = self.max_ammo
        self.power_timer = 0
        self.camera_shake = 0
        self.flash = 0
        self.bullets = []
        self.enemy_shells = []
        self.enemies = []
        self.hazards = []
        self.planes = []
        self.particles = []
        self.pickups = []
        self.texts = []
        self.event_timer = 7.0
        self.event_name = "전장 안정"
        self.event_message_timer = 0
        self.emp_timer = 0
        self.objective = None
        self.objective_timer = 7.0
        self.airstrike_charges = 0
        self.obstacles = [{"x": x, "y": y, "w": w, "h": h} for x, y, w, h in stage["obstacles"]]
        self.player["x"] = WORLD_W / 2
        self.player["y"] = WORLD_H / 2
        self.player["invuln"] = 1.0
        self.spawn_wave(4 + self.stage_index * 2)

    def start_game(self):
        self.new_campaign()
        self.scene = "playing"

    def next_stage(self):
        self.total_score += self.score
        if self.stage_index >= len(self.stages) - 1:
            self.high_score = max(self.high_score, self.total_score)
            self.scene = "victory"
            return
        self.stage_index += 1
        self.player["hp"] = min(self.player["max_hp"], self.player["hp"] + 35)
        self.load_stage()
        self.scene = "playing"

    def spawn_wave(self, count):
        for _ in range(count):
            self.spawn_enemy()

    def spawn_enemy(self):
        stage = self.stages[self.stage_index]
        kind = random.choice(stage["spawn"])
        if self.kills > stage["target"] * 0.65 and "warden" in stage["spawn"]:
            kind = random.choice(["heavy", "warden"])

        side = random.randrange(4)
        margin = 90
        pos = [
            {"x": random.random() * WORLD_W, "y": -margin},
            {"x": WORLD_W + margin, "y": random.random() * WORLD_H},
            {"x": random.random() * WORLD_W, "y": WORLD_H + margin},
            {"x": -margin, "y": random.random() * WORLD_H},
        ][side]

        stats = {
            "scout": {"r": 22, "hp": 1.3, "speed": 118, "damage": 10, "score": 70, "color": "#9b5cff", "accent": "#dfcbff"},
            "raider": {"r": 27, "hp": 2.2, "speed": 78, "damage": 15, "score": 95, "color": "#ff7a1a", "accent": "#ffe0bd"},
            "heavy": {"r": 34, "hp": 4.2, "speed": 50, "damage": 22, "score": 140, "color": "#ff3b6b", "accent": "#ffd0db"},
            "warden": {"r": 39, "hp": 6.2, "speed": 42, "damage": 28, "score": 230, "color": "#ffd166", "accent": "#fff1bf"},
        }[kind].copy()

        scale = 1 + self.stage_index * 0.12 + (self.difficulty - 1) * 0.16
        enemy = {
            "type": kind,
            "x": pos["x"],
            "y": pos["y"],
            "r": stats["r"],
            "hp": stats["hp"] * scale,
            "max_hp": stats["hp"] * scale,
            "speed": stats["speed"] * (0.94 + self.difficulty * 0.08),
            "damage": stats["damage"] * (0.88 + self.difficulty * 0.12),
            "score": stats["score"],
            "color": stats["color"],
            "accent": stats["accent"],
            "hit": 0,
            "hull": 0,
            "turret": 0,
            "cooldown": 0.6 + random.random(),
        }
        self.enemies.append(enemy)

    def start_reload(self):
        if self.reload_timer <= 0 and self.ammo < self.max_ammo:
            self.reload_timer = self.reload_time
            self.float_text(self.player["x"], self.player["y"] - 48, "RELOAD", "#ffd166")

    def shoot(self):
        if self.scene != "playing" or self.fire_cooldown > 0 or self.reload_timer > 0:
            return
        if self.ammo <= 0:
            self.start_reload()
            return

        p = self.player
        angle = p["turret"]
        powered = self.power_timer > 0
        spread = [-0.055, 0, 0.055] if powered else [0]
        shell_speed = 780 if powered else 705
        for offset in spread:
            a = angle + offset
            self.bullets.append({
                "x": p["x"] + math.cos(a) * 45,
                "y": p["y"] + math.sin(a) * 45,
                "vx": math.cos(a) * shell_speed,
                "vy": math.sin(a) * shell_speed,
                "r": 6,
                "life": 1.18,
                "range": 640 if powered else 520,
                "travel": 0,
                "damage": 1.8 if powered else 1.0,
                "color": "#ffd166" if powered else "#00e5ff",
            })

        self.ammo -= 1
        self.fire_cooldown = 0.11 if powered else 0.2
        self.camera_shake = max(self.camera_shake, 8)
        self.muzzle_flash(angle)
        if self.ammo <= 0:
            self.start_reload()

    def update(self, dt):
        if self.scene != "playing":
            return

        self.time_left -= dt
        self.fire_cooldown = max(0, self.fire_cooldown - dt)
        self.combo_timer = max(0, self.combo_timer - dt)
        self.power_timer = max(0, self.power_timer - dt)
        self.emp_timer = max(0, self.emp_timer - dt)
        self.event_message_timer = max(0, self.event_message_timer - dt)
        self.player["invuln"] = max(0, self.player["invuln"] - dt)
        self.player["dash"] = max(0, self.player["dash"] - dt)
        self.camera_shake = max(0, self.camera_shake - dt * 40)
        self.flash = max(0, self.flash - dt * 1.8)

        if self.reload_timer > 0:
            self.reload_timer -= dt
            if self.reload_timer <= 0:
                self.reload_timer = 0
                self.ammo = self.max_ammo
                self.float_text(self.player["x"], self.player["y"] - 48, "READY", "#53ff9c")

        if self.combo_timer == 0:
            self.combo = 1
        if "space" in self.keys:
            self.shoot()

        self.update_player(dt)
        self.update_bullets(dt)
        self.update_enemy_shells(dt)
        self.update_enemies(dt)
        self.update_pickups(dt)
        self.update_planes(dt)
        self.update_events(dt)
        self.update_objective(dt)
        self.update_particles(dt)
        self.check_stage_state()

    def update_player(self, dt):
        p = self.player
        old_x = p["x"]
        old_y = p["y"]
        ax = 0
        ay = 0
        if "w" in self.keys or "up" in self.keys:
            ay -= 1
        if "s" in self.keys or "down" in self.keys:
            ay += 1
        if "a" in self.keys or "left" in self.keys:
            ax -= 1
        if "d" in self.keys or "right" in self.keys:
            ax += 1

        length = math.hypot(ax, ay) or 1
        speed = p["speed"] * (1.65 if p["dash"] > 0 else 1)
        p["x"] = clamp(p["x"] + ax / length * speed * dt, p["r"], WORLD_W - p["r"])
        p["y"] = clamp(p["y"] + ay / length * speed * dt, p["r"], WORLD_H - p["r"])
        if self.hit_obstacle(p):
            p["x"], p["y"] = old_x, old_y

        if ax or ay:
            p["hull"] = self.turn_toward(p["hull"], math.atan2(ay, ax), dt * 8)
            if random.random() < 0.35:
                self.track_dust(p["x"], p["y"], p["hull"])
        p["turret"] = math.atan2(self.mouse["world_y"] - p["y"], self.mouse["world_x"] - p["x"])

    def update_bullets(self, dt):
        for b in self.bullets:
            step_x = b["vx"] * dt
            step_y = b["vy"] * dt
            b["x"] += step_x
            b["y"] += step_y
            b["travel"] += math.hypot(step_x, step_y)
            b["life"] -= dt
            if b["travel"] >= b["range"]:
                b["life"] = 0
                self.burst(b["x"], b["y"], 8, b["color"], 0.9)
            if self.point_in_obstacle(b["x"], b["y"]):
                b["life"] = 0
                self.burst(b["x"], b["y"], 10, b["color"], 1.2)
        self.bullets = [b for b in self.bullets if b["life"] > 0 and -80 < b["x"] < WORLD_W + 80 and -80 < b["y"] < WORLD_H + 80]

    def update_enemy_shells(self, dt):
        p = self.player
        for shell in self.enemy_shells:
            step_x = shell["vx"] * dt
            step_y = shell["vy"] * dt
            shell["x"] += step_x
            shell["y"] += step_y
            shell["travel"] += math.hypot(step_x, step_y)
            shell["life"] -= dt
            if shell["travel"] >= shell["range"]:
                shell["life"] = 0
            if self.point_in_obstacle(shell["x"], shell["y"]):
                shell["life"] = 0
                self.burst(shell["x"], shell["y"], 10, shell["color"], 1.1)
            if shell["life"] > 0 and dist(shell, p) < shell["r"] + p["r"] and p["invuln"] <= 0:
                shell["life"] = 0
                p["hp"] -= shell["damage"]
                p["invuln"] = 0.45
                self.combo = 1
                self.combo_timer = 0
                self.camera_shake = max(self.camera_shake, 13)
                self.flash = max(self.flash, 0.25)
                self.burst(p["x"], p["y"], 20, "#ff3b6b", 2.5)
        self.enemy_shells = [s for s in self.enemy_shells if s["life"] > 0 and -90 < s["x"] < WORLD_W + 90 and -90 < s["y"] < WORLD_H + 90]

    def update_enemies(self, dt):
        p = self.player
        for e in self.enemies:
            old_x = e["x"]
            old_y = e["y"]
            angle = math.atan2(p["y"] - e["y"], p["x"] - e["x"])
            e["hull"] = self.turn_toward(e["hull"], angle, dt * 4.5)
            e["turret"] = self.turn_toward(e["turret"], angle, dt * 6)
            e["cooldown"] = max(0, e["cooldown"] - dt)
            e["x"] += math.cos(angle) * e["speed"] * dt
            e["y"] += math.sin(angle) * e["speed"] * dt
            if self.hit_obstacle(e):
                sidestep = angle + math.pi / 2
                e["x"] = old_x + math.cos(sidestep) * e["speed"] * dt
                e["y"] = old_y + math.sin(sidestep) * e["speed"] * dt
                if self.hit_obstacle(e):
                    e["x"], e["y"] = old_x, old_y
            e["hit"] = max(0, e["hit"] - dt)
            if random.random() < 0.18:
                self.track_dust(e["x"], e["y"], e["hull"])

            fire_range = 520 if e["type"] == "scout" else 690
            if dist(e, p) < fire_range and e["cooldown"] <= 0:
                self.enemy_shoot(e, angle)

            if dist(e, p) < e["r"] + p["r"] and p["invuln"] <= 0:
                p["hp"] -= e["damage"]
                p["invuln"] = 0.72
                self.combo = 1
                self.combo_timer = 0
                self.camera_shake = max(self.camera_shake, 18)
                self.flash = max(self.flash, 0.35)
                self.burst(p["x"], p["y"], 28, "#ff3b6b", 3.2)
                e["x"] -= math.cos(angle) * 44
                e["y"] -= math.sin(angle) * 44

        for b in self.bullets:
            if b["life"] <= 0:
                continue
            for e in self.enemies:
                if e["hp"] <= 0:
                    continue
                if dist(b, e) <= b["r"] + e["r"]:
                    b["life"] = 0
                    e["hp"] -= b["damage"]
                    e["hit"] = 0.08
                    self.camera_shake = max(self.camera_shake, 8)
                    self.burst(b["x"], b["y"], 15, e["color"], 2.0)
                    if e["hp"] <= 0:
                        self.kill_enemy(e)
                    break
        self.enemies = [e for e in self.enemies if e["hp"] > 0]

    def enemy_shoot(self, enemy, angle):
        lead = 0.16 if enemy["type"] in ("heavy", "warden") else 0.08
        target_x = self.player["x"] + math.cos(self.player["hull"]) * self.player["speed"] * lead
        target_y = self.player["y"] + math.sin(self.player["hull"]) * self.player["speed"] * lead
        a = math.atan2(target_y - enemy["y"], target_x - enemy["x"]) + random.uniform(-0.08, 0.08)
        speed = 350 if enemy["type"] == "scout" else 420
        damage = 8 if enemy["type"] == "scout" else 13
        if enemy["type"] == "warden":
            speed = 460
            damage = 18
        self.enemy_shells.append({
            "x": enemy["x"] + math.cos(a) * (enemy["r"] + 22),
            "y": enemy["y"] + math.sin(a) * (enemy["r"] + 22),
            "vx": math.cos(a) * speed,
            "vy": math.sin(a) * speed,
            "r": 5,
            "life": 1.8,
            "range": 455 if enemy["type"] == "scout" else 540,
            "travel": 0,
            "damage": damage,
            "color": "#ff4d7d" if enemy["type"] != "warden" else "#ffd166",
        })
        base = {"scout": 2.2, "raider": 1.8, "heavy": 2.35, "warden": 1.45}[enemy["type"]]
        enemy["cooldown"] = base / (0.9 + self.difficulty * 0.15) + random.uniform(0.25, 0.8)
        self.muzzle_flash_from(enemy["x"], enemy["y"], a, enemy["color"])

    def kill_enemy(self, e):
        gain = round(e["score"] * self.combo)
        self.score += gain
        self.combo = min(9, self.combo + 1)
        self.combo_timer = 2.2
        self.kills += 1
        self.camera_shake = max(self.camera_shake, 16 if e["type"] in ("heavy", "warden") else 10)
        self.burst(e["x"], e["y"], 60 if e["type"] == "warden" else 38, e["color"], 3.2)
        self.float_text(e["x"], e["y"], "+" + str(gain), e["color"])
        if random.random() < 0.17:
            self.pickups.append({"x": e["x"], "y": e["y"], "r": 15, "type": random.choice(["heal", "ammo", "power"]), "spin": 0})
        if len(self.enemies) < 4 and self.kills < self.stages[self.stage_index]["target"]:
            self.spawn_wave(2)

    def update_pickups(self, dt):
        p = self.player
        for item in self.pickups:
            item["spin"] += dt * 5
            if dist(item, p) < item["r"] + p["r"]:
                if item["type"] == "heal":
                    p["hp"] = min(p["max_hp"], p["hp"] + 26)
                    self.float_text(p["x"], p["y"] - 42, "REPAIR", "#53ff9c")
                    self.burst(item["x"], item["y"], 24, "#53ff9c", 2.2)
                elif item["type"] == "ammo":
                    self.ammo = self.max_ammo
                    self.reload_timer = 0
                    self.float_text(p["x"], p["y"] - 42, "AMMO", "#00e5ff")
                    self.burst(item["x"], item["y"], 24, "#00e5ff", 2.2)
                else:
                    self.power_timer = 7
                    self.float_text(p["x"], p["y"] - 42, "OVERDRIVE", "#ffd166")
                    self.burst(item["x"], item["y"], 24, "#ffd166", 2.2)
                item["dead"] = True
        self.pickups = [i for i in self.pickups if not i.get("dead")]

    def update_events(self, dt):
        self.event_timer -= dt
        if self.event_timer <= 0:
            self.trigger_event()
            self.event_timer = random.uniform(8.0, 12.5) - self.stage_index

        p = self.player
        for hazard in self.hazards:
            hazard["timer"] -= dt
            if hazard["type"] == "artillery" and hazard["timer"] <= 0 and not hazard.get("done"):
                hazard["done"] = True
                hazard["boom"] = 0.34
                self.camera_shake = max(self.camera_shake, 18)
                blast_color = "#00e5ff" if hazard.get("friendly") else "#ff3b6b"
                self.burst(hazard["x"], hazard["y"], 46, blast_color, 3.0)
                for enemy in self.enemies:
                    if math.hypot(enemy["x"] - hazard["x"], enemy["y"] - hazard["y"]) < hazard["r"] * 1.08:
                        enemy["hp"] -= 2.6 if hazard.get("friendly") else 0.9
                        enemy["hit"] = 0.12
                if not hazard.get("friendly") and math.hypot(p["x"] - hazard["x"], p["y"] - hazard["y"]) < hazard["r"]:
                    p["hp"] -= 24
                    p["invuln"] = 0.6
                    self.flash = max(self.flash, 0.38)
            elif hazard["type"] == "emp":
                if math.hypot(p["x"] - hazard["x"], p["y"] - hazard["y"]) < hazard["r"]:
                    self.emp_timer = max(self.emp_timer, 0.18)
                    self.fire_cooldown = max(self.fire_cooldown, 0.1)
                hazard["r"] += 18 * dt
            if hazard.get("boom", 0) > 0:
                hazard["boom"] -= dt

        self.hazards = [
            h for h in self.hazards
            if (h["type"] == "emp" and h["timer"] > 0) or (h["type"] == "artillery" and (h["timer"] > -0.45 or h.get("boom", 0) > 0))
        ]
        for enemy in list(self.enemies):
            if enemy["hp"] <= 0:
                self.kill_enemy(enemy)
        self.enemies = [e for e in self.enemies if e["hp"] > 0]

    def update_objective(self, dt):
        if self.objective is None:
            self.objective_timer -= dt
            if self.objective_timer <= 0:
                self.spawn_objective()
            return

        obj = self.objective
        obj["time"] -= dt
        if obj["type"] == "relay":
            inside = math.hypot(self.player["x"] - obj["x"], self.player["y"] - obj["y"]) < obj["r"]
            if inside:
                obj["progress"] += dt
                if random.random() < 0.35:
                    self.burst(self.player["x"], self.player["y"], 2, "#53ff9c", 0.6)
            else:
                obj["progress"] = max(0, obj["progress"] - dt * 0.5)
            if obj["progress"] >= obj["need"]:
                self.complete_objective("RELAY LINK")
        elif obj["type"] == "ace":
            if not any(e.get("ace") for e in self.enemies):
                self.complete_objective("ACE DOWN")

        if self.objective and obj["time"] <= 0:
            self.float_text(self.player["x"], self.player["y"] - 64, "OBJECTIVE LOST", "#ff3b6b")
            self.objective = None
            self.objective_timer = random.uniform(11, 16)

    def spawn_objective(self):
        if random.random() < 0.55:
            self.objective = {
                "type": "relay",
                "x": random.uniform(230, WORLD_W - 230),
                "y": random.uniform(210, WORLD_H - 210),
                "r": 82,
                "progress": 0,
                "need": 3.2,
                "time": 15.0,
            }
            self.event_name = "중계기 점령"
        else:
            self.spawn_enemy()
            ace = self.enemies[-1]
            ace["ace"] = True
            ace["hp"] *= 1.8
            ace["max_hp"] = ace["hp"]
            ace["score"] += 220
            ace["color"] = "#53ff9c"
            ace["accent"] = "#ddffe9"
            self.objective = {"type": "ace", "time": 18.0}
            self.event_name = "에이스 전차"
        self.event_message_timer = 2.6

    def complete_objective(self, label):
        self.score += 180
        self.airstrike_charges = min(3, self.airstrike_charges + 1)
        self.ammo = self.max_ammo
        self.power_timer = max(self.power_timer, 3.5)
        self.float_text(self.player["x"], self.player["y"] - 70, label + " + AIRSTRIKE", "#53ff9c")
        self.objective = None
        self.objective_timer = random.uniform(14, 20)

    def update_planes(self, dt):
        for plane in self.planes:
            plane["x"] += plane["vx"] * dt
            plane["y"] += plane["vy"] * dt
            plane["life"] -= dt
            if not plane["dropped"] and math.hypot(plane["x"] - plane["target_x"], plane["y"] - plane["target_y"]) < 95:
                plane["dropped"] = True
                self.hazards.append({
                    "type": "artillery",
                    "x": plane["target_x"],
                    "y": plane["target_y"],
                    "r": plane["r"],
                    "timer": 0.95,
                    "friendly": plane["friendly"],
                })
                self.float_text(plane["target_x"], plane["target_y"] - 60, "BOMB DROP", "#00e5ff" if plane["friendly"] else "#ff3b6b")
        self.planes = [p for p in self.planes if p["life"] > 0]

    def trigger_event(self):
        choices = ["artillery", "supply", "surge", "emp"]
        if self.stage_index == 0:
            choices = ["artillery", "supply", "surge"]
        event = random.choice(choices)
        if event == "artillery":
            self.event_name = "궤도 포격"
            self.event_message_timer = 2.4
            for _ in range(2 + self.stage_index):
                self.launch_bomber(random.uniform(180, WORLD_W - 180), random.uniform(170, WORLD_H - 170), random.uniform(78, 105))
        elif event == "supply":
            self.event_name = "긴급 보급"
            self.event_message_timer = 2.4
            for kind in ["ammo", random.choice(["heal", "power"])]:
                self.pickups.append({
                    "x": random.uniform(180, WORLD_W - 180),
                    "y": random.uniform(170, WORLD_H - 170),
                    "r": 15,
                    "type": kind,
                    "spin": 0,
                })
        elif event == "surge":
            self.event_name = "코어 서지"
            self.event_message_timer = 2.4
            self.power_timer = max(self.power_timer, 6.5)
            self.ammo = self.max_ammo
            self.burst(self.player["x"], self.player["y"], 52, "#ffd166", 2.8)
        else:
            self.event_name = "EMP 필드"
            self.event_message_timer = 2.4
            self.hazards.append({
                "type": "emp",
                "x": random.uniform(220, WORLD_W - 220),
                "y": random.uniform(190, WORLD_H - 190),
                "r": 90,
                "timer": 6.0,
            })

    def launch_bomber(self, target_x, target_y, radius, friendly=False):
        angle = random.choice([0, math.pi]) + random.uniform(-0.22, 0.22)
        start_x = target_x - math.cos(angle) * 760
        start_y = target_y - math.sin(angle) * 760
        speed = 520
        self.planes.append({
            "x": start_x,
            "y": start_y,
            "vx": math.cos(angle) * speed,
            "vy": math.sin(angle) * speed,
            "angle": angle,
            "target_x": target_x,
            "target_y": target_y,
            "r": radius,
            "dropped": False,
            "life": 3.4,
            "friendly": friendly,
        })

    def call_support_strike(self):
        if self.scene != "playing" or self.airstrike_charges <= 0:
            return
        self.airstrike_charges -= 1
        self.event_name = "지원 포격"
        self.event_message_timer = 2.0
        self.launch_bomber(self.mouse["world_x"], self.mouse["world_y"], 115, True)

    def update_particles(self, dt):
        for p in self.particles:
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            p["vx"] *= p.get("drag", 0.965)
            p["vy"] *= p.get("drag", 0.965)
            p["vy"] += p.get("gravity", 0) * dt
            p["r"] += p.get("grow", 0) * dt
            p["life"] -= dt
        self.particles = [p for p in self.particles if p["life"] > 0]
        for text in self.texts:
            text["y"] -= 38 * dt
            text["life"] -= dt
        self.texts = [t for t in self.texts if t["life"] > 0]

    def check_stage_state(self):
        if self.player["hp"] <= 0 or self.time_left <= 0:
            self.scene = "game_over"
            self.high_score = max(self.high_score, self.total_score + self.score)
            return
        if self.kills >= self.stages[self.stage_index]["target"] and not self.enemies:
            self.scene = "stage_clear"
            self.burst(self.player["x"], self.player["y"], 70, self.stages[self.stage_index]["color"], 3.5)

    def hit_obstacle(self, obj):
        for block in self.obstacles:
            nx = clamp(obj["x"], block["x"], block["x"] + block["w"])
            ny = clamp(obj["y"], block["y"], block["y"] + block["h"])
            if math.hypot(obj["x"] - nx, obj["y"] - ny) < obj["r"] * 0.82:
                return True
        return False

    def point_in_obstacle(self, x, y):
        for block in self.obstacles:
            if block["x"] <= x <= block["x"] + block["w"] and block["y"] <= y <= block["y"] + block["h"]:
                return True
        return False

    def render(self):
        self.canvas.delete("all")
        self.buttons = []
        if self.scene == "title":
            self.draw_title()
        elif self.scene == "settings":
            self.draw_settings()
        elif self.scene == "howto":
            self.draw_howto()
        elif self.scene in ("playing", "stage_clear", "game_over", "victory"):
            self.draw_game_world()
            if self.scene == "stage_clear":
                self.draw_stage_clear()
            elif self.scene == "game_over":
                self.draw_game_over()
            elif self.scene == "victory":
                self.draw_victory()

    def draw_game_world(self):
        active_shake = self.camera_shake if self.effects else 0
        shake_x = random.uniform(-active_shake, active_shake)
        shake_y = random.uniform(-active_shake, active_shake)
        cam_x = clamp(self.player["x"] - WIDTH / 2, 0, WORLD_W - WIDTH)
        cam_y = clamp(self.player["y"] - HEIGHT / 2, 0, WORLD_H - HEIGHT)

        def sx(x):
            return x - cam_x + shake_x

        def sy(y):
            return y - cam_y + shake_y

        self.draw_backdrop()
        self.draw_arena(sx, sy)
        self.draw_objective(sx, sy)
        self.draw_planes(sx, sy)
        self.draw_hazards(sx, sy)
        self.draw_pickups(sx, sy)
        self.draw_particles(sx, sy, "smoke")
        self.draw_bullets(sx, sy)
        self.draw_enemy_shells(sx, sy)
        self.draw_enemies(sx, sy)
        self.draw_player(sx, sy)
        self.draw_particles(sx, sy, "hot")
        self.draw_texts(sx, sy)
        self.draw_hud()
        self.draw_vignette()
        if self.flash > 0:
            self.canvas.create_rectangle(0, 0, WIDTH, HEIGHT, fill="#3b0613", stipple="gray25", outline="")

    def draw_backdrop(self):
        stage = self.stages[self.stage_index]
        self.canvas.create_rectangle(0, 0, WIDTH, HEIGHT, fill="#03050a", outline="")
        self.canvas.create_rectangle(0, 0, WIDTH, HEIGHT, fill=stage["floor"], stipple="gray75", outline="")
        self.canvas.create_oval(-160, -110, 380, 260, fill="#04202a", outline="")
        self.canvas.create_oval(WIDTH - 260, HEIGHT - 230, WIDTH + 190, HEIGHT + 150, fill=stage["accent"], outline="")

    def draw_arena(self, sx, sy):
        stage = self.stages[self.stage_index]
        image = self.asset_images.get(stage.get("asset"))
        if image:
            self.canvas.create_image(sx(0), sy(0), image=image, anchor="nw")
            self.canvas.create_rectangle(sx(0), sy(0), sx(WORLD_W), sy(WORLD_H), fill="#03050a", stipple="gray25", outline="")
        else:
            self.canvas.create_rectangle(sx(0), sy(0), sx(WORLD_W), sy(WORLD_H), fill=stage["floor"], outline="")

        # Calm floor: only sparse reference lines and large panels, avoiding visual noise.
        for x in range(0, WORLD_W + 1, 280):
            self.canvas.create_line(sx(x), sy(0), sx(x), sy(WORLD_H), fill="#10202c")
        for y in range(0, WORLD_H + 1, 260):
            self.canvas.create_line(sx(0), sy(y), sx(WORLD_W), sy(y), fill="#10202c")

        for block in self.obstacles:
            self.draw_prism(sx(block["x"]), sy(block["y"]), block["w"], block["h"], 34, "#172538", "#21334d", "#09111c")

        for i, color in enumerate([stage["color"], "#183447", "#071018"]):
            self.canvas.create_rectangle(sx(10 - i * 3), sy(10 - i * 3), sx(WORLD_W - 10 + i * 3), sy(WORLD_H - 10 + i * 3), outline=color, width=2)

    def draw_prism(self, x, y, w, h, z, top, side, dark):
        self.canvas.create_polygon(x, y, x + w, y, x + w + 24, y - z, x + 24, y - z, fill=top, outline="#31445f")
        self.canvas.create_polygon(x + w, y, x + w, y + h, x + w + 24, y + h - z, x + w + 24, y - z, fill=side, outline="#31445f")
        self.canvas.create_polygon(x, y, x, y + h, x + w, y + h, x + w, y, fill=dark, outline="#31445f")

    def sprite_frame(self, name, angle=0):
        frames = self.sprite_frames.get(name)
        if not frames:
            return None
        if len(frames) == 1:
            return frames[0]
        index = int((angle % TAU) / TAU * len(frames)) % len(frames)
        return frames[index]

    def draw_sprite(self, name, x, y, angle=0):
        frame = self.sprite_frame(name, angle)
        if not frame:
            return False
        self.canvas.create_image(x, y, image=frame)
        return True

    def draw_effect(self, name, x, y, angle=0):
        if self.draw_sprite(name, x, y, angle):
            return True
        image = self.asset_images.get(name.replace("-", "_"))
        if not image:
            return False
        self.canvas.create_image(x, y, image=image)
        return True

    def draw_tank(self, unit, sx, sy, is_player=False):
        x = sx(unit["x"])
        y = sy(unit["y"])
        r = unit["r"]
        hull = unit["hull"]
        turret = unit["turret"]
        flashing = unit.get("hit", 0) > 0 or (is_player and unit["invuln"] > 0 and int(time.perf_counter() * 12) % 2)
        color = "#ffffff" if flashing else unit["color"]
        accent = unit["accent"]

        sprite_name = "tank-player" if is_player else "tank-" + unit.get("type", "raider")
        if self.draw_sprite(sprite_name, x, y, turret):
            if flashing:
                self.draw_effect("effect-hit-spark", x, y)
            return

        self.canvas.create_oval(x - r * 1.4 + 12, y - r * 0.9 + 16, x + r * 1.4 + 12, y + r * 0.95 + 16, fill="#020306", outline="")
        self.canvas.create_polygon(rotated_box(x, y + 7, r * 2.42, r * 1.38, hull), fill="#071018", outline="#263447", width=2)
        self.canvas.create_polygon(rotated_box(x, y - 2, r * 2.02, r * 1.06, hull), fill=color, outline=accent, width=2)
        self.canvas.create_polygon(rotated_box(x, y - 13, r * 1.3, r * 0.52, hull), fill="#dff9ff" if is_player else accent, outline="")
        left_track = rotated_box(x - math.sin(hull) * r * 0.8, y + math.cos(hull) * r * 0.8, r * 2.46, r * 0.28, hull)
        right_track = rotated_box(x + math.sin(hull) * r * 0.8, y - math.cos(hull) * r * 0.8, r * 2.46, r * 0.28, hull)
        self.canvas.create_polygon(left_track, fill="#02060a", outline="#334155")
        self.canvas.create_polygon(right_track, fill="#02060a", outline="#334155")

        barrel_len = r * 1.78
        bx = x + math.cos(turret) * barrel_len
        by = y + math.sin(turret) * barrel_len
        self.canvas.create_line(x, y - 8, bx, by - 8, fill="#021018", width=max(8, int(r * 0.27)))
        self.canvas.create_line(x, y - 10, bx, by - 10, fill=accent, width=max(4, int(r * 0.13)))
        self.canvas.create_oval(x - r * 0.6, y - r * 0.6 - 8, x + r * 0.6, y + r * 0.6 - 8, fill=color, outline=accent, width=2)
        self.canvas.create_oval(x - 4, y - 12, x + 4, y - 4, fill="#ffffff", outline="")

    def draw_player(self, sx, sy):
        self.draw_tank(self.player, sx, sy, True)
        x = sx(self.player["x"])
        y = sy(self.player["y"])
        glow = "#ffd166" if self.power_timer > 0 else "#00e5ff"
        ring = "effect-power-ring" if self.power_timer > 0 else "effect-shield-ring"
        if not self.draw_effect(ring, x, y):
            self.canvas.create_oval(x - 45, y - 45, x + 45, y + 45, outline=glow, width=2)

    def draw_enemies(self, sx, sy):
        for e in self.enemies:
            self.draw_tank(e, sx, sy, False)
            if e["hp"] < e["max_hp"]:
                x = sx(e["x"])
                y = sy(e["y"])
                w = e["r"] * 2.15
                self.canvas.create_rectangle(x - w / 2, y - e["r"] - 22, x + w / 2, y - e["r"] - 17, fill="#1f2937", outline="")
                self.canvas.create_rectangle(x - w / 2, y - e["r"] - 22, x - w / 2 + w * max(0, e["hp"] / e["max_hp"]), y - e["r"] - 17, fill=e["color"], outline="")

    def draw_bullets(self, sx, sy):
        for b in self.bullets:
            x = sx(b["x"])
            y = sy(b["y"])
            angle = math.atan2(b["vy"], b["vx"])
            if not self.draw_sprite("projectile-player", x, y, angle):
                self.canvas.create_line(x - b["vx"] * 0.018, y - b["vy"] * 0.018, x, y, fill=b["color"], width=3)
                self.canvas.create_oval(x - b["r"], y - b["r"], x + b["r"], y + b["r"], fill=b["color"], outline="")

    def draw_planes(self, sx, sy):
        for plane in self.planes:
            x = sx(plane["x"])
            y = sy(plane["y"])
            a = plane["angle"]
            color = "#00e5ff" if plane["friendly"] else "#ff3b6b"
            if self.draw_sprite("strike-plane", x, y, a):
                continue
            body = rotated_box(x, y, 66, 18, a)
            wing = rotated_box(x - math.cos(a) * 6, y - math.sin(a) * 6, 28, 70, a)
            nose_x = x + math.cos(a) * 45
            nose_y = y + math.sin(a) * 45
            self.canvas.create_polygon(wing, fill="#101827", outline=color)
            self.canvas.create_polygon(body, fill="#182338", outline=color, width=2)
            self.canvas.create_oval(nose_x - 5, nose_y - 5, nose_x + 5, nose_y + 5, fill=color, outline="")
            self.canvas.create_line(x - math.cos(a) * 42, y - math.sin(a) * 42, x - math.cos(a) * 85, y - math.sin(a) * 85, fill=color, width=2)

    def draw_enemy_shells(self, sx, sy):
        for s in self.enemy_shells:
            x = sx(s["x"])
            y = sy(s["y"])
            angle = math.atan2(s["vy"], s["vx"])
            if not self.draw_sprite("projectile-enemy", x, y, angle):
                self.canvas.create_line(x - s["vx"] * 0.022, y - s["vy"] * 0.022, x, y, fill="#ff93ad", width=3)
                self.canvas.create_oval(x - s["r"], y - s["r"], x + s["r"], y + s["r"], fill=s["color"], outline="")

    def draw_hazards(self, sx, sy):
        for h in self.hazards:
            x = sx(h["x"])
            y = sy(h["y"])
            r = h["r"]
            if h["type"] == "artillery":
                color = "#ff3b6b"
                width = 3 if int(time.perf_counter() * 8) % 2 else 1
                warning = "effect-friendly-warning" if h.get("friendly") else "effect-artillery-warning"
                if not self.draw_effect(warning, x, y):
                    self.canvas.create_oval(x - r, y - r, x + r, y + r, outline=color, width=width)
                    self.canvas.create_line(x - r, y, x + r, y, fill=color)
                    self.canvas.create_line(x, y - r, x, y + r, fill=color)
                if h.get("done"):
                    if not self.draw_effect("effect-bomb-impact", x, y):
                        boom_r = r * (1.15 + max(0, h.get("boom", 0)) * 1.7)
                        self.canvas.create_oval(x - boom_r, y - boom_r, x + boom_r, y + boom_r, outline="#ffd166", width=4)
            else:
                if not self.draw_effect("effect-emp-field", x, y):
                    self.canvas.create_oval(x - r, y - r, x + r, y + r, outline="#9b5cff", width=2)
                    self.canvas.create_oval(x - r * 0.55, y - r * 0.55, x + r * 0.55, y + r * 0.55, outline="#00e5ff", width=1)

    def draw_objective(self, sx, sy):
        if not self.objective:
            return
        obj = self.objective
        if obj["type"] == "relay":
            x = sx(obj["x"])
            y = sy(obj["y"])
            r = obj["r"]
            progress = obj["progress"] / obj["need"]
            if not self.draw_effect("effect-relay-zone", x, y):
                self.canvas.create_oval(x - r, y - r, x + r, y + r, outline="#53ff9c", width=2)
            if not self.draw_effect("effect-relay-core", x, y):
                self.canvas.create_oval(x - 16, y - 16, x + 16, y + 16, fill="#0d261b", outline="#53ff9c", width=2)
            self.canvas.create_text(x, y - r - 18, text="CAPTURE RELAY {:.0f}%".format(progress * 100), fill="#53ff9c", font=("Arial", 10, "bold"))
        else:
            self.canvas.create_text(WIDTH / 2, 176, text="BONUS: 에이스 전차를 제한 시간 안에 격파", fill="#53ff9c", font=("Arial", 11, "bold"))

    def draw_pickups(self, sx, sy):
        for item in self.pickups:
            x = sx(item["x"])
            y = sy(item["y"])
            color = {"heal": "#53ff9c", "ammo": "#00e5ff", "power": "#ffd166"}[item["type"]]
            if self.draw_sprite("pickup-supply", x, y):
                continue
            self.canvas.create_oval(x - 19, y - 19, x + 19, y + 19, outline=color, width=2)
            if item["type"] == "heal":
                self.canvas.create_line(x - 11, y, x + 11, y, fill=color, width=4)
                self.canvas.create_line(x, y - 11, x, y + 11, fill=color, width=4)
            elif item["type"] == "ammo":
                self.canvas.create_rectangle(x - 10, y - 7, x + 10, y + 7, fill=color, outline="")
            else:
                self.canvas.create_polygon(x, y - 13, x + 12, y + 9, x - 12, y + 9, outline=color, fill="", width=3)

    def draw_particles(self, sx, sy, layer="all"):
        for p in self.particles:
            kind = p.get("kind")
            if layer == "smoke" and kind != "smoke":
                continue
            if layer == "hot" and kind == "smoke":
                continue
            alpha = max(0, p["life"] / p["max"])
            r = max(1, p["r"] * (0.55 + 0.45 * alpha))
            x = sx(p["x"])
            y = sy(p["y"])
            if kind == "smoke":
                self.draw_smoke_particle(x, y, r, alpha, p)
                continue
            if kind == "blast":
                self.draw_blast_particle(x, y, r, alpha, p)
                continue
            if kind == "spark":
                self.draw_spark_particle(x, y, r, alpha, p)
                continue
            sprite = p.get("sprite", "effect-hit-spark")
            if not self.draw_effect(sprite, x, y, p.get("angle", 0)):
                self.canvas.create_oval(x - r, y - r, x + r, y + r, fill=p["color"], outline="")

    def particle_stipple(self, alpha):
        if alpha > 0.72:
            return ""
        if alpha > 0.48:
            return "gray75"
        if alpha > 0.23:
            return "gray50"
        return "gray25"

    def draw_smoke_particle(self, x, y, r, alpha, p):
        color = p.get("color", "#263447")
        stipple = self.particle_stipple(alpha)
        squeeze = p.get("squeeze", 0.78)
        wobble = math.sin((1 - alpha) * math.pi + p.get("seed", 0)) * r * 0.16
        self.canvas.create_oval(x - r * 0.86, y - r * squeeze, x + r * 0.9, y + r * squeeze, fill=color, stipple=stipple, outline="")
        if alpha > 0.34:
            self.canvas.create_oval(x - r * 0.46 + wobble, y - r * 0.42, x + r * 0.52 + wobble, y + r * 0.36, fill="#526176", stipple="gray50", outline="")

    def draw_blast_particle(self, x, y, r, alpha, p):
        color = p.get("color", "#ffd166")
        warm = "#ffd166" if alpha > 0.55 else "#ff7a3d"
        self.canvas.create_oval(x - r * 0.95, y - r * 0.72, x + r * 0.95, y + r * 0.72, outline=color, width=max(1, int(5 * alpha)))
        if alpha > 0.28:
            self.canvas.create_oval(x - r * 0.46, y - r * 0.36, x + r * 0.46, y + r * 0.36, fill=warm, stipple=self.particle_stipple(alpha), outline="")
        if alpha > 0.62:
            self.canvas.create_oval(x - r * 0.18, y - r * 0.16, x + r * 0.18, y + r * 0.16, fill="#fff6cf", outline="")

    def draw_spark_particle(self, x, y, r, alpha, p):
        angle = p.get("angle", 0)
        length = max(6, r * (0.9 + alpha))
        tail = length * (0.45 + 0.7 * alpha)
        color = p.get("color", "#ffd166")
        self.canvas.create_line(
            x - math.cos(angle) * tail,
            y - math.sin(angle) * tail,
            x + math.cos(angle) * length,
            y + math.sin(angle) * length,
            fill=color,
            width=max(1, int(3 * alpha)),
        )

    def draw_texts(self, sx, sy):
        for text in self.texts:
            self.canvas.create_text(sx(text["x"]), sy(text["y"]), text=text["text"], fill=text["color"], font=("Arial", 18, "bold"))

    def draw_hud(self):
        stage = self.stages[self.stage_index]
        self.canvas.create_rectangle(12, 10, WIDTH - 12, 52, fill="#070b12", outline="#223044")
        self.canvas.create_rectangle(14, 12, WIDTH - 14, 50, outline="#101b2a")
        self.canvas.create_text(28, 31, text=stage["name"].upper(), fill=stage["color"], anchor="w", font=("Arial", 11, "bold"))
        self.canvas.create_text(284, 31, text="SCORE {}".format(self.total_score + self.score), fill="#eef5ff", anchor="w", font=("Arial", 10, "bold"))
        self.canvas.create_text(408, 31, text="x{}".format(self.combo), fill="#ffd166", anchor="w", font=("Arial", 10, "bold"))
        self.canvas.create_text(468, 31, text="TARGET {}/{}".format(self.kills, stage["target"]), fill="#9aa6c4", anchor="w", font=("Arial", 10, "bold"))
        self.canvas.create_text(WIDTH - 330, 31, text="ARMOR {}".format(max(0, math.ceil(self.player["hp"]))), fill="#53ff9c", anchor="w", font=("Arial", 10, "bold"))
        self.canvas.create_text(WIDTH - 210, 31, text="TIME {:.1f}".format(max(0, self.time_left)), fill="#eef5ff", anchor="w", font=("Arial", 10, "bold"))
        self.canvas.create_text(WIDTH - 92, 31, text="E x{}".format(self.airstrike_charges), fill="#00e5ff", anchor="w", font=("Arial", 10, "bold"))

        status = "목표 {}/{} · E 지원포격 · 클릭/스페이스 발사 · R 재장전".format(self.kills, stage["target"])
        if self.reload_timer > 0:
            status = "재장전 중 {:.1f}s".format(self.reload_timer)
        if self.emp_timer > 0:
            status = "EMP 간섭: 사격 반응 저하"

        if self.event_message_timer > 0:
            self.canvas.create_rectangle(WIDTH / 2 - 118, 62, WIDTH / 2 + 118, 92, fill="#120b18", outline=stage["color"], width=2)
            self.canvas.create_text(WIDTH / 2, 77, text="EVENT: " + self.event_name, fill="#eef5ff", font=("Arial", 10, "bold"))

        tray_w = 430
        tray_x = WIDTH / 2 - tray_w / 2
        tray_y = HEIGHT - 48
        self.canvas.create_rectangle(tray_x, tray_y, tray_x + tray_w, tray_y + 34, fill="#070b12", outline="#223044")
        self.canvas.create_text(tray_x + 14, tray_y + 17, text="AMMO", fill="#9aa6c4", anchor="w", font=("Arial", 8, "bold"))
        ammo_x = tray_x + 64
        ammo_y = tray_y + 6
        for i in range(self.max_ammo):
            fill = "#ffd166" if i < self.ammo else "#1c2432"
            self.canvas.create_rectangle(ammo_x + i * 12, ammo_y, ammo_x + i * 12 + 8, ammo_y + 22, fill=fill, outline="#39465a")
        self.canvas.create_text(tray_x + 220, tray_y + 17, text=status, fill="#9aa6c4", anchor="w", font=("Arial", 8, "bold"))
        if self.objective:
            remain = max(0, self.objective["time"])
            self.canvas.create_text(tray_x + tray_w - 12, tray_y + 17, text="BONUS {:.1f}s".format(remain), fill="#53ff9c", anchor="e", font=("Arial", 8, "bold"))
        if self.reload_timer > 0:
            progress = 1 - self.reload_timer / self.reload_time
            self.canvas.create_rectangle(ammo_x, tray_y + 28, ammo_x + 12 * self.max_ammo, tray_y + 31, fill="#1c2432", outline="")
            self.canvas.create_rectangle(ammo_x, tray_y + 28, ammo_x + 12 * self.max_ammo * progress, tray_y + 31, fill="#00e5ff", outline="")

    def hud_box(self, x, y, label, value):
        self.canvas.create_rectangle(x, y, x + 102, y + 58, fill="#080d16", outline="#263247")
        self.canvas.create_text(x + 12, y + 17, text=label, fill="#9aa6c4", anchor="w", font=("Arial", 8, "bold"))
        self.canvas.create_text(x + 12, y + 40, text=value, fill="#eef5ff", anchor="w", font=("Arial", 18, "bold"))

    def draw_vignette(self):
        self.canvas.create_rectangle(0, 0, WIDTH, HEIGHT, outline="#000000", width=16)

    def draw_title(self):
        self.draw_menu_background()
        self.canvas.create_text(WIDTH / 2, 108, text="NEON CORE TANK", fill="#eef5ff", font=("Arial", 44, "bold"))
        self.canvas.create_text(WIDTH / 2, 154, text="포탄을 피하고, 이벤트를 이용하고, 전장을 돌파하는 네온 탱크 아케이드", fill="#00e5ff", font=("Arial", 15, "bold"))
        self.canvas.create_text(WIDTH / 2, 198, text="적 전차도 포격합니다. 포격 경고, EMP, 보급, 코어 서지를 읽고 움직이세요.", fill="#9aa6c4", font=("Arial", 12))
        self.draw_menu_tank(WIDTH / 2, 325)
        self.add_button(WIDTH / 2 - 120, 465, 240, 46, "게임 시작", self.start_game)
        self.add_button(WIDTH / 2 - 120, 522, 240, 46, "설정", lambda: self.set_scene("settings"))
        self.add_button(WIDTH / 2 - 120, 579, 240, 46, "게임 방법", lambda: self.set_scene("howto"))
        self.add_button(WIDTH / 2 - 120, 636, 240, 46, "종료", self.root.destroy)
        self.canvas.create_text(WIDTH - 150, HEIGHT - 28, text="HIGH SCORE {}".format(self.high_score), fill="#6f7f9e", font=("Arial", 10, "bold"))

    def draw_settings(self):
        self.draw_menu_background()
        self.canvas.create_text(WIDTH / 2, 120, text="설정", fill="#eef5ff", font=("Arial", 36, "bold"))
        difficulty = ["쉬움", "보통", "어려움"][self.difficulty - 1]
        effect_text = "켜짐" if self.effects else "꺼짐"
        self.canvas.create_text(WIDTH / 2, 214, text="난이도: " + difficulty, fill="#00e5ff", font=("Arial", 18, "bold"))
        self.canvas.create_text(WIDTH / 2, 276, text="화면 효과: " + effect_text, fill="#ffd166", font=("Arial", 15, "bold"))
        self.add_button(WIDTH / 2 - 130, 340, 260, 46, "난이도 변경", self.toggle_difficulty)
        self.add_button(WIDTH / 2 - 130, 400, 260, 46, "효과 표시 전환", self.toggle_effects)
        self.add_button(WIDTH / 2 - 130, 500, 260, 46, "뒤로", lambda: self.set_scene("title"))

    def draw_howto(self):
        self.draw_menu_background()
        self.canvas.create_text(WIDTH / 2, 95, text="게임 방법", fill="#eef5ff", font=("Arial", 36, "bold"))
        lines = [
            "WASD 또는 방향키: 전차 이동",
            "마우스: 포탑 조준",
            "클릭 또는 스페이스: 포탄 발사",
            "E: 획득한 지원 포격을 마우스 위치에 호출",
            "R: 수동 재장전, 탄이 0이면 자동 재장전",
            "Shift: 짧은 대시",
            "적 전차 포탄은 느리지만 강합니다. 멈춰서 맞딜하지 마세요.",
            "EVENT와 BONUS 목표가 전장을 바꿉니다. 보너스 성공 시 지원 포격을 얻습니다.",
            "목표 처치 수를 채우고 남은 적을 정리하면 스테이지 클리어",
            "탄약, 수리, 오버드라이브 아이템으로 전황을 뒤집으세요.",
        ]
        y = 150
        for line in lines:
            self.canvas.create_text(WIDTH / 2, y, text=line, fill="#c5d2ef", font=("Arial", 14))
            y += 38
        self.add_button(WIDTH / 2 - 130, 590, 260, 46, "뒤로", lambda: self.set_scene("title"))

    def draw_stage_clear(self):
        self.draw_modal("STAGE CLEAR", self.stages[self.stage_index]["name"], "#00e5ff")
        self.canvas.create_text(WIDTH / 2, HEIGHT / 2 - 2, text="스테이지 점수 {} · 남은 장갑 {}".format(self.score, max(0, int(self.player["hp"]))), fill="#c5d2ef", font=("Arial", 14))
        label = "최종 결과 보기" if self.stage_index == len(self.stages) - 1 else "다음 스테이지"
        self.add_button(WIDTH / 2 - 140, HEIGHT / 2 + 58, 280, 48, label, self.next_stage)
        self.add_button(WIDTH / 2 - 140, HEIGHT / 2 + 118, 280, 48, "타이틀로", lambda: self.set_scene("title"))

    def draw_game_over(self):
        self.draw_modal("MISSION FAILED", "코어 전차가 파괴되었습니다.", "#ff3b6b")
        self.canvas.create_text(WIDTH / 2, HEIGHT / 2 - 2, text="총점 {} · 스테이지 {}".format(self.total_score + self.score, self.stage_index + 1), fill="#c5d2ef", font=("Arial", 14))
        self.add_button(WIDTH / 2 - 140, HEIGHT / 2 + 58, 280, 48, "다시 시작", self.start_game)
        self.add_button(WIDTH / 2 - 140, HEIGHT / 2 + 118, 280, 48, "타이틀로", lambda: self.set_scene("title"))

    def draw_victory(self):
        self.draw_modal("CAMPAIGN CLEAR", "코어 게이트를 장악했습니다.", "#ffd166")
        self.canvas.create_text(WIDTH / 2, HEIGHT / 2 - 2, text="최종 점수 {} · 최고 점수 {}".format(self.total_score, self.high_score), fill="#c5d2ef", font=("Arial", 14))
        self.add_button(WIDTH / 2 - 140, HEIGHT / 2 + 58, 280, 48, "새 캠페인", self.start_game)
        self.add_button(WIDTH / 2 - 140, HEIGHT / 2 + 118, 280, 48, "타이틀로", lambda: self.set_scene("title"))

    def draw_modal(self, title, subtitle, color):
        self.canvas.create_rectangle(0, 0, WIDTH, HEIGHT, fill="#03050a", stipple="gray50", outline="")
        self.canvas.create_rectangle(WIDTH / 2 - 325, HEIGHT / 2 - 150, WIDTH / 2 + 325, HEIGHT / 2 + 170, fill="#080d16", outline="#2c3a52", width=2)
        self.canvas.create_text(WIDTH / 2, HEIGHT / 2 - 86, text=title, fill=color, font=("Arial", 34, "bold"))
        self.canvas.create_text(WIDTH / 2, HEIGHT / 2 - 40, text=subtitle, fill="#9aa6c4", font=("Arial", 14))

    def draw_menu_background(self):
        title_image = self.asset_images.get("title")
        if title_image:
            self.canvas.create_image(WIDTH / 2, HEIGHT / 2, image=title_image, anchor="center")
            self.canvas.create_rectangle(0, 0, WIDTH, HEIGHT, fill="#03050a", stipple="gray25", outline="")
        else:
            self.canvas.create_rectangle(0, 0, WIDTH, HEIGHT, fill="#03050a", outline="")
            self.canvas.create_oval(-180, -130, 420, 300, fill="#04202a", outline="")
            self.canvas.create_oval(WIDTH - 320, HEIGHT - 260, WIDTH + 220, HEIGHT + 200, fill="#251222", outline="")
        self.canvas.create_rectangle(0, HEIGHT - 160, WIDTH, HEIGHT, fill="#071018", outline="")
        for x in range(90, WIDTH, 220):
            self.canvas.create_rectangle(x, HEIGHT - 145, x + 88, HEIGHT - 126, fill="#0f1c2a", outline="#243044")
        self.canvas.create_text(80, HEIGHT - 38, text="v0.3 THONNY BUILD", fill="#536079", anchor="w", font=("Arial", 9, "bold"))

    def draw_menu_tank(self, x, y):
        fake = {"x": x, "y": y, "r": 52, "hull": -0.18, "turret": -0.45, "color": "#00d9ff", "accent": "#e8fbff", "hit": 0, "invuln": 0}
        self.draw_tank(fake, lambda v: v, lambda v: v, True)
        self.canvas.create_oval(x - 92, y - 92, x + 92, y + 92, outline="#00e5ff", width=2)
        self.canvas.create_text(x, y + 98, text="탄창 관리 + 적 포격 회피 + 전장 이벤트 활용", fill="#9aa6c4", font=("Arial", 11))

    def add_button(self, x, y, w, h, label, action):
        self.canvas.create_rectangle(x + 3, y + 4, x + w + 3, y + h + 4, fill="#02050a", outline="")
        self.canvas.create_rectangle(x, y, x + w, y + h, fill="#0b1320", outline="#2d405a", width=2)
        self.canvas.create_text(x + w / 2, y + h / 2, text=label, fill="#eef5ff", font=("Arial", 14, "bold"))
        self.buttons.append({"rect": (x, y, x + w, y + h), "action": action})

    def set_scene(self, scene):
        self.scene = scene

    def toggle_difficulty(self):
        self.difficulty += 1
        if self.difficulty > 3:
            self.difficulty = 1

    def toggle_effects(self):
        self.effects = not self.effects

    def muzzle_flash(self, angle):
        if not self.effects:
            return
        p = self.player
        self.muzzle_flash_from(p["x"], p["y"], angle, "#ffd166")

    def muzzle_flash_from(self, x, y, angle, color):
        if not self.effects:
            return
        fx = x + math.cos(angle) * 48
        fy = y + math.sin(angle) * 48
        self.particles.append({"x": fx, "y": fy, "vx": 0, "vy": 0, "r": 46, "life": 0.16, "max": 0.16, "color": color, "sprite": "effect-muzzle-flash", "angle": angle})
        for _ in range(4):
            a = angle + random.uniform(-0.42, 0.42)
            speed = random.uniform(100, 280)
            self.particles.append({"x": fx, "y": fy, "vx": math.cos(a) * speed, "vy": math.sin(a) * speed, "r": random.uniform(18, 32), "life": 0.22, "max": 0.22, "color": color, "sprite": "effect-hit-spark", "angle": a})

    def track_dust(self, x, y, angle):
        if not self.effects:
            return
        rear = angle + math.pi
        side = angle + math.pi / 2
        life = random.uniform(0.34, 0.68)
        offset = random.uniform(-14, 14)
        self.particles.append({
            "x": x + math.cos(rear) * 28 + math.cos(side) * offset + random.uniform(-4, 4),
            "y": y + math.sin(rear) * 28 + math.sin(side) * offset + random.uniform(-4, 4),
            "vx": math.cos(rear) * random.uniform(18, 48) + math.cos(side) * random.uniform(-12, 12),
            "vy": math.sin(rear) * random.uniform(18, 48) + math.sin(side) * random.uniform(-12, 12) - random.uniform(4, 18),
            "r": random.uniform(8, 16),
            "life": life,
            "max": life,
            "color": random.choice(["#1c2a38", "#263447", "#344254"]),
            "kind": "smoke",
            "grow": random.uniform(18, 30),
            "drag": 0.94,
            "squeeze": random.uniform(0.62, 0.84),
            "seed": random.random() * TAU,
        })

    def burst(self, x, y, count, color, force):
        if not self.effects:
            return
        blast_life = 0.18 + min(0.16, force * 0.04)
        self.particles.append({
            "x": x,
            "y": y,
            "vx": 0,
            "vy": 0,
            "r": 28 * min(2.3, force),
            "life": blast_life,
            "max": blast_life,
            "color": color,
            "kind": "blast",
            "grow": 115 * min(1.6, force / 2.2),
        })
        for _ in range(max(3, int(count * 0.32))):
            a = random.random() * TAU
            speed = random.uniform(28, 92) * min(1.6, force)
            life = random.uniform(0.48, 0.95)
            self.particles.append({
                "x": x + math.cos(a) * random.uniform(4, 18),
                "y": y + math.sin(a) * random.uniform(4, 18),
                "vx": math.cos(a) * speed,
                "vy": math.sin(a) * speed - random.uniform(12, 34),
                "r": random.uniform(10, 20) * min(1.35, force / 2),
                "life": life,
                "max": life,
                "color": random.choice(["#202c38", "#2c3947", "#3e4b5a"]),
                "kind": "smoke",
                "grow": random.uniform(24, 44),
                "drag": 0.952,
                "squeeze": random.uniform(0.7, 0.95),
                "seed": random.random() * TAU,
            })
        for _ in range(count):
            a = random.random() * TAU
            speed = random.uniform(55, 170) * force
            life = random.uniform(0.28, 0.74)
            self.particles.append({"x": x, "y": y, "vx": math.cos(a) * speed, "vy": math.sin(a) * speed, "r": random.uniform(5, 13), "life": life, "max": life, "color": color, "kind": "spark", "angle": a, "drag": 0.94, "gravity": 140})

    def float_text(self, x, y, text, color):
        self.texts.append({"x": x, "y": y, "text": text, "color": color, "life": 0.9, "max": 0.9})

    def turn_toward(self, current, target, amount):
        diff = (target - current + math.pi) % TAU - math.pi
        return current + clamp(diff, -amount, amount)

    def on_key_down(self, event):
        key = event.keysym.lower()
        self.keys.add(key)
        if key == "escape":
            self.scene = "title"
        if key == "r" and self.scene == "playing":
            self.start_reload()
        if key == "e" and self.scene == "playing":
            self.call_support_strike()
        if key == "space":
            if self.scene == "title":
                self.start_game()
            elif self.scene == "stage_clear":
                self.next_stage()
            elif self.scene == "game_over":
                self.start_game()
            elif self.scene == "playing":
                self.shoot()
        if key in ("shift_l", "shift_r") and self.scene == "playing":
            self.player["dash"] = 0.2

    def on_key_up(self, event):
        self.keys.discard(event.keysym.lower())

    def on_mouse_move(self, event):
        cam_x = clamp(self.player["x"] - WIDTH / 2, 0, WORLD_W - WIDTH)
        cam_y = clamp(self.player["y"] - HEIGHT / 2, 0, WORLD_H - HEIGHT)
        self.mouse["x"] = event.x
        self.mouse["y"] = event.y
        self.mouse["world_x"] = event.x + cam_x
        self.mouse["world_y"] = event.y + cam_y

    def on_mouse_down(self, event):
        self.on_mouse_move(event)
        for button in self.buttons:
            x1, y1, x2, y2 = button["rect"]
            if x1 <= event.x <= x2 and y1 <= event.y <= y2:
                button["action"]()
                return
        if self.scene == "playing":
            self.shoot()

    def loop(self):
        now = time.perf_counter()
        dt = min(0.033, now - self.last_time)
        self.last_time = now
        self.update(dt)
        self.render()
        self.root.after(16, self.loop)


if __name__ == "__main__":
    root = tk.Tk()
    root.geometry(str(WIDTH) + "x" + str(HEIGHT))
    root.resizable(False, False)
    NeonCoreTank(root)
    root.mainloop()
