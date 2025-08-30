FROM nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04
RUN apt-get update && \
    apt-get install -y ffmpeg software-properties-common
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
ADD . /app
WORKDIR /app
RUN uv sync --frozen
RUN chmod +x ./startup.sh
ENTRYPOINT uv run bash ./startup.sh