#!/bin/sh
# Simple health check for cloudflared tunnel
# Check if cloudflared process is running
if pgrep cloudflared > /dev/null; then
  exit 0
else
  exit 1
fi

