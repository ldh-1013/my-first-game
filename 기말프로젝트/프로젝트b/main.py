import pygame, sys, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from settings import (SCREEN_WIDTH, SCREEN_HEIGHT, FPS, TITLE, TILE_SIZE,
                      FONT_PATH, palette)
from src.tilemap import load_stage, TileMap
from src.player import Player
from src.hud import HUD
from src.menu import Menu
from src.clear_screen import ClearScreen, compute_stars
from src.save_manager import SaveManager

pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption(TITLE)
clock = pygame.time.Clock()

save_manager = SaveManager()
hud          = HUD()
clear_screen = ClearScreen()

# ── State machine ──────────────────────────────────────────────────────────────
STATE_MENU  = "menu"
STATE_PLAY  = "play"
STATE_CLEAR = "clear"

state = STATE_MENU

current_stage = 1
stage_data = tilemap = player = None
clear_score = 0
clear_stars = 0


def build_main_menu():
    items = [("START", "start")]
    if save_manager.has_progress():
        items.insert(1, ("CONTINUE", "continue"))
    items.append(("QUIT", "quit"))
    return Menu(items)


menu       = build_main_menu()
clear_menu = Menu([("NEXT", "next"), ("RETRY", "retry"), ("MENU", "menu")])


def load_level(n):
    sd     = load_stage(n)
    tm     = TileMap(sd)
    sc, sr = sd["player_start"]
    p      = Player(sc, sr, sd["initial_mode"])
    return sd, tm, p


def enter_play(stage_n):
    global state, current_stage, stage_data, tilemap, player
    current_stage                = stage_n
    stage_data, tilemap, player  = load_level(current_stage)
    save_manager.set_last_stage(current_stage)
    state = STATE_PLAY


def enter_clear():
    global state, clear_score, clear_stars
    clear_score = player.move_count + player.switch_count
    clear_stars = compute_stars(clear_score, stage_data["star_thresholds"])
    save_manager.record_clear(current_stage, clear_stars, clear_score)
    clear_menu.selected = 0
    state = STATE_CLEAR


# ── Main loop ──────────────────────────────────────────────────────────────────
while True:

    # ── Events ────────────────────────────────────────────────────────────────
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        if state == STATE_MENU:
            action = menu.handle_event(event)
            if action == "start":
                enter_play(1)
            elif action == "continue":
                enter_play(save_manager.get_last_stage())
            elif action == "quit":
                pygame.quit()
                sys.exit()

        elif state == STATE_PLAY:
            if event.type == pygame.KEYDOWN:
                moved = False

                if event.key in (pygame.K_UP, pygame.K_w):
                    moved = player.try_move(0, -1, tilemap)
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    moved = player.try_move(0, 1, tilemap)
                elif event.key in (pygame.K_LEFT, pygame.K_a):
                    moved = player.try_move(-1, 0, tilemap)
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    moved = player.try_move(1, 0, tilemap)
                elif event.key == pygame.K_SPACE:
                    player.try_switch(stage_data["switch_limit"])
                elif event.key == pygame.K_r:
                    enter_play(current_stage)
                elif event.key == pygame.K_n:
                    enter_play(min(current_stage + 1, 30))
                elif event.key == pygame.K_ESCAPE:
                    menu = build_main_menu()
                    state = STATE_MENU

                if moved and player.is_at_goal(tilemap):
                    enter_clear()

        elif state == STATE_CLEAR:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                menu = build_main_menu()
                state = STATE_MENU
            else:
                action = clear_menu.handle_event(event)
                if action == "next":
                    if current_stage < 30:
                        enter_play(current_stage + 1)
                    else:
                        menu = build_main_menu()
                        state = STATE_MENU
                elif action == "retry":
                    enter_play(current_stage)
                elif action == "menu":
                    menu = build_main_menu()
                    state = STATE_MENU

    # ── Update ────────────────────────────────────────────────────────────────
    if state == STATE_PLAY:
        tilemap.update_timers()

    # ── Draw ──────────────────────────────────────────────────────────────────
    if state == STATE_MENU:
        menu.draw(screen)

    elif state == STATE_PLAY:
        offset_x = (SCREEN_WIDTH  - tilemap.width  * TILE_SIZE) // 2
        offset_y = hud.bar_height + (
            (SCREEN_HEIGHT - hud.bar_height - tilemap.height * TILE_SIZE) // 2
        )
        pal = palette(player.mode)
        screen.fill(pal["bg"])
        tilemap.render(screen, offset_x, offset_y, player.mode)
        player.render(screen, offset_x, offset_y, player.mode)
        tilemap.render_timer_labels(screen, offset_x, offset_y, player.mode)
        hud.draw(screen, current_stage, player, stage_data["switch_limit"])

    elif state == STATE_CLEAR:
        best_stars, best_score = save_manager.get_best(current_stage)
        clear_screen.draw(screen, current_stage, clear_stars, clear_score,
                          stage_data["star_thresholds"],
                          best_stars=best_stars, best_score=best_score)
        clear_menu.draw(screen, start_y=SCREEN_HEIGHT - 160,
                        draw_bg=False, draw_title=False)

    pygame.display.flip()
    clock.tick(FPS)
