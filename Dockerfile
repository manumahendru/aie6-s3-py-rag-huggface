# Multi-stage build for a smaller final image
# Stage 1: Build the React frontend
FROM node:20-slim AS frontend-build

WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install

# Copy frontend source code
COPY frontend/ ./
RUN npm run build

# Stage 2: Python application with frontend static files
FROM python:3.12-slim

# Install Node.js for serving the frontend
RUN apt-get update && apt-get install -y \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Add user - this is the user that will run the app
RUN useradd -m -u 1000 user

# Set the home directory and path
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH
    
# Set the environment variable for WebSocket
ENV UVICORN_WS_PROTOCOL=websockets

# Set the working directory
WORKDIR $HOME/app

# Copy the backend code
COPY --chown=user backend/ ./backend/

# Copy the built React app
COPY --chown=user --from=frontend-build /app/frontend/build ./frontend/build/

# Install backend requirements
USER root
RUN pip install --no-cache-dir -r backend/requirements.txt

# Install serve globally
RUN npm install -g serve

# Switch back to non-root user
USER user
WORKDIR $HOME/app

# Copy the entrypoint script
COPY --chown=user docker-entrypoint.sh ./
RUN chmod +x docker-entrypoint.sh

# Expose ports
EXPOSE 8000 3000

# Set the entrypoint
ENTRYPOINT ["./docker-entrypoint.sh"]