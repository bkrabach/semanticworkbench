FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml uv.lock ./
RUN pip install uv && \
    uv pip install -e .

# Copy the application
COPY . .

# Expose ports
EXPOSE 8000 9000 9100

# Set the entrypoint
CMD ["python", "-m", "app.main"]