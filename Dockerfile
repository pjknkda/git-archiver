FROM python:3.7

ENV TINI_VERSION v0.18.0
ADD https://github.com/krallin/tini/releases/download/${TINI_VERSION}/tini /tini
RUN chmod +x /tini
ENTRYPOINT ["/tini", "-g", "--"]

WORKDIR /app-container/
COPY requirements.txt /app-container/
RUN pip install -r requirements.txt \
    && pip install gunicorn==19.9.0 uvloop==0.12.2

COPY git_archiver.py setup.py /app-container/
COPY assets/gunicorn-conf.py /app-container/assets/gunicorn-conf.py
COPY docker-entry.sh  /

EXPOSE 80

CMD ["/bin/bash", "/docker-entry.sh"]
