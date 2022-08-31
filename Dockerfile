FROM apache/airflow:2.3.4

ENV AIRFLOW_HOME=/opt/airflow

COPY . .

RUN pip install --no-cache-dir -r requirements.txt
RUN python -m nltk.downloader stopwords punkt averaged_perceptron_tagger wordnet
WORKDIR $AIRFLOW_HOME

USER $AIRFLOW_UID