FROM python:3.12-slim

RUN groupadd -g 1000 sidecar && useradd -u 1000 -g 1000 -m -s /bin/bash sidecar

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app/security/

USER 1000

EXPOSE 8001

CMD ["uvicorn", "security.main:app", "--host", "0.0.0.0", "--port", "8001"]
