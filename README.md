# 🗄️ DataPilot AI

> **Ask questions about your data in plain English. Get SQL queries, charts, and insights instantly.**

[![Live Demo](https://img.shields.io/badge/Live%20Demo-datapilot--ai--ac.streamlit.app-ff4b4b?style=for-the-badge&logo=streamlit)](https://datapilot-ai-ac.streamlit.app/)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Groq](https://img.shields.io/badge/Groq-LLaMA%203.3%2070B-F55036?style=for-the-badge)](https://console.groq.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.45+-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io)

---

## What is DataPilot AI?

DataPilot AI is an intelligent data analytics copilot that lets you upload any CSV or Excel file and instantly query it using natural language — no SQL knowledge required. It generates SQL, executes it, visualizes the results, and explains the findings using a state-of-the-art LLM.

```
User: "Show me top 5 customers by revenue in Q3"
  ↓
DataPilot: Generates SQL → Executes → Charts → Insights
```

---

## ✨ Features

### 🧠 Natural Language → SQL
Type questions in plain English. DataPilot converts them to SQLite queries using LLaMA 3.3 70B via Groq's ultra-fast inference API.

### 💬 Conversational Analytics
Ask follow-up questions with full context. "Only show Delhi" or "Compare with last month" — DataPilot remembers the conversation.

### 🔗 Multi-Table JOIN (NEW)
Upload 2 files and ask questions across them. DataPilot auto-detects join keys with confidence scoring and pins the correct key in every query — no hallucinated joins.

### 📊 Auto Visualization
Every query result gets an appropriate chart — bar, line, scatter, or pie — powered by Plotly.

### 🏥 Data Health Report
On upload, DataPilot analyzes your dataset for null values, duplicates, outliers, and data quality issues, scoring it from 0–100.

### 🔒 Query Validation
Every generated SQL is validated for safety before execution. DROP, DELETE, UPDATE, INSERT are blocked at the validator layer — not just by prompt.

### 📁 Smart Ingestion
- CSV with auto-encoding detection (UTF-8, Latin-1, CP1252)
- Excel with multi-sheet support and dirty header cleaning
- Unicode column names sanitized (Hindi, Gujarati, special chars)
- Merged cells and blank rows handled automatically

---

## 🏗️ Architecture


![DataPilot AI Architecture](assets/arch.png)


## 🚀 Quick Start

### 1. Clone the repo
```bash
git clone https://github.com/aasthac26/DataPilot-AI.git
cd DataPilot-AI
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Set up your API key
```bash
cp .env.example .env
# Edit .env and add your Groq API key
# Get a free key at https://console.groq.com
```

### 4. Run the app
```bash
streamlit run app.py
```

Open `http://localhost:8501` in your browser.

---

## 🔧 Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Streamlit |
| LLM | LLaMA 3.3 70B via Groq |
| Database | SQLite (per-session) |
| Data Processing | Pandas, NumPy |
| Visualization | Plotly |
| Excel Parsing | OpenPyXL |
| HTTP Client | HTTPX |

---

## 📁 Project Structure

```
DataPilot-AI/
├── app.py                  # Main Streamlit app
├── core/
│   ├── ingestion.py        # File loading + schema detection
│   ├── nl_to_sql.py        # Natural language → SQL generation
│   ├── validator.py        # SQL safety validation
│   ├── database.py         # SQLite session management
│   ├── explainer.py        # SQL explanation
│   ├── visualizer.py       # Chart generation
│   ├── insights.py         # AI-generated insights
│   ├── conversation.py     # Conversational memory
│   ├── multi_table.py      # JOIN key detection
│   └── health_analyzer.py  # Data quality scoring
├── ui/
│   ├── sidebar.py          # Upload + session info
│   ├── chat_interface.py   # Chat UI components
│   └── result_display.py   # Result rendering
├── utils/
│   ├── llm_client.py       # Groq API wrapper
│   └── schema_utils.py     # Schema formatting helpers
├── database/
│   └── sessions/           # Per-session SQLite files
├── .streamlit/
│   └── config.toml         # Streamlit config
├── requirements.txt
└── .env.example
```

---

## 💡 Example Queries

**Single table:**
- "Show top 10 customers by revenue"
- "Which months had sales above 50,000?"
- "What is the average order value by region?"
- "Show me rows where discount is greater than 20%"

**Multi-table JOIN:**
- "Show employee names with their department"
- "Which departments have more than 10 employees?"
- "Find employees who joined after 2022 with their manager names"

**Follow-up (conversational):**
- "Only show results from Mumbai" *(after a previous query)*
- "Now sort by revenue descending"
- "What's the percentage breakdown?"

---

## ⚙️ Configuration

Create a `.env` file with:
```env
GROQ_API_KEY=your_groq_api_key_here
```

Optional — `.streamlit/config.toml`:
```toml
[server]
maxUploadSize = 50

[theme]
base = "dark"
```

---




*Powered by Groq · LLaMA 3.3 70B · SQLite · Streamlit*
