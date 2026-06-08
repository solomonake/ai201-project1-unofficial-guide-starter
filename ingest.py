"""
Stage 1 & 2: Ingest raw reviews from Rate My Professors GraphQL API,
save raw text, clean it, and produce chunked documents ready for embedding.
"""

import json
import base64
import re
import time
import random
import urllib.request
from pathlib import Path

# ── Configuration ─────────────────────────────────────────────────────────────

PROFESSOR_IDS = [
    1416958,  # Robert Hatch — Computer Science
    2469981,
    500943,
    935641,
    1619372,
    1488390,
    1530330,
    817517,
    1452141,
    415903,
]

DOCUMENTS_DIR = Path("documents")
RAW_DIR = DOCUMENTS_DIR / "raw"
CLEAN_DIR = DOCUMENTS_DIR / "clean"
CHUNKS_FILE = DOCUMENTS_DIR / "chunks.json"

CHUNK_SIZE = 400    # characters — matches planning.md
CHUNK_OVERLAP = 50  # characters — matches planning.md

RMP_GRAPHQL = "https://www.ratemyprofessors.com/graphql"
GRAPHQL_QUERY = """
query TeacherRatingsPageQuery($id: ID!) {
  node(id: $id) {
    ... on Teacher {
      id
      firstName
      lastName
      department
      school { name }
      numRatings
      avgRating
      avgDifficulty
      ratings(first: 50) {
        edges {
          node {
            date
            class
            comment
            ratingTags
            grade
            wouldTakeAgain
            qualityRating: helpfulRating
            difficultyRating: clarityRating
          }
        }
      }
    }
  }
}
"""

# ── Helpers ────────────────────────────────────────────────────────────────────

def encode_teacher_id(legacy_id: int) -> str:
    return base64.b64encode(f"Teacher-{legacy_id}".encode()).decode()


def fetch_professor(legacy_id: int) -> dict:
    teacher_id = encode_teacher_id(legacy_id)
    payload = json.dumps({"query": GRAPHQL_QUERY, "variables": {"id": teacher_id}}).encode()
    req = urllib.request.Request(
        RMP_GRAPHQL,
        data=payload,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Content-Type": "application/json",
            "Referer": "https://www.ratemyprofessors.com/",
            "Authorization": "Basic dGVzdDp0ZXN0",
        },
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())


def build_raw_text(data: dict) -> str:
    """Convert GraphQL response into structured plain text."""
    node = data["data"]["node"]
    name = f"{node['firstName']} {node['lastName']}"
    dept = node["department"]
    school = node["school"]["name"]
    avg_rating = node["avgRating"]
    avg_diff = node["avgDifficulty"]
    num_ratings = node["numRatings"]

    lines = [
        f"Professor: {name}",
        f"Department: {dept}",
        f"School: {school}",
        f"Overall Rating: {avg_rating}/5.0",
        f"Difficulty: {avg_diff}/5.0",
        f"Number of Ratings: {num_ratings}",
        "",
    ]

    for edge in node["ratings"]["edges"]:
        r = edge["node"]
        date = r["date"][:10]
        course = r.get("class", "N/A")
        grade = r.get("grade", "N/A")
        quality = r.get("qualityRating", "N/A")
        difficulty = r.get("difficultyRating", "N/A")
        tags = r.get("ratingTags", "")
        would_take_again = r.get("wouldTakeAgain")
        again_str = "Yes" if would_take_again == 1 else ("No" if would_take_again == 0 else "N/A")
        comment = (r.get("comment") or "").strip()

        lines.append(f"--- Review ({date}) ---")
        lines.append(f"Course: {course} | Grade: {grade}")
        lines.append(f"Quality: {quality}/5 | Difficulty: {difficulty}/5 | Would Take Again: {again_str}")
        if tags:
            lines.append(f"Tags: {tags}")
        lines.append(f"Comment: {comment}")
        lines.append("")

    return "\n".join(lines)


