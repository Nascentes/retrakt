FROM ubuntu:16.04

#MAINTANER Tony Atkinson "tony@atkinso.net"

RUN apt-get update \
    && apt-get install -y cron python3-pip python3-dev \
    && cd /usr/local/bin \
    && ln -s /usr/bin/python3 python \
    && pip3 install --upgrade pip

COPY . /app/

COPY retrakt_cron /etc/cron.d/retrakt_cron

RUN chmod 0644 /etc/cron.d/retrakt_cron

RUN crontab /etc/cron.d/retrakt_cron

RUN touch /var/log/cron.log

WORKDIR /app

RUN pip install -r requirements.txt

CMD ["cron", "-f"]

#ENTRYPOINT [ "python3" ]

#CMD [ "watchlist.py" ]
