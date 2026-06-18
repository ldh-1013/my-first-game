"""
==========================================================================
  NEON SURVIVOR  -  Ursina 3D 트윈스틱 웨이브 서바이벌 슈터
--------------------------------------------------------------------------
  조작
    WASD        : 이동
    마우스       : 조준
    좌클릭(홀드)  : 사격
    SPACE       : 대시(무적 회피, 쿨다운 1초)
    R           : 게임 오버 후 재시작
    ESC         : 종료

  목표
    끝없이 몰려오는 적을 처치하고 웨이브를 버텨라.
    연속 처치로 콤보 배율을 올려 점수를 극대화하라.
==========================================================================
"""

import random
from ursina import *

app = Ursina(borderless=False)
window.title = 'NEON SURVIVOR'
window.color = color.hsv(250, .5, .06)      # 깊은 인디고 배경
window.fps_counter.enabled = True
mouse.visible = True

# --------------------------------------------------------------------------
# 전역 컨테이너 / 핸들
# --------------------------------------------------------------------------
bullets = []          # 플레이어 총알
enemy_bullets = []    # 적 총알
enemies = []          # 적
pickups = []          # 회복 아이템
player = None         # Player 인스턴스 (뒤에서 생성)
game = None           # GameController 인스턴스 (뒤에서 생성)

ARENA = 14            # 플레이 가능 반경(정사각 ±ARENA)

# --------------------------------------------------------------------------
# 유틸
# --------------------------------------------------------------------------
def flat(v):
    """y성분 제거한 평면 벡터"""
    return Vec3(v.x, 0, v.z)

def length(v):
    return v.length()

def spawn_particles(pos, col, count=8, speed=6, life=0.4, size=0.22):
    """타격/사망/머즐 파티클"""
    for _ in range(count):
        Particle(pos, col, speed, life, size)

def play_sound(name):
    """사운드는 환경에 따라 없을 수 있으니 안전하게 무시"""
    try:
        Audio(name, autoplay=True, loop=False)
    except Exception:
        pass

# --------------------------------------------------------------------------
# 파티클
# --------------------------------------------------------------------------
class Particle(Entity):
    def __init__(self, pos, col, speed, life, size):
        super().__init__(model='cube', color=col, scale=size,
                         position=pos + Vec3(0, 0.3, 0), unlit=True)
        self.velocity = Vec3(random.uniform(-1, 1),
                             random.uniform(0.4, 1.6),
                             random.uniform(-1, 1)).normalized() * (speed * random.uniform(0.5, 1.2))
        self.life = life
        self.rotation = Vec3(random.uniform(0, 360), random.uniform(0, 360), 0)

    def update(self):
        self.position += self.velocity * time.dt
        self.velocity += Vec3(0, -16, 0) * time.dt   # 중력
        self.rotation_y += 400 * time.dt
        f = max(0, 1 - 6 * time.dt)
        self.scale *= f
        self.life -= time.dt
        if self.life <= 0 or self.scale_x < 0.02:
            destroy(self)

# --------------------------------------------------------------------------
# 플레이어 총알
# --------------------------------------------------------------------------
class Bullet(Entity):
    def __init__(self, pos, direction):
        super().__init__(model='sphere', color=color.hsv(55, .3, 1),
                         scale=0.32, position=pos + Vec3(0, 0.4, 0), unlit=True)
        self.dir = direction.normalized()
        self.speed = 24
        self.life = 1.1
        self.damage = 26
        bullets.append(self)

    def update(self):
        self.position += self.dir * self.speed * time.dt
        self.life -= time.dt
        for e in enemies[:]:
            if length(flat(e.world_position - self.world_position)) < (0.45 + e.radius):
                e.take_damage(self.damage, self.dir)
                self._remove()
                return
        if self.life <= 0 or abs(self.x) > ARENA + 3 or abs(self.z) > ARENA + 3:
            self._remove()

    def _remove(self):
        if self in bullets:
            bullets.remove(self)
        destroy(self)

