FROM python:3.11.4-bullseye

ENV PYTHONFAULTHANDLER=1     PYTHONHASHSEED=random     PYTHONUNBUFFERED=1

WORKDIR /code
RUN mkdir /code/logs && touch /code/logs/log.log

RUN pip install poetry

COPY poetry.lock pyproject.toml /code/
RUN poetry config virtualenvs.create false && poetry install --no-interaction --no-ansi

RUN apt update
RUN apt install -y gettext
COPY . /code
