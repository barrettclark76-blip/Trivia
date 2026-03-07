import math
import random
import sys
import time

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
BG_COLOR = pygame.Color("#2C3E50")
CARD_COLOR = pygame.Color("#34495E")
TEXT_COLOR = pygame.Color("#FFFFFF")
ACCENT_COLOR = pygame.Color("#1ABC9C")
ERROR_COLOR = pygame.Color("#E74C3C")
INFO_COLOR = pygame.Color("#F1C40F")

WHEEL_COLORS = [
    pygame.Color("#E74C3C"),
    pygame.Color("#3498DB"),
    pygame.Color("#9B59B6"),
    pygame.Color("#F1C40F"),
    pygame.Color("#E67E22"),
    pygame.Color("#95A5A6"),
]

CATEGORIES = ["Sports", "Geography", "Arts", "Science", "History", "General Knowledge"]
TOTAL_QUESTIONS = 10
POLL_INTERVAL_MS = 500

# --- Placeholder question bank ---
# Replace this with loading from your own JSON file.
# Example structure expected:
# {
#   "Sports": [{"question": "...", "answer": "..."}, ...],
#   ...
# }
QUESTION_BANK = {
    "Sports": [
        {"question": "How many players are on a basketball team on court at one time?", "answer": "5"},
        {"question": "Which country won the 2018 FIFA World Cup?", "answer": "france"},
    ],
    "Geography": [
        {"question": "What is the capital of Japan?", "answer": "tokyo"},
        {"question": "Which river is the longest in the world?", "answer": "nile"},
    ],
    "Arts": [
        {"question": "Who painted the Mona Lisa?", "answer": "leonardo da vinci"},
        {"question": "How many strings does a standard violin have?", "answer": "4"},
    ],
    "Science": [
        {"question": "What planet is known as the Red Planet?", "answer": "mars"},
        {"question": "What gas do plants absorb from the atmosphere?", "answer": "carbon dioxide"},
    ],
    "History": [
        {"question": "In what year did World War II end?", "answer": "1945"},
        {"question": "Who was the first President of the United States?", "answer": "george washington"},
    ],
    "General Knowledge": [
        {"question": "How many days are there in a leap year?", "answer": "366"},
        {"question": "What is the largest ocean on Earth?", "answer": "pacific"},
    ],
}


class Button:
    def __init__(self, x, y, w, h, text, color=ACCENT_COLOR):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.color = color

    def draw(self, screen, font, enabled=True):
        draw_color = self.color if enabled else pygame.Color("#566573")
        pygame.draw.rect(screen, draw_color, self.rect, border_radius=8)
        txt = font.render(self.text, True, TEXT_COLOR)
        screen.blit(txt, txt.get_rect(center=self.rect.center))

    def is_clicked(self, pos):
        return self.rect.collidepoint(pos)


class InputBox:
    def __init__(self, x, y, w, h, placeholder=""):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = ""
        self.active = False
        self.placeholder = placeholder

    def handle_event(self, event, max_len=80):
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
    def clear(self):
        self.text = ""

    def draw(self, screen, font):
        border = ACCENT_COLOR if self.active else CARD_COLOR
        pygame.draw.rect(screen, border, self.rect, 2, border_radius=6)
        shown = self.text if self.text else self.placeholder
        color = TEXT_COLOR if self.text else pygame.Color("#AAB7B8")
        txt = font.render(shown, True, color)
        screen.blit(txt, (self.rect.x + 10, self.rect.y + 10))


def normalize_answer(text):
    return " ".join(text.strip().lower().split())


def create_wheel_surface(radius):
    surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
    slice_angle = 360 / len(CATEGORIES)
    for i, category in enumerate(CATEGORIES):
        points = [(radius, radius)]
        for angle in range(int(i * slice_angle), int((i + 1) * slice_angle) + 1):
            rad = math.radians(angle)
            points.append((radius + radius * math.cos(rad), radius + radius * math.sin(rad)))
        pygame.draw.polygon(surf, WHEEL_COLORS[i], points)

        label_angle = math.radians((i + 0.5) * slice_angle)
        label_r = radius * 0.62
        label_x = radius + label_r * math.cos(label_angle)
        label_y = radius + label_r * math.sin(label_angle)
        label_surface = pygame.font.SysFont("Verdana", 16, bold=True).render(category, True, TEXT_COLOR)
        surf.blit(label_surface, label_surface.get_rect(center=(label_x, label_y)))
    return surf


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
    out = {}
    for name, info in players.items():
        if isinstance(info, dict):
            out[name] = int(info.get("score", 0))
        else:
            out[name] = int(info)
    return out


