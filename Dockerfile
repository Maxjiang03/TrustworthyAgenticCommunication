# Minimal pinned runtime (reproducibility requirement, design Part J.1).
#
# 3.13 because `frozen_parameters` row 9 -- the SEALED measurement platform,
# read off the machine rather than chosen -- records Python 3.13.5, and this
# image pinned 3.11. Two sealed artifacts disagreeing about the interpreter is
# not a detail: `uv.lock` is a universal resolve, so the two pins produced
# different dependency sets and "the pinned environment" was two environments
# (ADR 0044). The adjudicative runs are the row 9 machine's; this image exists
# so a third party can re-derive them, which requires it to agree.
FROM python:3.13-slim

# Determinism control: fixed hash seed (design Part J.1 / PROJECT_RULES.md Setup).
ENV PYTHONHASHSEED=0

# Pinned uv — same version family used to produce uv.lock.
RUN pip install --no-cache-dir uv==0.10.6

WORKDIR /app

# Locked environment first (layer caching), then the source tree.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

COPY . .

ENV PATH="/app/.venv/bin:${PATH}"
CMD ["pytest", "-q"]
