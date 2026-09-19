# 💭 Reflection: Game Glitch Investigator

Answer each question in 3 to 5 sentences. Be specific and honest about what actually happened while you worked. This is about your process, not trying to sound perfect.

## 1. What was broken when you started?

The first time I ran `python -m streamlit run app.py` the game *looked* completely finished — title, sidebar with a difficulty picker, a score, a "Developer Debug Info" expander, even balloons on a win. Nothing crashed, and there was no traceback in the terminal, which is exactly what made it hard to trust: every bug was a silent logic bug rather than an error message. I opened the debug expander so I could see the secret number and played through a few rounds on Normal, and once I could compare my guess against the real secret the problems showed up fast.

To get evidence I could actually reason about instead of "it felt wrong", I pulled the four pure functions out of `app.py` into a scratch file and called them directly with a fixed secret of 42. That turned a fuzzy complaint into a table.

### The bugs I found

1. **The hint messages are inverted.** In `check_guess` ([`app.py:36-40`](app.py#L36-L40)) the branch for `guess > secret` returns the outcome `"Too High"` but the message `"📈 Go HIGHER!"`, and the `guess < secret` branch returns `"Too Low"` with `"📉 Go LOWER!"`. The outcome label is right; the sentence shown to the player is the exact opposite of it. Since the player only ever sees the message, the game actively steers you away from the answer on every single guess.

2. **On even-numbered attempts the secret becomes a string, so guesses are compared alphabetically.** [`app.py:158-161`](app.py#L158-L161) does `secret = str(st.session_state.secret)` whenever `attempts % 2 == 0`. `check_guess` then evaluates `guess > secret` as `int > str`, raises `TypeError`, and falls into an `except` block that retries the comparison with *both sides as strings*. `"100" > "42"` is `False` and `"5" > "42"` is `True`, so with a secret of 42 a guess of 100 is reported "Too Low" and a guess of 5 is reported "Too High". This is the bug that makes the game feel genuinely unwinnable, because the hints flip meaning every other turn. (A correct guess still registers as a win — the fallback re-checks `str(guess) == secret` — so the bug hides behind a working win condition.)

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

- Which AI tools did you use on this project (for example: ChatGPT, Gemini, Copilot)?
- Give one example of an AI suggestion that was correct (including what the AI suggested and how you verified the result).
- Give one example of an AI suggestion that was incorrect or misleading (including what the AI suggested and how you verified the result).

---

## 3. Debugging and testing your fixes

- How did you decide whether a bug was really fixed?
- Describe at least one test you ran (manual or using pytest)  
  and what it showed you about your code.
- Did AI help you design or understand any tests? How?

---

## 4. What did you learn about Streamlit and state?

- How would you explain Streamlit "reruns" and session state to a friend who has never used Streamlit?

---

## 5. Looking ahead: your developer habits

- What is one habit or strategy from this project that you want to reuse in future labs or projects?
  - This could be a testing habit, a prompting strategy, or a way you used Git.
- What is one thing you would do differently next time you work with AI on a coding task?
- In one or two sentences, describe how this project changed the way you think about AI generated code.
