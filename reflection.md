# 💭 Reflection: Game Glitch Investigator

Answer each question in 3 to 5 sentences. Be specific and honest about what actually happened while you worked. This is about your process, not trying to sound perfect.

## 1. What was broken when you started?

The first time I ran `python -m streamlit run app.py` the game *looked* completely finished — title, sidebar with a difficulty picker, a score, a "Developer Debug Info" expander, even balloons on a win. Nothing crashed, and there was no traceback in the terminal, which is exactly what made it hard to trust: every bug was a silent logic bug rather than an error message. I opened the debug expander so I could see the secret number and played through a few rounds on Normal, and once I could compare my guess against the real secret the problems showed up fast.

To get evidence I could actually reason about instead of "it felt wrong", I pulled the four pure functions out of `app.py` into a scratch file and called them directly with a fixed secret of 42. That turned a fuzzy complaint into a table.

### The bugs I found

1. **The hint messages are inverted.** In `check_guess` ([`app.py:36-40`](app.py#L36-L40)) the branch for `guess > secret` returns the outcome `"Too High"` but the message `"📈 Go HIGHER!"`, and the `guess < secret` branch returns `"Too Low"` with `"📉 Go LOWER!"`. The outcome label is right; the sentence shown to the player is the exact opposite of it. Since the player only ever sees the message, the game actively steers you away from the answer on every single guess.

2. **On even-numbered attempts the secret becomes a string, so guesses are compared alphabetically.** [`app.py:158-161`](app.py#L158-L161) does `secret = str(st.session_state.secret)` whenever `attempts % 2 == 0`. `check_guess` then evaluates `guess > secret` as `int > str`, raises `TypeError`, and falls into an `except` block that retries the comparison with *both sides as strings*. `"100" > "42"` is `False` and `"5" > "42"` is `True`, so with a secret of 42 a guess of 100 is reported "Too Low" and a guess of 5 is reported "Too High". Sweeping every guess from 1 to 100 against a secret of 42 shows this changes the answer for 6 values — 5, 6, 7, 8, 9 and 100 — since the first digit only sorts against the true ordering at the extremes. That is rare by count but common in play, because single digits and 100 are exactly where you probe when bracketing a range, and it only happens on even turns, so the game feels intermittently rather than obviously broken. (A correct guess still registers as a win — the fallback re-checks `str(guess) == secret`, and `"42" == "42"` is `True` — so the bug hides behind a working win condition.)

3. **"New Game 🔁" does nothing once a game has ended.** The handler at [`app.py:134-138`](app.py#L134-L138) resets `attempts` and `secret` but never resets `status`, `score`, or `history`. Because `status` is still `"won"` or `"lost"`, the guard at [`app.py:140-145`](app.py#L140-L145) calls `st.stop()` on the very next rerun, so the screen keeps showing "Game over. Start a new game to try again." and the button looks dead. The score and guess history also leak into what was supposed to be a fresh game.

4. **The scoring rules are asymmetric and punish you for playing.** `update_score` ([`app.py:50-65`](app.py#L50-L65)) subtracts 5 for every "Too Low" but *adds* 5 for a "Too High" on even attempts and subtracts 5 on odd ones. Two equally-informative wrong guesses can move the score in opposite directions for no reason, and the score routinely goes negative. The win bonus is also off: `100 - 10 * (attempt_number + 1)` with `attempts` already incremented means a first-guess win pays 80, not the 90 the formula looks like it intends.

5. **The difficulty settings are incoherent and the on-screen prompt ignores them.** `get_range_for_difficulty` returns 1–20 for Easy, 1–100 for Normal, but only 1–50 for Hard — Hard has a *narrower* range than Normal, which inverts the difficulty. Hard also allows 5 attempts for 50 numbers when optimal binary search needs 6, so Hard is unwinnable with perfect play. Separately, the main prompt at [`app.py:109-112`](app.py#L109-L112) is hardcoded to "Guess a number between 1 and 100" regardless of difficulty, and `attempts` initialises to `1` ([`app.py:95-96`](app.py#L95-L96)) while "New Game" resets it to `0`, so "Attempts left" is off by one and inconsistent between the first game and later ones.

### Bug Reproduction Log

| Input | Expected Behavior | Actual Behavior | Console Output / Error |
|-------|-------------------|-----------------|------------------------|
| Normal, secret = 42 (read from debug panel), guess `30` on attempt 1 | Hint tells me to go up: "Go HIGHER!" | Outcome `Too Low`, but message shown is "📉 Go LOWER!" — points away from 42 | none |
| Normal, secret = 42, guess `100` on attempt 2 (an even attempt) | Outcome "Too High" and hint "Go LOWER!" | Outcome `Too Low`, message "📉 Go LOWER!" — the game claims 100 is *below* 42 | none (the `TypeError` is silently swallowed by the `except TypeError` block) |
| Normal, secret = 42, guess `5` on attempt 2 | Outcome "Too Low" and hint "Go HIGHER!" | Outcome `Too High`, message "📈 Go HIGHER!" — the game claims 5 is *above* 42 | none |
| Clicked "New Game 🔁" after losing on Normal | Fresh game: new secret, attempts back to full, score reset to 0, guess box usable again | Still shows "Game over. Start a new game to try again."; the guess input does nothing and the old score and history are still there | none |
| Two wrong guesses in a row from score 0: one "Too Low" (attempt 1), one "Too High" (attempt 2) | Both are wrong guesses, so both should cost the same | Score goes `0 → -5 → 0`: the "Too Low" costs 5 but the "Too High" *awards* 5 | none |
| Selected "Hard" in the sidebar | Hard should be *harder* than Normal — a range at least as wide as 1–100, and the on-screen prompt should match the range | Sidebar reports "Range: 1 to 50" (narrower than Normal), attempts drop to 5 when 50 numbers need 6 guesses, and the main prompt still reads "Guess a number between 1 and 100" | none |

### Reproduction trace (starter code, before any fixes)

I called the starter `check_guess` directly with a fixed secret of 42 to prove bugs 1 and 2 without having to screenshot the UI:

```
secret = 42, EVEN attempt (app.py passes secret as the string '42'):
  guess   5 (actually lower than 42  ) -> outcome=Too High message=📈 Go HIGHER!
  guess   9 (actually lower than 42  ) -> outcome=Too High message=📈 Go HIGHER!
  guess  30 (actually lower than 42  ) -> outcome=Too Low  message=📉 Go LOWER!
  guess 100 (actually higher than 42 ) -> outcome=Too Low  message=📉 Go LOWER!
  guess  42 (actually correct        ) -> outcome=Win      message=🎉 Correct!

secret = 42, ODD attempt (secret stays an int):
  guess   5 (actually lower than 42  ) -> outcome=Too Low  message=📉 Go LOWER!
  guess   9 (actually lower than 42  ) -> outcome=Too Low  message=📉 Go LOWER!
  guess  30 (actually lower than 42  ) -> outcome=Too Low  message=📉 Go LOWER!
  guess 100 (actually higher than 42 ) -> outcome=Too High message=📈 Go HIGHER!
  guess  42 (actually correct        ) -> outcome=Win      message=🎉 Correct!
```

Read the "ODD attempt" block: every outcome label is correct and every message contradicts it. Then read the "EVEN attempt" block: now even the outcome labels are wrong for 5, 9 and 100.

And the starter test suite does not pass, because `logic_utils.py` ships as four `NotImplementedError` stubs:

```
$ python -m pytest
=========================== short test summary info ============================
FAILED tests/test_game_logic.py::test_winning_guess - NotImplementedError: Re...
FAILED tests/test_game_logic.py::test_guess_too_high - NotImplementedError: R...
FAILED tests/test_game_logic.py::test_guess_too_low - NotImplementedError: Re...
============================== 3 failed in 0.02s ===============================
```

---

## 2. How did you use AI as a teammate?

I used **Claude (Opus 5) inside VS Code** as an agent with access to the repo, plus inline chat for one-off "explain this line" questions. The pattern that worked was: gather evidence myself first, then hand the AI the evidence rather than the vibe. Asking "why is my game broken?" got me vague answers; pasting the actual `check_guess` source and a table of guess/outcome pairs got me a correct diagnosis in one shot.

### AI explanation of a bug

I highlighted the `except TypeError` block in `check_guess` and asked, *"Explain this logic step-by-step — when would this branch ever run?"* The explanation I got back:

> `app.py` passes `str(st.session_state.secret)` whenever `attempts % 2 == 0`. On those turns `guess` is an `int` and `secret` is a `str`, so `guess > secret` raises `TypeError: '>' not supported between instances of 'int' and 'str'`. The `except` block catches it and retries with `g = str(guess)` — but that means the comparison is now **lexicographic**, not numeric. Python compares strings character by character, so `"100" > "42"` is `False` (because `"1" < "4"`) and `"5" > "42"` is `True` (because `"5" > "4"`). The hint is therefore inverted for any guess whose first digit sorts differently from the secret's.

That was the piece I had not worked out on my own. I knew the hints felt random on some turns; I did not know the `except` block was quietly converting a crash into a wrong answer.

### An AI suggestion that was correct

**What it suggested:** that the fix belongs in `check_guess` — coerce both sides with `int()` *before* comparing and delete the `except TypeError` fallback entirely — rather than only removing the `str()` call in `app.py`. The reasoning given was that deleting the `str()` call fixes today's caller but leaves a function that silently returns wrong answers if anyone ever passes it a string again, whereas coercing at the boundary makes the bug unreproducible.

**Why it's correct:** the `except` block wasn't a safety net, it was a bug amplifier — it turned a loud `TypeError` into a silent wrong hint. Removing it means a genuinely bad input (`check_guess("fifty", 42)`) now raises `ValueError` immediately instead of guessing.

**How I verified it:** I wrote a test that sweeps every guess from 1 to 100 and asserts `check_guess(g, 42) == check_guess(g, "42")` (`test_int_and_string_secret_agree`). Under the starter code that test fails on 6 of the 100 values — guesses 5, 6, 7, 8, 9 and 100. It passes now. I also re-ran my original scratch trace against the fixed function and confirmed guess 100 vs secret 42 reports "Too High" instead of "Too Low".

### An AI suggestion that was incorrect or misleading

**What it suggested:** early on, when summarising the bugs, the AI told me that the stringified-secret bug meant **a correct guess could never register as a win** — its reasoning was that `42 == "42"` evaluates to `False`, so the `if guess == secret` check at the top of `check_guess` would never fire on an even attempt. It presented this as the headline bug and tied it to the README's "You can't win" claim.

**Why it's wrong:** it stopped reading at the first `if`. The `except TypeError` fallback re-checks `if g == secret` where `g = str(guess)` — and `"42" == "42"` **is** `True`, so the win is caught after all. The fallback that causes the comparison bug is the same code that rescues the equality case.

**How I caught it:** I didn't argue with it, I ran it. I extracted the starter functions into a scratch file and called `check_guess(42, "42")` directly:

```
guess=42 secret='42' -> ('Win', '🎉 Correct!')
```

A win, exactly the opposite of what I'd been told. That one line changed how I wrote the bug up — the real bug is *lexicographic comparison of the non-equal cases*, which is subtler and easier to miss precisely because the win condition still works and hides it. If I had trusted the summary I would have documented a bug that does not exist and written a test that fails for the wrong reason.

**A second suggestion I revised rather than rejected:** the starter tests assert `check_guess(50, 50) == "Win"`, but the function returned a tuple `("Win", "🎉 Correct!")`, so they could not pass as written. The AI's first move was to update the tests to unpack the tuple. I pushed back — the assignment says the *existing* tests should pass, and rewriting a test to match broken code is how you end up certifying a bug. Instead I had it split the function: `check_guess` returns the outcome string only, and a new `hint_message(outcome)` owns the wording. The starter tests then passed untouched, and as a bonus the inverted-hint bug became directly testable in isolation, which is where `test_too_high_tells_the_player_to_go_lower` came from.

---

## 3. Debugging and testing your fixes

I decided a bug was fixed when I had a test that **failed against the starter code and passed against mine** — not when the app merely stopped looking wrong. That distinction mattered, because several of these bugs only surface on alternating turns, so clicking around in the browser can easily produce a run where everything looks fine by luck.

The test that taught me the most was `test_int_and_string_secret_agree`, which loops `g` from 1 to 100 and asserts `check_guess(g, 42) == check_guess(g, "42")`. I had guessed before running it that roughly half the values would disagree, since lexicographic ordering feels like it should scramble everything. The real answer was **6 of 100** — guesses 5, 6, 7, 8, 9 and 100 — because `"1" < "4"` and `"5" > "4"` only bite when the first digit sorts against the true ordering.

That was a more useful result than the number I expected, in two directions. It stopped me overstating the bug: most turns really are fine, which is exactly why the game feels *intermittently* broken rather than obviously broken, and why I couldn't pin it down by playing. But those 6 values are not a random sample — 5 through 9 and 100 are the extremes, which is precisely where a player probes when they're bracketing a range. So the bug is rare by count and common in practice. It also taught me not to trust my own intuition about a failure's shape any more than the AI's: I was wrong about the magnitude by almost a factor of ten, and only running it told me so.

I also used a full-game test, `test_a_full_binary_search_game_wins_within_the_attempt_limit`, which plays an optimal game through the logic layer and asserts it actually reaches the secret inside the attempt limit. This is the test that catches bug 5: if a difficulty's attempt limit is set below `ceil(log2(range))` the way Hard's was, a perfect player still loses and the test goes red. It's a rule about the game being winnable at all, which no single-function unit test expresses.

Finally I ran the real app end-to-end using Streamlit's `AppTest` harness rather than only clicking manually, so the walkthrough in the README is captured output instead of something I typed from memory. That run is what confirmed the two state fixes: a typo (`abc`) leaves `attempts` at 1 instead of burning a guess, and "New Game" returns `status` to `playing` with score, attempts and history all cleared.

AI helped most with *breadth* on tests, not the important ones. Once I described a bug it would readily produce the boundary cases I'd have skipped out of laziness — empty string, whitespace-only, `None`, `"42.0"` versus `"3.9"`, guesses exactly on the range boundary. The two tests that actually carry the project — the 1-to-100 sweep and the binary-search game — came from my own question of "what would have caught this automatically?", which is a different question from "what are the edge cases".

---

## 4. What did you learn about Streamlit and state?

The mental model that finally made it click: **Streamlit re-runs your entire script, top to bottom, every single time anything happens.** Click a button, type in a box, move a slider — the whole file executes again from line 1. It's less like a normal GUI app where you attach event handlers, and more like a web page that fully regenerates itself on every interaction.

Which means every ordinary Python variable is wiped on every interaction. `st.session_state` is the only thing that survives, a dictionary that persists between reruns. That's why the starter code wraps its setup in `if "secret" not in st.session_state:` — without that guard, `random.randint` would run again on every rerun and the secret would change out from under you mid-game.

The subtler lesson was that *partial* state resets are worse than no reset at all. The "New Game" bug wasn't a missing `session_state` — it was a handler that reset three keys and forgot three others, leaving the app in a state that was internally contradictory: a fresh secret and zero attempts, but `status` still `"lost"`, so the guard killed the script before the player could do anything. That's why my fix is a single `start_new_game()` function that every reset path goes through. If the reset lives in one place, no caller can remember half of it. I'd explain it to a friend as: with reruns, the bug is rarely "I forgot to save something" — it's "I saved some of it."

---

## 5. Looking ahead: your developer habits

**The habit I'm keeping:** reproduce before you diagnose. My first real move on this project was pulling the four pure functions out of `app.py` into a scratch file and calling them directly with a fixed secret of 42. It took about five minutes and it converted "the hints feel wrong sometimes" into a table showing exactly which guesses broke and on which turns. Every good decision afterward came from that table — including catching the AI's incorrect claim, which I would have had no way to challenge otherwise. Related: I now treat "can I write a test that fails on the old code?" as the definition of understanding a bug, rather than "does it look fixed in the browser?"

**What I'd do differently:** I'd stop asking AI to *summarise* code and start asking it to *predict specific outputs*. When I asked "what's wrong with this function" I got a confident, partly-wrong narrative. When I asked "what does `check_guess(42, '42')` return, and walk me through each branch" I got something I could immediately check by running it. Concrete, falsifiable questions make the AI's mistakes visible in seconds; open-ended ones let the mistakes hide inside plausible prose. I'd also attach files earlier — the answers got markedly better once the assistant could see `app.py` and `logic_utils.py` together and understand that the `str()` call and the `except` block were in different files.

**How this changed how I think about AI-generated code:** the thing that unsettled me wasn't that the AI wrote buggy code — it's that the buggy code was *polished*. Docstrings, type hints, a defensive `try/except`, sensible function names. It looked more trustworthy than code I'd write myself, and every bug ran silently with no traceback. The `except TypeError` block is the perfect example: it's a defensive-programming pattern that looks responsible and is in fact the single most damaging line in the file, because it converts a crash that would have told me something into a wrong answer that told me nothing. So my takeaway isn't "don't trust AI code" — it's that fluency and correctness are completely independent, and the review effort I spend has to scale with how *consequential* the code is, not with how sketchy it looks.
