# MTCA — Multi-Tenant Conversational AI Backend

A production-grade, multi-tenant conversational AI backend designed to orchestrate tenant-isolated AI assistants. MTCA equips multiple organizations with capabilities like enterprise knowledge retrieval, dynamic lead qualification, intelligent appointment scheduling, and persistent, asynchronous conversational workflows.

## 🎯 Core Design Goal

> **Allow multiple organizations to share the same AI infrastructure while keeping their data, business rules, conversations, and integrations completely isolated.**

MTCA combines **FastAPI**, **LangGraph**, **OpenAI**, **MongoDB**, **Redis**, and **Pinecone** to coordinate stateful conversations that move naturally between different operational workflows without losing context.

---

## 💡 Why This Project?

Most conversational AI blueprints focus on single-tenant architectures connected to an LLM. Production-ready enterprise software requires solving complex system design hurdles simultaneously:

* **Multi-Tenancy:** Multiple independent organizations sharing a unified backend infrastructure.
* **Isolated Knowledge Bases:** Strict data boundaries preventing cross-tenant document leaks.
* **Persistent Conversation State:** Maintaining rich history across long communication spans.
* **Enterprise Security:** Robust authentication and granular authorization layers.
* **External Ecosystem Integrations:** Native connection with calendars, CRMs, and communication tools.
* **Asynchronous Workflows:** Long-running multi-turn dialogs that users can interrupt and resume at will.

---

## 🏛️ Architectural Design Principles

Rather than organizing the codebase around fragile prompt-engineering patterns, MTCA is built strictly on rock-solid architectural foundations:

### 1. Zero-Trust Tenant Isolation
Every inbound request undergoes rigorous authentication resolving to a distinct organization and branch. Following validation, the backend instantiates a **Tenant-Aware Context State**:

$$\text{Tenant Context} = \big\{ \text{Org ID}, \text{Branch ID}, \text{Business Config}, \text{Calendar Mapping}, \text{Vector Namespace} \big\}$$

This state automatically propagates downstream across the entire execution graph. Rather than forcing individual microservices or graph nodes to compute multi-tenancy access scopes, **the active tenant context is injected natively into every executable component.**

Isolation guarantees apply universally across all sub-systems:
* Knowledge Retrieval
* Lead Storage
* Conversation History
* Calendar Operations
* Business Rules
* Email Notifications

Vector isolation leverages **Pinecone Namespaces** dynamically structured using a cryptographic delimiter format:
`{organization_id}_{branch_id}`
This strictly ensures semantic search vectors never cross corporate organizational boundaries.

### 2. Stateful Conversation Management & Context Resilience
Unlike typical stateless chat architectures that treat each user query as an isolated event, MTCA models dialogue as a long-running distributed workflow state machine. 

```
[User Request] ────────────────────────┐
                                       ▼
                         ┌──────────────────────────┐
                         │   Active Workflow State  │
                         ├──────────────────────────┤
                         │ • Conversation History   │
                         │ • Active Node Pointer    │
                         │ • Booking Pipeline Stage │
                         │ • Lead Profile Payload   │
                         │ • Contextual Intent Flags│
                         └──────────────────────────┘
                                       │
                                       ▼
                    [State Evaluated & Updated in Redis]
```

Because the execution graph state persists reliably across execution loops, users can seamlessly interrupt processes without breaking system memory:

```
User: "I'd like to schedule a product demo."
  │
  └──► [Booking Workflow Initiated]
        │
        └──► User: "Before that, what enterprise features do you offer?"
               │
               ├──► [Booking Workflow Suspended]
               ├──► [Knowledge Retrieval Node Invoked & Answer Delivered]
               │
               └──► [Booking Workflow Resumed from Checkpoint]
```
Workflows can gracefully **start, suspend, resume, terminate, and recover** after multi-turn interruptions—mimicking natural human communication structures instead of rigid, linear form-filling logic.

### 3. Graph-Based Workflow Orchestration
MTCA decouples monolithic conversational agents into modular, specialized execution units managed via **LangGraph**. Responsibilities are isolated into dedicated graph nodes:
* **Knowledge Retrieval Node:** Handles RAG pipelines and semantic documentation lookups.
* **Lead Qualification Node:** Dynamically evaluates customer profiles against qualifying criteria.
* **Appointment Scheduling Node:** Interacts with booking infrastructure APIs.

This modular separation allows team developers to scale, iterate, or deploy new domain nodes without breaking existing conversation logic.

### 4. Context-Aware Routing Matrix
Routing paths are dynamically computed by parsing the overarching systemic context instead of relying solely on the latest user text array. The router systematically evaluates:
* The current active node workflow context
* Historical dialogue records
* Tenant-specific business configurations
* Real-time semantic similarity weights
* Embedded routing few-shot examples

```
[Booking Request] ──► [Business Hours Validation] ──► [Knowledge Lookup] ──► [Booking Completion]
```

