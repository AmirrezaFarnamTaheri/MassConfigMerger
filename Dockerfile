FROM python:3.11-slim
WORKDIR /app

# Install package and its dependencies using pyproject.toml
COPY pyproject.toml ./
COPY . ./
RUN pip install --no-cache-dir .

ENTRYPOINT ["python", "vpn_merger.py"]
