# Project 1 Planning: The Unofficial Guide

> Write this document before you write any pipeline code.
> Your spec and architecture diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Update the Retrieval Approach and Chunking Strategy sections if you change your approach during implementation.
> Update this file before starting any stretch features.

---

## Domain

<!-- What domain did you choose? Why is this knowledge valuable and hard to find through official channels? -->
This domain covers unofficial student reviews of professors at UVA Wise. This knowledge is highly valuable because official course catalogs don't provide insight into exam difficulty, grading curves, attendance policies, or actual teaching styles.
---

## Documents

<!-- List your specific sources: URLs, subreddit names, forum threads, or file descriptions.
     Aim for at least 10 sources that together cover different subtopics or perspectives within your domain. -->

| # | Source | Description | URL or location |
|---|--------|-------------|-----------------|
| 1 | Rate My Professors | Student reviews, difficulty ratings, and teaching feedback for a UVA Wise professor. | https://www.ratemyprofessors.com/professor/1416958 |
| 2 | Rate My Professors | Student reviews, difficulty ratings, and teaching feedback for a UVA Wise professor. | https://www.ratemyprofessors.com/professor/2469981 |
| 3 | Rate My Professors | Student reviews, difficulty ratings, and teaching feedback for a UVA Wise professor. | https://www.ratemyprofessors.com/professor/500943 |
| 4 | Rate My Professors | Student reviews, difficulty ratings, and teaching feedback for a UVA Wise professor. | https://www.ratemyprofessors.com/professor/935641 |
| 5 | Rate My Professors | Student reviews, difficulty ratings, and teaching feedback for a UVA Wise professor. | https://www.ratemyprofessors.com/professor/1619372 |
| 6 | Rate My Professors | Student reviews, difficulty ratings, and teaching feedback for a UVA Wise professor. | https://www.ratemyprofessors.com/professor/1488390 |
| 7 | Rate My Professors | Student reviews, difficulty ratings, and teaching feedback for a UVA Wise professor. | https://www.ratemyprofessors.com/professor/1530330 |
| 8 | Rate My Professors | Student reviews, difficulty ratings, and teaching feedback for a UVA Wise professor. | https://www.ratemyprofessors.com/professor/817517 |
| 9 | Rate My Professors | Student reviews, difficulty ratings, and teaching feedback for a UVA Wise professor. | https://www.ratemyprofessors.com/professor/1452141 |
| 10 | Rate My Professors | Student reviews, difficulty ratings, and teaching feedback for a UVA Wise professor. | https://www.ratemyprofessors.com/professor/415903 |
---

## Chunking Strategy

<!-- How will you split documents into chunks?
     State your chunk size (in tokens or characters), overlap size, and explain why those
     numbers fit the structure of your documents.
     A review-heavy corpus warrants different chunking than a long FAQ. -->

**Chunk size:** 400 characters

**Overlap:** 50 characters

**Reasoning:** Rate My Professors reviews are typically short, dense paragraphs consisting of 2-4 sentences of highly opinionated text. Using a smaller chunk size (around 400 characters) ensures that each chunk generally maps to a single, distinct student review rather than blurring multiple reviews together. A 50-character overlap prevents sentences from being awkwardly cut in half, ensuring we don't lose the critical association between a professor's name and the specific sentiment being expressed in that sentence.
---

## Retrieval Approach

<!-- Which embedding model are you using (e.g., all-MiniLM-L6-v2 via sentence-transformers)?
     How many chunks will you retrieve per query (top-k)?
     If you were deploying this for real users and cost wasn't a constraint, what tradeoffs
     would you weigh in choosing a different embedding model — context length, multilingual
     support, accuracy on domain-specific text, latency? -->

**Embedding model:** `all-MiniLM-L6-v2` (via `sentence-transformers`)

**Top-k:** 5

**Production tradeoff reflection:** If cost and computing constraints were removed for a production deployment, I would weigh upgrading to a model like OpenAI's `text-embedding-3-small` or `text-embedding-3-large`. While `all-MiniLM-L6-v2` is excellent for zero-cost, local latency, it has a smaller context window and might struggle with highly specific academic slang or complex semantic nuances compared to larger commercial models. However, moving to an API-based model introduces latency and recurring costs, which must be balanced against the need for high-fidelity retrieval.
---

## Evaluation Plan

<!-- List your 5 test questions with their expected correct answers.
     Questions should be specific enough that you can judge whether the system's response
     is right or wrong. "What are good dining halls?" is too vague.
     "What do students say about wait times at [dining hall name] during lunch?" is testable. -->

