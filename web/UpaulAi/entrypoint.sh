#!/bin/sh
# Render entrypoint: fetch GGUF once (ephemeral disk), start llama-server, run webapp.
set -e
export ASPNETCORE_URLS="http://0.0.0.0:${PORT:-10000}"
mkdir -p /data
if [ ! -s /data/model.gguf ]; then
  if [ -z "$MODEL_URL" ]; then
    echo "MODEL_URL not set; webapp will run with AI backend unavailable."
  else
    echo "Downloading model..."
    curl -L --fail --retry 3 -o /data/model.gguf "$MODEL_URL"
  fi
fi
if [ -s /data/model.gguf ]; then
  /usr/local/bin/llama-server -m /data/model.gguf --port 8080 -c 512 --batch-size 4 -t 1 --log-disable &
fi
exec dotnet UPaulAi.dll
