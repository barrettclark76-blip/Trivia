import math
import random
import re
import sys
import time
from pathlib import Path

import pygame
import pyrebase

# --- Firebase Configuration ---
# REPLACE THESE with your actual Firebase project credentials
config = {
    "apiKey": "AIzaSyD2gatwKx8VILOxCJoQ2ebAJ8zCceMy918",
    "authDomain": "triviality-7817d.firebaseapp.com",
    "databaseURL": "https://triviality-7817d-default-rtdb.firebaseio.com",
    "storageBucket": "triviality-7817d.firebasestorage.app",
}

firebase = pyrebase.initialize_app(config)
db = firebase.database()

# --- Configuration & Constants ---
WIDTH, HEIGHT = 1000, 680
FPS = 60
POLL_INTERVAL_MS = 400
TOTAL_QUESTIONS = 10

# Modern dark palette
BG_TOP = pygame.Color("#0F172A")
BG_BOTTOM = pygame.Color("#111827")
CARD_COLOR = pygame.Color("#1F2937")
CARD_ALT = pygame.Color("#253143")
TEXT_PRIMARY = pygame.Color("#E5E7EB")
TEXT_MUTED = pygame.Color("#9CA3AF")
ACCENT = pygame.Color("#22D3EE")
SUCCESS = pygame.Color("#34D399")
DANGER = pygame.Color("#FB7185")
WARNING = pygame.Color("#F59E0B")

CATEGORIES = ["Sports", "Geography", "Arts", "Science", "History", "General Knowledge"]
CATEGORY_ICONS = {
    "Sports": "⚽",
    "Geography": "🗺",
    "Arts": "🎨",
    "Science": "🔬",
    "History": "🏛",
    "General Knowledge": "🧠",
}
WHEEL_COLORS = [
    pygame.Color("#E76F51"),
    pygame.Color("#2A9D8F"),
    pygame.Color("#9B5DE5"),
    pygame.Color("#F4A261"),
    pygame.Color("#577590"),
    pygame.Color("#43AA8B"),
]

# Fallback bank, used when raw text files are missing/unreadable.
FALLBACK_QUESTION_BANK = {
    "Sports": [
        {"question": "How many players are on a basketball team on court at one time?", "answer": "5"},
    ],
    "Geography": [{"question": "What is the capital of Japan?", "answer": "tokyo"}],
    "Arts": [{"question": "Who painted the Mona Lisa?", "answer": "leonardo da vinci"}],
    "Science": [{"question": "What planet is known as the Red Planet?", "answer": "mars"}],
    "History": [{"question": "In what year did World War II end?", "answer": "1945"}],
    "General Knowledge": [{"question": "How many days are there in a leap year?", "answer": "366"}],
}


class Button:
    def __init__(self, x, y, w, h, text, color=ACCENT):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.color = color

    def draw(self, screen, font, enabled=True):
        color = self.color if enabled else pygame.Color("#475569")
        pygame.draw.rect(screen, color, self.rect, border_radius=10)
        label = font.render(self.text, True, TEXT_PRIMARY)
        screen.blit(label, label.get_rect(center=self.rect.center))

    def is_clicked(self, pos):
        return self.rect.collidepoint(pos)


class InputBox:
    def __init__(self, x, y, w, h, placeholder=""):
        self.rect = pygame.Rect(x, y, w, h)
        self.placeholder = placeholder
        self.text = ""
        self.active = False

    def handle_event(self, event, max_len=120):
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(event.pos)
        if event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.key == pygame.K_RETURN:
                return "submit"
            elif event.unicode and event.unicode.isprintable() and len(self.text) < max_len:
                self.text += event.unicode
        return None

    def draw(self, screen, font):
        border = ACCENT if self.active else pygame.Color("#334155")
        pygame.draw.rect(screen, CARD_ALT, self.rect, border_radius=10)
        pygame.draw.rect(screen, border, self.rect, 2, border_radius=10)
        shown = self.text if self.text else self.placeholder
        color = TEXT_PRIMARY if self.text else TEXT_MUTED
        txt = font.render(shown, True, color)
        screen.blit(txt, (self.rect.x + 12, self.rect.y + 10))

    def clear(self):
        self.text = ""


def normalize_answer(text):
    return " ".join((text or "").strip().lower().split())


