# 🔍 Ergosign Content Discovery & Competitor Analysis

> NLP-powered competitor content analysis tool built for Ergosign, a German UX design firm — enabling data-driven editorial strategy through automated scraping, topic extraction, and visual analytics.

---

## 📌 Project Overview

This project was developed as part of an industry collaboration between **RMIT University** and **Ergosign GmbH**, a leading UX design firm based in Germany. As **Team Lead** of a 5-person student team, I delivered a working content analytics prototype that helped Ergosign identify competitor content gaps and emerging UX topics to guide their editorial strategy.

The project was delivered using **Agile methodology** with weekly client demonstrations and a final runbook outlining a roadmap for future automation and business adoption.

---

## 🎯 Problem Statement

Ergosign needed visibility into what competitors were publishing across blogs and service pages. Key questions included:

- What topics are competitors writing about?
- What content gaps exist that Ergosign could fill?
- What emerging UX themes should inform their editorial calendar?

Previously, this was done manually with no repeatable or scalable process.

---

## 🛠️ Tech Stack

| Category | Tools |
|----------|-------|
| Web Scraping | Python, BeautifulSoup, ChromeDriver |
| Data Processing | Pandas, Translation APIs |
| AI/LLM | LLM-assisted topic & keyword extraction |
| Visualisation | Word Clouds, Timeline Charts, Topic Charts |
| App Interface | Streamlit |
| Workflow | GitHub, Trello (Agile) |

---

## ✨ Key Features

- **Automated Web Scraping** — Collected competitor blogs and service pages using BeautifulSoup and ChromeDriver
- **Data Preprocessing Pipeline** — Deduplication, translation (DE → EN), and structured labelling of content
- **LLM-Assisted Analysis** — Topic extraction and keyword identification powered by large language models
- **Visual Analytics Dashboard** — Interactive Streamlit dashboard featuring:
  - Word clouds for keyword frequency
  - Timelines showing content publication trends
  - Topic charts comparing competitor focus areas
- **Agile Delivery** — Managed sprints via Trello with weekly demos to the Ergosign client team

---

## 📁 Project Structure

```
Ergosin-Project/
│
├── main.py              # Entry point — orchestrates the full pipeline
├── llm_process.py       # LLM-assisted topic extraction and keyword analysis
├── config.py            # Configuration settings (paths, API keys, parameters)
├── requirements.txt     # Python dependencies
├── .streamlit/          # Streamlit app configuration
└── __pycache__/         # Python cache (auto-generated)
```

---

## 🚀 Getting Started

### Prerequisites

```bash
pip install -r requirements.txt
```

### Run the Streamlit App

```bash
streamlit run main.py
```

---

## 📈 Outcomes & Impact

- Delivered a **working prototype** and comprehensive **runbook** to Ergosign
- Enabled the client to identify **competitor content gaps** and **emerging UX topics**
- Provided a **roadmap for future automation** and business-scale adoption
- Project managed end-to-end with Agile delivery across a **5-month engagement**

---

## 👥 Team & Role

| Detail | Info |
|--------|------|
| **My Role** | Team Lead |
| **Team Size** | 5 members |
| **Client** | Ergosign GmbH, Germany |
| **Institution** | RMIT University, Melbourne |
| **Duration** | July 2025 – November 2025 |

---
*Built as part of RMIT University's Industry Project Program*
