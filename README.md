# The Unofficial Guide — Project 1

> **How to use this template:**
> Complete each section *after* you've built and tested the corresponding part of your system.
> Do not write placeholder text — if a section isn't done yet, leave it blank and come back.
> Every section below is required for submission. One-liners will not receive full credit.

---

## Domain

This system covers unofficial student reviews of professors at the University of Virginia College at Wise. Specifically, it ingests Rate My Professors reviews for 10 UVA Wise professors across the Computer Science and Mathematics departments.

This knowledge is valuable because official course catalogs tell you nothing about how a professor actually teaches — their exam style, grading fairness, homework load, or how available they are outside class. A student trying to choose between two sections of Calculus I has no official way to learn that one instructor curves every exam while the other does not. Rate My Professors fills that gap, but browsing it professor-by-professor is slow. A retrieval-augmented system lets a student ask a natural-language question and get an answer grounded in many reviews at once.

---

## Document Sources

| # | Source | Type | URL or file path |
|---|--------|------|-----------------|
| 1 | Rate My Professors — Robert Hatch | Web (GraphQL API) | https://www.ratemyprofessors.com/professor/1416958 |
| 2 | Rate My Professors — David Frazier | Web (GraphQL API) | https://www.ratemyprofessors.com/professor/2469981 |
| 3 | Rate My Professors — Jacob Somervell | Web (GraphQL API) | https://www.ratemyprofessors.com/professor/500943 |
| 4 | Rate My Professors — James Vance | Web (GraphQL API) | https://www.ratemyprofessors.com/professor/935641 |
| 5 | Rate My Professors — Matthew Harvey | Web (GraphQL API) | https://www.ratemyprofessors.com/professor/1619372 |
| 6 | Rate My Professors — Daniel Ray | Web (GraphQL API) | https://www.ratemyprofessors.com/professor/1488390 |
| 7 | Rate My Professors — Yvonne Jessee | Web (GraphQL API) | https://www.ratemyprofessors.com/professor/1530330 |
| 8 | Rate My Professors — Alex Edwards | Web (GraphQL API) | https://www.ratemyprofessors.com/professor/817517 |
| 9 | Rate My Professors — Carlos Otero | Web (GraphQL API) | https://www.ratemyprofessors.com/professor/1452141 |
| 10 | Rate My Professors — Jennifer Wilson | Web (GraphQL API) | https://www.ratemyprofessors.com/professor/415903 |

Raw documents are saved in `documents/raw/` and cleaned versions in `documents/clean/`. The site uses JavaScript rendering, so a plain HTTP request returns only a shell. All review data was fetched through Rate My Professors' internal GraphQL API endpoint, which returns structured JSON including each review's comment, course, date, grade, quality rating, difficulty rating, and tags.

---

## Chunking Strategy

**Chunk size:** 400 characters

**Overlap:** 50 characters

**Why these choices fit your documents:** Rate My Professors reviews are short, dense paragraphs — typically 2–4 sentences expressing a single opinion. A 400-character window captures roughly one complete review plus the immediately surrounding metadata (course, grade, quality score), which gives the embedding model enough context to understand both *what* is being said and *about whom*. Smaller chunks risked splitting a review mid-sentence and losing the association between a rating tag ("Tough grader") and the comment that explains it. Larger chunks would blur multiple reviews together, diluting the specific signal a query needs to match.

The 50-character overlap prevents a sentence from being cleanly severed at a boundary. Without overlap, a review like "His tests are challenging, but he grades them fairly" could appear in two chunks with neither containing the full sentence.

One discovered risk from planning.md was pronoun ambiguity: a chunk starting "He is a really tough grader" carries no information about *which* professor "he" refers to if the professor's name appeared in the preceding chunk. This was fixed in `ingest.py` by prepending `[Professor Name]` to any chunk that did not already contain the professor's name. This anchor is included in the embedded text so the vector for that chunk encodes the professor identity, not just the sentiment.

**Final chunk count:** 81 chunks across 10 documents.

---

## Embedding Model

**Model used:** `all-MiniLM-L6-v2` via `sentence-transformers`. Embeddings are 384-dimensional unit-normalised vectors. The vector store uses cosine distance (configured via `metadata={"hnsw:space": "cosine"}` at collection creation), which gives scores in [0, 1] where lower means more similar. Strong matches in this corpus have distances below 0.35; scores above 0.50 reliably indicate that the retrieved chunk is not about the queried professor.

**Production tradeoff reflection:** For a real deployment, the most meaningful upgrade would be to `text-embedding-3-small` (OpenAI) or a fine-tuned bi-encoder trained on student-review text. `all-MiniLM-L6-v2` was trained on general web text, so it handles informal phrasing and academic slang reasonably well, but it has a 256-token context limit — a long review that exceeds that is silently truncated before embedding, which loses information. A model with a 512- or 8192-token window (e.g., `bge-large-en-v1.5` or `text-embedding-3-large`) would be better suited to longer, multi-review chunks. The tradeoff is latency and cost: `all-MiniLM-L6-v2` runs locally in milliseconds with no API key; a hosted model adds ~100ms of network latency per query and recurring cost per token.

