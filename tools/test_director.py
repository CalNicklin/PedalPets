import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import director as dr  # noqa: E402

MOVES = ["wave", "beckon", "sweep"]


def summary(**kw):
    s = {"t": 0, "character": "skeleton", "mood": "Curious", "energy": 0.2, "intent": "None", "thought": "",
         "familiarity": 0.5, "silence_s": 0.5, "notes": 0, "hits": 0, "played_s": 100}
    s.update(kw)
    return s


def test_to_line_validates_everything():
    line = dr.to_line({"intent": "WantsYou", "for_s": 99, "move": "wave", "look": "you",
                       "thought": 'play "that", again; please?'}, MOVES)
    assert line.startswith("#D ")
    assert "intent=WantsYou" in line and "for=30000" in line and "move=wave" in line and "look=you" in line
    thought = line.split("thought=")[1]
    assert "," not in thought and '"' not in thought and ";" not in thought


def test_to_line_drops_what_it_doesnt_know():
    assert dr.to_line({"intent": "Dance", "move": "moonwalk"}, MOVES) is None
    assert dr.to_line({}, MOVES) is None
    assert len(dr.to_line({"thought": "x" * 100}, MOVES).split("thought=")[1]) == dr.THOUGHT_MAX


def test_rules_misses_a_friend_once_per_silence():
    r = dr.Rules(seed=1)
    d = r.decide(summary(silence_s=10), MOVES)
    assert d["intent"] == "WantsYou" and d["move"] == "wave" and d["look"] == "you"
    assert r.decide(summary(silence_s=14), MOVES) == {}        # said it already
    r.decide(summary(silence_s=0.5), MOVES)                    # you played again
    assert r.decide(summary(silence_s=10), MOVES)["intent"] == "WantsYou"


def test_rules_stays_quiet_asleep_and_with_strangers():
    r = dr.Rules(seed=1)
    assert r.decide(summary(mood="Asleep", silence_s=10), MOVES) == {}
    assert r.decide(summary(familiarity=0.1, silence_s=10), MOVES) == {}
