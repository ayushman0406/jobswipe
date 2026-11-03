# JobSwipe backend (job seeker side)

Stack (all open source): FastAPI + SQLModel/SQLite, Ollama (Qwen2.5 / Llama 3.1) for LLM + tool calling,
BAAI/bge-m3 multilingual embeddings, faster-whisper (en/hi/kn) for voice, Jitsi for meet links.

## Run
    ollama pull qwen2.5:7b-instruct
    pip install -r requirements.txt && cp .env.example .env
    python scripts/seed_jobs.pyc;
    uvicorn app.main:app --reload

## Flow
    POST /users {"name":"H","preferred_lang":"en"}              -> id
    POST /users/1/resume  (pdf file)                             -> resume json (resume_reader)
    GET  /users/1/feed                                           -> swipe cards ranked (match_finder inside)
    POST /users/1/swipe {"job_id":1,"action":"like"}             -> learns preference, creates match(applied)
    POST /users/1/search/refine {"text":"sirf Bengaluru, 25 LPA se upar, remote nahi"}
    POST /users/1/search/voice  (audio file, ?lang=kn optional)  -> transcript + new cards
    GET  /users/1/jobs/1/why                                     -> LLM explanation in user's language
    POST /dev/matches/1/provider-accept                          -> simulates provider; creates meet link
    GET  /users/1/matches

## Ranking
score = 0.55*semantic(pref_vec, job_vec) + 0.30*skill_overlap + 0.15*experience_fit.
pref_vec starts as resume embedding, moves toward liked jobs / away from passed ones. Hard filters from
the agent are applied before ranking; the agent's "focus" phrase is added to the query vector.

## Swap points
- Vector search: numpy now (fine to ~50k jobs) -> pgvector/FAISS/Qdrant.
- Kannada ASR weak? replace voice.transcribe with AI4Bharat IndicConformer.
- Scanned resumes: add OCR (ocrmypdf/tesseract) in resume.resume_reader.
- Job ingestion: add adapters that call matching.add_job (provider API later).
