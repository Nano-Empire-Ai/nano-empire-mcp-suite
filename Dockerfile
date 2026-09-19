FROM python:3.12-slim
WORKDIR /app
RUN pip install uv
COPY . /app/
RUN uv pip install --system -e .
ENV HOST=0.0.0.0
ENV PORT=8080
CMD ["sh", "-c", "python -m uvicorn src.nano_mcp_suite.x402_gateway:app --host 0.0.0.0 --port ${PORT}"]
