FROM python:3.7-alpine

MAINTAINER Wanderley Teixeira <wanderley@linux.com>

# Timezone
ENV TIMEZONE America/Toronto

# AWS
ENV AWS_ACCESS_KEY_ID <ID>
ENV AWS_SECRET_ACCESS_KEY <KEY>
ENV AWS_DEFAULT_REGION <REGION>
ENV AWS_S3_BUCKET <BUCKET>

# Pushover
ENV PUSHOVER_TOKEN <TOKEN>
ENV PUSHOVER_USER <USERNAME>

# VoIP.ms
ENV VOIPMS_USER <USER>
ENV VOIPMS_KEY <KEY>

# Groundwire
ENV ACROBITS_FILENAME <FILENAME>

# Update and installation of packages
RUN apk update &&  \
    apk upgrade && \
    apk add --update tzdata && \
    cp /usr/share/zoneinfo/${TIMEZONE} /etc/localtime && \
    echo "${TIMEZONE}" > /etc/timezone &&                \
    apk add --no-cache      \
        bash                \
        supervisor &&       \
    pip install awscli &&   \
    apk del tzdata &&       \
    rm -fr /tmp/*.apk &&    \
    rm -rf /var/cache/apk/*

# For cron
WORKDIR /home
COPY crontab.txt /var/crontab.txt
RUN crontab /var/crontab.txt

# For supervisor
ADD supervisor.conf /etc/supervisor/conf.d/supervisor.conf

# Main
RUN touch $ACROBITS_FILENAME
COPY getBalance.py /home/getBalance.py

COPY requirements.txt /var/requirements.txt
RUN pip install -r /var/requirements.txt

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisor.conf"]
