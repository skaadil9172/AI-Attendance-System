# SnapClass: Technical Interview Prep Guide

This document summarizes the technical architecture, design decisions, machine learning pipelines, and implementation details of SnapClass. Use this guide to prepare for technical interviews.

---

## 📌 Core Architecture & Database Design

### 1. Problem Statement
Traditional attendance systems are inefficient (wasting up to 10% of lecture hours) and vulnerable to attendance fraud (buddy-punching).

### 2. Solution Architecture
SnapClass uses a serverless multi-modal biometrics portal. The Streamlit interface acts as the frontend client. Deep learning pipelines (Dlib & Resemblyzer) compute facial and vocal embeddings locally, which are synced with Supabase. The teacher portal initiates biometric verification runs and writes logs directly to Supabase.

```text
Streamlit Client (app.py) 
  ├── Student Views (Register Face/Voice, Check logs)
  └── Teacher Views (Manage courses, take attendance, view history)
        │
        ├──► Face ID Pipeline ──► Dlib ResNet v1 Model ──► SVC Classifier (Linear)
        ├──► Voice ID Pipeline ──► Resemblyzer Encoder ──► Cosine Similarity (Dot-Product)
        └──► Database Queries ──► supabase-py client ──► Supabase Cloud PostgreSQL
```

### 3. Database Design (PostgreSQL)
SnapClass uses a relational database schema:
*   `teachers`: Storing `teacher_id`, `username`, `password` (encrypted with Bcrypt), and `name`.
*   `students`: Storing `student_id`, `name`, `face_embedding` (128d array), and `voice_embedding` (256d array).
*   `subjects`: Storing `subject_id`, `subject_code` (unique), `name`, `section`, and `teacher_id` (foreign key pointing to `teachers`).
*   `subject_students`: A junction table mapping `student_id` to `subject_id` (representing active student enrollments).
*   `attendance_logs`: Storing unique transaction records mapping `student_id` and `subject_id` to a `timestamp` and a boolean `is_present` flag.

---

## 🧠 AI/ML & Biometric Pipelines

### 1. Face Recognition Workflow
*   **Preprocessing & Detection:** Faces are located in classroom images using Dlib's Frontal Face Detector.
*   **Feature Alignment:** Dlib's 68-point shape predictor localizes key facial landmarks to align the face.
*   **Embedding Generation:** A pre-trained Dlib ResNet model extracts a 128-dimensional floating point embedding vector.
*   **Dynamic Classification:** Instead of standard distance checks against a static list, an SVM classifier (`sklearn.svm.SVC`) with a linear kernel is trained on-the-fly inside the Streamlit instance using templates of students enrolled in that specific course.
*   **Prediction:** The classifier predicts the student ID. A backup threshold filter validates the match by checking if the Euclidean distance between the predicted student's template vector and the query vector is less than or equal to `0.6`.

### 2. Voice Recognition Workflow
*   **Ingestion:** Classroom audio streams are ingested using `librosa.load`, which downsamples input files to a standard sampling rate of 16,000 Hz.
*   **Activity Splitting:** Silence is trimmed, and audio streams are divided into voice intervals using `librosa.effects.split` (dynamic range threshold: `top_db=30`). Segments shorter than 0.5 seconds are ignored.
*   **Embedding Extraction:** The pre-trained Resemblyzer `VoiceEncoder` extracts a 256-dimensional d-vector speech embedding from each voice segment.
*   **Matching & Verification:** Speaker identity is determined by calculating the dot product (equivalent to cosine similarity for normalized vectors) between the extracted embedding and the enrolled templates. A similarity threshold of `>= 0.65` confirms student presence.

---

## 🛠️ Optimizations & Engineering Challenges

### 1. Challenges Faced
*   **Dlib Source Compilations:** Compiling Dlib on system targets without precompiled packages frequently fails.
    *   *Solution:* Integrated a multi-stage Docker build container compiling Dlib within an isolated Debian compiler image, copying built wheels directly to the execution image.
*   **Speech Signal Segments Resolution:** Group classroom voice check-ins contain overlapping signals or silence.
    *   *Solution:* Implemented dynamic windowing and signal-activity boundaries via `librosa.effects.split`, ignoring ambient noise segments.
