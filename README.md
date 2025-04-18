# 💬 Portfolio-LangGraph Bot

This project powers the conversational agent for [Ethan's Portfolio Website](https://portfolio-phi-mocha-72.vercel.app/), built with [LangGraph](https://github.com/langchain-ai/langgraph). It uses OpenAI, Pinecone, and PostgreSQL to serve personalized and interactive chatbot experiences.

📁 **Portfolio Repo:** [github.com/misterworker/Portfolio](https://github.com/misterworker/Portfolio)

---

## 🧪 Getting Started (Local Development)

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

---

### 2. Setup Environment Variables

You’ll need two `.env` files:

#### ✅ Root `.env`
Place this in the root directory (same level as `requirements.txt`):

```env
OPENAI_API_KEY=your_openai_key
PINECONE_API_KEY=your_pinecone_key
DB_URI=your_postgres_connection_string
GITHUB_CONTRIBUTIONS=your_github_username
```

#### ✅ GitHub Script `.env`
Place this inside `scripts/github/.env`:

```env
GIT_TOKEN=your_personal_access_token
AGENT_LINK=https://your-agent-url.com
```

---

### 3. Run the Main API

#### 🔷 PowerShell (Windows)
```powershell
$env:PYTHONPATH = "src"
uvicorn src.main:app --reload --port 8000
```

#### 🐧 Bash / Zsh (Linux/macOS)
```bash
export PYTHONPATH=src
uvicorn src.main:app --reload --port 8000
```

---

### 4. Run API Tests

```bash
python __tests__/apiTest.py
```

---

### 5. Start GitHub Contributions Server

```bash
cd scripts/github
uvicorn contributions_by_year:app --reload --port 8001
```

---

## 🐳 Docker

Make sure your `Dockerfile` is in the project root and references `src.main:app`.

Sample command to build and run:

```bash
docker build -t username/portfolio-bot:1.0.0 .
docker run -p 8000:8000 --env-file .env portfolio-bot
```

---

## 🧠 Project Structure

```
Portfolio-Langgraph/
│
├── src/
│   ├── agents.py
│   ├── build_graph.py
│   ├── db.py
│   ├── helper.py
│   └── main.py
│
├── scripts/
│   └── github/
│       ├── contributions_by_year.py
│       └── .env
│   └── pinecone/
│       └── pc.py
│
├── __tests__/
│       └── apiTest.py
│
├── Dockerfile
├── requirements.txt
└── README.md
```


## 👀 Coming Soon

- Streaming Outputs

---

Enjoy building your bot! 🛠️