def clean_text(raw: str) -> str:
    """Remove artifacts while keeping all substantive review content."""
    text = raw

    # Collapse multiple blank lines to one
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Remove HTML entities if any sneak through
    text = text.replace("&amp;", "&").replace("&nbsp;", " ").replace("&#39;", "'")
    text = text.replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')

    # Remove any leftover HTML tags
    text = re.sub(r"<[^>]+>", "", text)

    # Normalise whitespace within lines
    lines = [" ".join(line.split()) for line in text.splitlines()]
    text = "\n".join(lines)

    return text.strip()


def chunk_text(text: str, source: str, professor_name: str) -> list[dict]:
    """
    Character-level sliding-window chunker.
    chunk_size=400, overlap=50 as specified in planning.md.
    Each chunk carries its source filename and professor name as metadata.
    Chunks that don't already contain the professor name get a prefix so
    pronoun references ("he", "she", "his exams") remain resolvable without
    reading the surrounding context — mitigating the ambiguity risk noted in
    planning.md.
    """
    chunks = []
    start = 0
    length = len(text)

    while start < length:
        end = start + CHUNK_SIZE
        chunk = text[start:end].strip()
        if len(chunk) > 0:
            # Anchor pronoun-heavy mid-document chunks to the professor
            if professor_name not in chunk:
                chunk = f"[{professor_name}] " + chunk
            chunks.append({"text": chunk, "source": source, "professor": professor_name})
        if end >= length:
            break
        start += CHUNK_SIZE - CHUNK_OVERLAP

    return chunks


# ── Pipeline ──────────────────────────────────────────────────────────────────

def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)

    all_chunks = []

    for legacy_id in PROFESSOR_IDS:
        print(f"\n=== Fetching professor {legacy_id} ===")
        raw_path = RAW_DIR / f"prof_{legacy_id}_raw.txt"
        clean_path = CLEAN_DIR / f"prof_{legacy_id}_clean.txt"

        # ── Stage 1: Ingest ──
        try:
            data = fetch_professor(legacy_id)
        except Exception as e:
            print(f"  ERROR fetching {legacy_id}: {e}")
            continue

        raw_text = build_raw_text(data)
        raw_path.write_text(raw_text, encoding="utf-8")
        print(f"  Raw saved → {raw_path} ({len(raw_text)} chars)")

        # ── Stage 2: Clean ──
        clean = clean_text(raw_text)
        clean_path.write_text(clean, encoding="utf-8")
        print(f"  Clean saved → {clean_path} ({len(clean)} chars)")

        # ── Stage 3: Chunk ──
        source_name = clean_path.name
        node = data["data"]["node"]
        prof_name = f"{node['firstName']} {node['lastName']}"
        chunks = chunk_text(clean, source=source_name, professor_name=prof_name)
        all_chunks.extend(chunks)
        print(f"  Chunks produced: {len(chunks)}")

        # Polite delay to avoid hammering the server
        time.sleep(random.uniform(1.0, 2.0))

    # Save all chunks
    CHUNKS_FILE.write_text(json.dumps(all_chunks, indent=2), encoding="utf-8")
    print(f"\n{'='*60}")
    print(f"Total chunks across all documents: {len(all_chunks)}")
    print(f"Chunks saved → {CHUNKS_FILE}")

    # ── Checkpoint: print one full clean document ──────────────────────────────
    print("\n" + "="*60)
    print("SAMPLE CLEAN DOCUMENT (prof_1416958_clean.txt)")
    print("="*60)
    sample = (CLEAN_DIR / "prof_1416958_clean.txt").read_text(encoding="utf-8")
    print(sample)

    # ── Checkpoint: print 5 representative chunks ──────────────────────────────
    print("\n" + "="*60)
    print("5 REPRESENTATIVE CHUNKS")
    print("="*60)
    indices = [0, len(all_chunks)//4, len(all_chunks)//2, 3*len(all_chunks)//4, len(all_chunks)-1]
    for i, idx in enumerate(indices, 1):
        c = all_chunks[idx]
        print(f"\n--- Chunk {i} (index {idx}, source: {c['source']}) ---")
        print(c["text"])
        print(f"[{len(c['text'])} chars]")


if __name__ == "__main__":
    main()