# --------------------------------------------------------------------------
# 적 총알
# --------------------------------------------------------------------------
class EnemyBullet(Entity):
    def __init__(self, pos, direction):
        super().__init__(model='sphere', color=color.hsv(140, .9, 1),
                         scale=0.4, position=pos + Vec3(0, 0.4, 0), unlit=True)
        self.dir = direction.normalized()
        self.speed = 11
        self.life = 3
        self.damage = 12
        enemy_bullets.append(self)

    def update(self):
        if game.state != 'playing':
            return
        self.position += self.dir * self.speed * time.dt
        self.life -= time.dt
        if length(flat(player.world_position - self.world_position)) < 0.8:
            player.take_damage(self.damage)
            self._remove()
            return
        if self.life <= 0 or abs(self.x) > ARENA + 3 or abs(self.z) > ARENA + 3:
            self._remove()

    def _remove(self):
        if self in enemy_bullets:
            enemy_bullets.remove(self)
        destroy(self)

# --------------------------------------------------------------------------
# 적
# --------------------------------------------------------------------------
ENEMY_TYPES = {
    #            model      색상(hsv)            scale  hp   speed dmg  radius pts  ranged
    'chaser':  ('sphere', color.hsv(330, .9, 1),  0.9,  55,  2.6,  10,  0.5,  100, False),
    'fast':    ('cube',   color.hsv(55, .9, 1),   0.55, 26,  4.8,  7,   0.35, 130, False),
    'tank':    ('cube',   color.hsv(15, .9, .95), 1.5,  220, 1.3,  22,  0.95, 280, False),
    'shooter': ('sphere', color.hsv(150, .9, 1),  0.8,  42,  1.9,  0,   0.5,  170, True),
}

class Enemy(Entity):
    def __init__(self, etype, pos, hp_mult=1.0, dmg_mult=1.0):
        m, col, sc, hp, spd, dmg, rad, pts, ranged = ENEMY_TYPES[etype]
        super().__init__(model=m, color=col, scale=sc, position=pos, unlit=True)
        self.etype = etype
        self.base_color = col
        self.max_hp = hp * hp_mult
        self.hp = self.max_hp
        self.speed = spd
        self.dmg = dmg * dmg_mult
        self.radius = rad
        self.points = pts
        self.ranged = ranged
        self.attack_cd = random.uniform(0, 1)
        self.y = 0
        enemies.append(self)
        # 등장 연출
        self.scale_value = sc
        self.scale = sc * 0.1
        self.animate_scale(sc, duration=0.25, curve=curve.out_back)

    def update(self):
        if game.state != 'playing':
            return
        self.attack_cd = max(0, self.attack_cd - time.dt)
        to_player = flat(player.position - self.position)
        dist = length(to_player)
        dirn = to_player.normalized() if dist > 0.001 else Vec3(0, 0, 0)

        if self.ranged:
            # 거리 유지하며 사격
            if dist > 9:
                self.position += dirn * self.speed * time.dt
            elif dist < 6:
                self.position -= dirn * self.speed * time.dt
            if self.attack_cd <= 0 and dist < 16:
                EnemyBullet(self.position, dirn)
                self.attack_cd = 1.6
        else:
            self.position += dirn * self.speed * time.dt
            if dist < (self.radius + 0.6) and self.attack_cd <= 0:
                player.take_damage(self.dmg)
                self.attack_cd = 0.8

        self.x = clamp(self.x, -ARENA - 1, ARENA + 1)
        self.z = clamp(self.z, -ARENA - 1, ARENA + 1)
        self.rotation_y += 90 * time.dt   # 자글자글 회전 (생동감)

    def take_damage(self, amount, knockdir=None):
        self.hp -= amount
        self.color = color.white
        invoke(setattr, self, 'color', self.base_color, delay=0.06)
        if knockdir is not None:
            self.position += flat(knockdir).normalized() * 0.35
        spawn_particles(self.position, self.base_color, count=4, speed=5, life=0.25)
        if self.hp <= 0:
            self.die()

    def die(self):
        spawn_particles(self.position, self.base_color, count=14, speed=9, life=0.5, size=0.28)
        game.on_enemy_killed(self)
        if self in enemies:
            enemies.remove(self)
        if random.random() < 0.13:
            HealthPickup(self.position)
        destroy(self)