*   **Cold-start SVM Overfitting:** SVM models require at least 2 distinct classes to perform binary or multi-class fitting.
    *   *Solution:* Implemented exception handling fallback in `face_pipeline.py`. If only one student is enrolled, the classifier skips SVC fitting and falls back to a direct Euclidean distance check.

### 2. Key Learnings & Optimizations
*   **Model Caching:** Biometric encoders (`VoiceEncoder` & Dlib predictors) are heavy to reload. Using Streamlit's `@st.cache_resource` decorator caches model instances in memory, decreasing latency from seconds to milliseconds.
*   **Bulk Database Commits:** Inserting logs row-by-row bottlenecks database connections. SnapClass groups attendance logs into list dictionaries and writes to Supabase using a single bulk insert request.

---

## 💬 12 Key Interview Questions & Answers

#### Q1: Why did you choose to use an SVM classifier for face recognition instead of standard Euclidean distance matching?
**A:** Standard Euclidean distance matching requires doing $O(N)$ comparisons against every student template, which scales poorly. Training an SVM dynamically on the enrolled class list provides a decision boundary that scales better and handles subtle variations in facial features better than raw distance metrics. We also keep a fallback Euclidean distance filter to prevent false positives.

#### Q2: How does the system handle a cold-start where a new subject has only one student enrolled?
**A:** `face_pipeline.py` checks if the number of enrolled student templates is less than 2. If so, the SVM classifier cannot be trained. The pipeline automatically bypasses the SVC training step and performs a direct Euclidean distance check against the single template.

#### Q3: What is the purpose of using Librosa inside the voice recognition pipeline?
**A:** Librosa downsamples incoming audio to 16,000 Hz to match Resemblyzer's training domain. It also splits continuous classroom audio into segments based on silent gaps, filtering out ambient noise and segments shorter than 0.5 seconds.

#### Q4: Why is the dot product used for speaker similarity verification instead of cosine similarity?
**A:** Resemblyzer's VoiceEncoder outputs normalized embeddings. The dot product of two unit-normalized vectors is mathematically equivalent to their cosine similarity, which saves computational overhead.

#### Q5: How do you prevent database connections from slowing down UI rendering in Streamlit?
**A:** Database logic is separated into a dedicated helper module (`src/database/db.py`). Streamlit only interacts with high-level functions, and model weights are cached using `@st.cache_resource` to prevent reloading model weights on every user interaction.

#### Q6: How does the system handle teacher authentication securely?
**A:** Student portals are biometrics-based, while the teacher portal uses username/password credentials. Passwords are encrypted using Bcrypt with a salt round during registration and verified securely via database queries.

#### Q7: What are the dimensions of the biometric embeddings, and why do they matter?
**A:** Face embeddings are 128-dimensional vectors from Dlib's ResNet, while voice embeddings are 256-dimensional vectors from Resemblyzer's VoiceEncoder. Pinned dimensions are crucial because vector similarity algorithms require identical dimensional inputs, and higher dimensions capture more biometric detail but increase database storage size.

#### Q8: Where are the Supabase connection keys stored in production?
**A:** In production, keys are stored in Streamlit Cloud's encrypted secrets settings, which are loaded dynamically at runtime via `st.secrets`. Locally, they are stored in `.streamlit/secrets.toml`, which is ignored by Git to prevent leakages.

#### Q9: What happens if a student registers a profile but does not record a voice template?
**A:** The database stores `voice_embedding` as a nullable field. If a student lacks a voice profile, they are skipped during voice attendance verification, and the system prompts them to record a voice sample.

#### Q10: Why did you pin setuptools<70.0.0 in requirements.txt?
**A:** Older C-extensions in packages like `dlib` or `resemblyzer` rely on deprecated functions in `setuptools`. Pinning `setuptools<70.0.0` prevents installation failures when compiling these libraries on newer systems.

#### Q11: How would you scale the face recognition pipeline for a class size of 10,000 students?
**A:** Instead of training a single SVM dynamically in memory, I would implement **Vector Similarity Search** using PGVector in Supabase. This would allow querying candidate matches using HNSW indexing directly in PostgreSQL.

#### Q12: How would you prevent attendance fraud (e.g. someone showing a photo of a student)?
**A:** I would implement **Face Liveness Detection** using OpenCV to check for physical motion like eye-blinking, head rotation, or texture analysis to distinguish actual 3D faces from flat 2D screens/photos.
