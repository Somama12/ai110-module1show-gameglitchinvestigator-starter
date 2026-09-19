"""Tests for logic_utils.

The first three tests are the ones that shipped with the starter repo, kept
verbatim. They failed before the refactor because logic_utils.py was a set of
NotImplementedError stubs. Everything below them is a regression test written
against a specific bug documented in reflection.md section 1.
"""

import math

import pytest

from logic_utils import (
    check_guess,
    get_attempt_limit,
    get_range_for_difficulty,
    hint_message,
    parse_guess,
    update_score,
)


# --------------------------------------------------------------------------
# Starter tests (unchanged)
# --------------------------------------------------------------------------

def test_winning_guess():
    # If the secret is 50 and guess is 50, it should be a win
    result = check_guess(50, 50)
    assert result == "Win"

def test_guess_too_high():
    # If secret is 50 and guess is 60, hint should be "Too High"
    result = check_guess(60, 50)
    assert result == "Too High"

def test_guess_too_low():
    # If secret is 50 and guess is 40, hint should be "Too Low"
    result = check_guess(40, 50)
    assert result == "Too Low"


# --------------------------------------------------------------------------
# Bug 1: the hint message contradicted the outcome
# --------------------------------------------------------------------------

def test_too_high_tells_the_player_to_go_lower():
    """The starter paired 'Too High' with 'Go HIGHER!'. Guard the direction."""
    message = hint_message("Too High")
    assert "LOWER" in message
    assert "HIGHER" not in message


def test_too_low_tells_the_player_to_go_higher():
    message = hint_message("Too Low")
    assert "HIGHER" in message
    assert "LOWER" not in message


def test_win_message_does_not_give_a_direction():
    assert hint_message("Win") == "🎉 Correct!"


# --------------------------------------------------------------------------
# Bug 2: a stringified secret turned the comparison lexicographic
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "guess, expected",
    [
        (5, "Too Low"),     # starter said "Too High" because "5" > "42"
        (9, "Too Low"),     # starter said "Too High" because "9" > "42"
        (100, "Too High"),  # starter said "Too Low"  because "100" < "42"
        (42, "Win"),
    ],
)
def test_string_secret_still_compares_numerically(guess, expected):
    """app.py used to pass str(secret) on even attempts. Even if a caller does
    that again, the outcome must stay numerically correct."""
    assert check_guess(guess, "42") == expected


def test_int_and_string_secret_agree():
    """The same guess must get the same answer regardless of the secret's type
    -- this is the even/odd attempt asymmetry the starter had."""
    for guess in range(1, 101):
        assert check_guess(guess, 42) == check_guess(guess, "42")


# --------------------------------------------------------------------------
# Bug 4: scoring was asymmetric, unbounded below, and off by one on a win
# --------------------------------------------------------------------------

def test_wrong_guesses_cost_the_same_regardless_of_parity():
    """The starter ADDED 5 for a 'Too High' on an even attempt."""
    assert update_score(50, "Too High", 2) == update_score(50, "Too Low", 2)
    assert update_score(50, "Too High", 3) == update_score(50, "Too Low", 3)


def test_wrong_guess_costs_five_points():
    assert update_score(50, "Too High", 1) == 45
    assert update_score(50, "Too Low", 4) == 45


def test_score_never_goes_negative():
    assert update_score(0, "Too Low", 1) == 0
    assert update_score(3, "Too High", 2) == 0


def test_first_guess_win_pays_full_points():
    """attempt_number is 1-based; the starter's `attempt_number + 1` against an
    already-incremented counter paid 80 here instead of 100."""
    assert update_score(0, "Win", 1) == 100


def test_win_bonus_decays_with_each_attempt():
    assert update_score(0, "Win", 2) == 90
    assert update_score(0, "Win", 5) == 60


def test_win_bonus_has_a_floor():
    assert update_score(0, "Win", 50) == 10