# --------------------------------------------------------------------------
# 회복 아이템
# --------------------------------------------------------------------------
class HealthPickup(Entity):
    def __init__(self, pos):
        super().__init__(model='cube', color=color.hsv(120, .8, 1),
                         scale=0.5, position=Vec3(pos.x, 0.3, pos.z), unlit=True)
        self.cross = Entity(parent=self, model='cube', color=color.white,
                            scale=(1.6, 0.4, 0.4), unlit=True)
        self.heal = 25
        self.life = 12
        pickups.append(self)

    def update(self):
        if game.state != 'playing':
            return
        self.rotation_y += 120 * time.dt
        self.y = 0.3 + math.sin(time.time() * 4) * 0.12
        self.life -= time.dt
        if length(flat(player.position - self.position)) < 0.9:
            player.health = min(player.max_health, player.health + self.heal)
            spawn_particles(self.position, color.hsv(120, .8, 1), count=10, speed=6)
            self._remove()
            return
        if self.life <= 0:
            self._remove()

    def _remove(self):
        if self in pickups:
            pickups.remove(self)
        destroy(self)

# --------------------------------------------------------------------------
# 플레이어
# --------------------------------------------------------------------------
class Player(Entity):
    def __init__(self):
        super().__init__(model='cube', color=color.hsv(190, .8, 1),
                         scale=0.9, position=(0, 0, 0), unlit=True)
        self.gun = Entity(parent=self, model='cube', color=color.hsv(190, .2, 1),
                          scale=(0.28, 0.28, 1.2), z=0.75, unlit=True)
        self.glow = Entity(parent=self, model='sphere', color=color.hsv(190, .6, 1),
                           scale=1.6, alpha=0.12, unlit=True)
        self.speed = 7.5
        self.max_health = 100
        self.health = 100
        self.fire_rate = 0.12
        self.fire_cd = 0
        self.dash_cd = 0
        self.dashing = 0
        self.dash_dir = Vec3(0, 0, 1)
        self.invuln = 0
        self.aim = Vec3(0, 0, 1)

    def update(self):
        if game.state == 'game_over':
            return
        self.fire_cd = max(0, self.fire_cd - time.dt)
        self.dash_cd = max(0, self.dash_cd - time.dt)
        self.invuln = max(0, self.invuln - time.dt)

        # --- 조준 ---
        wp = mouse.world_point
        if wp is not None:
            d = flat(wp - self.position)
            if length(d) > 0.2:
                self.aim = d.normalized()
        self.look_at(self.position + self.aim)

        if game.state != 'playing':
            return

        # --- 이동 ---
        move = Vec3(0, 0, 0)
        if held_keys['w']: move.z += 1
        if held_keys['s']: move.z -= 1
        if held_keys['d']: move.x += 1
        if held_keys['a']: move.x -= 1
        if length(move) > 0:
            move = move.normalized()

        spd = self.speed
        if self.dashing > 0:
            self.dashing -= time.dt
            spd = self.speed * 3.6
            move = self.dash_dir
            # 대시 잔상
            if random.random() < 0.7:
                ghost = Entity(model='cube', color=color.hsv(190, .8, 1),
                               scale=0.9, position=self.position, alpha=0.4, unlit=True)
                ghost.animate_scale(0.1, duration=0.25)
                ghost.fade_out(duration=0.25)
                destroy(ghost, delay=0.3)

        newpos = self.position + move * spd * time.dt
        newpos.x = clamp(newpos.x, -ARENA, ARENA)
        newpos.z = clamp(newpos.z, -ARENA, ARENA)
        self.position = newpos

        # 무적 깜빡임
        self.glow.alpha = 0.4 if self.invuln > 0 else 0.12

        # --- 사격(홀드) ---
        if mouse.left and self.fire_cd <= 0 and self.dashing <= 0:
            self.shoot()

    def shoot(self):
        self.fire_cd = self.fire_rate
        muzzle = self.position + self.aim * 0.9 + Vec3(0, 0.4, 0)
        Bullet(self.position, self.aim)
        spawn_particles(muzzle, color.hsv(55, .3, 1), count=2, speed=4, life=0.12, size=0.15)
        game.shake(0.05, 0.1)
        play_sound('shoot')

    def input(self, key):
        if key == 'space' and self.dash_cd <= 0 and self.dashing <= 0 and game.state == 'playing':
            d = Vec3(0, 0, 0)
            if held_keys['w']: d.z += 1
            if held_keys['s']: d.z -= 1
            if held_keys['d']: d.x += 1
            if held_keys['a']: d.x -= 1
            self.dash_dir = d.normalized() if length(d) > 0 else self.aim
            self.dashing = 0.18
            self.dash_cd = 1.0
            self.invuln = 0.35

    def take_damage(self, amount):
        if self.invuln > 0 or self.dashing > 0:
            return
        self.health -= amount
        self.invuln = 0.6
        game.shake(0.18, 0.45)
        game.flash_damage()
        if self.health <= 0:
            self.health = 0
            game.game_over()

