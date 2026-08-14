docker build -t hbg-typesense-mcp:latest . && \
docker run -it --rm -p 8000:8000 --env-file .env hbg-typesense-mcp:latest