def start_new_round(room_id, game, question_index):
    category = random.choice(CATEGORIES)
    pool = QUESTION_BANK.get(category, [{"question": "Placeholder question", "answer": "placeholder"}])
    selected = random.choice(pool)

    wheel_start_angle = random.uniform(0, 360)
    wheel_rotation = random.uniform(1080, 1800)
    round_start = time.time()

    round_payload = {
        "question_index": question_index,
        "category": category,
        "question": selected["question"],
        "answer": normalize_answer(selected["answer"]),
        "phase_start": round_start,
        "durations": {
            "spin": 4,
            "countdown": 3,
            "answer": 30,
            "feedback": 3,
            "leaderboard": 4,
        },
        "wheel_start_angle": wheel_start_angle,
        "wheel_rotation": wheel_rotation,
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
            "round": round_payload,
            "score_applied_round": -1,
            "updated_at": round_start,
        }
    )


def ensure_player(room_id, nickname):
    room = db.child("rooms").child(room_id).get().val() or {}
    players = get_players(room)
    if nickname not in players:
        db.child("rooms").child(room_id).child("players").child(nickname).set(
            {"score": 0, "joined_at": time.time()}
        )


def apply_round_scoring(room_id, room, nickname):
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
    correct_answer = round_data.get("answer", "")
    answers = db.child("rooms").child(room_id).child("answers").child(str(round_idx)).get().val() or {}
    players = get_players(room)

    for player in players:
        response = answers.get(player, {}) if isinstance(answers.get(player), dict) else {}
        answer_text = normalize_answer(response.get("answer", ""))
        if not answer_text:
            delta = -2
        elif answer_text == correct_answer:
            delta = 5
        else:
            delta = -5

        score_ref = db.child("rooms").child(room_id).child("players").child(player).child("score")
        current = int(score_ref.get().val() or 0)
        score_ref.set(current + delta)
        score_path = db.child("rooms").child(room_id).child("players").child(player).child("score")
        current_score = score_path.get().val() or 0
        score_path.set(int(current_score) + delta)

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
def submit_answer(room_id, nickname, round_idx, answer_text):
    db.child("rooms").child(room_id).child("answers").child(str(round_idx)).child(nickname).set(
        {
            "answer": answer_text,
            "submitted_at": time.time(),
        }
    )


def host_start_game(room_id):
    room = db.child("rooms").child(room_id).get().val() or {}
    players = get_players(room)
    for name in players:
        db.child("rooms").child(room_id).child("players").child(name).child("score").set(0)

    db.child("rooms").child(room_id).child("answers").set({})
    db.child("rooms").child(room_id).child("game").set(
        {"status": "running", "started_at": time.time(), "score_applied_round": -1}
    )
    start_new_round(room_id, room.get("game", {}), 0)


