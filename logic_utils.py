"""Pure game logic for the Glitchy Guesser.

Everything in this module is deliberately free of Streamlit imports so it can be
unit tested directly with pytest. `app.py` owns the UI and session state and
calls into here for every decision about the game.

# FIX: All four functions below were refactored out of app.py with an AI
# assistant in agent mode; the bugs described in reflection.md section 1 were
# repaired during the move rather than copied across.
"""

import math

# Scoring constants. Named so the rules are visible instead of buried in
# magic numbers the way the starter code had them.
WIN_BASE_POINTS = 100
POINTS_LOST_PER_ATTEMPT = 10
MINIMUM_WIN_POINTS = 10
WRONG_GUESS_PENALTY = 5

# (low, high) inclusive, per difficulty.
# FIXME (starter bug 5): the original returned Hard = (1, 50), which is a
# NARROWER range than Normal = (1, 100), so "Hard" was easier than "Normal".
# FIX: Hard now spans 1-200 so the ranges increase monotonically with difficulty.
DIFFICULTY_RANGES = {
    "Easy": (1, 20),
    "Normal": (1, 100),
    "Hard": (1, 200),
}

# Spare guesses on top of the binary-search minimum. Hard gets none, so it is
# only winnable with near-optimal play -- but it IS winnable, which the
# starter's 5-attempts-for-50-numbers setting was not.
DIFFICULTY_BUFFERS = {
    "Easy": 2,
    "Normal": 1,
    "Hard": 0,
}

DEFAULT_DIFFICULTY = "Normal"


def get_range_for_difficulty(difficulty: str):
    """Return the (low, high) inclusive range for a given difficulty."""
    return DIFFICULTY_RANGES.get(difficulty, DIFFICULTY_RANGES[DEFAULT_DIFFICULTY])


def get_attempt_limit(difficulty: str) -> int:
    """Return how many guesses a difficulty allows.

    Derived from the range instead of hardcoded, so the limit can never drift
    below the number of guesses a perfect binary search needs. The starter code
    hardcoded 5 attempts for Hard's 50 numbers, which needs 6 -- an unwinnable
    setting. Computing it removes that whole class of mistake.
    """
    low, high = get_range_for_difficulty(difficulty)
    span = high - low + 1
    minimum_guesses = max(1, math.ceil(math.log2(span)))
    buffer = DIFFICULTY_BUFFERS.get(difficulty, DIFFICULTY_BUFFERS[DEFAULT_DIFFICULTY])
    return minimum_guesses + buffer


def parse_guess(raw, low=None, high=None):
    """Parse user input into an int guess.

    Returns: (ok: bool, guess_int: int | None, error_message: str | None)

    When `low` and `high` are supplied, a numeric guess outside the range is
    rejected with a message naming the range.
    """
    if raw is None:
        return False, None, "Enter a guess."

    text = str(raw).strip()
    if text == "":
        return False, None, "Enter a guess."

    # FIXME (starter bug): the original did int(float(raw)) for anything
    # containing a ".", silently truncating 3.9 to 3 and then scoring the guess
    # the player never made.
    # FIX: accept a float only when it is a whole number, and say so otherwise.
    try:
        if "." in text or "e" in text.lower():
            value_as_float = float(text)
            if not value_as_float.is_integer():
                return False, None, "Whole numbers only -- no decimals."
            value = int(value_as_float)
        else:
            value = int(text)
    except (TypeError, ValueError):
        return False, None, "That is not a number."

    if low is not None and high is not None and not (low <= value <= high):
        return False, None, f"Guess must be between {low} and {high}."

    return True, value, None


def check_guess(guess, secret) -> str:
    """Compare guess to secret and return the outcome as a string.

    Returns one of: "Win", "Too High", "Too Low".

    # FIXME (starter bug 2): app.py handed this function `str(secret)` on every
    # even-numbered attempt. The original compared the values directly, hit a
    # TypeError, and silently retried as a STRING comparison -- so "100" > "42"
    # was False and a guess of 100 against a secret of 42 was reported as
    # "Too Low".
    # FIX: coerce both sides to int before comparing, so the outcome is correct
    # no matter which type the caller passes in. The int()/int() pair is what
    # makes the even/odd attempt asymmetry impossible to reintroduce.
    """
    guess_value = int(guess)
    secret_value = int(secret)

    if guess_value == secret_value:
        return "Win"
    if guess_value > secret_value:
        return "Too High"
    return "Too Low"


def hint_message(outcome: str) -> str:
    """Return the player-facing hint for an outcome.

    # FIXME (starter bug 1): the original built the message inside check_guess
    # and paired "Too High" with "Go HIGHER!" and "Too Low" with "Go LOWER!" --
    # the exact opposite of what each outcome means.
    # FIX: messages live in one small lookup next to nothing else, so the
    # mapping is readable at a glance and a test can assert it directly. If the
    # guess was too high, the player must go LOWER.
    """
    messages = {
        "Win": "🎉 Correct!",
        "Too High": "📉 Too high -- go LOWER!",
        "Too Low": "📈 Too low -- go HIGHER!",
    }
    return messages.get(outcome, "")


def update_score(current_score: int, outcome: str, attempt_number: int) -> int:
    """Update the score based on the outcome and which attempt it was.

    `attempt_number` is 1-based: the player's first guess is attempt 1.

    # FIXME (starter bug 4): the original added 5 points for a "Too High" on
    # even attempts and subtracted 5 otherwise, so two equally wrong guesses
    # moved the score in opposite directions. It also let the score go negative
    # and used `attempt_number + 1` against an already-incremented counter, so a
    # first-guess win paid 80 instead of the full 100.
    # FIX: every wrong guess costs the same, the score floors at 0, and the win
    # bonus decays from 100 using a 1-based attempt number.
    """
    if outcome == "Win":
        decay = POINTS_LOST_PER_ATTEMPT * (attempt_number - 1)
        points = max(MINIMUM_WIN_POINTS, WIN_BASE_POINTS - decay)
        return current_score + points

    if outcome in ("Too High", "Too Low"):
        return max(0, current_score - WRONG_GUESS_PENALTY)

    return current_score
