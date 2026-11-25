#!/bin/sh
nginx -c /app/nginx.conf

while true; do
  xray run -c /app/config.json
  sleep 1
done &

if [ -n "$CF_TOKEN" ]; then
  cloudflared tunnel --no-autoupdate run --token "$CF_TOKEN" &
fi

python3 /app/app.py &
sleep 1

exec python3 /app/proxy_wrapper.py
