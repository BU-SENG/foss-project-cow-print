CONTRIBUTOR : ANURIAM ISAAC 22/0004

```markdown
# 🧠 Gemini AI Reasoning Core (`sqlm.py`)

The **Gemini AI Reasoning Core** is the intelligent engine that transforms **natural language (NL) instructions** into precise, executable **SQL queries**.  
It uses **Google’s Gemini 1.5 Pro** model to understand intent, apply schema awareness, and generate safe SQL — serving as the brain of your AI-driven database management system.

---

## 🚀 Overview

The Reasoning Core sits at the heart of your multi-layer architecture:

```

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
│              Gemini AI Reasoning Core        │
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

````

---

## 🧩 Features

- ⚙️ Converts **natural language commands** into SQL queries  
- 🧠 Uses **Gemini 1.5 Pro** for reasoning and logic inference  
- 🧾 Integrates **schema awareness** for contextually accurate queries  
- 🛡️ Includes **execution safety flags** and confidence scores  
- 🔄 Accepts structured payloads from the **Command Processing Layer**  
- 🔍 Returns structured JSON to the **Database Controller Layer**

---

## 📦 Installation

```bash
pip install google-generativeai python-dotenv
````

Create a `.env` file in the project root:

```
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-1.5-pro
DEFAULT_DIALECT=mysql
```

---

## ⚙️ Configuration

| Variable                  | Description                             | Default          |
| ------------------------- | --------------------------------------- | ---------------- |
| `GEMINI_API_KEY`          | Your Google Gemini API key              | —                |
| `GEMINI_MODEL`            | Gemini model version                    | `gemini-1.5-pro` |
| `DEFAULT_DIALECT`         | SQL dialect (`mysql`, `postgres`, etc.) | `mysql`          |
| `MAX_SCHEMA_PROMPT_CHARS` | Limit on schema size sent to Gemini     | `14000`          |

---

## 🧠 Usage Example

### 1. Run the core directly

```bash
python sqlm.py --schema schema.txt
```

### 2. Example CLI Interaction

```
Gemini Reasoner (single-file) ready.
Type 'exit' to quit.
Example NL:
  show me students whose surname starts with A
  count how many classes exist
  create a new table called pets with fields name, species, age

NL> show me all employees whose surname starts with A
SQL => SELECT * FROM employees WHERE surname LIKE 'A%';
```

---

## 🧰 Code Structure

### `GeminiReasoner`

Main orchestrator class that handles:

* Prompt construction
* Gemini API call
* Query validation
* Result packaging

### `CommandPayload`

Input data structure provided by the Command Processing Layer:

```python
CommandPayload(
  intent="query",
  raw_nl="Show all employees in the Engineering department",
  entities={"table": "employees", "filter": "department='Engineering'"},
  schema_snapshot=current_schema_dict
)
```

### `ReasonerOutput`

Structured output returned to the Database Controller Layer:

```python
{
  "sql": "SELECT * FROM employees WHERE department='Engineering';",
  "confidence": 0.93,
  "safe_to_execute": true,
  "warnings": [],
  "errors": [],
  "metadata": {...}
}
```

---

## ⚖️ Adjustable Runtime Variables (Frontend-Controlled)

| Variable               | Type    | Purpose                                                 |
| ---------------------- | ------- | ------------------------------------------------------- |
| `allow_destructive`    | `bool`  | Allow dangerous operations like `DROP` or `DELETE`      |
| `dialect`              | `str`   | Switch between SQL dialects                             |
| `safe_to_execute`      | `bool`  | Execution safety flag from Reasoner (can be overridden) |
| `confidence_threshold` | `float` | Minimum confidence before automatic execution           |
| `schema_refresh`       | `bool`  | Forces schema reload before reasoning                   |
| `target_db`            | `str`   | Specify which database context to reason in             |

---

## 🧬 Integration with Other Layers

### 🔹 Command Processing Layer → Gemini Reasoner

Detects user intent, extracts entities, and sends structured payload:

```python
payload = CommandPayload(
    intent="query",
    raw_nl="list all employees in Engineering",
    entities={"table": "employees"},
    schema_snapshot=schema_module.snapshot()
)
response = reasoner.reason(payload)
```

### 🔹 Gemini Reasoner → Database Controller Layer

Controller executes the SQL if `safe_to_execute` and confidence ≥ threshold:

```python
if response.safe_to_execute and response.confidence >= 0.85:
    db.execute(response.sql)
else:
    prompt_user_for_approval(response.sql)
```

### 🔹 Schema Awareness Module → Gemini Reasoner

Keeps Gemini’s context current:

```python
schema = schema_module.generate_snapshot()
reasoner.update_schema(schema)
```

---

## 🧪 Testing with Sample Schema

Create a `schema.txt` file (example: `companydb`):

```
Database: companydb
  Table employees: id, first_name, last_name, department_id, salary
  Table departments: id, department_name, manager_id
  Table projects: id, project_name, department_id, start_date
```

Run:

```bash
python sqlm.py --schema schema.txt
```

Example query:

```
NL> show me employees in the Engineering department who earn above 100000
```

---

## 🧱 Internal Data Flow

1. **Command Processor:** extracts user intent → builds payload
2. **Gemini Reasoner:** transforms NL → SQL
3. **Database Controller:** validates and executes SQL safely
4. **Schema Awareness Module:** updates schema context dynamically

---

## 🧭 Example Real-World Query

> “Show me the full names, departments, and total hours worked last month for all employees who have participated in at least two projects managed by the same department they belong to, whose average performance score in the last three reviews is above 80, and whose total bonuses this year exceed 10% of their annual base salary.”

This complex prompt will challenge Gemini’s reasoning on joins, aggregates, and conditional logic — ideal for validating the engine’s depth.

---

## 🔐 Safety & Reliability

* All reasoning outputs are flagged with:

  * `safe_to_execute` → ensures destructive SQL isn’t auto-run.
  * `confidence` → helps filter low-certainty outputs.
  * `warnings` → highlights potential schema or logic ambiguities.

---

## 🧩 Future Enhancements

* Context memory for follow-up queries
* Schema compression for large databases
* Read-only “sandbox execution” mode
* Automatic dialect adaptation
* Advanced query explanation in natural language

---

## 👨‍💻 Author Notes

This module is part of the larger **AI Database Automation System**, where the Gemini Reasoning Core acts as the **intelligent SQL processor**.
All layers are modular — you can integrate this core into REST APIs, CLI tools, or GUI dashboards seamlessly.

---



