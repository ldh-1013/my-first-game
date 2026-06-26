# -*- coding: utf-8 -*-
"""
한밤의관 — 새벽 1시
메인 진입점. 씬 관리 및 게임 루프.
"""

import sys
import pygame

from settings import (
    INTERNAL_W, INTERNAL_H, FPS,
    SCENE_TITLE, SCENE_GAME, SCENE_PAUSE,
    SCENE_GAMEOVER, SCENE_ENDING_A,
    BLACK, WHITE, GOLD, GOLD2, RED, DIM, BRIGHT, PANEL,
    FONT_EXTRABOLD, FONT_REGULAR, FONT_CHOSUN,
)
from asset_loader    import AssetLoader
from sound_manager   import SoundManager
from room            import Room
from room_data       import ROOMS
from player          import Player
from darkness_system import DarknessSystem
from inventory       import Inventory
from ui              import UI

# ── 추가 씬 상수 (settings.py에 없는 타이틀 전용 씬) ──
SCENE_HOWTO           = "HOWTO"
SCENE_SETTINGS_SCREEN = "SETTINGS_SCREEN"

# ─────────────────────────────────────────────────────────
#  전역 객체
# ─────────────────────────────────────────────────────────
loader  = None
sound   = None
screen  = None
game_sf = None
clock   = None

current_scene = SCENE_TITLE
debug_mode    = False

# ── 타이틀 씬 상태 ──────────────────────────────────────
title_state = {
    "menu_idx":   0,
    "bg":         None,
    "logo":       None,
    "font_title": None,
    "font_menu":  None,
    "font_sub":   None,
}
TITLE_MENU = ["게임 시작", "플레이 방법", "설  정", "게임 종료"]

# ── 게임 씬 상태 ─────────────────────────────────────────
game_state = {
    "room":             None,
    "player":           None,
    "darkness":         None,
    "inventory":        None,
    "ui":               None,
    "game_time":        0.0,
    "flags":            {},
    "interact_prompt": None,
    "msg":       "",       # 화면 피드백 메시지 텍스트
    "msg_timer": 0.0,      # 남은 표시 시간(초)
    "msg_type":  "info",   # "info" | "success" | "error"
}

# ─────────────────────────────────────────────────────────
#  렌더링 유틸
# ─────────────────────────────────────────────────────────
def blit_scaled(dst, src):
    sw, sh = dst.get_size()
    scale  = min(sw / INTERNAL_W, sh / INTERNAL_H)
    dw     = int(INTERNAL_W * scale)
    dh     = int(INTERNAL_H * scale)
    ox     = (sw - dw) // 2
    oy     = (sh - dh) // 2
    scaled = pygame.transform.scale(src, (dw, dh))
    dst.fill(BLACK)
    dst.blit(scaled, (ox, oy))

# ─────────────────────────────────────────────────────────
#  타이틀 씬
# ─────────────────────────────────────────────────────────
def title_init():
    ts = title_state
    ts["bg"]         = loader.load_bg("backgrounds/bg_mainlibrary_title.png")
    ts["font_title"] = loader.load_font(FONT_CHOSUN,   64)
    ts["font_menu"]  = loader.load_font(FONT_REGULAR,  30)
    ts["font_sub"]   = loader.load_font(FONT_REGULAR,  18)
    ts["menu_idx"]   = 0

    # ── 로고: 원본 비율 유지하며 가로 560px로 스케일 ──
    raw    = loader.load_image("title/title_logo.png")   # size=None → 원본
    ow, oh = raw.get_size()
    tw     = 560
    th     = int(oh * tw / ow) if ow > 0 else 160
    ts["logo"] = pygame.transform.scale(raw, (tw, th))

    sound.play_bgm("sounds/bgm/bgm_title.ogg")


def title_handle_event(event):
    global current_scene
    ts  = title_state

    if event.type == pygame.KEYDOWN:
        if event.key in (pygame.K_UP, pygame.K_w):
            ts["menu_idx"] = (ts["menu_idx"] - 1) % len(TITLE_MENU)
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            ts["menu_idx"] = (ts["menu_idx"] + 1) % len(TITLE_MENU)
        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
            _title_select(ts["menu_idx"])

    elif event.type == pygame.MOUSEMOTION:
        mx = event.pos[0] * INTERNAL_W / screen.get_width()
        my = event.pos[1] * INTERNAL_H / screen.get_height()
        for i, r in enumerate(_title_menu_rects()):
            if r.collidepoint(mx, my):
                ts["menu_idx"] = i

    elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        _title_select(ts["menu_idx"])