# --------------------------------------------------------------------------
# 게임 컨트롤러 (상태 / 웨이브 / 카메라 / UI)
# --------------------------------------------------------------------------
class GameController(Entity):
    def __init__(self):
        super().__init__()
        self.state = 'playing'
        self.wave = 0
        self.score = 0
        self.combo = 0
        self.combo_timer = 0
        self.enemies_to_spawn = 0
        self.spawn_timer = 0
        self.break_timer = 0

        # 카메라
        camera.rotation_x = 70
        self.cam_offset = Vec3(0, 25, -9)
        self.cam_base = Vec3(0, 25, -9)
        self.shake_t = 0
        self.shake_mag = 0

        # ---------------- UI ----------------
        self.hp_bg = Entity(parent=camera.ui, model='quad', color=color.hsv(0, 0, .2),
                            scale=(0.42, 0.045), position=(-0.84, 0.46), origin=(-0.5, 0))
        self.hp_fill = Entity(parent=camera.ui, model='quad', color=color.hsv(120, .8, .9),
                              scale=(0.42, 0.045), position=(-0.84, 0.46), origin=(-0.5, 0))
        self.hp_label = Text(parent=camera.ui, text='HP', position=(-0.84, 0.495),
                             scale=0.8, color=color.white)

        self.dash_bg = Entity(parent=camera.ui, model='quad', color=color.hsv(0, 0, .2),
                              scale=(0.42, 0.02), position=(-0.84, 0.42), origin=(-0.5, 0))
        self.dash_fill = Entity(parent=camera.ui, model='quad', color=color.hsv(190, .8, 1),
                                scale=(0.42, 0.02), position=(-0.84, 0.42), origin=(-0.5, 0))

        self.score_text = Text(parent=camera.ui, text='SCORE 0', position=(0, 0.47),
                               origin=(0, 0), scale=1.4, color=color.white)
        self.wave_text = Text(parent=camera.ui, text='WAVE 1', position=(0.78, 0.46),
                              origin=(0, 0), scale=1.3, color=color.hsv(55, .8, 1))
        self.combo_text = Text(parent=camera.ui, text='', position=(0, 0.33),
                               origin=(0, 0), scale=1.8, color=color.hsv(330, .8, 1))
        self.announce_text = Text(parent=camera.ui, text='', position=(0, 0.05),
                                  origin=(0, 0), scale=4, color=color.white)
        self.hint_text = Text(parent=camera.ui,
                              text='WASD 이동   |   마우스 조준 + 좌클릭 사격   |   SPACE 대시',
                              position=(0, -0.47), origin=(0, 0), scale=0.8,
                              color=color.hsv(0, 0, .7))

        # 화면 데미지 플래시 / 저체력 비네트
        self.flash = Entity(parent=camera.ui, model='quad',
                            color=color.color(0, .9, .9, 0), scale=(2.2, 1.3))
        self.vignette = Entity(parent=camera.ui, model='quad',
                               color=color.color(0, .9, .9, 0), scale=(2.2, 1.3))

        # 게임 오버 오버레이
        self.over_bg = Entity(parent=camera.ui, model='quad',
                              color=color.color(0, 0, 0, 0.75), scale=(2.2, 1.3), enabled=False)
        self.over_title = Text(parent=camera.ui, text='GAME OVER', position=(0, 0.18),
                               origin=(0, 0), scale=4, color=color.hsv(330, .9, 1), enabled=False)
        self.over_stats = Text(parent=camera.ui, text='', position=(0, -0.02),
                               origin=(0, 0), scale=1.6, color=color.white, enabled=False)
        self.over_hint = Text(parent=camera.ui, text='R 키를 눌러 다시 시작', position=(0, -0.18),
                              origin=(0, 0), scale=1.2, color=color.hsv(55, .8, 1), enabled=False)

        # 월드 조준 십자선
        self.crosshair = Entity(model='quad', color=color.hsv(55, .3, 1),
                                scale=0.7, rotation_x=90, alpha=0.6, unlit=True)
        self.crosshair_inner = Entity(parent=self.crosshair, model='quad',
                                      color=color.hsv(190, .6, 1), scale=0.45, alpha=0.7, unlit=True)

    # ---------------- 메인 루프 ----------------
    def update(self):
        self.update_camera()
        self.update_crosshair()

        if self.state == 'playing':
            self.combo_timer = max(0, self.combo_timer - time.dt)
            if self.combo_timer <= 0:
                self.combo = 0

            if self.enemies_to_spawn > 0:
                self.spawn_timer -= time.dt
                if self.spawn_timer <= 0:
                    self.spawn_one()
                    self.spawn_timer = max(0.25, 1.1 - self.wave * 0.04)
            elif len(enemies) == 0:
                self.start_break()

        elif self.state == 'wave_break':
            self.break_timer -= time.dt
            if self.break_timer <= 0:
                self.start_wave(self.wave + 1)

        self.update_ui()

    def update_camera(self):
        desired = Vec3(player.x, 0, player.z) + self.cam_offset
        self.cam_base = lerp(self.cam_base, desired, min(1, 8 * time.dt))
        off = Vec3(0, 0, 0)
        if self.shake_t > 0:
            self.shake_t -= time.dt
            m = self.shake_mag
            off = Vec3(random.uniform(-m, m), random.uniform(-m, m), random.uniform(-m, m))
        camera.position = self.cam_base + off

    def update_crosshair(self):
        wp = mouse.world_point
        if wp is not None:
            self.crosshair.enabled = True
            self.crosshair.position = Vec3(wp.x, 0.05, wp.z)
            self.crosshair.rotation_y += 120 * time.dt
        else:
            self.crosshair.enabled = False

    def update_ui(self):
        # 체력바
        frac = max(0, player.health / player.max_health)
        self.hp_fill.scale_x = 0.42 * frac
        self.hp_fill.color = color.hsv(120 * frac, .8, .9)
        # 대시 쿨다운
        dfrac = 1 - (player.dash_cd / 1.0)
        self.dash_fill.scale_x = 0.42 * clamp(dfrac, 0, 1)
        self.dash_fill.color = color.hsv(190, .8, 1) if dfrac >= 1 else color.hsv(0, 0, .5)
        # 점수 / 웨이브
        self.score_text.text = f'SCORE {self.score:,}'
        self.wave_text.text = f'WAVE {self.wave}'
        # 콤보
        if self.combo > 1:
            self.combo_text.text = f'COMBO x{self.combo}'
            self.combo_text.scale = 1.6 + min(self.combo, 20) * 0.04
        else:
            self.combo_text.text = ''
        # 저체력 비네트
        if frac < 0.35 and self.state == 'playing':
            pulse = 0.18 + math.sin(time.time() * 6) * 0.08
            self.vignette.color = color.color(0, .9, .9, pulse * (1 - frac))
        else:
            self.vignette.color = color.color(0, .9, .9, 0)
        # 데미지 플래시 페이드
        a = self.flash.color.a
        if a > 0:
            self.flash.color = color.color(0, .9, .9, max(0, a - 2 * time.dt))

    # ---------------- 웨이브 ----------------
    def start_wave(self, n):
        self.wave = n
        self.enemies_to_spawn = 4 + n * 2
        self.spawn_timer = 0.4
        self.state = 'playing'
        self.announce(f'WAVE {n}', color.hsv(55, .8, 1))

    def start_break(self):
        self.state = 'wave_break'
        self.break_timer = 3.0
        bonus = self.wave * 50
        self.score += bonus
        self.announce(f'WAVE {self.wave} CLEAR!  +{bonus}', color.hsv(120, .8, 1))

    def spawn_one(self):
        self.enemies_to_spawn -= 1
        w = self.wave
        roll = random.random()
        if w >= 3 and roll < 0.15:
            t = 'tank'
        elif w >= 2 and roll < 0.38:
            t = 'shooter'
        elif roll < 0.68:
            t = 'chaser'
        else:
            t = 'fast'
        hp_mult = 1 + (w - 1) * 0.16
        dmg_mult = 1 + (w - 1) * 0.10
        Enemy(t, self.random_edge_pos(), hp_mult, dmg_mult)

    def random_edge_pos(self):
        edge = random.choice(['n', 's', 'e', 'w'])
        r = ARENA - 0.5
        if edge == 'n':
            return Vec3(random.uniform(-r, r), 0, r)
        if edge == 's':
            return Vec3(random.uniform(-r, r), 0, -r)
        if edge == 'e':
            return Vec3(r, 0, random.uniform(-r, r))
        return Vec3(-r, 0, random.uniform(-r, r))

    # ---------------- 이벤트 ----------------
    def on_enemy_killed(self, enemy):
        self.combo += 1
        self.combo_timer = 3.0
        mult = 1 + (self.combo - 1) // 5   # 5콤보마다 배율 +1
        self.score += enemy.points * mult
        self.shake(0.06, 0.12)

    def shake(self, dur, mag):
        self.shake_t = max(self.shake_t, dur)
        self.shake_mag = max(self.shake_mag, mag)

    def flash_damage(self):
        self.flash.color = color.color(0, .9, .9, 0.5)

    def announce(self, msg, col=color.white):
        self.announce_text.text = msg
        self.announce_text.color = col
        self.announce_text.scale = 5
        self.announce_text.animate_scale(4, duration=0.3, curve=curve.out_back)
        invoke(self.clear_announce, msg, delay=1.8)

    def clear_announce(self, msg):
        if self.announce_text.text == msg:
            self.announce_text.text = ''

    def game_over(self):
        self.state = 'game_over'
        self.over_bg.enabled = True
        self.over_title.enabled = True
        self.over_stats.enabled = True
        self.over_hint.enabled = True
        self.over_stats.text = f'WAVE {self.wave}  도달   |   SCORE {self.score:,}'

    # ---------------- 재시작 ----------------
    def start_game(self):
        for lst in (bullets, enemy_bullets, enemies, pickups):
            for e in lst[:]:
                destroy(e)
            lst.clear()
        player.health = player.max_health
        player.position = Vec3(0, 0, 0)
        player.invuln = 0
        player.dashing = 0
        player.dash_cd = 0
        self.score = 0
        self.combo = 0
        self.combo_timer = 0
        self.over_bg.enabled = False
        self.over_title.enabled = False
        self.over_stats.enabled = False
        self.over_hint.enabled = False
        self.start_wave(1)

