FROM public.ecr.aws/lambda/python:3.10 as base

RUN pip install "poetry~=1.5.0"

COPY filenameprocessor/poetry.lock filenameprocessor/pyproject.toml filenameprocessor/README.md ./
RUN poetry config virtualenvs.create false && poetry install --no-interaction --no-ansi --no-root --only main

# -----------------------------
FROM base as test

COPY filenameprocessor/src src
COPY filenameprocessor/tests tests
RUN python -m unittest

# -----------------------------
FROM base as build

COPY filenameprocessor/src .
RUN chmod 644 $(find . -type f)
RUN chmod 755 $(find . -type d)
CMD ["file_name_processor.lambda_handler"]