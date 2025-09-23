FROM python:3.13.7-alpine3.22

COPY m3ugen.py /etc/periodic/daily/m3ugen.py

COPY docker-entrypoint.sh /docker-entrypoint.sh

ENV M3UGEN_VERSION 1.0.0
ENV CONFIG_FILE /data/playlists.conf

RUN apk --update --no-cache add \
    bash \
  && chmod +x /etc/periodic/daily/m3ugen.py \
  && chmod +x /docker-entrypoint.sh

VOLUME /data

ENTRYPOINT ["/docker-entrypoint.sh"]

CMD ["crond", "-f"]