def _title_select(idx):
    global current_scene
    if idx == 0:
        game_init("mainhall_1f")
        current_scene = SCENE_GAME
    elif idx == 1:
        current_scene = SCENE_HOWTO
    elif idx == 2:
        current_scene = SCENE_SETTINGS_SCREEN
    elif idx == 3:
        pygame.quit()
        sys.exit()


def _title_menu_rects():
    rects = []
    base_y = 470
    for i in range(len(TITLE_MENU)):
        rects.append(pygame.Rect(INTERNAL_W // 2 - 150, base_y + i * 52, 300, 42))
    return rects


def title_update(dt):
    pass  # 글리치 타이머 등 Phase 4에서 추가


def title_draw(surface):
    ts = title_state

    # 배경
    surface.blit(ts["bg"], (0, 0))

    # 로고 (비율 유지된 이미지)
    logo = ts["logo"]
    lx   = (INTERNAL_W - logo.get_width()) // 2
    surface.blit(logo, (lx, 60))

    # 부제
    sub = ts["font_sub"].render("ABANDONED LIBRARY  —  새벽 1시", True, GOLD)
    surface.blit(sub, ((INTERNAL_W - sub.get_width()) // 2, 395))

    # 메뉴
    rects = _title_menu_rects()
    for i, (label, r) in enumerate(zip(TITLE_MENU, rects)):
        selected = (i == ts["menu_idx"])

        if selected:
            bg_s = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
            bg_s.fill((200, 169, 110, 38))
            surface.blit(bg_s, r.topleft)
            pygame.draw.rect(surface, GOLD, r, 1)

        color = GOLD2 if selected else DIM
        txt   = ts["font_menu"].render(label, True, color)
        surface.blit(txt, (r.centerx - txt.get_width() // 2,
                           r.centery - txt.get_height() // 2))

    # 시계
    ct = ts["font_sub"].render("01:00 AM", True, RED)
    surface.blit(ct, (INTERNAL_W - ct.get_width() - 20, 16))

    # 조작 힌트
    hint = ts["font_sub"].render("↑ ↓  이동    ENTER  선택", True, (50, 60, 75))
    surface.blit(hint, ((INTERNAL_W - hint.get_width()) // 2, INTERNAL_H - 30))

# ─────────────────────────────────────────────────────────
#  플레이 방법 씬
# ─────────────────────────────────────────────────────────
def howto_handle_event(event):
    global current_scene
    if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
        current_scene = SCENE_TITLE


def howto_draw(surface):
    surface.fill((10, 12, 18))
    font_title = title_state["font_menu"]
    font_body  = title_state["font_sub"]

    t = font_title.render("플 레 이 방 법", True, GOLD)
    surface.blit(t, ((INTERNAL_W - t.get_width()) // 2, 70))

    lines = [
        ("이동",     "WASD / 방향키"),
        ("달리기",   "Shift + 이동"),
        ("상호작용", "E  —  아이템 줍기 / 문 열기 / 조사"),
        ("숨기",     "E  —  은신처 근처에서"),
        ("라이터",   "F  —  켜기 / 끄기"),
        ("일시정지", "ESC"),
        ("디버그",   "F9  —  충돌 영역 표시"),
    ]
    y = 160
    for label, key in lines:
        surface.blit(font_body.render(label, True, DIM),    (300, y))
        surface.blit(font_body.render(key,   True, BRIGHT), (500, y))
        y += 42

    hint = font_body.render("ESC  →  돌아가기", True, (50, 60, 75))
    surface.blit(hint, ((INTERNAL_W - hint.get_width()) // 2, INTERNAL_H - 40))

# ─────────────────────────────────────────────────────────
#  설정 씬 (Phase 4에서 완성)
# ─────────────────────────────────────────────────────────
def settings_handle_event(event):
    global current_scene
    if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
        current_scene = SCENE_TITLE


def settings_draw(surface):
    surface.fill((10, 12, 18))
    font_title = title_state["font_menu"]
    font_body  = title_state["font_sub"]

    t = font_title.render("설  정", True, GOLD)
    surface.blit(t, ((INTERNAL_W - t.get_width()) // 2, 200))

    b = font_body.render("추후 구현 예정입니다.", True, DIM)
    surface.blit(b, ((INTERNAL_W - b.get_width()) // 2, 290))

    hint = font_body.render("ESC  →  돌아가기", True, (50, 60, 75))
    surface.blit(hint, ((INTERNAL_W - hint.get_width()) // 2, INTERNAL_H - 40))

# ─────────────────────────────────────────────────────────
#  게임 씬
# ─────────────────────────────────────────────────────────
def game_init(room_id, player_pos=None):
    gs = game_state
    gs["room"]              = Room(room_id, loader)
    gs["inventory"]         = Inventory()
    gs["darkness"]          = DarknessSystem()
    gs["ui"]                = UI(loader)
    gs["game_time"]         = 0.0
    gs["flags"]             = {}
    gs["interact_prompt"] = None
    gs["msg"]             = ""
    gs["msg_timer"]       = 0.0
    gs["msg_type"]        = "info"

    start = player_pos or ROOMS[room_id].get("player_start", (640, 400))
    gs["player"] = Player(start, loader)

    _preload_sfx()

    music = gs["room"].music
    if music:
        sound.play_bgm(music)


def _preload_sfx():
    sound.preload_sfx("footstep_L",         "sounds/sfx/sfx_footstep_tile_L.wav")
    sound.preload_sfx("footstep_R",         "sounds/sfx/sfx_footstep_tile_R.wav")
    sound.preload_sfx("lighter_ignite",     "sounds/sfx/sfx_lighter_ignite.wav")
    sound.preload_sfx("lighter_open",       "sounds/sfx/sfx_lighter_open.wav")
    sound.preload_sfx("lighter_extinguish", "sounds/sfx/sfx_lighter_extinguish.wav")
    sound.preload_sfx("door_locked",        "sounds/sfx/sfx_door_locked.wav")
    sound.preload_sfx("door_open",          "sounds/sfx/sfx_door_open.wav")
    sound.preload_sfx("item_pickup",        "sounds/sfx/sfx_item_pickup.wav")
    sound.preload_sfx("note_open",          "sounds/sfx/sfx_note_open.wav")


def game_handle_event(event):
    global current_scene, debug_mode
    gs = game_state

    if event.type == pygame.KEYDOWN:
        if event.key == pygame.K_ESCAPE:
            current_scene = SCENE_PAUSE
            sound.pause_bgm()
            return
        if event.key == pygame.K_F9:
            debug_mode = not debug_mode
            return

    result = gs["player"].handle_event(event, gs["room"], gs["inventory"], sound)
    if result:
        _handle_player_action(result)


def _handle_player_action(result):
    gs     = game_state
    action = result.get("action")

    if action == "door":
        door = result["door"]
        req  = door.get("requires_key")
        if req and not gs["inventory"].has(req):
            sound.play_sfx("door_locked")
            key_hints = {
                "item_key_archive": "자료실 열쇠가 필요합니다.",
                "item_key_study":   "학습 공간 열쇠가 필요합니다.",
                "item_key_exit":    "출구 열쇠가 필요합니다.",
            }
            gs["msg"]       = "🔒  " + key_hints.get(req, "열쇠가 필요합니다.")
            gs["msg_timer"] = 2.0
            gs["msg_type"]  = "error"
        else:
            sound.play_sfx("door_open")
            _transition_to_room(door["target"], door["target_pos"])

    elif action == "interact":
        obj = result.get("obj")
        if not obj:
            return
        obj_action = obj.get("action")

        if obj_action == "pickup":
            item_id = obj.get("item_id", "")
            if gs["inventory"].has(item_id):
                gs["msg"]       = "이미 가지고 있습니다."
                gs["msg_timer"] = 1.5
                gs["msg_type"]  = "info"
            elif gs["inventory"].is_full():
                gs["msg"]       = "인벤토리가 가득 찼습니다."
                gs["msg_timer"] = 1.5
                gs["msg_type"]  = "error"
            else:
                gs["inventory"].add(item_id)
                sound.play_sfx("item_pickup")
                gs["room"].remove_interactable(obj)
                gs["msg"]       = "✔  " + obj.get("label", "아이템") + " 획득!"
                gs["msg_timer"] = 1.8
                gs["msg_type"]  = "success"

        elif obj_action == "read_note":
            sound.play_sfx("note_open")
            gs["msg"]       = obj.get("text", "")
            gs["msg_timer"] = 4.0
            gs["msg_type"]  = "info"

        elif obj_action == "examine":
            gs["msg"]       = obj.get("text", "조사한다.")
            gs["msg_timer"] = 3.0
            gs["msg_type"]  = "info"


def _transition_to_room(target_id, target_pos):
    gs = game_state
    gs["room"]            = Room(target_id, loader)
    gs["player"].rect.center = target_pos
    music = gs["room"].music
    if music:
        sound.play_bgm(music)


def game_update(dt):
    gs = game_state
    gs["game_time"] += dt

    # 메시지 타이머 감소
    if gs["msg_timer"] > 0:
        gs["msg_timer"] -= dt
        if gs["msg_timer"] <= 0:
            gs["msg"]      = ""
            gs["msg_type"] = "info"

    keys = pygame.key.get_pressed()
    gs["player"].update(keys, gs["room"], dt, sound)

    pos  = gs["player"].pos
    room = gs["room"]
    prompt = None

    door, door_dist = room.nearest_door(pos)
    if door and door_dist <= room.DOOR_RADIUS:
        req = door.get("requires_key")
        if req and not gs["inventory"].has(req):
            prompt = "[E] 문 열기  🔒"
        else:
            prompt = "[E] 문 열기"

    hide, hide_dist = room.nearest_hide_spot(pos)
    if hide and hide_dist <= room.INTERACT_RADIUS:
        prompt = "[E] 나오기" if gs["player"].is_hiding else "[E] 숨기"

    obj = room.get_interactable_at(pos)
    if obj:
        prompt = obj.get("prompt", "[E] 조사")

    gs["interact_prompt"] = prompt


def game_draw(surface):
    gs   = game_state
    p    = gs["player"]
    ui   = gs["ui"]
    room = gs["room"]

    room.draw(surface)
    p.draw(surface)
    gs["darkness"].render(surface, p.pos, p.lighter_on, p.oil)
    ui.draw(surface, gs["game_time"], p, gs["inventory"], room.room_id)

    if gs["interact_prompt"]:
        ui.draw_interact_prompt(surface, gs["interact_prompt"])

    if gs["msg"]:
        ui.draw_message(surface, gs["msg"], gs["msg_type"])

    if debug_mode:
        room.draw_debug(surface)

# ─────────────────────────────────────────────────────────
#  일시정지 씬
# ─────────────────────────────────────────────────────────
def pause_handle_event(event):
    global current_scene
    if event.type == pygame.KEYDOWN:
        if event.key == pygame.K_ESCAPE:
            current_scene = SCENE_GAME
            sound.resume_bgm()
        elif event.key == pygame.K_q:
            pygame.quit()
            sys.exit()


def pause_draw(surface):
    game_draw(surface)
    game_state["ui"].draw_pause_overlay(surface)

# ─────────────────────────────────────────────────────────
#  초기화 & 메인 루프
# ─────────────────────────────────────────────────────────
def init():
    global loader, sound, screen, game_sf, clock
    pygame.init()
    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

    screen  = pygame.display.set_mode((INTERNAL_W, INTERNAL_H))
    pygame.display.set_caption("한밤의관 — 새벽 1시")

    game_sf = pygame.Surface((INTERNAL_W, INTERNAL_H))
    clock   = pygame.time.Clock()
    loader  = AssetLoader()
    sound   = SoundManager()

    title_init()


def main():
    global current_scene
    init()

    running = True
    while running:
        dt = min(clock.tick(FPS) / 1000.0, 0.05)

        # ── 이벤트 ────────────────────────────────────────
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                break

            if current_scene == SCENE_TITLE:
                title_handle_event(event)
            elif current_scene == SCENE_GAME:
                game_handle_event(event)
            elif current_scene == SCENE_PAUSE:
                pause_handle_event(event)
            elif current_scene == SCENE_HOWTO:
                howto_handle_event(event)
            elif current_scene == SCENE_SETTINGS_SCREEN:
                settings_handle_event(event)

        # ── 업데이트 ──────────────────────────────────────
        if current_scene == SCENE_GAME:
            game_update(dt)
        elif current_scene == SCENE_TITLE:
            title_update(dt)

        # ── 렌더 ─────────────────────────────────────────
        game_sf.fill(BLACK)

        if current_scene == SCENE_TITLE:
            title_draw(game_sf)
        elif current_scene == SCENE_GAME:
            game_draw(game_sf)
        elif current_scene == SCENE_PAUSE:
            pause_draw(game_sf)
        elif current_scene == SCENE_HOWTO:
            howto_draw(game_sf)
        elif current_scene == SCENE_SETTINGS_SCREEN:
            settings_draw(game_sf)

        blit_scaled(screen, game_sf)
        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
