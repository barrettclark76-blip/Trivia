import pygame
import sys
import math
import random
import pyrebase

# --- Firebase Configuration ---
# REPLACE THESE with your actual Firebase project credentials
config = {
    "apiKey": "AIzaSyD2gatwKx8VILOxCJoQ2ebAJ8zCceMy918",
    "authDomain": "triviality-7817d.firebaseapp.com",
    "databaseURL": "https://triviality-7817d-default-rtdb.firebaseio.com",
    "storageBucket": "triviality-7817d.firebasestorage.app"
}

firebase = pyrebase.initialize_app(config)
db = firebase.database()

# --- Configuration & Constants ---
WIDTH, HEIGHT = 900, 600
FPS = 60
BG_COLOR = pygame.Color("#2C3E50")
CARD_COLOR = pygame.Color("#34495E")
TEXT_COLOR = pygame.Color("#FFFFFF")
ACCENT_COLOR = pygame.Color("#1ABC9C")
WHEEL_COLORS = [pygame.Color("#E74C3C"), pygame.Color("#3498DB"), pygame.Color("#9B59B6"), 
                pygame.Color("#F1C40F"), pygame.Color("#E67E22"), pygame.Color("#95A5A6")]
CATEGORIES = ["Sports", "Geography", "History", "Art", "Gen. Knowledge", "Mystery"]

class Button:
    def __init__(self, x, y, w, h, text, color):
        self.rect = pygame.Rect(x, y, w, h)
        self.text, self.color = text, color
    def draw(self, screen, font):
        pygame.draw.rect(screen, self.color, self.rect, border_radius=8)
        txt = font.render(self.text, True, TEXT_COLOR)
        screen.blit(txt, txt.get_rect(center=self.rect.center))
    def is_clicked(self, pos):
        return self.rect.collidepoint(pos)

def create_wheel_surface(radius):
    surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
    slice_angle = 360 / len(CATEGORIES)
    for i in range(len(CATEGORIES)):
        pts = [(radius, radius)]
        for a in range(int(i*slice_angle), int((i+1)*slice_angle) + 1):
            rad = math.radians(a)
            pts.append((radius + radius*math.cos(rad), radius + radius*math.sin(rad)))
        pygame.draw.polygon(surf, WHEEL_COLORS[i], pts)
    return surf

def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()
    
    # Fonts
    font = pygame.font.SysFont("Verdana", 30, bold=True)
    small_font = pygame.font.SysFont("Verdana", 18)

    # --- State Variables ---
    game_state = "MENU"
    room_id = ""
    nickname = ""
    is_private = False
    active_input = "nickname"
    
    # Wheel/Game vars
    wheel_angle = 0
    spin_speed = 0
    current_category = ""
    my_score = 0
    opponent_score = 0
    question_count = 1

    # Buttons
    start_btn = Button(350, 480, 200, 60, "START", ACCENT_COLOR)

    running = True
    while running:
        current_time = pygame.time.get_ticks()
        screen.fill(BG_COLOR)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            if game_state == "MENU":
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if 250 < event.pos[0] < 650:
                        if 180 < event.pos[1] < 230: active_input = "nickname"
                        elif 380 < event.pos[1] < 430: active_input = "room_id"
                    if start_btn.is_clicked(event.pos) and nickname:
                        # FIREBASE LOGIC: Create or Join Room
                        room_id = room_id if room_id else str(random.randint(1000, 9999))
                        db.child("rooms").child(room_id).child("players").update({nickname: 0})
                        game_state = "LOBBY"

                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_BACKSPACE:
                        if active_input == "nickname": nickname = nickname[:-1]
                        else: room_id = room_id[:-1]
                    else:
                        if event.unicode.isalnum():
                            if active_input == "nickname" and len(nickname) < 10: nickname += event.unicode
                            elif active_input == "room_id" and len(room_id) < 6: room_id += event.unicode

            elif game_state == "LOBBY":
                # In a real game, you'd check Firebase here to see if Player 2 joined
                # For this debugged demo, we'll press SPACE to simulate a match start
                if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                    game_state = "SPIN_WAIT"

            elif game_state == "SPIN_WAIT":
                if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                    spin_speed = random.uniform(20, 35)
                    game_state = "SPINNING"

        # --- Logic & Rendering ---
        if game_state == "MENU":
            screen.blit(font.render("QUIZ DUEL", True, TEXT_COLOR), (350, 50))
            # Nickname
            pygame.draw.rect(screen, CARD_COLOR if active_input != "nickname" else ACCENT_COLOR, (250, 180, 400, 50), 2)
            screen.blit(small_font.render(f"Nickname: {nickname}", True, TEXT_COLOR), (260, 195))
            # Room ID
            pygame.draw.rect(screen, CARD_COLOR if active_input != "room_id" else ACCENT_COLOR, (250, 380, 400, 50), 2)
            screen.blit(small_font.render(f"Room ID (Leave blank for random): {room_id}", True, TEXT_COLOR), (260, 395))
            start_btn.draw(screen, font)

        elif game_state == "LOBBY":
            screen.blit(font.render(f"Room: {room_id}", True, TEXT_COLOR), (350, 200))
            screen.blit(small_font.render("Waiting for Opponent... (Press SPACE to Mock Start)", True, TEXT_COLOR), (280, 300))

        elif game_state in ["SPIN_WAIT", "SPINNING"]:
            if game_state == "SPINNING":
                wheel_angle += spin_speed
                spin_speed *= 0.98
                if spin_speed < 0.1:
                    idx = int((360 - ((wheel_angle + 90) % 360)) // 60) % 6
                    current_category = CATEGORIES[idx]
                    game_state = "QUESTION"
            
            # Draw Wheel
            wheel_surf = create_wheel_surface(150)
            rot_wheel = pygame.transform.rotate(wheel_surf, wheel_angle)
            screen.blit(rot_wheel, rot_wheel.get_rect(center=(WIDTH//2, HEIGHT//2)))
            pygame.draw.polygon(screen, TEXT_COLOR, [(WIDTH//2, 190), (WIDTH//2-15, 160), (WIDTH//2+15, 160)])
            screen.blit(font.render("SPIN THE WHEEL", True, TEXT_COLOR), (310, 80))

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()

if __name__ == "__main__":
    main()