# Project Marketplace Chatbot

A hybrid chatbot built with **Rasa + FastAPI + MySQL + Claude AI**.

## Folder Structure

```
rasa_project/
├── action/
│   └── actions.py        ← All custom Rasa actions + MySQL queries
├── data/
│   ├── nlu.yml           ← 17 intents, 150+ training examples
│   ├── rules.yml         ← 15 strict rule-based triggers
│   └── stories.yml       ← 12 conversation flow stories
├── models/               ← Trained models saved here (auto-generated)
├── config.yml            ← NLU pipeline + policies
├── domain.yml            ← Intents, slots, entities, responses
├── endpoints.yml         ← Action server URL config
├── rasamain.py           ← FastAPI app (main entry point)
├── schema.sql            ← MySQL database schema
└── requirements.txt      ← All Python dependencies
```

## Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Set up MySQL
```bash
mysql -u root -p < schema.sql
```

### 3. Update credentials
Edit `rasamain.py` and `action/actions.py`:
- Replace `your_db_password` with your MySQL password
- Replace `your-anthropic-api-key-here` with your Claude API key

### 4. Run (3 terminals)

**Terminal 1 — Train and start Rasa:**
```bash
rasa train
rasa run --enable-api --cors "*" --port 5005
```

**Terminal 2 — Start action server:**
```bash
rasa run actions --port 5055
```

**Terminal 3 — Start FastAPI:**
```bash
uvicorn rasamain:app --reload --port 8000
```

### 5. Open the chatbot
Visit: http://localhost:8000

## API Endpoints

| Method | URL | Description |
|--------|-----|-------------|
| GET  | `/`                        | Built-in chat test UI |
| POST | `/chat`                    | Send a message to the bot |
| GET  | `/health`                  | Check Rasa + FastAPI status |
| GET  | `/projects/search?q=python` | Search projects from DB |
| GET  | `/chat/history/{session_id}` | Get chat history |

## How It Works

1. User sends message → FastAPI `/chat` endpoint
2. FastAPI forwards to Rasa → Rasa classifies intent
3. If Rasa confidence ≥ 0.70 → rule-based response
4. If Rasa confidence < 0.70 or empty → Claude AI fallback
5. All messages saved to MySQL `chat_messages` table
