#!/bin/bash
set -e

export PORT=${PORT:-80}

/usr/local/bin/xray run -config /etc/xray/config.json &
sleep 1

python3 /app/app.py &
sleep 1

nginx -t
nginx -g "daemon on;"

exec python3 /app/proxy_wrapper.py
