FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt

COPY settings.py embed.py /app/
RUN python3 embed.py --download

COPY . /app

EXPOSE 8000

CMD ["python3", "server.py"]
