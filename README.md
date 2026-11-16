# Private Advisor

**A personalized AI advisory web app with user-controlled long-term memory**  
**Status:** Functional local prototype (v0.1) 

This repository contains a cleaned snapshot of Private Advisor v0.1, a full-stack educational project developed beginning in October 2026. It was prepared for review in November 2026 and does not include the original experimental development history.

## What the project does

Private Advisor explores how an AI assistant can provide more context-aware responses across separate conversations. Instead of automatically treating everything said in a chat as a permanent fact, the app extracts candidate long-term memories from the user’s own statements and requires the user to confirm them before they are used in future advice.

### Implemented in v0.1

- **User accounts:** registration and login, with access limited to each user’s own data.
- **AI chat:** multi-conversation chat interface using the OpenAI Responses API.
- **User profile:** editable name, locale, time zone, and response preferences.
- **Memory review:** extracts candidate memories from user messages; candidates start as `pending` and become `active` only after the user confirms them.
- **Cross-conversation personalization:** retrieves active memories and includes relevant user context in later requests.
- **Usage tracking:** shows counts of model calls and input/output tokens.
- **Basic testing:** automated checks for user-scoped profiles and memory access.

**Current limitations:** Memory relevance is based on lightweight keyword matching, not semantic vector search. This is a local educational prototype, not a deployed service. Planned multi-model deliberation (GPT/Claude/Grok) is **not yet implemented**.

**The current frontend primarily uses a Chinese interface and is mainly intended for Chinese-speaking users.** There are plans to introduce a formal i18n (Internationalization) architecture in the future, first supporting switching between Simplified Chinese and English, and reserving the ability to add other languages later.

## Technology

| Layer | Tools |
|---|---|
| Frontend | Next.js, React, TypeScript |
| Backend | Python, FastAPI, SQLAlchemy |
| Storage | PostgreSQL (Docker); SQLite option for local backend development |
| AI | OpenAI Responses API |
| Development | Docker Compose, pytest |

## Example workflow

1. A user mentions an ongoing project and their preferred style of advice.
2. The backend proposes candidate memories for review.
3. The user confirms the relevant memories.
4. In a separate conversation, the application can retrieve the confirmed context to personalize a new answer.

## Run locally

1. Install and start Docker Desktop.
2. From the project root, run:

   ```bash
   cp .env.example .env
   ```

3. Set **your own** `OPENAI_API_KEY` and a long random `JWT_SECRET` in `.env`; never commit that file.
4. Start services:

   ```bash
   docker compose up --build
   ```

5. Open **http://localhost:3000** (web app) or **http://localhost:8000/docs** (API docs).

To stop, press **Control + C**, then run `docker compose down` (without `-v` if you want to preserve the database volume).

### Automated tests

Install backend requirements in an isolated Python environment and run:

```bash
cd backend
pytest -q
```

## Project scope and credits

This is an educational project developed with AI assistance. The broader product concept was developed collaboratively with family. The application has been manually tested locally.
