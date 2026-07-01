# 🤖 Multi-Tenant Conversational Sales Agent (MTCA)

> **Enterprise-grade conversational AI infrastructure for B2B SaaS operators**  
> Built with **FastAPI + LangGraph**, MTCA enables multiple organizations and branches to operate autonomous AI sales agents on shared infrastructure while maintaining **strict tenant isolation, contextual memory, and secure data boundaries**.

MTCA dynamically routes conversations across:

- 📚 **Knowledge Base Q&A (Agentic RAG)**
- 💼 **Stateful Lead Capture**
- 📅 **Automated Calendar Booking**
- ✉️ **Transactional Email Notifications**

Each organization gets its own AI-powered sales assistant while sharing a scalable, production-ready backend.

---

# ✨ Core Features

## 🏢 Multi-Tenant Architecture

Strict tenant and branch-level data isolation.

Users interacting with **Organization A / Branch X** can only access:

- Their branch-specific knowledge base
- Their business rules
- Their calendar availability
- Their CRM data

Powered by dynamic namespace separation and tenant-aware routing.

---

## 🧠 LangGraph Orchestration

Stateful, graph-based conversational workflows.

The agent intelligently manages complex conversations:

✅ Handles user interruptions  
✅ Supports multi-step flows  
✅ Maintains conversation state  
✅ Resumes interrupted workflows seamlessly  

Example:

> User starts booking → asks business hours → receives answer → booking continues automatically

---

## 📚 Agentic RAG

Organization-specific knowledge retrieval powered by:

- Pinecone Vector Database
- Semantic search
- Grounded context generation

The agent retrieves only relevant branch-specific information to prevent hallucination and data leakage.

---

## 📅 Calendar & Booking Automation

Native Google Calendar integration.

Capabilities:

- Real-time availability checking
- Event creation
- Rescheduling
- Cancellation handling
- Double-booking prevention

Powered through Google Service Accounts.

---

## 💼 Stateful Lead Capture

Conversational CRM collection without rigid forms.

The agent intelligently extracts:

- Customer intent
- Budget
- Product requirements
- Contact details
- Additional qualification data

Information is collected naturally throughout the conversation.

---

## ✉️ Automated Communications

Integrated with Resend for automated customer communication.

Supports:

- HTML booking confirmations
- Follow-up emails
- Event notifications

---

# 🏗 Architecture & Tech Stack

## 🧠 AI Orchestration

| Component | Technology |
|---|---|
| Agent Framework | LangGraph |
| LLM Framework | LangChain |
| Models | OpenAI|

---

## ⚡ Backend

| Component | Technology |
|---|---|
| API Framework | FastAPI |
| Server | Uvicorn |
| Validation | Pydantic |

---

## 🗄 Databases

| Purpose | Technology |
|---|---|
| Authentication & Tenant Config | MongoDB Atlas |
| Leads & Booking Indexes | MongoDB Atlas |
| Vector Search / RAG | Pinecone |
| Conversation State Memory | Redis |

---

## 🔌 Integrations

| Service | Purpose |
|---|---|
| Google Calendar API | Scheduling |
| Resend Email API | Notifications |

---

## 🎨 Frontend

| Component | Technology |
|---|---|
| UI Portal | Gradio |
| Theme | Dark-mode interface |

---

# 🚀 Getting Started

## 1. Prerequisites

Create accounts and obtain API credentials for:

- OpenAI
- Pinecone
- MongoDB Atlas
- Redis
- Google Cloud Console
- Resend

Required services:


OpenAI
├── LLM Generation
└── Embeddings

Pinecone
└── Vector Database

MongoDB
└── Tenant Data + CRM

Redis
└── LangGraph State Checkpointing

Google Calendar API
└── Booking Automation

Resend
└── Transaction Emails


---

# 📦 Installation

# 🚀 MTCA — Multi-Tenant Conversational AI Platform

<p align="center">
  <b>Enterprise-grade AI agents for sales, support, and business automation.</b>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue?logo=python" />
  <img src="https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi" />
  <img src="https://img.shields.io/badge/LangGraph-Agent%20Workflow-purple" />
  <img src="https://img.shields.io/badge/MongoDB-Database-green?logo=mongodb" />
  <img src="https://img.shields.io/badge/Pinecone-Vector%20Search-blueviolet" />
</p>

---

## 🌐 Overview

**MTCA (Multi-Tenant Conversational AI)** is a scalable AI-powered conversational platform designed for organizations that need intelligent automation across multiple businesses, branches, and workflows.

It combines:

- 🤖 LLM-powered conversations
- 🧠 Stateful AI workflows
- 🔍 Retrieval-Augmented Generation (RAG)
- 🏢 Enterprise multi-tenancy
- 📅 Calendar automation
- 💼 Lead qualification
- 📊 CRM-style customer intelligence

MTCA enables businesses to deploy intelligent AI agents while maintaining strict tenant and branch-level data isolation.

---

# ⚡ Quick Start

## 1. Clone Repository

```bash
git clone https://github.com/yourusername/mtca.git

cd mtca
```

---

## 2. Create Virtual Environment

```bash
python -m venv venv
```

Activate:

### Linux / macOS

```bash
source venv/bin/activate
```

### Windows

```bash
venv\Scripts\activate
```

---

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

# 🔐 Environment Configuration

Create a `.env` file in the project root:

```env
# ==================================
# Application & Model Configuration
# ==================================

ENVIRONMENT=development
DEBUG=True

ROUTER_MODEL=gpt-4o-mini
AGENT_MODEL=gpt-4o-mini

OPENAI_API_KEY=sk-proj-...


# ==================================
# Database Configuration
# ==================================

MONGO_URI=mongodb+srv://<user>:<pass>@cluster.mongodb.net/?retryWrites=true&w=majority

REDIS_URL=redis://default:<pass>@<host>:<port>


# ==================================
# Vector Database
# ==================================

PINECONE_API_KEY=your_pinecone_api_key

PINECONE_INDEX_NAME=mtca-index


# ==================================
# Authentication & Security
# ==================================

JWT_SECRET_KEY=your_super_secret_jwt_key

JWT_ALGORITHM=HS256


# ==================================
# External Integrations
# ==================================

GOOGLE_SERVICE_ACCOUNT_FILE=service_account.json

RESEND_API_KEY=re_your_resend_key

RESEND_EMAIL=onboarding@resend.dev
```

---

# ⚠️ Security Configuration

Place your Google Cloud credentials in the project root:

```
service_account.json
```

Never commit secrets.

Add to `.gitignore`:

```gitignore
.env
service_account.json
```

---

# 🗄 Database Seeding & Initialization

Before starting MTCA, initialize:

- 🏢 Tenant configurations
- 📚 Knowledge bases
- 🧠 Semantic routing examples

All initialization scripts are located in:

```
scripts/
```

---

# 1️⃣ Tenant Onboarding (MongoDB)

Creates:

- Organization settings
- Branch configurations
- Business rules
- Booking preferences

Run:

```bash
python scripts/onboarding_pipeline.py
```

---

# 2️⃣ Knowledge Base Processing

Processes business documents:

- Cleans raw content
- Creates semantic chunks
- Prepares documents for embedding


Run:

```bash
python scripts/chunker.py
```

Optional review:

```
chunk_review_debug.md
```

---

# 3️⃣ Knowledge Embedding (Pinecone)

Uploads embeddings using tenant-isolated namespaces:

```
{org_id}_{branch_id}
```

Guarantees:

✅ Tenant isolation  
✅ Branch-level retrieval  
✅ Zero cross-company data leakage  

Run:

```bash
python scripts/verctor_kb.py
```

---

# 4️⃣ Routing Example Embeddings

Creates semantic few-shot examples for intent detection.

Used by the LangGraph router for:

- 📅 Booking requests
- 💼 Lead capture
- 💬 General conversations

Run:

```bash
python scripts/embed_routing_example.py
```

---

# 🏃 Running MTCA

MTCA contains:

```
Backend  → FastAPI
Frontend → Gradio
```

Run both separately.

---

# 1. Start Backend

```bash
uvicorn main:app --reload
```

Backend:

```
http://localhost:8000
```

API Documentation:

```
http://localhost:8000/docs
```

---

# 2. Start Frontend

Open another terminal:

```bash
cd ui

python ui.py
```

Frontend:

```
http://localhost:7860
```

---

# 🧠 System Architecture

## 1. Authentication Flow

```
Organization
      |
      ↓
Branch Selection
      |
      ↓
JWT Authentication
      |
      ↓
Tenant-Aware Session
```

The system creates isolated sessions for every organization and branch.

---

# 2. State Initialization

The `/chat` endpoint:

1. Extracts `org_id`
2. Extracts `branch_id`
3. Loads tenant configuration
4. Creates `MultiTenantState`

Storage:

```
MongoDB
   +
Redis
```

---

# 3. Intent Router

The LangGraph router analyzes conversation context.

```
                User Message
                     |
                     ↓
              Intent Router
                     |
        ┌────────────┼────────────┐
        ↓            ↓            ↓

    Booking     Lead Capture   Conversation
```

Handles:

✅ Flow interruptions  
✅ Context switching  
✅ Resume logic  
✅ Cancellation requests  

---

# ⚙️ Agent Execution Pipeline

## 📚 RAG Node

Responsible for intelligent knowledge retrieval.

Responsibilities:

- Detect search intent
- Query Pinecone
- Search branch namespace
- Generate grounded answers


Flow:

```
User Question
      ↓
Semantic Search
      ↓
Tenant Vector Namespace
      ↓
Grounded Response
```

---

# 💼 Lead Capture Node

Automatically qualifies customers.

Responsibilities:

- Identify missing information
- Ask contextual questions
- Extract customer details
- Store qualified leads


Example:

```
Customer:
"I need enterprise pricing"

Agent:
"How many users need access?"
```

↓

```
Lead Profile Created
```

---

# 📅 Booking Node

Automates scheduling workflows.

Responsibilities:

- Parse date/time requests
- Check Google Calendar availability
- Reserve appointments
- Prevent duplicates
- Send confirmations


Flow:

```
Booking Request
        ↓
Availability Check
        ↓
Calendar Reservation
        ↓
MongoDB Update
        ↓
Email Notification
```

---

# 🌟 Why MTCA?

MTCA combines:

| Capability | Description |
|---|---|
| 🏢 Multi-Tenancy | Enterprise organization isolation |
| 🤖 AI Agents | Stateful intelligent workflows |
| 🔍 RAG | Knowledge-grounded responses |
| 💼 Lead Automation | Automated qualification |
| 📅 Scheduling | Calendar-based booking |
| 🔐 Security | Tenant-aware authentication |

into one scalable conversational AI platform.

---

# 🛣 Roadmap

Future improvements:

- 💬 WhatsApp / SMS channels
- 🎙 Voice AI agents
- 🔗 Advanced CRM integrations
- 📊 Analytics dashboard
- 📈 Agent performance monitoring
- 👥 Human handoff workflows
- 🛠 Custom enterprise tools

---