def test_unknown_outcome_leaves_the_score_alone():
    assert update_score(42, "Something Else", 3) == 42


# --------------------------------------------------------------------------
# Bug 5: Hard was narrower than Normal and had too few attempts to win
# --------------------------------------------------------------------------

def test_ranges_widen_as_difficulty_increases():
    """The starter returned Hard = (1, 50), narrower than Normal = (1, 100)."""
    easy = get_range_for_difficulty("Easy")
    normal = get_range_for_difficulty("Normal")
    hard = get_range_for_difficulty("Hard")

    easy_span = easy[1] - easy[0]
    normal_span = normal[1] - normal[0]
    hard_span = hard[1] - hard[0]

    assert easy_span < normal_span < hard_span


def test_unknown_difficulty_falls_back_to_normal():
    assert get_range_for_difficulty("Nightmare") == get_range_for_difficulty("Normal")


@pytest.mark.parametrize("difficulty", ["Easy", "Normal", "Hard"])
def test_every_difficulty_is_winnable_by_binary_search(difficulty):
    """The starter gave Hard 5 attempts for 50 numbers; binary search needs 6,
    so Hard could not be won even with perfect play."""
    low, high = get_range_for_difficulty(difficulty)
    span = high - low + 1
    assert get_attempt_limit(difficulty) >= math.ceil(math.log2(span))


# --------------------------------------------------------------------------
# parse_guess: input validation
# --------------------------------------------------------------------------

def test_parse_guess_accepts_a_plain_integer():
    assert parse_guess("42") == (True, 42, None)


def test_parse_guess_strips_surrounding_whitespace():
    assert parse_guess("  42  ") == (True, 42, None)


@pytest.mark.parametrize("raw", ["", "   ", None])
def test_parse_guess_rejects_empty_input(raw):
    ok, value, error = parse_guess(raw)
    assert ok is False
    assert value is None
    assert error == "Enter a guess."


def test_parse_guess_rejects_words():
    ok, value, error = parse_guess("fifty")
    assert ok is False
    assert value is None
    assert error == "That is not a number."


def test_parse_guess_rejects_a_fractional_decimal():
    """The starter silently truncated 3.9 to 3 and scored a guess the player
    never made."""
    ok, value, error = parse_guess("3.9")
    assert ok is False
    assert value is None
    assert "Whole numbers" in error


def test_parse_guess_accepts_a_whole_number_written_as_a_decimal():
    assert parse_guess("42.0") == (True, 42, None)


def test_parse_guess_rejects_a_guess_above_the_range():
    ok, value, error = parse_guess("150", 1, 100)
    assert ok is False
    assert error == "Guess must be between 1 and 100."


def test_parse_guess_rejects_a_guess_below_the_range():
    ok, value, error = parse_guess("0", 1, 100)
    assert ok is False
    assert error == "Guess must be between 1 and 100."


def test_parse_guess_accepts_the_range_boundaries():
    assert parse_guess("1", 1, 100) == (True, 1, None)
    assert parse_guess("100", 1, 100) == (True, 100, None)


# --------------------------------------------------------------------------
# End-to-end: a full winning game driven through the logic layer only
# --------------------------------------------------------------------------

def test_a_full_binary_search_game_wins_within_the_attempt_limit():
    """Play Normal the way an optimal player would and assert the hints are
    consistent enough to actually reach the secret."""
    secret = 73
    low, high = get_range_for_difficulty("Normal")
    limit = get_attempt_limit("Normal")

    score = 0
    attempts = 0
    lo, hi = low, high

    while attempts < limit:
        guess = (lo + hi) // 2
        attempts += 1
        outcome = check_guess(guess, secret)
        score = update_score(score, outcome, attempts)

        if outcome == "Win":
            break
        if outcome == "Too High":
            hi = guess - 1
        else:
            lo = guess + 1

    assert outcome == "Win"
    assert attempts <= limit
    assert score > 0