def phase_from_elapsed(round_data, elapsed):
    durations = round_data.get("durations", {})
    t_spin = durations.get("spin", 4)
    t_count = durations.get("countdown", 3)
    t_answer = durations.get("answer", 30)
    t_feedback = durations.get("feedback", 3)
    t_lb = durations.get("leaderboard", 4)

    if elapsed < t_spin:
        return "spinning", t_spin - elapsed
    if elapsed < t_spin + t_count:
        return "countdown", t_spin + t_count - elapsed
    if elapsed < t_spin + t_count + t_answer:
        return "answer", t_spin + t_count + t_answer - elapsed
    if elapsed < t_spin + t_count + t_answer + t_feedback:
        return "feedback", t_spin + t_count + t_answer + t_feedback - elapsed
    if elapsed < t_spin + t_count + t_answer + t_feedback + t_lb:
        return "leaderboard", t_spin + t_count + t_answer + t_feedback + t_lb - elapsed
    return "round_done", 0


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
    title_font = pygame.font.SysFont("Verdana", 40, bold=True)
    large_font = pygame.font.SysFont("Verdana", 30, bold=True)
    mid_font = pygame.font.SysFont("Verdana", 24)
    small_font = pygame.font.SysFont("Verdana", 18)

    menu_nick = InputBox(320, 190, 360, 46, "Nickname")
    menu_room = InputBox(320, 280, 360, 46, "Room ID (blank = create random)")
    answer_box = InputBox(200, 520, 600, 46, "Type answer and press Enter")

    join_btn = Button(410, 360, 180, 56, "JOIN LOBBY")
    host_start_btn = Button(390, 520, 220, 60, "START GAME")
    submit_btn = Button(820, 520, 140, 46, "SUBMIT")

    wheel_surface = create_wheel_surface(190)

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
            is_host = room_data.get("game", {}).get("host") == nickname
            if state == "LOBBY" and room_data.get("game", {}).get("status") == "running":
        if state in {"LOBBY", "GAME"} and room_id and (now_ms - last_poll >= POLL_INTERVAL_MS):
            room_data = db.child("rooms").child(room_id).get().val() or {}
            game = room_data.get("game", {})
            is_host = game.get("host") == nickname
            if state == "LOBBY" and game.get("status") == "running":
                state = "GAME"
                submitted_round = -1
                local_feedback = ""
            last_poll = now_ms

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if state == "MENU":
                menu_nick.handle_event(event, max_len=16)
                menu_room.handle_event(event, max_len=10)
                menu_room.handle_event(event, max_len=8)
                if event.type == pygame.MOUSEBUTTONDOWN and join_btn.is_clicked(event.pos):
                    nickname = menu_nick.text.strip()
                    room_id = menu_room.text.strip() or str(random.randint(1000, 9999))
                    if not nickname:
                        status_message = "Nickname is required."
                        continue

                    room = db.child("rooms").child(room_id).get().val()
                    if not room:
                        db.child("rooms").child(room_id).set(
                            {
                                "players": {nickname: {"score": 0, "joined_at": now}},
                                "game": {
                                    "status": "lobby",
                                    "host": nickname,
                                    "started_at": 0,
                                    "score_applied_round": -1,
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
                if event.type == pygame.MOUSEBUTTONDOWN and host_start_btn.is_clicked(event.pos):
                    players = get_players(room_data)
                    if is_host and len(players) >= 2:
                        host_start_game(room_id)
                        room_data = db.child("rooms").child(room_id).get().val() or {}
                        state = "GAME"
                        local_feedback = ""
                        submitted_round = -1

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
                    if phase == "answer" and round_idx >= 0 and submitted_round != round_idx:
                        submit_answer(room_id, nickname, round_idx, answer_box.text.strip())
                        submitted_round = round_idx
                        local_feedback = "Answer submitted!"

        screen.fill(BG_COLOR)

        if state == "MENU":
            screen.blit(title_font.render("MULTIPLAYER TRIVIA", True, TEXT_COLOR), (270, 90))
            menu_nick.draw(screen, mid_font)
            menu_room.draw(screen, mid_font)
            join_btn.draw(screen, mid_font)
            if status_message:
                msg = small_font.render(status_message, True, ERROR_COLOR)
                screen.blit(msg, (320, 430))

        elif state == "LOBBY":
            players = get_players(room_data)
            game = room_data.get("game", {})
            is_host = game.get("host") == nickname

            screen.blit(title_font.render(f"LOBBY #{room_id}", True, TEXT_COLOR), (320, 60))
            role = "Host" if is_host else "Player"
            screen.blit(mid_font.render(f"You: {nickname} ({role})", True, INFO_COLOR), (40, 140))
            screen.blit(mid_font.render(f"Players joined: {len(players)}", True, TEXT_COLOR), (40, 180))

            y = 230
            for player in sorted(players.keys()):
                screen.blit(small_font.render(f"• {player}", True, TEXT_COLOR), (60, y))
                y += 32

            can_start = is_host and len(players) >= 2
            host_start_btn.draw(screen, mid_font, enabled=can_start)
            tip = "Host can start when at least 2 players are in lobby."
            screen.blit(small_font.render(tip, True, TEXT_COLOR), (300, 600))

            if not is_host:
                wait_text = "Waiting for host to start the game..."
                screen.blit(mid_font.render(wait_text, True, INFO_COLOR), (300, 520))

        elif state == "GAME":
            game = room_data.get("game", {})
            round_data = game.get("round", {})
            players = get_players(room_data)
            scores = get_scores(players)

            if not round_data:
                screen.blit(mid_font.render("Waiting for host to initialize round...", True, INFO_COLOR), (260, 320))
            else:
                round_idx = int(round_data.get("question_index", 0))
                elapsed = now - float(round_data.get("phase_start", now))
                phase, time_left = phase_from_elapsed(round_data, elapsed)

                if is_host and phase == "feedback":
                    apply_round_scoring(room_id, room_data, nickname)
                    room_data = db.child("rooms").child(room_id).get().val() or {}
                    scores = get_scores(get_players(room_data))

                if is_host and phase == "round_done":
                    next_q = round_idx + 1
                    if next_q < TOTAL_QUESTIONS:
                        start_new_round(room_id, game, next_q)
                        room_data = db.child("rooms").child(room_id).get().val() or {}
                        answer_box.clear()
                        local_feedback = ""
                        submitted_round = -1
                    else:
                        db.child("rooms").child(room_id).child("game").update(
                            {"status": "finished", "finished_at": now}
                        )

                game_status = room_data.get("game", {}).get("status", "running")
                if game_status == "finished":
                    ranking = sorted(scores.items(), key=lambda x: x[1], reverse=True)
                    screen.blit(title_font.render("FINAL STANDINGS", True, TEXT_COLOR), (315, 80))
                    y = 180
                    for i, (player, score) in enumerate(ranking, start=1):
                        screen.blit(mid_font.render(f"{i}. {player} - {score}", True, TEXT_COLOR), (360, y))
                        y += 46
                    screen.blit(
                        small_font.render("Returning to lobby...", True, INFO_COLOR),
                        (420, 560),
                    )
                    if is_host and now - float(room_data.get("game", {}).get("finished_at", now)) > 8:
                        db.child("rooms").child(room_id).child("game").update(
                            {"status": "lobby", "round": {}, "score_applied_round": -1}
                        )
                    if game_status == "finished" and now - float(room_data.get("game", {}).get("finished_at", now)) > 8:
                        state = "LOBBY"
                    pygame.display.flip()
                    clock.tick(FPS)
                    continue

                category = round_data.get("category", "")
                question = round_data.get("question", "")
                answer_key = round_data.get("answer", "")

                screen.blit(mid_font.render(f"Question {round_idx + 1} / {TOTAL_QUESTIONS}", True, TEXT_COLOR), (40, 20))
                screen.blit(mid_font.render(f"Category: {category}", True, INFO_COLOR), (40, 55))

                if phase == "spinning":
                    t_spin = round_data.get("durations", {}).get("spin", 4)
                    progress = max(0, min(1, elapsed / t_spin))
                    angle = float(round_data.get("wheel_start_angle", 0)) + float(
                        round_data.get("wheel_rotation", 0)
                    ) * progress
                    rot_wheel = pygame.transform.rotate(wheel_surface, angle)
                    screen.blit(rot_wheel, rot_wheel.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 20)))
                    pygame.draw.polygon(screen, TEXT_COLOR, [(WIDTH // 2, 120), (WIDTH // 2 - 14, 90), (WIDTH // 2 + 14, 90)])
                    screen.blit(large_font.render("Spinning category wheel...", True, TEXT_COLOR), (280, 90))

                elif phase == "countdown":
                    count = max(1, int(math.ceil(time_left)))
                    screen.blit(large_font.render(f"Get ready: {count}", True, TEXT_COLOR), (390, 250))
                    screen.blit(mid_font.render(f"Category selected: {category}", True, INFO_COLOR), (350, 320))

                elif phase in {"answer", "feedback", "leaderboard"}:
                    pygame.draw.rect(screen, CARD_COLOR, (90, 130, 820, 190), border_radius=10)
                    wrapped = question
                    question_surface = mid_font.render(wrapped, True, TEXT_COLOR)
                    screen.blit(question_surface, (120, 180))

                    if phase == "answer":
                        screen.blit(mid_font.render(f"Time left: {int(math.ceil(time_left))}s", True, INFO_COLOR), (120, 140))
                        answer_box.draw(screen, mid_font)
                        submit_btn.draw(screen, small_font, enabled=submitted_round != round_idx)
                        if local_feedback:
                            screen.blit(small_font.render(local_feedback, True, INFO_COLOR), (200, 580))
                    else:
                        answers = db.child("rooms").child(room_id).child("answers").child(str(round_idx)).get().val() or {}
                        my_answer = normalize_answer((answers.get(nickname) or {}).get("answer", ""))
                        if not my_answer:
                            outcome = "No answer submitted (-2)"
                            color = ERROR_COLOR
                        elif my_answer == answer_key:
                            outcome = "Correct! (+5)"
                            color = ACCENT_COLOR
                        else:
                            outcome = "Incorrect (-5)"
                            color = ERROR_COLOR

                        if phase == "feedback":
                            screen.blit(mid_font.render(outcome, True, color), (390, 430))
                            screen.blit(small_font.render(f"Correct answer: {answer_key}", True, TEXT_COLOR), (350, 470))
                        else:
                            ranking = sorted(scores.items(), key=lambda x: x[1], reverse=True)
                            screen.blit(mid_font.render("Leaderboard", True, TEXT_COLOR), (430, 350))
                            y = 390
                            for i, (player, score) in enumerate(ranking, start=1):
                                screen.blit(small_font.render(f"{i}. {player}: {score}", True, TEXT_COLOR), (390, y))
                                y += 30

                board_x = 760
                board_y = 20
                screen.blit(mid_font.render("Scores", True, TEXT_COLOR), (board_x, board_y))
                for i, (player, score) in enumerate(sorted(scores.items(), key=lambda x: x[1], reverse=True)):
                    screen.blit(small_font.render(f"{player}: {score}", True, TEXT_COLOR), (board_x, board_y + 35 + i * 25))

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
