# ReturnGuard System Architecture: Two-Phase Asynchronous Pipeline

To handle heavy AI workflows (Gemini / Groq) safely without encountering Redis lock timeouts, duplication bugs, or frozen tasks, ReturnGuard implements a **Two-Phase Async Ingestion & Processing Pipeline**.

---

## 🏗️ Technical Workflow Overview

```text
[ Client Request ] 
       │
       ▼
┌────────────────────────────────────────────────────────┐
│ PHASE 1: Fast Intake (Takes < 0.01 seconds)             │
│ 1. FastAPI accepts payload.                             │
│ 2. PostgreSQL inserts row with status: 'pending_ai'.   │
│ 3. Push a lightweight job trigger to Redis (arq).       │
│ 4. Worker claims job and instantly sends ACK to Redis.  │
│ 5. FastAPI returns `202 Accepted` to frontend.          │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼ (Message is safely removed from Redis queue)
┌────────────────────────────────────────────────────────┐
│ PHASE 2: Independent AI processing (No Redis Ticking Clock)│
│ 1. Arq Worker reads PostgreSQL Row ID.                 │
│ 2. Updates status to 'processing' + started_at timestamp│
│ 3. Executes slow AI evaluation (Gemini/Groq APIs).      │
│ 4. Updates database status to 'completed' or 'failed'. │
└────────────────────────────────────────────────────────┘
```

---

## 🚦 Error Handling & Fault Tolerance Strategies

### 1. Eliminating Duplicate Processing (The "Race Condition" Fix)
In a single-queue setup, if an AI worker takes 45 seconds to finish but the Redis timeout is 30 seconds, Redis will unlock the message and hand it to a duplicate worker. 

**Our Solution:** In Phase 1, the worker issues an **instant Acknowledgment (ACK)** to Redis the millisecond the data safely lands in PostgreSQL. Because the message is completely deleted from Redis within 1 second, **it is impossible for a timeout race condition to occur.**

### 2. Discarding Poison Pills (Permanent Errors)
If a payload contains malformed JSON or unparseable corrupted image files, retrying it will continuously crash our workers.
* **Action:** The system catches validation exceptions immediately in code, skips the automatic queue retry loops, marks the row as `failed`, and logs the error description to `error_log` for developer triage.

### 3. Database-Driven Crash Recovery (The Cron Monitor)
If a worker physically crashes (e.g., Out Of Memory errors or a server disconnection) mid-way through a heavy model task in Phase 2, the job will become stuck in a `"processing"` state.

**Automated Rescue System:**
Instead of a rigid queue timeout, we use a time-based rule in our database schema:
* An `arq` background **Cron Job** executes natively every 60 seconds.
* It identifies any database row that has been stuck in a `"processing"` state for **longer than 5 minutes** (based on `started_processing_at`).
* The monitor safely resets the row status back to `"pending_ai"` and re-enqueues the job ID back into `arq` to try again on a healthy process thread.

---

## ⚙️ Core Configuration Variables

* **Redis Lock Duration / Visibility Timeout:** Not dynamic. It can remain short since Phase 1 handles ingestion instantly.
* **Worker Concurrency Limit (`max_jobs`):** Managed in `app.worker.WorkerSettings`. Since our models rely on network web requests to Gemini and Groq APIs, the limit is bound by API rate ceilings rather than local GPU hardware restrictions.
