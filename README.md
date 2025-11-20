# 🌌 AetherDB — Natural Language → SQL, Powered by Gemini AI

## **Transform Plain English Into Executable SQL With Intelligence, Safety & Style**

![AI Engine](https://img.shields.io/badge/AI_Engine-Gemini_2.5_Pro-purple?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge)
![UI](https://img.shields.io/badge/UI-Streamlit-magenta?style=for-the-badge)
![Team](https://img.shields.io/badge/Team-COW_PRINT-black?style=for-the-badge)
[![contributors](https://img.shields.io/github/contributors/BU-SENG/foss-project-cow-print.svg)](https://github.com/BU-SENG/foss-project-cow-print/graphs/contributors)
[![open issues](https://img.shields.io/github/issues/BU-SENG/foss-project-cow-print.svg)](https://github.com/BU-SENG/foss-project-cow-print/issues)
[![License](https://img.shields.io/github/license/BU-SENG/foss-project-cow-print)](LICENSE)

AetherDB is a **production-ready AI SQL Assistant** that converts natural language statements like:

➡️ *“Show all students whose surname starts with A”*
into
➡️ `SELECT * FROM students WHERE surname LIKE 'A%';`

It uses:

* **Gemini 2.5 Pro** for advanced reasoning
* **Automatic Schema Awareness**
* **Safe SQL Execution Layer**
* **Streamlit Frontend** with chart visualizations
* **Beautiful UI + Real-time statistics**

This is the **official repository** for the **COW PRINT 🤖 Engineering Team**.

---

## 🔥 Features at a Glance

### 🧠 **Gemini-Powered SQL Generation**

* Natural language → Valid SQL
* Supports SELECT, JOIN, INSERT, DELETE, ALTER, CREATE, DROP, and more
* Automatic join discovery
* Context-aware logic reasoning

### 🗄️ **Database Support**

| Database   | Supported | Notes             |
| ---------- | --------- | ----------------- |
| MySQL      | ✅         | Full CRUD         |
| PostgreSQL | ✅         | Full CRUD         |
| SQLite     | ✅         | Default sample DB |

### 🧩 **Schema Awareness**

* Auto-scans connected databases
* Builds `schema.txt` and `schema_metadata.json`
* Creates specialized schema snapshots per query
* Tracks schema version changes

### 🎨 **Streamlit Frontend**

* Gradient purple UI
* Responsive layout
* Real-time query preview
* Interactive data tables
* Automatic charts (bar/line/scatter/pie)
* Query history + statistics dashboard

### 🛡️ **Safety Layer**

* Detects destructive SQL operations
* Blocks execution unless explicitly allowed
* SQL syntax validation using `sqlglot`
* Dry-run mode
* Automatic rollback on errors

---

## 📦 Project Structure

```
AetherDB/
│
├── Core Modules
│   ├── sqlm.py                # Gemini AI Reasoning Core
│   ├── schema_awareness.py    # Schema Management Engine
│   ├── db_executor.py         # SQL Execution & Safety Module
│   └── command_processor.py   # CLI Processor (Standalone Mode)
│
├── Frontend
│   └── streamlit_app.py       # Beautiful Streamlit UI
│
├── Auto-Generated Files
│   ├── schema.txt
│   ├── schema_metadata.json
│   └── specialized_*.txt
│
├── Configuration
│   ├── .env                    # API keys & settings
│   └── requirements.txt
│
├── Setup
│   └── setup.py               # Automatic installer
│
└── Documentation
    └── README.md              # You're reading this :)
```

---

## 🚀 Quick Start

## **1. Clone the Repository**

```bash
git clone https://github.com/BU-SENG/foss-project-cow-print
cd foss-project-cow-print
```

## **2. Run Setup Wizard**

```bash
python setup.py
```

This will:

✔ Install dependencies
✔ Create `.env`
✔ Configure Gemini AI
✔ Generate `requirements.txt`
✔ Build sample DB for testing

## **3. Add Gemini API Key**

Create `.env`:

```
GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL=models/gemini-2.5-pro
DEFAULT_DIALECT=mysql
MAX_SCHEMA_PROMPT_CHARS=14000
```

## **4. Start the App**

```bash
streamlit run streamlit_app.py
```

Visit **[http://localhost:8501](http://localhost:8501)**

---

## 🧠 How It Works — Full Architecture

```
User → Streamlit UI
      → Schema Awareness Module
      → Gemini Reasoning Core
      → SQL Safety Engine
      → Database Executor
      → Results + Charts + History
```

---

## 🔄 Complete Data Flow

1. User connects to MySQL/PostgreSQL/SQLite
2. Schema Awareness scans DB → generates `schema.txt`
3. User selects tables (ALL / SOME / NONE)
4. User types natural language query
5. Gemini converts NL → SQL with safety metadata
6. SQL Executor validates & safely executes
7. UI presents:

   * Table results
   * Auto-generated charts
   * SQL preview
   * Execution time
   * Query history

---

## 💡 Example Usage

### **1. Basic Filtering**

**NL:**
*"Show students whose surname starts with A"*

**SQL:**

```sql
SELECT * FROM students WHERE surname LIKE 'A%';
```

---

### **2. Aggregate Query**

**NL:**
*"Count how many classes exist"*

**SQL:**

```sql
SELECT COUNT(*) FROM classes;
```

---

### **3. JOIN Query**

**NL:**
*"List students with their class names"*

**SQL:**

```sql
SELECT s.*, c.classname
FROM students s
JOIN classes c ON s.class_id = c.id;
```

---

### **4. Table Creation**

*(Requires “Allow Destructive Operations”)*

**NL:**
*"Create a table courses with id, name, credits"*

**SQL:**

```sql
CREATE TABLE courses (
  id INT PRIMARY KEY,
  name VARCHAR(255),
  credits INT
);
```

---

## 🎨 Frontend Features

### ✔ Clean, modern UI

### ✔ Dark sidebar

### ✔ Real-time preview

### ✔ Smart table selection

### ✔ Automatic charts

### ✔ CSV Export

### ✔ Query history

### ✔ Live execution statistics

Statistics include:

* Total queries executed
* Success vs failed vs blocked
* Execution time average
* Pie chart breakdown

---

## 🛡 Safety System

### Detects & blocks dangerous SQL

* `DROP TABLE`
* `DELETE`
* `UPDATE`
* `ALTER`
* `TRUNCATE`
* `DROP DATABASE`

### Only executes when:

✔ User toggles "Allow Destructive Operations"
✔ SQL passes schema checks
✔ SQL passes dialect validation

### Plus:

* Dry run mode
* Automatic rollback
* Error logs
* Reasoner confidence scores

---

## 🧪 Testing

### Test with sample DB:

```bash
python setup.py
streamlit run streamlit_app.py
```

### Try queries:

* “Show all students”
* “Count students older than 20”
* “Classes with their teachers”

### Run Reasoning Core tests:

```bash
python sqlm.py --run-test
```

### Run CLI mode:

```bash
python command_processor.py
```

---

## 🧩 Programmatic Usage

```python
from sqlm import GeminiReasoner, CommandPayload
from schema_awareness import SchemaAwarenessModule
from db_executor import DatabaseExecutor

sam = SchemaAwarenessModule()
sam.connect_database("sqlite", database="sample.db")

reasoner = GeminiReasoner(schema_snapshot=open("schema.txt").read())
executor = DatabaseExecutor(sam.connection, "sqlite")

payload = CommandPayload(
    intent="select",
    raw_nl="Show all users"
)

output = reasoner.generate(payload)
result = executor.execute_query(output.sql, output.safe_to_execute)

print(result.data)
```

---

## 🔐 Security Best Practices

* Never commit `.env`
* Rotate API keys regularly
* Use read-only DB accounts
* Always review generated SQL
* Do not enable destructive operations globally

---

## 🤝 How to Contribute

We welcome contributions from everyone! This project is built by the community, for the community.

Please read our **[CONTRIBUTING.md](CONTRIBUTING.md)** file to see how you can get started, set up your development environment, and submit your code.

## 📄 License

This project is licensed under the MIT License. See the **[LICENSE](LICENSE)** file for details.


---

# 🧑‍💻 COW PRINT Team

Built with ❤️ to empower developers with AI-powered database reasoning.

---

# 🎉 Start using AetherDB now!

```bash
streamlit run streamlit_app.py
```

Enjoy the magic. ✨🔥

---
