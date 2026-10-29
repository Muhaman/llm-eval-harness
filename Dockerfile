FROM python:3.12-slim AS build
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /src
COPY pyproject.toml README.md ./
COPY src ./src
RUN uv venv /opt/venv && uv pip install --python /opt/venv/bin/python .

FROM python:3.12-slim
RUN useradd --uid 10001 --create-home evalh
COPY --from=build /opt/venv /opt/venv
COPY examples /app/examples
ENV PATH="/opt/venv/bin:$PATH" PYTHONUNBUFFERED=1
WORKDIR /app
USER evalh
ENTRYPOINT ["evalh"]
CMD ["--help"]