def normalize_category_from_filename(filename):
    stem = Path(filename).stem
    cleaned = stem.replace("_", " ").replace("-", " ").strip().lower()
    aliases = {
        "art": "Arts",
        "arts": "Arts",
        "sport": "Sports",
        "sports": "Sports",
        "science": "Science",
        "history": "History",
        "geography": "Geography",
        "general knowledge": "General Knowledge",
        "generalknowledge": "General Knowledge",
        "gk": "General Knowledge",
        "general": "General Knowledge",
    }
    if cleaned in aliases:
        return aliases[cleaned]
    title = " ".join([w.capitalize() for w in cleaned.split()])
    return title if title in CATEGORIES else None


def parse_question_bank_file(path):
    raw = Path(path).read_text(encoding="utf-8", errors="ignore")
    raw = raw.replace("\\n", "\n")
    blocks = [b.strip() for b in re.split(r"(?=\#Q\s)", raw) if b.strip()]
    parsed = []

    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines:
            continue

        question = ""
        answer = ""

        for idx, line in enumerate(lines):
            if line.startswith("#Q"):
                question = line[2:].strip()
                if not question and idx + 1 < len(lines):
                    question = lines[idx + 1]
            elif line.startswith("^"):
                answer = line[1:].strip()

        if not question:
            continue

        # If answer wasn't on ^ line, try to find prefixed option e.g. ^ OXO / C OXO
        if not answer:
            for line in lines:
                if line.startswith("^"):
                    answer = line[1:].strip()
                    break

        if question and answer:
            parsed.append({"question": question, "answer": normalize_answer(answer)})

    return parsed


def load_question_bank(base_dir="."):
    bank = {cat: [] for cat in CATEGORIES}
    for txt_path in Path(base_dir).glob("*.txt"):
        category = normalize_category_from_filename(txt_path.name)
        if not category:
            continue
        try:
            questions = parse_question_bank_file(txt_path)
            bank[category].extend(questions)
        except Exception:
            continue

    for category in CATEGORIES:
        if not bank[category]:
            bank[category] = FALLBACK_QUESTION_BANK.get(category, []).copy()
    return bank


QUESTION_BANK = load_question_bank(Path(__file__).parent)


def get_players(room):
    return room.get("players", {}) if room else {}


def get_scores(players):
    scores = {}
    for name, info in players.items():
        if isinstance(info, dict):
            scores[name] = int(info.get("score", 0))
        else:
            scores[name] = int(info or 0)
    return scores


def ensure_player(room_id, nickname):
    room = db.child("rooms").child(room_id).get().val() or {}
    players = get_players(room)
    if nickname not in players:
        db.child("rooms").child(room_id).child("players").child(nickname).set(
            {"score": 0, "joined_at": time.time()}
        )


def create_wheel_surface(radius, small_font, icon_font):
    surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
    slice_angle = 360 / len(CATEGORIES)
    center = radius

    for i, category in enumerate(CATEGORIES):
        points = [(center, center)]
        for ang in range(int(i * slice_angle), int((i + 1) * slice_angle) + 1):
            rad = math.radians(ang)
            points.append((center + radius * math.cos(rad), center + radius * math.sin(rad)))
        pygame.draw.polygon(surf, WHEEL_COLORS[i], points)

        label_angle = math.radians((i + 0.5) * slice_angle)
        icon_r = radius * 0.58
        text_r = radius * 0.75

        icon_x = center + icon_r * math.cos(label_angle)
        icon_y = center + icon_r * math.sin(label_angle)
        text_x = center + text_r * math.cos(label_angle)
        text_y = center + text_r * math.sin(label_angle)

        icon = icon_font.render(CATEGORY_ICONS.get(category, "•"), True, TEXT_PRIMARY)
        text = small_font.render(category, True, TEXT_PRIMARY)

        surf.blit(icon, icon.get_rect(center=(icon_x, icon_y)))
        surf.blit(text, text.get_rect(center=(text_x, text_y)))

    return surf


def phase_from_elapsed(round_data, elapsed):
    durations = round_data.get("durations", {})
    spin = float(durations.get("spin", 4))
    reveal = float(durations.get("reveal", 1.2))
    count = float(durations.get("countdown", 3))
    answer = float(durations.get("answer", 30))
    feedback = float(durations.get("feedback", 3))
    leaderboard = float(durations.get("leaderboard", 4))

    if elapsed < spin:
        return "spinning", spin - elapsed
    if elapsed < spin + reveal:
        return "category_reveal", spin + reveal - elapsed
    if elapsed < spin + reveal + count:
        return "countdown", spin + reveal + count - elapsed
    if elapsed < spin + reveal + count + answer:
        return "answer", spin + reveal + count + answer - elapsed
    if elapsed < spin + reveal + count + answer + feedback:
        return "feedback", spin + reveal + count + answer + feedback - elapsed
    if elapsed < spin + reveal + count + answer + feedback + leaderboard:
        return "leaderboard", spin + reveal + count + answer + feedback + leaderboard - elapsed
    return "round_done", 0