# --------------------------------------------------------------------------
# 아레나 (바닥 + 벽 + 그리드)
# --------------------------------------------------------------------------
ground = Entity(model='plane', color=color.hsv(250, .35, .14),
                scale=ARENA * 2 + 4, position=(0, 0, 0), collider='box')

# 네온 테두리 벽
wall_col = color.hsv(190, .7, .8)
wall_h = 1.0
for (px, pz, sx, sz) in [(0, ARENA + 1, ARENA * 2 + 2, 0.3),
                         (0, -ARENA - 1, ARENA * 2 + 2, 0.3),
                         (ARENA + 1, 0, 0.3, ARENA * 2 + 2),
                         (-ARENA - 1, 0, 0.3, ARENA * 2 + 2)]:
    Entity(model='cube', color=wall_col, unlit=True,
           scale=(sx, wall_h, sz), position=(px, wall_h / 2 - 0.5, pz))

# 바닥 그리드 라인 (분위기)
for i in range(-ARENA, ARENA + 1, 2):
    Entity(model='cube', color=color.hsv(250, .3, .22), unlit=True,
           scale=(ARENA * 2, 0.02, 0.04), position=(0, -0.48, i))
    Entity(model='cube', color=color.hsv(250, .3, .22), unlit=True,
           scale=(0.04, 0.02, ARENA * 2), position=(i, -0.48, 0))

# --------------------------------------------------------------------------
# 인스턴스 생성 & 전역 입력
# --------------------------------------------------------------------------
player = Player()
game = GameController()
game.start_wave(1)

def input(key):
    if key == 'r' and game.state == 'game_over':
        game.start_game()

app.run()