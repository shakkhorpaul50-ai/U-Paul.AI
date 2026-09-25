# U_Paul-AI webapp + llama-server in one image (Render free, single service).
FROM mcr.microsoft.com/dotnet/sdk:10.0 AS build
WORKDIR /src
COPY *.csproj ./
RUN dotnet restore
COPY . ./
RUN dotnet publish -c Release -o /app/publish --no-restore

FROM mcr.microsoft.com/dotnet/aspnet:10.0
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*
# Pinned llama.cpp CPU server (ggml-org nightly b11146); layout-proof extract.
ADD https://github.com/ggml-org/llama.cpp/releases/download/b11146/llama-b11146-bin-ubuntu-x64.tar.gz /tmp/llama.tgz
RUN mkdir -p /opt/llama \
    && tar -xzf /tmp/llama.tgz -C /opt/llama \
    && cp "$(find /opt/llama -name llama-server -type f | head -1)" /usr/local/bin/llama-server \
    && rm /tmp/llama.tgz \
    && llama-server --version
WORKDIR /app
COPY --from=build /app/publish ./
COPY entrypoint.sh ./
RUN chmod +x entrypoint.sh
EXPOSE 10000
ENTRYPOINT ["./entrypoint.sh"]
