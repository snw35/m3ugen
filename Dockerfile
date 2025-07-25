FROM python:3.12.5-alpine3.20

COPY m3ugen.py /etc/periodic/daily/m3ugen.py

COPY docker-entrypoint.sh /docker-entrypoint.sh

ENV M3UGEN_VERSION 0.0.2
ENV CONFIG_FILE /data/playlists.conf

RUN apk --update --no-cache add \
    bash \
  && chmod +x /etc/periodic/daily/m3ugen.py \
  && chmod +x /docker-entrypoint.sh

VOLUME /data

ENTRYPOINT ["/docker-entrypoint.sh"]

CMD ["crond", "-f"]
