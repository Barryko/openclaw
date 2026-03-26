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

# 1. Load and export all variables in .env
if [ -f my.env ]; then
  set -a
  source my.env
  set +a
fi

# 2. Dynamically insert .env variables into the environment section of docker-compose.yml
MARKER_DC="# OPENCLAW_CUSTOM_ENV_INJECTED_DC"

if grep -q "$MARKER_DC" docker-compose.yml; then
  echo "Environment variables already injected in docker-compose.yml. Skipping."
else
  if [ -f my.env ]; then
    awk -v marker="$MARKER_DC" '
      BEGIN {
        while ((getline line < "my.env") > 0) {
          # Ignore comments and lines without equals signs
          if (line !~ /^[[:space:]]*#/ && line ~ /=/) {
            split(line, parts, "=")
            key = parts[1]
            sub(/^[[:space:]]*(export[[:space:]]+)?/, "", key)
            sub(/[[:space:]]+$/, "", key)
            if (key != "") {
              keys[++count] = key
            }
          }
        }
      }
      /^[[:space:]]*environment:/ {
        print
        print "      " marker
        for (i = 1; i <= count; i++) {
          print "      " keys[i] ": ${" keys[i] ":-}"
        }
        next
      }
      { print }
    ' docker-compose.yml > docker-compose.yml.tmp
    mv docker-compose.yml.tmp docker-compose.yml
  fi
fi

# Execute the script after setup is complete
./docker-setup.sh
