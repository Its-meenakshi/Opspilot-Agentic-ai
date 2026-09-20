# 🚀 OpsPilot

**OpsPilot** is an AI-powered operations management system designed to help businesses monitor inventory, expenses, products, suppliers, and operational data through a centralized backend.

It combines **AI-powered business tools** with a structured database to simplify everyday operational decision-making.

## ✨ Features

* 📦 **Inventory Management** — Track products, stock levels, and inventory status.
* 🛒 **Product & Supplier Management** — Manage product and supplier records through CRUD operations.
* 💰 **Expense Tracking** — Record and monitor operational expenses.
* 📊 **Business Insights** — Generate useful operational information from stored data.
* 🤖 **AI Business Tools** — Access business operations through structured AI tools.
* 📥 **CSV Import** — Import inventory data efficiently with idempotent imports.
* 🗄️ **MySQL/MariaDB Database** — Reliable relational data storage.
* 🔄 **Full CRUD Operations** — Create, read, update, and delete records across core entities.

## 🛠️ Tech Stack

**Backend**

* Python
* FastAPI
* SQLAlchemy
* PyMySQL

**Database**

* MySQL / MariaDB

**AI & Automation**

* AI-powered business tools
* Agentic workflow integration

**Data**

* CSV-based inventory import

## 📂 Core Modules

```text
OpsPilot
├── Backend
│   ├── Database
│   ├── API Routes
│   ├── Business Logic
│   └── AI Tools
├── Data
│   └── Inventory CSV
└── README.md
```

## ⚙️ Setup

### 1. Clone the repository

```bash
git clone <your-repository-url>
cd OpsPilot
```

### 2. Create a virtual environment

```bash
python -m venv venv
```

Activate it:

**Windows**

```bash
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure the database

Create a MySQL/MariaDB database and configure the required environment variables:

```env
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=
MYSQL_DATABASE=opspilot
```

### 5. Run the application

```bash
uvicorn backend.main:app --reload
```

The API will be available locally through the configured server.

## 📊 Data Import

OpsPilot supports importing inventory data from CSV files.

The import process is designed to be **idempotent**, meaning running the same import multiple times does not unnecessarily create duplicate records.

## 🧠 AI Tools

OpsPilot provides structured tools for interacting with operational data, allowing an AI agent to perform tasks such as:

* Checking inventory
* Finding low-stock products
* Retrieving expense information
* Working with operational records

This allows business data to be accessed through natural-language interactions instead of relying entirely on manual database queries.

## 🧪 Testing

The system was tested against **MariaDB/MySQL**, including:

* Database connection
* Table creation
* CSV import
* Repeated CSV import for idempotency
* CRUD operations across core entities
* AI/business tools

## 🎯 Project Goal

OpsPilot aims to demonstrate how **AI agents + business databases + backend automation** can work together to simplify operational management and provide actionable access to business data.

## 👨‍💻 Built For

**Agentic AI Hackathon 2026 — IIT Bhubaneswar**

---

⭐ If you find this project useful, consider giving the repository a star.
