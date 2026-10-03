"""docs/RULES.md is the specification the engine tests cite rule by rule, so
its own numbering has to hold together."""
import collections
import re
from pathlib import Path

RULES = (Path(__file__).parent.parent / "docs" / "RULES.md").read_text(encoding="utf-8")

RULE = r"\d{1,2}\.\d{1,2}(?:\.\d{1,2})?"


def defined():
    """Every numbered rule, section heading and section-18 decision."""
    rules = re.findall(rf"^\*\*({RULE})[ .*]", RULES, re.M)
    heads = re.findall(r"^#{2,3} (\d+(?:\.\d+)?)[. ]", RULES, re.M)
    decisions = re.findall(rf"^- \*\*({RULE}) ", RULES, re.M)
    return rules + heads + decisions


def test_no_rule_number_is_used_twice():
    twice = [n for n, count in collections.Counter(defined()).items() if count > 1]
    assert twice == []


def test_every_rule_cited_exists():
    body = re.sub(rf"^(\*\*|- \*\*){RULE}", "", RULES, flags=re.M)
    cited = set(re.findall(rf"(?<![\d.,])({RULE})(?![\d%]|\.\d)", body))
    assert sorted(cited - set(defined())) == []


def test_every_constant_named_is_in_a_table():
    named = set(re.findall(r"`([A-Z][A-Z_]{2,})`", RULES))
    rows = re.findall(r"^\| `([A-Z_]+)`(?:, `([A-Z_]+)`)?", RULES, re.M)
    in_tables = {name for row in rows for name in row if name}
    assert sorted(named - in_tables) == []
