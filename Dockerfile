# --- Build Stage ---
FROM python:3.10-slim-bullseye AS builder

# Prevent python from writing pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system compilation dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    libopenblas-dev \
    liblapack-dev \
    libx11-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy and install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# --- Final Production Stage ---
FROM python:3.10-slim-bullseye

WORKDIR /app

# Install runtime dependencies (librosa needs soundfile/sndfile, libx11/glib for graphics if needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsndfile1 \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed libraries from the builder stage
COPY --from=builder /root/.local /root/.local
COPY --from=builder /app /app

# Copy application source code
COPY . .

# Update PATH env to find packages installed in user space
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Expose Streamlit default port
EXPOSE 8501

# Run the Streamlit application
ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