def start_new_round(room_id, question_index):
    category = random.choice(CATEGORIES)
    options = QUESTION_BANK.get(category, FALLBACK_QUESTION_BANK[category])
    question = random.choice(options)

    payload = {
        "question_index": int(question_index),
        "category": category,
        "question": question["question"],
        "answer": normalize_answer(question["answer"]),
        "phase_start": time.time(),
        "wheel_start_angle": random.uniform(0, 360),
        "wheel_rotation": random.uniform(1300, 1900),
        "all_answered_at": 0,
        "durations": {
            "spin": 4.0,
            "reveal": 1.2,
            "countdown": 3.0,
            "answer": 30.0,
            "feedback": 3.0,
            "leaderboard": 4.0,
        },
    }

    db.child("rooms").child(room_id).child("game").update(
        {
            "status": "running",
            "round": payload,
            "score_applied_round": -1,
            "updated_at": time.time(),
        }
    )


def host_start_game(room_id):
    room = db.child("rooms").child(room_id).get().val() or {}
    players = get_players(room)
    for p in players:
        db.child("rooms").child(room_id).child("players").child(p).child("score").set(0)

    db.child("rooms").child(room_id).child("answers").set({})
    db.child("rooms").child(room_id).child("game").set(
        {
            "host": room.get("game", {}).get("host", ""),
            "status": "running",
            "started_at": time.time(),
            "finished_at": 0,
            "score_applied_round": -1,
        }
    )
    start_new_round(room_id, 0)


def submit_answer(room_id, nickname, round_idx, answer_text):
    db.child("rooms").child(room_id).child("answers").child(str(round_idx)).child(nickname).set(
        {"answer": answer_text, "submitted_at": time.time()}
    )


def maybe_shorten_answer_phase(room_id, room):
    game = room.get("game", {})
    round_data = game.get("round", {})
    if not round_data:
        return

    all_answered_at = float(round_data.get("all_answered_at", 0) or 0)
    if all_answered_at > 0:
        return

    round_idx = int(round_data.get("question_index", -1))
    answers = db.child("rooms").child(room_id).child("answers").child(str(round_idx)).get().val() or {}
    players = get_players(room)
    if not players:
        return

    all_answered = all(p in answers and normalize_answer((answers[p] or {}).get("answer", "")) != "" for p in players)
    if not all_answered:
        return

    phase_start = float(round_data.get("phase_start", time.time()))
    durations = round_data.get("durations", {})
    elapsed = time.time() - phase_start
    pre_answer = float(durations.get("spin", 4)) + float(durations.get("reveal", 1.2)) + float(
        durations.get("countdown", 3)
    )
    elapsed_answer = max(0.5, elapsed - pre_answer)
    short_answer = min(float(durations.get("answer", 30)), elapsed_answer + 1.5)

    db.child("rooms").child(room_id).child("game").child("round").update(
        {"all_answered_at": time.time(), "durations": {**durations, "answer": short_answer}}
    )


def apply_round_scoring(room_id, room):
    game = room.get("game", {})
    round_data = game.get("round", {})
    if not round_data:
        return

    round_idx = int(round_data.get("question_index", -1))
    if int(game.get("score_applied_round", -1)) == round_idx:
        return

    correct = normalize_answer(round_data.get("answer", ""))
    players = get_players(room)
    answers = db.child("rooms").child(room_id).child("answers").child(str(round_idx)).get().val() or {}

    for player in players:
        submitted = normalize_answer((answers.get(player) or {}).get("answer", ""))
        if not submitted:
            delta = -2
        elif submitted == correct:
            delta = 5
        else:
            delta = -5

        score_ref = db.child("rooms").child(room_id).child("players").child(player).child("score")
        current = int(score_ref.get().val() or 0)
        score_ref.set(current + delta)

    db.child("rooms").child(room_id).child("game").child("score_applied_round").set(round_idx)