---

## Grounded Generation

**System prompt grounding instruction:**

```
You are an assistant that helps students at the University of Virginia College at
Wise learn about professors based on Rate My Professors reviews.

STRICT RULES — follow all of them:
1. Answer ONLY from the context passages provided below. Do not use any outside
   knowledge, general reasoning, or information from your training data.
2. If the context does not contain enough information to answer the question,
   respond with exactly: "I don't have enough information in my documents to answer that."
3. Do not guess, speculate, or fill gaps with plausible-sounding information.
4. When you cite a detail, attribute it naturally in the sentence
   (e.g., "Students report that…", "According to reviews…", "One reviewer noted…").
5. Keep your answer concise — 3 to 6 sentences unless the question genuinely
   requires more detail.
```

The prompt uses numbered rules rather than soft suggestions specifically because language models respond more reliably to explicit, enumerated constraints than to prose instructions like "please use only the documents." Rule 2 provides an exact fallback string the model is told to return verbatim, which makes it possible to detect the no-information case programmatically if needed.

**How source attribution is surfaced in the response:** Source attribution is assembled programmatically in `query.py` before the LLM call runs. After `retrieve()` returns the top-k chunks, the code builds a deduplicated list of `"Professor Name (source_filename)"` strings from the chunk metadata. This list is passed to the UI as a separate field — the LLM never touches it. Even if the model ignored citation instructions entirely, the UI still shows the correct sources. The retrieved chunks are also labelled with `[Passage N — Professor | filename]` inside the user message, so when the model writes "According to reviews…" it is drawing on labelled passages and the reader can cross-check.

---

## Evaluation Report

| # | Question | Expected answer | System response (summarized) | Retrieval quality | Response accuracy |
|---|----------|-----------------|------------------------------|-------------------|-------------------|
| 1 | What do students say about Robert Hatch's homework and exam difficulty in computer science? | Homework is regular but manageable; tests are challenging but fairly graded with partial credit for correct logic even when code is not perfect. | "Homework is regular but not too tough. Tests are challenging but graded fairly — partial credit given if logic is right. Varying opinions on difficulty; grading criteria are clear." | Relevant — all 5 chunks from Hatch, distances 0.26–0.36 | Accurate |
| 2 | Is Jacob Somervell's computer science class hard, and do students recommend him? | Mixed — harsh grading, exams don't match lectures, pop quizzes hurt grades; but students who engage find him helpful and recommend him. | "Difficulty rated 3.9/5. Homework challenging for basic concepts. Students generally recommend him — good feedback, respected, hilarious. Pop quizzes can affect grade." | Relevant — all 5 chunks from Somervell, distances 0.30–0.37 | Accurate |
| 3 | What do students say about Jennifer Wilson's math class and grading style? | Very positive — clear lectures, caring, tests are hard but extra credit and office hours help; nearly universally recommended. | "Classes are challenging (5/5 difficulty). Explains concepts clearly, always available to help. Tests difficult, homework assigned and graded. Office hours key to success. Students highly recommend her." | Relevant — all 5 chunks from Wilson, distances 0.29–0.32 | Accurate |
| 4 | What is James Vance's teaching style and do students find his math class useful? | Mostly negative — fast lectures, little outside-class support, no grade drops, heavy online component; students largely advise avoiding him. | "Good feedback and clear criteria, but lectures are fast. Some find him great and helpful; others describe chaotic lectures. Students suggest putting in effort to get value from the class." | Partially relevant — all Vance chunks but mix of rare positive and dominant negative reviews | Partially accurate |
| 5 | Do students say Matthew Harvey's math class is worth taking despite the difficulty? | Yes — covers material well, goes the extra mile, accessible, pop quizzes and workload are noted but consensus is he is worth it. | "One student would take again despite D+ grade. Warns of pop quizzes and test-heavy grading. Another got an A. Overall limited info — unclear if worth it." | Off-target — rank-1 chunk was James Vance, not Harvey; only 2 of 5 chunks were Harvey | Inaccurate |

**Retrieval quality:** Relevant / Partially relevant / Off-target
**Response accuracy:** Accurate / Partially accurate / Inaccurate

---

## Failure Case Analysis

**Question that failed:** "Do students say Matthew Harvey's math class is worth taking despite the difficulty?"

**What the system returned:** A hedging, inconclusive answer that said "it's unclear if most students find the class worth taking." The system cited James Vance as a source alongside Matthew Harvey, and Vance dominated the retrieved set with 3 of 5 top chunks.

**Root cause (tied to a specific pipeline stage):** The failure is in the **retrieval stage**, caused by a phrase-level semantic collision between the query and an unrelated professor's review text.

The query contains the phrase "worth taking despite the difficulty." James Vance's chunk #33 contains the sentence: *"Was he hard? Yes! Was it worth it? Yes!"* This review is structurally and semantically very close to the query — both use the pattern "hard/difficult + worth it." The cosine distance for that Vance chunk (0.29) was lower than the best Harvey chunk (0.35), so Vance ranked first.