### 5. Tenant-Aware Knowledge Retrieval (RAG Pipeline)
Information security is tightly coupled to the vector ingestion and retrieval lifecycle:

```
[User Query] ──► [Extract Tenant Context] ──► [Intent Detection] ──► [Scope to Branch Namespace] ──► [Semantic Search Execution] ──► [Grounded Response]
```
Restricting vector queries exclusively to the resolved tenant namespace programmatically neutralizes any possibility of cross-organization information disclosure.

### 6. Conversational Lead Qualification
Static input forms are replaced with asynchronous conversational profile building. When a business-critical datapoint is missing, the workflow smoothly introduces soft follow-up questions within the conversational flow. 
The system naturally extracts and persists:
* Full contact identification profiles
* Company information & vertical metrics
* Budget ranges & procurement authority
* Technical / product product scope requirements
* High-level timeline & business milestones

### 7. Native Appointment Scheduling
The calendar infrastructure layer is exposed directly to the LangGraph execution layer. When a scheduling intent is parsed and validated, the engine safely triggers actions directly against external APIs:
* Dynamic availability lookup matrices
* Real-time calendar slot reservations
* Automated cancellation and scheduling modifications
* Instant transactional confirmation dispatches

Calendar operations use the organizational metadata configuration mapped during the initial authentication phase, allowing a shared microservice cluster to connect to isolated calendars across hundreds of tenants.

### 8. Durable Memory Checkpointing
State longevity is anchored via **Redis Checkpointers**. Persisting execution state at every node transition allows conversational graphs to seamlessly wake up upon receiving incoming messages, avoiding memory rebuild cycles and optimizing compute consumption.

---

## 🏗️ System Architecture

```
                             [ User ]
                                │
                                ▼
                      [ Authentication Layer ]
                                │
                                ▼
               [ Tenant & Branch Resolution Engine ]
                                │
                                ▼
                    [ MultiTenantState Payload ]
                                │
                                ▼
                     [ LangGraph Router Core ]
             ┌──────────────────┼──────────────────┐
             ▼                  ▼                  ▼
    [ Knowledge Engine ]  [ Lead Capture ]   [ Booking Node ]
             │                  │                  │
             ▼                  ▼                  ▼
       [(Pinecone)]       [(MongoDB Atlas)]  [Google Calendar API]
                                                   │
                                                   ▼
                                              [(Resend API)]
```

---

## 🛠️ Technology Ecosystem

| Component | Technology | Enterprise Purpose |
| :--- | :--- | :--- |
| **API Framework** | FastAPI | High-performance, async-first REST infrastructure. |
| **Workflow Engine** | LangGraph | Stateful, cyclically controlled conversation graph management. |
| **LLM Orchestration** | LangChain | Standardized tool bindings and advanced prompt layout patterns. |
| **Language Models** | OpenAI GPT-4o / Models | Context-aware responses and structural JSON extractions. |
| **Primary Data Layer** | MongoDB Atlas | Distributed document store for multi-tenant config and leads. |
| **Vector Indexing** | Pinecone | Hardware-accelerated semantic search isolated by namespaces. |
| **Durable Checkpoints** | Redis | High-speed, atomic checkpointing for system graph memory. |
| **Calendar Sync** | Google Calendar API | Enterprise schedule synchronization and booking management. |
| **Communication** | Resend | Programmatic, high-deliverability transactional email pipelines. |
| **Demonstration UI** | Gradio | Developer-friendly real-time prototyping interface. |

---

## 🚀 Engineering Highlights

* **Token-Based Security:** JWT-based user and tenant authentication parsing.
* **Multi-Tenant Isolation Matrix:** Native session management and dependency injection patterns.
* **Advanced DAG Control:** Directed Acyclic Graph structures utilizing LangGraph logic.
* **State Hydration & Dehydration:** Native workflow suspension and resumption over asynchronous intervals.
* **Intent Classification System:** Few-shot semantic intent routers preventing graph decay.
* **Enterprise Integration Patterns:** Concurrent connections with cloud database layers and transactional notification providers.

---

## 🔮 Roadmap & Future Directions

* [ ] **Omnichannel Support:** Native ingestion adapters for WhatsApp, SMS, and messaging networks.
* [ ] **Voice Topology:** Integration with sub-100ms streaming text-to-speech and automated speech recognition services.
* [ ] **Human-in-the-Loop (HITL):** Seamless live-agent handoff routines with conversational history synchronization.
* [ ] **CRM Bridges:** Direct sync connectors targeting Salesforce, HubSpot, and custom enterprise databases.
* [ ] **Observability Console:** Distributed tracing dashboards mapping graph execution costs, token optimization analytics, and error vectors.
* [ ] **Localization Matrix:** Context-aware multilingual capabilities adapting to regional idioms in real-time.