FROM python:3.13-slim-bookworm@sha256:f3614d98f38b0525d670f287b0474385952e28eb43016655dd003d0e28cf8652 AS builder

RUN pip install -U pip setuptools wheel
RUN pip install pdm

COPY pyproject.toml pdm.lock README.md /project/

WORKDIR /project

RUN mkdir __pypackages__ && pdm sync --prod --no-editable --no-self

COPY src/ /project/src

RUN pdm sync --prod --no-editable


FROM python:3.13-slim-bookworm@sha256:f3614d98f38b0525d670f287b0474385952e28eb43016655dd003d0e28cf8652

ARG UID=18311

# ensure no buffers, prevents losing logs e.g. from crashes
ENV PYTHONUNBUFFERED=1
# ensure we see tracebacks in C crashes
ENV PYTHONFAULTHANDLER=1

RUN addgroup --gid "$UID" containeruser && \
  adduser --uid "$UID" --ingroup containeruser --disabled-login --home /home/containeruser --shell /bin/false containeruser && \
  mkdir /project && \
  chown $UID:$UID /project

ENV PYTHONPATH=/project/pkgs
COPY --from=builder /project/__pypackages__/3.12/lib /project/pkgs
COPY --from=builder /project/__pypackages__/3.12/bin/* /bin/

USER $UID:$UID
WORKDIR /project
