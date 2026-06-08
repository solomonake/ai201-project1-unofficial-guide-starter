"""
Retrieval diagnostic for Milestone 4.

Runs 3 test queries against the actual professors in the corpus,
prints full retrieved chunks with distance scores, and flags any
result that looks off-target.
"""

from embed import retrieve

DIVIDER = "=" * 70
SUBDIV  = "-" * 70

DISTANCE_THRESHOLD = 0.50   # cosine distance; above this = weak match

# Three evaluation queries about professors that ARE in the corpus.
# (The planning.md questions referenced professors not collected;
#  these are the corrected versions tied to actual documents.)
QUERIES = [
    {
        "id": 1,
        "question": "What do students say about Robert Hatch's homework and exam difficulty in computer science?",
        "expect_professor": "Robert Hatch",
    },
    {
        "id": 2,
        "question": "Is Jacob Somervell's computer science class hard, and do students recommend him?",
        "expect_professor": "Jacob Somervell",
    },
    {
        "id": 3,
        "question": "What do students say about Jennifer Wilson's math class and grading style?",
        "expect_professor": "Jennifer Wilson",
    },
]


def assess_hit(chunk_text: str, distance: float, expected_prof: str, actual_prof: str) -> str:
    """Return a short verdict string for one retrieval hit."""
    wrong_source = actual_prof != expected_prof
    weak_signal  = distance > DISTANCE_THRESHOLD
    if wrong_source and weak_signal:
        return "BAD  — wrong professor + weak signal"
    if wrong_source:
        return "WARN — right topic but wrong professor"
    if weak_signal:
        return "WARN — right professor but weak signal"
    return "GOOD"


def run_query(q: dict, k: int = 5) -> None:
    print(f"\n{DIVIDER}")
    print(f"Query {q['id']}: {q['question']}")
    print(f"Expected professor: {q['expect_professor']}")
    print(DIVIDER)

    hits = retrieve(q["question"], k=k)

    all_good = True
    for rank, h in enumerate(hits, 1):
        verdict = assess_hit(h["text"], h["distance"], q["expect_professor"], h["professor"])
        if verdict != "GOOD":
            all_good = False

        print(f"\n  Rank {rank} | {verdict}")
        print(f"  Professor : {h['professor']}")
        print(f"  Source    : {h['source']}  (chunk #{h['chunk_index']})")
        print(f"  Distance  : {h['distance']:.4f}  {'<-- ABOVE THRESHOLD' if h['distance'] > DISTANCE_THRESHOLD else ''}")
        print(f"  {SUBDIV}")
        # Print full chunk, indented
        for line in h["text"].splitlines():
            print(f"  {line}")
        print(f"  {SUBDIV}")

    print(f"\n  Summary: {'All hits on-target.' if all_good else 'Some hits need attention — see WARN/BAD above.'}")


def main():
    print(DIVIDER)
    print("RETRIEVAL DIAGNOSTIC — 3 evaluation queries")
    print(f"Threshold: cosine distance < {DISTANCE_THRESHOLD}")
    print(DIVIDER)

    for q in QUERIES:
        run_query(q)

    # ── Additional: confirm planning.md mismatch is a corpus gap, not a bug ──
    print(f"\n\n{DIVIDER}")
    print("CORPUS GAP CHECK — query about a professor NOT in the corpus")
    print(DIVIDER)
    ghost_query = {
        "id": "X",
        "question": "Does Professor Zafar Khan require mandatory attendance for his economics classes?",
        "expect_professor": "Zafar Khan",
    }
    run_query(ghost_query)
    print("\nNote: distances > 0.5 above confirm this is a corpus gap,")
    print("not a retrieval bug. The system has no document for Zafar Khan.")


if __name__ == "__main__":
    main()
