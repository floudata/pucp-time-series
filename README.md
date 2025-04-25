# pucp-time-series
Proyecto Final

## Run in docker
```
docker container run -itd --name streamlit -v $PWD:/app -w /app -p 8501:8501 python:3.12.5-slim
```

## Run in docker compose
```
docker-compose up -d
```