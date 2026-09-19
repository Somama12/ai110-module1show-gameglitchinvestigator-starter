"""Streamlit UI for the Glitchy Guesser.

# FIX: This file used to define get_range_for_difficulty, parse_guess,
# check_guess and update_score inline, mixing game rules with layout code. All
# four now live in logic_utils.py (refactored with an AI assistant in agent
# mode) so pytest can exercise the rules without booting Streamlit. app.py is
# responsible only for widgets and session state.
"""

import random

import streamlit as st

from logic_utils import (
    check_guess,
    get_attempt_limit,
    get_range_for_difficulty,
    hint_message,
    parse_guess,
    update_score,
)

st.set_page_config(page_title="Glitchy Guesser", page_icon="🎮")

st.title("🎮 Game Glitch Investigator")
st.caption("A number guessing game — debugged, refactored and under test.")

st.sidebar.header("Settings")

difficulty = st.sidebar.selectbox(
    "Difficulty",
    ["Easy", "Normal", "Hard"],
    index=1,
)

low, high = get_range_for_difficulty(difficulty)
attempt_limit = get_attempt_limit(difficulty)

st.sidebar.caption(f"Range: {low} to {high}")
st.sidebar.caption(f"Attempts allowed: {attempt_limit}")


def start_new_game(for_difficulty: str) -> None:
    """Reset every piece of game state to a clean slate.

    # FIXME (starter bug 3): the old "New Game" handler reset only `attempts`
    # and `secret`. `status` stayed "won"/"lost", so the guard further down hit
    # st.stop() on the next rerun and the button appeared to do nothing, while
    # the previous score and history leaked into the new round.
    # FIX: one function resets ALL of it, and every caller goes through it, so
    # no reset path can forget a key again.
    """
    new_low, new_high = get_range_for_difficulty(for_difficulty)
    st.session_state.secret = random.randint(new_low, new_high)
    st.session_state.attempts = 0
    st.session_state.score = 0
    st.session_state.status = "playing"
    st.session_state.history = []
    st.session_state.difficulty = for_difficulty
    # Bumping the id gives the guess box a fresh widget key, which clears the
    # text left over from the previous game.
    st.session_state.game_id = st.session_state.get("game_id", 0) + 1


if "secret" not in st.session_state:
    start_new_game(difficulty)

# FIXME (starter bug): changing the difficulty mid-game left the old secret in
# place, so on Easy you could be hunting a number outside the 1-20 range the
# sidebar promised.
# FIX: a difficulty change starts a fresh game in the new range.
if st.session_state.difficulty != difficulty:
    start_new_game(difficulty)
    st.rerun()

st.subheader("Make a guess")

# FIXME (starter bug 5): this prompt was hardcoded to "between 1 and 100" no
# matter which difficulty was selected, and `attempts` started at 1 instead of
# 0 so "Attempts left" was short by one on the very first game.
# FIX: both numbers now come from the same source of truth as the game itself.
attempts_left = attempt_limit - st.session_state.attempts
st.info(
    f"Guess a number between {low} and {high}. "
    f"Attempts left: {attempts_left}"
)

with st.expander("Developer Debug Info"):
    st.write("Secret:", st.session_state.secret)
    st.write("Attempts used:", st.session_state.attempts)
    st.write("Attempts left:", attempts_left)
    st.write("Score:", st.session_state.score)
    st.write("Difficulty:", difficulty)
    st.write("History:", st.session_state.history)

raw_guess = st.text_input(
    "Enter your guess:",
    key=f"guess_input_{st.session_state.game_id}",
)

col1, col2, col3 = st.columns(3)
with col1:
    submit = st.button("Submit Guess 🚀")
with col2:
    new_game = st.button("New Game 🔁")
with col3:
    show_hint = st.checkbox("Show hint", value=True)

if new_game:
    start_new_game(difficulty)
    st.rerun()

if st.session_state.status != "playing":
    if st.session_state.status == "won":
        st.success(
            f"You already won with a score of {st.session_state.score}. "
            "Start a new game to play again."
        )
    else:
        st.error("Game over. Start a new game to try again.")
    st.stop()

if submit:
    ok, guess_int, err = parse_guess(raw_guess, low, high)

    if not ok:
        # FIXME (starter bug): the old code incremented `attempts` before
        # parsing, so a typo such as "abc" burned one of the player's guesses.
        # FIX: only a successfully parsed guess counts as an attempt.
        st.error(err)
    else:
        st.session_state.attempts += 1
        st.session_state.history.append(guess_int)

        # FIXME (starter bug 2): app.py used to pass `str(st.session_state.secret)`
        # on every even-numbered attempt, which pushed check_guess into a
        # string comparison. The secret is always an int now.
        outcome = check_guess(guess_int, st.session_state.secret)

        if show_hint:
            st.warning(hint_message(outcome))

        st.session_state.score = update_score(
            current_score=st.session_state.score,
            outcome=outcome,
            attempt_number=st.session_state.attempts,
        )

        if outcome == "Win":
            st.balloons()
            st.session_state.status = "won"
            st.success(
                f"You won in {st.session_state.attempts} "
                f"attempt{'s' if st.session_state.attempts != 1 else ''}! "
                f"The secret was {st.session_state.secret}. "
                f"Final score: {st.session_state.score}"
            )
        elif st.session_state.attempts >= attempt_limit:
            st.session_state.status = "lost"
            st.error(
                f"Out of attempts! "
                f"The secret was {st.session_state.secret}. "
                f"Score: {st.session_state.score}"
            )

st.divider()
st.caption("Refactored, fixed and tested by a human with an AI pair programmer.")
