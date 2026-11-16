"""Print all history or the context for one battle or trial chapter."""
import argparse

from . import for_chapter, load, markdown, problems


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--chapter", help="trial chapter or independent battle id")
args = parser.parse_args()
record = load()
issues = problems(record)
if issues:
    raise SystemExit("Invalid historical record: " + "; ".join(issues))
if args.chapter:
    story = for_chapter(args.chapter, record)
    if story is None:
        raise SystemExit(f"No historical context for {args.chapter}")
    record["episodes"] = [story] if "chapters" in story else []
    record["battles"] = [story] if "chapter" in story else []
print(markdown(record))
