# 🚀 AetherDB: AI-Powered Natural Language Database Processor

[![License](https://img.shields.io/github/license/BU-SENG/foss-project-cow-print)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-brightgreen.svg)](https://www.python.org/)
[![AI Engine: Gemini 2.5 Pro](https://img.shields.io/badge/AI_Engine-Gemini_2.5_Pro-purple.svg)](https://deepmind.google/technologies/gemini/)
[![contributors](https://img.shields.io/github/contributors/BU-SENG/foss-project-cow-print.svg)](https://github.com/BU-SENG/foss-project-cow-print/graphs/contributors)
[![open issues](https://img.shields.io/github/issues/BU-SENG/foss-project-cow-print.svg)](https://github.com/BU-SENG/foss-project-cow-print/issues)

**AetherDB** is an intelligent system that transforms natural language (NL) instructions into autonomous database operations. The core of this system is the **🧠 Gemini AI Reasoning Core (`sqlm.py`)**, an engine that converts plain English into precise, executable SQL queries.

Instead of writing complex SQL, you can simply describe what you want. AetherDB's AI engine interprets your intent, generates precise, context-aware SQL commands, executes them, and returns structured results.

> Made with ❤️ by **COW PRINT**

## 🏗️ System Architecture

AetherDB uses a multi-layer AI pipeline that combines structured database intelligence with LLM reasoning. The `sqlm.py` core sits at the heart of this architecture.

```mermaid
┌──────────────────────────────────────────────┐
│               User Interface Layer           │
│  (CLI / Web Dashboard / Voice Input)         │
└─────────────────────┬────────────────────────┘
                      │
                      ▼
┌──────────────────────────────────────────────┐
│           Command Processing Layer           │
│ - Receives NL instruction                    │
│ - Detects intent (create, query, update, etc.)│
│ - Extracts entities and conditions            │
└─────────────────────┬────────────────────────┘
                      │
                      ▼
┌──────────────────────────────────────────────┐
│        Gemini AI Reasoning Core (sqlm.py)    │
│ - Natural language understanding              │
│ - SQL construction and logical reasoning       │
│ - Uses schema awareness and dialect templates  │
└─────────────────────┬────────────────────────┘
                      │
                      ▼
┌──────────────────────────────────────────────┐
│            Database Controller Layer          │
│ - Executes SQL commands                       │
│ - Handles DB responses, errors, transactions  │
│ - Returns clean JSON results to AI core       │
└─────────────────────┬────────────────────────┘
                      │
                      ▼
┌──────────────────────────────────────────────┐
│            Schema Awareness Module            │
│ - Scans all databases, tables, fields         │
│ - Detects types, constraints, relationships   │
│ - Builds structured metadata snapshot         │
│ - Keeps Gemini’s context updated              │
└──────────────────────────────────────────────┘
```

## ✨ Features

* **Natural Language to SQL:** Converts commands like "show me all users" into `SELECT * FROM users;`.
* **Intelligent Reasoning:** Uses **Gemini 2.5 Pro** for advanced logic, joins, and context inference.
* **Schema Aware:** Understands your database structure for accurate, valid query generation.
* **Safety First:** Returns `safe_to_execute` flags and `confidence` scores to prevent accidental destructive operations (like `DROP` or `DELETE`).
* **Modular:** Designed to receive structured `CommandPayload` objects and return `ReasonerOutput` JSON, making it easy to integrate into any backend.

## 🏁 Getting Started

### 1. Prerequisites

* Python 3.10+
* Google Gemini API Key

### 2. Clone the Repository

```bash
git clone [https://github.com/BU-SENG/foss-project-cow-print.git](https://github.com/BU-SENG/foss-project-cow-print.git)
cd foss-project-cow-print
```

### 3. Install Dependencies

We recommend using a Python virtual environment.
```bash
# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate

# Install required packages
pip install google-generativeai python-dotenv
```
*(We recommend creating a `requirements.txt` file for easier setup!)*

### 4. Set Up Environment Variables

Create a `.env` file in the root of the project and add your API key:

```ini
# Your Google Gemini API Key
GEMINI_API_KEY="your_api_key_here"

# The model to use
GEMINI_MODEL="models/gemini-2.5-pro"

# Default SQL dialect (e.g., mysql, postgres, sqlite)
DEFAULT_DIALECT="mysql"
```

## 🚀 How to Run

The Reasoning Core runs as a standalone CLI tool by feeding it a schema file.

### 1. Create a Schema File

Create a `schema.txt` file in the project root to describe your database.

**Example `schema.txt`:**
```SQL
Database: companydb
  Table employees: id, first_name, last_name, department_id, salary
  Table departments: id, department_name, manager_id
  Table projects: id, project_name, department_id, start_date
```

### 2. Run the Core Engine

Run the `sqlm.py` script and pass in your schema file:

```bash
python sqlm.py --schema schema.txt
```

### 3. Start Talking

The application will load and wait for your input.

```bash
Gemini Reasoner (single-file) ready.
Type 'exit' to quit.
Example NL:
  show me students whose surname starts with A
  count how many classes exist
  create a new table called pets with fields name, species, age

NL> show me employees in the Engineering department
SQL => SELECT T1.id, T1.first_name, T1.last_name, T1.department_id, T1.salary
FROM employees AS T1
INNER JOIN departments AS T2 ON T1.department_id = T2.id
WHERE T2.department_name = 'Engineering';

NL>
```

## 🤝 How to Contribute

We welcome contributions from everyone! This project is built by the community, for the community.

Please read our **[CONTRIBUTING.md](CONTRIBUTING.md)** file to see how you can get started, set up your development environment, and submit your code.

## 📄 License

This project is licensed under the MIT License. See the **[LICENSE](LICENSE)** file for details.
