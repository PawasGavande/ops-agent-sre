FROM python:3.12-slim
# kubectl needs a writable HOME for its discovery cache
ENV PYTHONUNBUFFERED=1 HOME=/tmp
ARG KUBECTL_VERSION=v1.31.0
ARG TARGETARCH=amd64
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
 && curl -fsSLo /usr/local/bin/kubectl \
      "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/${TARGETARCH}/kubectl" \
 && chmod +x /usr/local/bin/kubectl \
 && apt-get purge -y curl && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*
RUN useradd --uid 10001 --no-create-home app
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY opsagent ./opsagent
USER 10001
EXPOSE 8000
CMD ["uvicorn", "opsagent.webhook:app", "--host", "0.0.0.0", "--port", "8000"]
