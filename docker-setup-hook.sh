#!/usr/bin/env bash

# Custom Gateway Port (Default 18789)
#export OPENCLAW_GATEWAY_PORT=18789

# Configure persistent Volume (Data will not be lost when container is rebuilt)
export OPENCLAW_HOME_VOLUME=openclaw-home

# Mount additional host directories into the container
# Here we mount the dynamically generated Caddyfile and certs directory (./certs)
#export OPENCLAW_EXTRA_MOUNTS="./Caddyfile:/etc/caddy/Caddyfile:ro,./certs:/etc/caddy/certs:ro"
# Install additional system packages (if required by your workflow)
# Note: Dockerfile must have Caddy repository configured first for this installation to succeed
#export OPENCLAW_DOCKER_APT_PACKAGES="caddy"

# Dynamically generate Caddyfile
# cat <<EOF > Caddyfile
# openclaw.barryko.tw {
#     reverse_proxy 127.0.0.1:18789
#     tls /etc/caddy/certs/fullchain.pem /etc/caddy/certs/privkey.pem
# }
# EOF

export OPENCLAW_DOCKER_APT_PACKAGES="git gh python3 python3-pip wget curl"
# add depend module for Chromium
export OPENCLAW_DOCKER_APT_PACKAGES="$OPENCLAW_DOCKER_APT_PACKAGES libnspr4 libnss3 libatk1.0-0 libatk-bridge2.0-0 libdbus-1-3 libcups2 libxkbcommon0 libatspi2.0-0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 libasound2"
export OPENCLAW_INSTALL_BROWSER=1
export OPENCLAW_TZ=Asia/Taipei

# Execute the script after setup is complete
./scripts/docker/setup.sh
