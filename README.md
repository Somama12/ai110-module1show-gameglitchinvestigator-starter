# 🎮 Game Glitch Investigator: The Impossible Guesser

A Streamlit number-guessing game that an AI wrote, shipped, and got wrong in five
different ways. This repo is the investigation: what was broken, how it was
diagnosed, and what the fixes were.

## 🎯 The Game's Purpose

Pick a difficulty, and the app hides a random secret number inside that
difficulty's range. You type guesses; after each one the game tells you whether
you were too high or too low and updates your score. Guess it before you run out
of attempts and you win, with a bonus that shrinks the longer you take. There is
a "Developer Debug Info" expander that reveals the secret, which is what makes
the bugs observable in the first place.

| Difficulty | Range | Attempts |
|-----------|-------|----------|
| Easy | 1–20 | 7 |
| Normal | 1–100 | 8 |
| Hard | 1–200 | 8 |

Attempt limits are computed as `ceil(log2(range)) + buffer`, so no difficulty can
ever be set below the number of guesses a binary search actually needs.

## 🛠️ Setup

```bash
pip install -r requirements.txt
python -m streamlit run app.py
```

Run the tests with:

```bash
pytest
```

## 🐛 Bugs Found

All five were silent logic bugs — the app never raised a traceback, which is
exactly what made them hard to trust. Full reproduction evidence, including
expected-vs-actual tables and terminal traces, is in
[reflection.md](reflection.md#1-what-was-broken-when-you-started).

1. **The hint messages contradicted the outcome.** `check_guess` returned the
   outcome `"Too High"` alongside the message `"📈 Go HIGHER!"`, and `"Too Low"`
   alongside `"📉 Go LOWER!"`. The player only ever sees the message, so the game
   pointed away from the answer on every single guess.

2. **Every even-numbered attempt compared guesses alphabetically.** `app.py` did
   `secret = str(st.session_state.secret)` whenever `attempts % 2 == 0`.
   `check_guess` then evaluated `int > str`, raised `TypeError`, and fell into an
   `except` block that retried the comparison with both sides as strings. With a
   secret of 42, `"100" > "42"` is `False`, so a guess of 100 was reported
   **Too Low**; `"5" > "42"` is `True`, so a guess of 5 was reported **Too High**.

3. **"New Game 🔁" dead-ended.** The handler reset `attempts` and `secret` but
   never `status`, `score` or `history`. With `status` still `"won"`/`"lost"`, the
   guard below it hit `st.stop()` on the next rerun, so the button appeared to do
   nothing and the old score leaked into the "new" game.

4. **Scoring was asymmetric.** `update_score` subtracted 5 for every "Too Low"
   but *added* 5 for a "Too High" on even attempts. Two equally wrong guesses
   moved the score in opposite directions, and it could go negative. The win
   bonus used `attempt_number + 1` against an already-incremented counter, so a
   first-guess win paid 80 instead of 100.

5. **Difficulty was incoherent.** Hard's range was 1–50 — *narrower* than
   Normal's 1–100 — with only 5 attempts for 50 numbers when binary search needs
   6, making Hard unwinnable with perfect play. The on-screen prompt was also
   hardcoded to "Guess a number between 1 and 100" regardless of difficulty.

## 🔧 Fixes Applied

The core move was a **refactor**: `get_range_for_difficulty`, `parse_guess`,
`check_guess` and `update_score` all lived inside `app.py`, tangled up with
Streamlit widget calls, so none of them could be tested without booting a
server. They now live in [`logic_utils.py`](logic_utils.py), which imports
nothing from Streamlit. `app.py` is UI and session state only.

| Bug | Fix |
|-----|-----|
| 1 | Hint text moved out of `check_guess` into `hint_message()`, a single lookup where `"Too High"` maps to `"go LOWER!"`. `check_guess` now returns only the outcome string, so the outcome and its wording can't drift apart. |
| 2 | `check_guess` coerces both operands with `int()` before comparing, so the `TypeError` path is gone entirely and a string secret still compares numerically. `app.py` also stopped stringifying the secret. |
| 3 | A single `start_new_game()` function resets *all* state — secret, attempts, score, status, history, difficulty, and a `game_id` that clears the input box. Every reset path calls it, so none can forget a key. Changing difficulty mid-game now restarts in the new range too. |
| 4 | Every wrong guess costs the same 5 points, the score floors at 0, and the win bonus decays from 100 using a 1-based attempt number. |
| 5 | Hard widens to 1–200 so ranges grow with difficulty, attempt limits are derived from `ceil(log2(span))` rather than hardcoded, and the prompt reads its range from the same source of truth as the secret generator. |

Two smaller issues surfaced during the refactor and were fixed alongside:
`parse_guess` used to do `int(float(raw))`, silently truncating a guess of `3.9`
to `3`; and `attempts` was incremented *before* parsing, so a typo like `abc`
burned one of the player's guesses.

## 📸 Demo Walkthrough

A full game on Normal difficulty, with the secret at **73** (read from the
Developer Debug Info expander):

1. App loads showing **"Guess a number between 1 and 100. Attempts left: 8"** —
   the range and the count both come from the selected difficulty.
2. User enters **50** → hint reads **"📈 Too low — go HIGHER!"**. 50 *is* below
   73, and the hint now points toward the answer. Attempts used: 1.
3. User enters **abc** → **"That is not a number."** Attempts used is still **1** —
   a typo no longer costs a guess.
4. User enters **150** → **"Guess must be between 1 and 100."** Still 1 attempt used.
5. User enters **75** → hint reads **"📉 Too high — go LOWER!"**. This is attempt
   **2**, an even-numbered turn, which in the starter code would have flipped to a
   string comparison. It no longer does. Attempts used: 2.
6. User enters **73** → 🎉 balloons, and **"You won in 3 attempts! The secret was
   73. Final score: 80"** (100 base, minus 10 for each of the 2 earlier guesses).
7. User clicks **New Game 🔁** → the board actually resets: status back to
   `playing`, score to 0, attempts to 0, history emptied, new secret drawn, and
   the guess box cleared.

That session was executed against the real app, not written from memory — here is
the captured output, driven through Streamlit's own `AppTest` harness:

```
exception on load: ElementList()
Prompt: Guess a number between 1 and 100. Attempts left: 8
Sidebar: Range: 1 to 100 | Attempts allowed: 8
Secret forced to 73 for a reproducible trace.

guess='50'   attempts=1 score=0
   hint    : Too low -- go HIGHER!
guess='abc'  attempts=1 score=0
   error   : That is not a number.
guess='150'  attempts=1 score=0
   error   : Guess must be between 1 and 100.
guess='75'   attempts=2 score=0
   hint    : Too high -- go LOWER!
guess='73'   attempts=3 score=80
   hint    : Correct!
   success : You won in 3 attempts! The secret was 73. Final score: 80

status: won
history: [50, 75, 73]

After clicking New Game:
  status : playing
  score  : 0
  attempts: 0
  history: []
  exception: ElementList()
```

`exception: ElementList()` is an empty list — the app raised nothing at any point
in the session.

## 🧪 Test Results

The three starter tests in `tests/test_game_logic.py` are kept **verbatim**. They
failed before this work because `logic_utils.py` shipped as `NotImplementedError`
stubs; they pass now without being edited. Everything else is a regression test
tied to a specific bug above — including a sweep asserting
`check_guess(g, 42) == check_guess(g, "42")` for every `g` in 1..100, which is the
assertion the starter code fails hardest.

```
$ pytest
============================= test session starts ==============================
platform darwin -- Python 3.13.3, pytest-9.1.1, pluggy-1.6.0
rootdir: /Users/somamasiddiqui/Desktop/codepathAI/ai110-module1show-gameglitchinvestigator-starter
plugins: anyio-4.15.1
collected 35 items

tests/test_game_logic.py ...................................             [100%]

============================== 35 passed in 0.02s ==============================
```

Before the fixes, the same command gave:

```
=========================== short test summary info ============================
FAILED tests/test_game_logic.py::test_winning_guess - NotImplementedError: Re...
FAILED tests/test_game_logic.py::test_guess_too_high - NotImplementedError: R...
FAILED tests/test_game_logic.py::test_guess_too_low - NotImplementedError: Re...
============================== 3 failed in 0.02s ===============================
```

The full current run is also committed to [test_results.txt](test_results.txt).

## 📝 Document Your Experience

- [x] **Describe the game's purpose.** See [The Game's Purpose](#-the-games-purpose).
- [x] **Detail which bugs you found.** See [Bugs Found](#-bugs-found), with
      reproduction evidence in [reflection.md](reflection.md).
- [x] **Explain what fixes you applied.** See [Fixes Applied](#-fixes-applied).

## 🚀 Stretch Features

- [ ] Challenge 4 (Enhanced UI) — not attempted.