| # | Question | Expected answer |
|---|----------|-----------------|
| 1 | What do students say about Robert Hatch's homework and exam difficulty in computer science? | Homework is assigned regularly but manageable; tests are challenging but graded fairly — partial credit given if logic is right even when code isn't perfect. He helps students who ask. |
| 2 | Is Jacob Somervell's computer science class hard, and do students recommend him? | Mixed — harsh grading, exams reportedly don't match lectures, pop quizzes hurt grades; but students who engage with him find him helpful and do recommend him. |
| 3 | What do students say about Jennifer Wilson's math class and grading style? | Very positive — clear lectures, genuinely cares about students, tests are hard but extra credit and office hours help; nearly universally recommended. |
| 4 | What is James Vance's teaching style and do students find his math class useful? | Mostly negative — fast lectures, little outside-class support, no grade drops, heavy online component with minimal real instruction; students largely advise avoiding him. |
| 5 | Do students say Matthew Harvey's math class is worth taking despite the difficulty? | Yes — covers material well, goes the extra mile, brings humor to class, and is accessible; pop quizzes and heavy workload are noted but the consensus is he is worth it. |

---

## Anticipated Challenges

<!-- What could go wrong? Name at least two specific risks with reasoning.
     Consider: noisy or inconsistent documents, missing source attribution, off-topic
     retrieval, chunks that split key information across boundaries. -->

1. **Scraping difficulties with JavaScript:** Rate My Professors relies heavily on JavaScript to render its reviews. A simple HTTP request (like `requests.get`) will likely only return the HTML shell without the actual review text. I will likely need to copy the text manually into `.txt` files or use a browser automation tool to get the raw data.
2. **Pronoun ambiguity in chunks:** If a review chunk starts with "He is a really tough grader but fair," the embedding might lose the context of *which* professor "he" refers to if the professor's name was left behind in the previous chunk. This could lead to retrieving a review for the wrong professor during a query.

---

## Architecture

<!-- Draw a diagram of your pipeline showing the five stages:
     Document Ingestion → Chunking → Embedding + Vector Store → Retrieval → Generation
     Label each stage with the tool or library you're using.
     You can use ASCII art, a Mermaid diagram, or embed a sketch as an image.
     You'll use this diagram as context when prompting AI tools to implement each stage. -->
```mermaid
flowchart TD
    A[Document Ingestion<br>Raw RMP Text Files] --> B[Chunking<br>Python Splitter Script]
    B --> C[Embedding<br>sentence-transformers: all-MiniLM-L6-v2]
    C --> D[(Vector Store<br>ChromaDB)]
    E[User Query] --> F[Retrieval<br>Similarity Search top-k=5]
    D --> F
    F --> G[Generation<br>Groq: llama-3.3-70b-versatile]
    G --> H[Query Interface<br>Gradio Web UI]
---

## AI Tool Plan

<!-- For each part of the pipeline below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, which requirements)
     - What you expect it to produce
     - How you'll verify the output matches your spec

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Chunking Strategy section and ask it to implement chunk_text()
     with my specified chunk size and overlap" is a plan. -->

## AI Tool Plan

**Milestone 3 — Ingestion and chunking:**
I will use Claude for this step. I will provide it with my Chunking Strategy section and my raw `.txt` files containing the Rate My Professors reviews. I will prompt Claude to: *"Write a Python script that cleans any HTML boilerplate from these text files and splits the remaining review text into 400-character chunks with a 50-character overlap. Ensure the text splitter respects sentence boundaries so reviews aren't awkwardly cut in half."* I will verify the output by having the script print 5 random chunks to check that they are self-contained and free of HTML tags.

**Milestone 4 — Embedding and retrieval:**
I will provide Claude with my Architecture diagram and the output of the successful chunking script from Milestone 3. I will prompt Claude to: *"Implement the embedding step using `all-MiniLM-L6-v2` via `sentence-transformers`. Store these embeddings in a local ChromaDB collection, attaching the professor's name and source file as metadata for each chunk. Then, write a retrieval function that takes a string query and returns the top 5 most relevant chunks."* I will verify the generated code by running 3 test queries about specific professors and checking that the returned distance scores are below 0.6.

**Milestone 5 — Generation and interface:**
I will provide Claude with my Evaluation Plan, the Grounding Requirement from the assignment, and the Gradio skeleton code. I will prompt Claude to: *"Wire up the ChromaDB retrieval function to Groq's `llama-3.3-70b-versatile` model. Write a strict system prompt that explicitly forces the LLM to answer only using the retrieved chunks, and programmatically append the source metadata to the final response. Finally, integrate this end-to-end flow into the Gradio web UI."* I will verify the system's grounding by asking an out-of-scope question to ensure the prompt successfully forces the model to decline answering.
