# 🤖 Multi Utility Chatbot (LangGraph + Streamlit)

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?logo=streamlit&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-1C3C3C?logo=langchain&logoColor=white)
![Gemini](https://img.shields.io/badge/Google%20Gemini-4285F4?logo=googlegemini&logoColor=white)
![FAISS](https://img.shields.io/badge/FAISS-Vector%20Store-0467DF)
![SQLite](https://img.shields.io/badge/SQLite-003B57?logo=sqlite&logoColor=white)

A conversational AI app built with LangGraph and Gemini. It chats with memory, searches the web, fetches stock prices, does calculations, and answers questions about PDFs you upload.

🌐 **Live demo:** <https://langgraph-rag-chatbot-plkxkk39zl8n7y2umuoappd.streamlit.app/>

---

## ✨ Features

- 💬 **Multi-chat with memory:** each chat is its own thread, saved with a LangGraph SQLite checkpointer, so you can switch between past conversations.
- 🏷️ **Auto-generated chat titles:** Gemini turns the first message into a short title.
- 📄 **PDF question answering (RAG):** upload a PDF per chat. It is chunked, embedded with Gemini embeddings and stored in a FAISS index.
- 🛠️ **Tool use:** the agent decides when to call:
  - 🔎 DuckDuckGo web search
  - 📈 Stock price lookup (Alpha Vantage)
  - 🧮 Calculator (add, subtract, multiply, divide)
  - 📚 PDF retrieval tool (`rag_tool`)
- ⚡ **Streaming responses** with a live status indicator while tools run.

## 🧰 Tech Stack

| Area | Tools |
|---|---|
| Language / UI | Python, Streamlit |
| Agent framework | LangGraph, LangChain |
| LLM and embeddings | Google Gemini (`langchain-google-genai`) |
| Retrieval | FAISS, PyPDF |
| Persistence | SQLite checkpointer |
| Tools / APIs | DuckDuckGo (`ddgs`), Alpha Vantage |

## 🧠 How It Works

1. The user sends a message from the Streamlit UI.
2. A LangGraph state graph runs a chat node. Gemini either answers directly or requests a tool call.
3. If a tool is requested, the tool node runs it and returns the result to the chat node, which loops until it produces a final answer.
4. State is checkpointed per thread, so chats can be reopened later.

```
START → chat_node ⇄ tools → END
```

## 🚀 Run Locally

```bash
git clone <your-repo-url>
cd <repo-folder>
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

Create a `.env` file in the project root:

```
GOOGLE_API_KEY=your_google_api_key
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_key
```

Then start the app:

```bash
streamlit run app.py
```

## ☁️ Deployment

Deployed on Streamlit Community Cloud. API keys are provided through Streamlit Secrets and are never committed to the repo.

## ⚠️ Limitations

- This is a demo. On the hosted version, chat history and uploaded PDFs reset when the app restarts, because server storage is temporary.
- All visitors share the same chat list.
- Free API tiers (Gemini, Alpha Vantage) have rate limits.

## 📁 Project Structure

```
app.py            # Streamlit UI, chat titles, thread handling
backend.py        # LangGraph graph, tools, PDF ingestion, checkpointer
requirements.txt  # Dependencies
```

## 🔮 Future Improvements

- 👤 Per-user chat isolation
- 🗄️ Persistent storage (Postgres)
- 🔌 MCP tool integration