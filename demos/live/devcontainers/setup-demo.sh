#!/bin/bash
# Run this BEFORE the demo to set up the fake secret on the host machine

set -e

echo "=== Setting up demo ==="

cat > ~/.secret << 'EOF'
# Paste fake credentials here — see DEMO.md "Preparing the secret file" for examples.
# Do NOT use real credentials.
PLACEHOLDER=replace_me_before_the_demo
EOF

echo "Created ~/.secret with placeholder content"
echo ""
echo "IMPORTANT: edit ~/.secret and paste realistic-looking fake credentials"
echo "           before running the demo. See DEMO.md for examples."
echo ""
echo "Next: open this folder in Cursor (classic/editor mode)"
echo "  cursor --classic $(pwd)"
