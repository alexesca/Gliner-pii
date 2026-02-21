# CUDA-enabled PyTorch base — provides Python 3.10, CUDA 12.1, cuDNN 8
FROM pytorch/pytorch:2.3.0-cuda12.1-cudnn8-runtime

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

# Bake model weights into the image (offline-capable after build)
RUN python -c "from gliner import GLiNER; GLiNER.from_pretrained('knowledgator/gliner-pii-base-v1.0')"

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
