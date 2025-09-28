FROM apache/airflow:2.7.1

USER root
RUN apt-get update && apt-get install -y libkrb5-dev build-essential
USER airflow

COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir --user -r /requirements.txt --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.7.1/constraints-3.8.txt"
