FROM python:3.9
RUN mkdir /usr/src/app
WORKDIR /usr/src/app
COPY src .
RUN pip install -r requirements.txt
CMD python3 exporter.py