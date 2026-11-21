FROM python:3.13.5-slim
ENV PYTHONHASHSEED=0 PYTHONUTF8=1
RUN pip install --no-cache-dir uv==0.10.6
WORKDIR /app
COPY pyproject.toml uv.lock requirements.txt ./
RUN uv sync --frozen && uv pip install --python .venv/bin/python -r requirements.txt
COPY . .
ENV PATH="/app/.venv/bin:${PATH}"
CMD ["python", "reproduce.py"]
