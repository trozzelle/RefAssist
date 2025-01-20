FROM python:3.13.1-slim-bookworm AS python-base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    WORKDIR_PATH="/opt/ref-assist" \
    VIRTUAL_ENV="/opt/ref-assist/.venv"

ENV PATH="$VIRTUAL_ENV/bin:$PATH"

FROM python-base AS builder-base

COPY --from=ghcr.io/astral-sh/uv:0.5.15 /uv /bin/uv

WORKDIR $WORKDIR_PATH

COPY . .

RUN uv sync --frozen

FROM builder-base AS development

CMD ["python","-m", "ref-assist.main"]

FROM python-base AS production

COPY --from=builder-base $VIRTUAL_ENV $VIRTUAL_ENV

WORKDIR $WORKDIR_PATH

COPY ./src/ ./

USER 10000

CMD ["python","-m", "ref-assist.main"]
