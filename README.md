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
| Models | OpenAI GPT-4o-mini / GPT-4o |

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

Clone the repository:

```bash
git clone https://github.com/yourusername/mtca.git

cd mtca

python -m venv venv

source venv/bin/activate
# Windows:
# venv\Scripts\activate

pip install -r requirements.txt
🔐 Environment Configuration

Create a .env file in the project root:

# -----------------------------
# App & Model Settings
# -----------------------------

ENVIRONMENT=development
DEBUG=True

ROUTER_MODEL=gpt-4o-mini
AGENT_MODEL=gpt-4o-mini

OPENAI_API_KEY=sk-proj-...


# -----------------------------
# Database URLs
# -----------------------------

MONGO_URI=mongodb+srv://<user>:<pass>@cluster.mongodb.net/?retryWrites=true&w=majority

REDIS_URL=redis://default:<pass>@<host>:<port>


# -----------------------------
# Pinecone
# -----------------------------

PINECONE_API_KEY=your_pinecone_api_key

PINECONE_INDEX_NAME=mtca-index


# -----------------------------
# Auth / Security
# -----------------------------

JWT_SECRET_KEY=your_super_secret_jwt_key_here

JWT_ALGORITHM=HS256


# -----------------------------
# External Integrations
# -----------------------------

GOOGLE_SERVICE_ACCOUNT_FILE=service_account.json

RESEND_API_KEY=re_your_resend_key

RESEND_EMAIL=onboarding@resend.dev

⚠️ Important

Place your Google Cloud service_account.json file in the project root.

Add it to .gitignore:

service_account.json
.env
🗄 Data Seeding & Initialization

Before launching the application, initialize:

Tenant configurations
Knowledge bases
Semantic routing examples

All scripts are available inside:

scripts/
Step 1 — Onboard Tenants (MongoDB)

Creates tenant configurations, branch settings, rules, and booking preferences.

python scripts/onboarding_pipeline.py
Step 2 — Process Knowledge Base

Reads raw business documents, cleans content, and creates semantic chunks.

python scripts/chunker.py

Optional:

Review:

chunk_review_debug.md

to validate generated chunks.

Step 3 — Embed Knowledge Base (Pinecone)

Uploads embeddings using dynamic tenant namespaces:

{org_id}_{branch_id}

This guarantees:

✅ Tenant isolation
✅ Branch-specific retrieval
✅ Zero cross-company data leakage

Run:

python scripts/verctor_kb.py
Step 4 — Embed Routing Examples

Creates semantic few-shot examples for intent classification.

Used by the LangGraph router to detect:

Booking requests
Lead capture requests
General conversations

Run:

python scripts/embed_routing_example.py
🏃 Running the Application

MTCA contains:

FastAPI backend
Gradio frontend

Run both separately.

1. Start Backend
uvicorn main:app --reload

Backend:

http://localhost:8000

API Documentation:

http://localhost:8000/docs
2. Start Frontend

Open another terminal:

cd ui

python ui.py

Frontend:

http://localhost:7860
📖 How It Works
1. Authentication

The user selects:

Organization
      ↓
Branch
      ↓
JWT Authentication

The system generates a tenant-aware session.

2. State Initialization

The /chat endpoint:

Extracts org_id
Extracts branch_id
Loads tenant configuration
Initializes MultiTenantState

Storage:

MongoDB
 +
Redis
3. Intent Dispatch (Router)

The LangGraph router analyzes conversation history.

Possible routes:

                User Message
                     |
                     ↓
              Intent Router
                     |
        ┌────────────┼────────────┐
        ↓            ↓            ↓

     Booking   Lead Capture   Conversation


The router handles:

Flow interruptions
Context switching
Resume logic
Cancellation requests
⚙️ Agent Execution Flow
📚 RAG Node

Responsibilities:

Extract search intent
Query Pinecone
Search branch namespace
Return grounded answers

Flow:

User Question
      ↓
Semantic Search
      ↓
Branch Vector Namespace
      ↓
Grounded Response
💼 Lead Capture Node

Responsibilities:

Identify missing information
Ask contextual questions
Extract customer details
Store completed leads

Example:

Customer:
"I need enterprise pricing"

Agent:
"Great. How many users will need access?"

↓

Lead Profile Saved
📅 Booking Node

Responsibilities:

Parse date/time requests
Check Google Calendar availability
Reserve slots
Prevent duplicates
Store booking records
Send confirmation emails

Flow:

Booking Request
        ↓
Availability Check
        ↓
Calendar Reservation
        ↓
Mongo Update
        ↓
Resend Notification
🌟 Why MTCA?

MTCA combines:

✅ Enterprise multi-tenancy
✅ Stateful AI workflows
✅ Retrieval-augmented intelligence
✅ Automated sales operations
✅ CRM-style lead qualification
✅ Calendar automation

into a single scalable conversational sales platform.

🛣 Future Roadmap

Potential extensions:

WhatsApp / SMS channels
Voice agents
Advanced CRM integrations
Analytics dashboard
Agent performance monitoring
Human handoff workflows
Custom enterprise tools