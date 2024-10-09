FROM public.ecr.aws/lambda/python:3.10 as base

RUN pip install "poetry~=1.5.0"

COPY recordforwarder/poetry.lock recordforwarder/pyproject.toml recordforwarder/README.md ./
RUN poetry config virtualenvs.create false && poetry install --no-interaction --no-ansi --no-root --only main

# -----------------------------
FROM base as test

RUN poetry install --no-interaction --no-ansi --no-root

COPY recordforwarder/src src
COPY recordforwarder/tests tests
RUN python -m unittest

# -----------------------------
FROM base as build

COPY recordforwarder/src .
RUN chmod 644 $(find . -type f)
RUN chmod 755 $(find . -type d)
CMD ["forwarding_lambda.forward_lambda_handler"]