Matthew Harvey has only 6 reviews and 7 total chunks — the fewest meaningful content of any professor in the corpus. With so little text, the embedding for his collection is sparse, and his chunks didn't happen to use the phrasing "worth it" or "worth taking." The embedding model matched the *phrasing pattern* of the query rather than the *subject* of the query, because Harvey's actual reviews discuss pop quizzes, classroom comfort, and lecture pace — not the "is it worth it" framing.

This is a corpus density problem compounded by query-phrasing sensitivity: a professor with very few reviews cannot compete semantically with a professor whose reviews happen to share the query's exact vocabulary.

**What you would change to fix it:** Two complementary fixes:

1. **Collect more reviews for low-density professors.** Harvey has 6 reviews; the professors where retrieval worked well (Hatch: 10, Wilson: 23, Somervell: 13) have substantially more. More reviews mean more chunks, and more chunks mean more opportunities to match the query from the correct source.

2. **Add professor-name filtering to retrieval when the query names a specific professor.** If a query contains a known professor name, pre-filter the ChromaDB query with `where={"professor": "Matthew Harvey"}` to restrict results to that professor's chunks. This trades recall (you can't retrieve cross-professor comparisons) for precision, which is the right tradeoff for single-professor questions.

---

## Spec Reflection

**One way the spec helped you during implementation:**

The planning.md section on anticipated challenges forced an early decision about the Rate My Professors scraping problem before any code was written. The spec named JavaScript rendering as a specific risk and noted that a plain HTTP request would return an empty shell. This pushed the implementation away from `requests` + BeautifulSoup and toward the site's internal GraphQL API, which returned clean structured JSON for every review including date, grade, quality, difficulty, and tags. Without that pre-written diagnosis, it would have been easy to write a scraper, discover it returned no content, and waste time debugging what was actually an architectural constraint. The spec turned a runtime surprise into a planned decision.

**One way your implementation diverged from the spec, and why:**

The chunking strategy in planning.md described a plain character-level split with 400-character chunks and 50-character overlap. The implementation added a professor-name prefix — `[Robert Hatch]` — to any chunk that did not already contain the professor's name. This was not in the spec. The spec did anticipate pronoun ambiguity as a risk ("if a review chunk starts with 'He is a really tough grader,' the embedding might lose the context of which professor 'he' refers to"), but the proposed mitigation was vague. During chunk inspection it became clear that overlap alone was insufficient: a chunk starting mid-sentence with "l tips and if you visit him during office hours" had no professor identity at all, and the 50-character overlap only carried partial sentence text, not a name. The prefix fix was added at the chunking stage rather than at query time because injecting it into the text means the embedding itself encodes the professor's identity — not just the sentiment — which directly improves retrieval precision.

---

## AI Usage

**Instance 1 — Ingestion pipeline and scraping strategy**

- *What I gave the AI:* The Documents table from planning.md (10 Rate My Professors URLs), the Anticipated Challenges section describing the JavaScript rendering problem, and the project structure showing an empty `documents/` directory. I asked it to write `ingest.py` that collected reviews, saved raw text, cleaned it, and produced chunks matching the 400/50 character spec.
- *What it produced:* A complete `ingest.py` using the Rate My Professors internal GraphQL API to bypass the JavaScript barrier, a `clean_text()` function that stripped HTML entities and collapsed whitespace, and a `chunk_text()` function with the specified character sliding window.
- *What I changed or overrode:* The initial generated chunker produced chunks with no professor identity on mid-document segments. After inspecting 5 sample chunks and seeing one begin with `"l tips and if you visit him during office hours"` with no professor name, I directed the AI to add a `[Professor Name]` prefix to any chunk that did not contain the name — solving the ambiguity the spec had flagged but not resolved. I also directed it to switch the ChromaDB distance metric from the default L2 to cosine after seeing that distances of 0.54 were above the 0.5 threshold and would fail the retrieval checkpoint.

**Instance 2 — Grounded generation and Gradio interface**

- *What I gave the AI:* The system architecture diagram from planning.md, the grounding requirement (answers from retrieved context only, no outside knowledge, explicit "I don't have enough information" fallback), the output format (answer + source list), and the Gradio skeleton structure from the milestone instructions. I asked it to wire retrieval → prompt → Groq API → UI into `query.py` and `app.py`.
- *What it produced:* `query.py` with a system prompt containing numbered grounding rules, a `_build_context()` function that labelled each passage with professor name and filename, a call to `groq.chat.completions.create()` at temperature 0.2, and programmatic source assembly from chunk metadata before the LLM call. `app.py` with a two-column Gradio layout showing answer and sources with retrieval diagnostics (distance scores per chunk).
- *What I changed or overrode:* The initial version left attribution entirely to the LLM — it instructed the model to list sources in its response but never guaranteed they would appear. I redirected the AI to separate source assembly from LLM output: sources are built from `chunk["professor"]` and `chunk["source"]` metadata in Python, passed to the UI as a distinct field, and the LLM response never touches them. This guarantees attribution even if the model ignores the citation instruction.