def draw_gradient_bg(screen):
    for y in range(HEIGHT):
        t = y / HEIGHT
        color = (
            int(BG_TOP.r + (BG_BOTTOM.r - BG_TOP.r) * t),
            int(BG_TOP.g + (BG_BOTTOM.g - BG_TOP.g) * t),
            int(BG_TOP.b + (BG_BOTTOM.b - BG_TOP.b) * t),
        )
        pygame.draw.line(screen, color, (0, y), (WIDTH, y))


def render_wrapped_text(screen, font, text, color, rect, line_spacing=6):
    words = text.split()
    lines = []
    line = ""
    for word in words:
        trial = f"{line} {word}".strip()
        if font.size(trial)[0] <= rect.width:
            line = trial
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)

    y = rect.y
    for ln in lines:
        surf = font.render(ln, True, color)
        screen.blit(surf, (rect.x, y))
        y += surf.get_height() + line_spacing


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Multiplayer Trivia")
    clock = pygame.time.Clock()

    title_font = pygame.font.SysFont("Segoe UI", 34, bold=True)
    section_font = pygame.font.SysFont("Segoe UI", 24, bold=True)
    body_font = pygame.font.SysFont("Segoe UI", 18)
    small_font = pygame.font.SysFont("Segoe UI", 15)
    icon_font = pygame.font.SysFont("Segoe UI Emoji", 18)

    menu_nick = InputBox(340, 210, 320, 42, "Nickname")
    menu_room = InputBox(340, 270, 320, 42, "Room ID (blank = create random)")
    answer_box = InputBox(120, 532, 700, 42, "Type your answer and press Enter")

    join_btn = Button(420, 340, 160, 46, "JOIN LOBBY")
    start_btn = Button(405, 552, 190, 48, "START GAME")
    submit_btn = Button(835, 532, 90, 42, "SEND")

    wheel_surface = create_wheel_surface(185, small_font, icon_font)

    state = "MENU"
    room_id = ""
    nickname = ""
    is_host = False
    status_message = ""
    local_feedback = ""
    submitted_round = -1
    room_data = {}
    last_poll = 0

    running = True
    while running:
        now = time.time()
        now_ms = pygame.time.get_ticks()

        if state in {"LOBBY", "GAME"} and room_id and now_ms - last_poll >= POLL_INTERVAL_MS:
            room_data = db.child("rooms").child(room_id).get().val() or {}
            game_status = room_data.get("game", {}).get("status", "lobby")
            is_host = room_data.get("game", {}).get("host") == nickname

            if state == "LOBBY" and game_status in {"running", "finished"}:
                state = "GAME"
                submitted_round = -1
                local_feedback = ""
            elif state == "GAME" and game_status == "lobby":
                # Only return to lobby when server state explicitly says so.
                state = "LOBBY"
                submitted_round = -1
                local_feedback = ""

            last_poll = now_ms

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if state == "MENU":
                menu_nick.handle_event(event, max_len=16)
                menu_room.handle_event(event, max_len=10)
                if event.type == pygame.MOUSEBUTTONDOWN and join_btn.is_clicked(event.pos):
                    nickname = menu_nick.text.strip()
                    room_id = menu_room.text.strip() or str(random.randint(1000, 9999))
                    if not nickname:
                        status_message = "Nickname required"
                        continue

                    room = db.child("rooms").child(room_id).get().val()
                    if not room:
                        db.child("rooms").child(room_id).set(
                            {
                                "players": {nickname: {"score": 0, "joined_at": now}},
                                "game": {
                                    "host": nickname,
                                    "status": "lobby",
                                    "started_at": 0,
                                    "finished_at": 0,
                                    "score_applied_round": -1,
                                    "round": {},
                                },
                            }
                        )
                        is_host = True
                    else:
                        ensure_player(room_id, nickname)
                    room_data = db.child("rooms").child(room_id).get().val() or {}
                    state = "LOBBY"
                    status_message = ""

            elif state == "LOBBY":
                if event.type == pygame.MOUSEBUTTONDOWN and start_btn.is_clicked(event.pos):
                    players = get_players(room_data)
                    if is_host and len(players) >= 2:
                        host_start_game(room_id)
                        state = "GAME"
                        submitted_round = -1
                        local_feedback = ""
                        answer_box.clear()

            elif state == "GAME":
                action = answer_box.handle_event(event)
                if event.type == pygame.MOUSEBUTTONDOWN and submit_btn.is_clicked(event.pos):
                    action = "submit"

                game = room_data.get("game", {})
                round_data = game.get("round", {})
                if action == "submit" and round_data:
                    elapsed = now - float(round_data.get("phase_start", now))
                    phase, _ = phase_from_elapsed(round_data, elapsed)
                    round_idx = int(round_data.get("question_index", -1))
                    if phase == "answer" and submitted_round != round_idx:
                        submit_answer(room_id, nickname, round_idx, answer_box.text.strip())
                        submitted_round = round_idx
                        local_feedback = "Answer sent"

        draw_gradient_bg(screen)

        if state == "MENU":
            screen.blit(title_font.render("MULTIPLAYER TRIVIA", True, TEXT_PRIMARY), (330, 120))
            menu_nick.draw(screen, body_font)
            menu_room.draw(screen, body_font)
            join_btn.draw(screen, body_font)
            if status_message:
                screen.blit(small_font.render(status_message, True, DANGER), (430, 405))

        elif state == "LOBBY":
            players = get_players(room_data)
            is_host = room_data.get("game", {}).get("host") == nickname
            can_start = is_host and len(players) >= 2

            pygame.draw.rect(screen, CARD_COLOR, (60, 70, 880, 540), border_radius=14)
            screen.blit(title_font.render(f"Lobby #{room_id}", True, TEXT_PRIMARY), (90, 95))
            role = "Host" if is_host else "Player"
            screen.blit(body_font.render(f"You: {nickname} ({role})", True, TEXT_MUTED), (90, 145))
            screen.blit(body_font.render(f"Players: {len(players)}", True, TEXT_MUTED), (90, 172))

            y = 225
            for player in sorted(players.keys()):
                score = int((players[player] or {}).get("score", 0)) if isinstance(players[player], dict) else int(players[player])
                screen.blit(body_font.render(f"• {player}   {score} pts", True, TEXT_PRIMARY), (100, y))
                y += 34

            start_btn.draw(screen, body_font, enabled=can_start)
            helper = "Host can start once at least 2 players have joined."
            screen.blit(small_font.render(helper, True, TEXT_MUTED), (360, 612))
            if not is_host:
                screen.blit(body_font.render("Waiting for host to start…", True, WARNING), (360, 553))

        elif state == "GAME":
            game = room_data.get("game", {})
            round_data = game.get("round", {})
            players = get_players(room_data)
            scores = get_scores(players)

            if not round_data:
                screen.blit(body_font.render("Waiting for host to initialize round…", True, WARNING), (360, 320))
            else:
                round_idx = int(round_data.get("question_index", 0))
                elapsed = now - float(round_data.get("phase_start", now))
                phase, time_left = phase_from_elapsed(round_data, elapsed)

                if is_host and phase == "answer":
                    maybe_shorten_answer_phase(room_id, room_data)

                if is_host and phase == "feedback":
                    apply_round_scoring(room_id, room_data)

                # Always refresh live scores to avoid stale leaderboard.
                if now_ms % 3 == 0:
                    room_data = db.child("rooms").child(room_id).get().val() or room_data
                    players = get_players(room_data)
                    scores = get_scores(players)
                    game = room_data.get("game", game)
                    round_data = game.get("round", round_data)
                    round_idx = int(round_data.get("question_index", round_idx))

                if is_host and phase == "round_done":
                    next_q = round_idx + 1
                    if next_q < TOTAL_QUESTIONS:
                        start_new_round(room_id, next_q)
                        room_data = db.child("rooms").child(room_id).get().val() or {}
                        submitted_round = -1
                        local_feedback = ""
                        answer_box.clear()
                        continue
                    db.child("rooms").child(room_id).child("game").update(
                        {"status": "finished", "finished_at": time.time()}
                    )

                status = room_data.get("game", {}).get("status", "running")
                if status == "finished":
                    ranking = sorted(scores.items(), key=lambda x: x[1], reverse=True)
                    pygame.draw.rect(screen, CARD_COLOR, (120, 80, 760, 520), border_radius=14)
                    screen.blit(title_font.render("Final Standings", True, TEXT_PRIMARY), (385, 120))
                    y = 210
                    for i, (player, score) in enumerate(ranking, start=1):
                        screen.blit(section_font.render(f"{i}. {player} — {score}", True, TEXT_PRIMARY), (320, y))
                        y += 48
                    screen.blit(small_font.render("Returning to lobby…", True, TEXT_MUTED), (450, 560))
                    finished_at = float(room_data.get("game", {}).get("finished_at", now))
                    if is_host and now - finished_at > 6:
                        db.child("rooms").child(room_id).child("game").update(
                            {"status": "lobby", "round": {}, "score_applied_round": -1}
                        )
                    pygame.display.flip()
                    clock.tick(FPS)
                    continue

                category = round_data.get("category", "")
                question = round_data.get("question", "")
                answer_key = normalize_answer(round_data.get("answer", ""))
                all_answered_at = float(round_data.get("all_answered_at", 0) or 0)

                # Header
                screen.blit(body_font.render(f"Question {round_idx + 1}/{TOTAL_QUESTIONS}", True, TEXT_PRIMARY), (40, 25))
                screen.blit(body_font.render(f"Category: {category}", True, ACCENT), (40, 52))

                pygame.draw.rect(screen, CARD_COLOR, (40, 88, 690, 500), border_radius=14)
                pygame.draw.rect(screen, CARD_ALT, (755, 88, 205, 500), border_radius=14)
                screen.blit(section_font.render("Leaderboard", True, TEXT_PRIMARY), (785, 110))
                y = 152
                for i, (player, score) in enumerate(sorted(scores.items(), key=lambda x: x[1], reverse=True), start=1):
                    screen.blit(small_font.render(f"{i}. {player}", True, TEXT_PRIMARY), (770, y))
                    screen.blit(small_font.render(str(score), True, ACCENT), (930, y))
                    y += 28

                if phase == "spinning":
                    progress = max(0, min(1, elapsed / float(round_data.get("durations", {}).get("spin", 4))))
                    eased = 1 - pow(1 - progress, 3)
                    angle = float(round_data.get("wheel_start_angle", 0)) + float(round_data.get("wheel_rotation", 0)) * eased
                    rw = pygame.transform.rotozoom(wheel_surface, angle, 1)
                    screen.blit(rw, rw.get_rect(center=(385, 330)))
                    pygame.draw.polygon(screen, TEXT_PRIMARY, [(385, 122), (373, 97), (397, 97)])
                    screen.blit(section_font.render("Spinning…", True, TEXT_PRIMARY), (320, 120))

                elif phase == "category_reveal":
                    screen.blit(section_font.render("Category selected", True, TEXT_PRIMARY), (280, 190))
                    icon = CATEGORY_ICONS.get(category, "•")
                    screen.blit(title_font.render(f"{icon}  {category}", True, ACCENT), (250, 250))

                elif phase == "countdown":
                    count = max(1, int(math.ceil(time_left)))
                    screen.blit(section_font.render(f"Get Ready: {count}", True, TEXT_PRIMARY), (300, 240))

                elif phase in {"answer", "feedback", "leaderboard"}:
                    render_wrapped_text(screen, section_font, question, TEXT_PRIMARY, pygame.Rect(72, 130, 625, 180))

                    if phase == "answer":
                        time_text = f"Time left: {int(math.ceil(time_left))}s"
                        screen.blit(body_font.render(time_text, True, WARNING), (72, 330))
                        if all_answered_at > 0:
                            screen.blit(body_font.render("Answers are in!", True, SUCCESS), (72, 356))
                        answer_box.draw(screen, body_font)
                        submit_btn.draw(screen, small_font, enabled=submitted_round != round_idx)
                        if local_feedback:
                            screen.blit(small_font.render(local_feedback, True, TEXT_MUTED), (122, 580))

                    elif phase == "feedback":
                        answers = db.child("rooms").child(room_id).child("answers").child(str(round_idx)).get().val() or {}
                        mine = normalize_answer((answers.get(nickname) or {}).get("answer", ""))
                        if not mine:
                            msg, color = "No answer submitted (-2)", DANGER
                        elif mine == answer_key:
                            msg, color = "Correct! (+5)", SUCCESS
                        else:
                            msg, color = "Incorrect (-5)", DANGER
                        screen.blit(section_font.render(msg, True, color), (72, 360))
                        screen.blit(body_font.render(f"Correct answer: {answer_key}", True, TEXT_MUTED), (72, 402))

                    else:
                        screen.blit(section_font.render("Leaderboard updated", True, TEXT_PRIMARY), (72, 360))

                # fallback safe render state
                elif phase == "round_done":
                    screen.blit(body_font.render("Loading next question…", True, TEXT_MUTED), (72, 360))

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
