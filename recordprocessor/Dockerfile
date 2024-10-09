FROM public.ecr.aws/lambda/python:3.10 as base

RUN pip install "poetry~=1.5.0"

COPY recordprocessor/poetry.lock recordprocessor/pyproject.toml recordprocessor/README.md ./
RUN poetry config virtualenvs.create false && poetry install --no-interaction --no-ansi --no-root --only main

# -----------------------------
FROM base as test

COPY recordprocessor/src src
COPY recordprocessor/tests tests
RUN python -m unittest

# -----------------------------
FROM base as build

COPY recordprocessor/src .
RUN chmod 644 $(find . -type f)
RUN chmod 755 $(find . -type d)
CMD ["python", "batch_processing.py"]
ENTRYPOINT ["python", "batch_processing.py"]