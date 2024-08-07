FROM python:3.9.18

WORKDIR /app

COPY requirements.txt .

RUN pip install --upgrade pip
RUN pip3 install -r requirements.txt

COPY . .

EXPOSE 5000

ENV FLASK_ENV=production

CMD ["gunicorn", "-w 1", "-b", "0.0.0.0:5000", "server:app"]