# utils/daily_prompts.py
import random, datetime
from typing import List, Tuple

DARE_BASE: List[str] = [
    "Send 3 emojis that describe your fantasy 😏🍓🔥",
    "Confess your wildest dream date in 5 words.",
    "Drop a flirty compliment for your last match 😉",
    "Type the 3 words that turn you on 👀",
    "React 🔥 on one story right now.",
    "Tell a secret you've never told anyone (one sentence).",
    "DM your favorite song line to your last chat 🎵",
    "Share a 'guilty pleasure' food + emoji combo 🍫😈",
    "Describe your perfect kiss with 3 emojis 😘💫🔥",
    "Confess a romantic fail in 10 words.",
]

DARE_ACTIONS = ["Send","Type","Confess","Describe","Drop","Reveal","Share","Admit","Whisper","Tease with"]
DARE_OBJECTS = [
    "3 emojis that explain your mood","your flirty opener","your guilty pleasure",
    "a secret fantasy in 7 words","your wildest date idea","a spicy compliment",
    "a romantic fail (1 line)","your favorite kiss style","a bold dare for others",
    "your last crush hint","a school-day secret","your weekend vibe in emojis"
]
DARE_SPICE = ["😏","🔥","🍓","😉","👀","💋","💫","🫦","😈","💌"]

WYR_PAIRS: List[Tuple[str,str]] = [
    ("Kiss in public 😘","Kiss in private 🔥"),
    ("Text a secret now 💬","Hold it till tomorrow ⏳"),
    ("Flirty voice note 🎙️","Spicy emoji only 😏"),
    ("Romantic slow dance 💞","Wild club night 🕺"),
    ("Truth (18+) 🫢","Dare (18+) 😈"),
    ("Cute café date ☕","Bold rooftop kiss 🌆"),
    ("Gentle cuddles 🧸","Passionate make-out 💥"),
    ("Compliment first 💐","Confess first 💌"),
    ("Midnight call 🌙","Morning surprise ☀️"),
    ("Hold hands in public 🤝","Stolen kiss in private 🫦"),
]

def _build_dare_pool(seed: int, count: int = 150):
    rnd = random.Random(seed)
    pool = set(DARE_BASE)
    for _ in range(count*2):
        a = rnd.choice(DARE_ACTIONS)
        o = rnd.choice(DARE_OBJECTS)
        s = "".join(rnd.sample(DARE_SPICE, k=3))
        pool.add(f"{a} {o} {s}")
        if len(pool) >= count: break
    return list(pool)

def get_daily_dare(today: datetime.date|None=None) -> str:
    if today is None: today = datetime.date.today()
    seed = int(today.strftime("%Y%m%d"))
    pool = _build_dare_pool(seed, 150)
    return random.Random(seed).choice(pool)

def get_daily_wyr(today: datetime.date|None=None) -> Tuple[str,str]:
    if today is None: today = datetime.date.today()
    seed = int(today.strftime("%Y%m%d"))
    rnd = random.Random(seed)
    return rnd.choice(WYR_PAIRS)