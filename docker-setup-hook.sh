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

export OPENCLAW_DOCKER_APT_PACKAGES="git gh python3 wget curl"
export OPENCLAW_INSTALL_BROWSER=1
export OPENCLAW_TZ=Asia/Taipei

# Execute the script after setup is complete
./docker-setup.sh
