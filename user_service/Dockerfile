FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt 

RUN mkdir -p protos
COPY protos/user.proto protos/
COPY . .

RUN python -m grpc_tools.protoc -I./protos --python_out=. --grpc_python_out=. ./protos/user.proto

CMD ["python", "user_service.py"]
