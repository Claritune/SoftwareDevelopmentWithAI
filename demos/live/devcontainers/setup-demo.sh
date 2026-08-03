#!/bin/bash
# Run this BEFORE the demo to set up the fake secret on the host machine

set -e

echo "=== Setting up demo ==="

# Create a fake secret file on the host
cat > ~/.secret << 'EOF'
# Production Database Credentials
SECRET = "SECRET"
# API Tokens

EOF

echo "Created ~/.secret with fake credentials"
echo ""
echo "=== Setup complete ==="
echo ""
echo "Next: open this folder in Cursor (classic/editor mode)"
echo "  cursor --classic $(pwd)"
