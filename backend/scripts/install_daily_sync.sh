#!/bin/zsh
set -euo pipefail

# Install a macOS LaunchAgent that runs feed sync once a day at 08:00 local time.
BACKEND="$(cd "$(dirname "$0")/.." && pwd)"
SYNC_SCRIPT="$BACKEND/scripts/run_sync.sh"
LABEL="com.jobaggregator.sync"
PLIST="$HOME/Library/LaunchAgents/${LABEL}.plist"
LOG_DIR="$HOME/Library/Logs"
LOG_FILE="$LOG_DIR/jobaggregator-sync.log"
GUI_DOMAIN="gui/$(id -u)"

chmod +x "$SYNC_SCRIPT"
mkdir -p "$HOME/Library/LaunchAgents" "$LOG_DIR"

cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${LABEL}</string>
  <key>WorkingDirectory</key>
  <string>${BACKEND}</string>
  <key>ProgramArguments</key>
  <array>
    <string>${SYNC_SCRIPT}</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key>
    <integer>8</integer>
    <key>Minute</key>
    <integer>0</integer>
  </dict>
  <key>StandardOutPath</key>
  <string>${LOG_FILE}</string>
  <key>StandardErrorPath</key>
  <string>${LOG_FILE}</string>
</dict>
</plist>
EOF

launchctl bootout "$GUI_DOMAIN" "$PLIST" >/dev/null 2>&1 || true
launchctl bootstrap "$GUI_DOMAIN" "$PLIST"
echo "Installed daily sync: $PLIST"
echo "Runs every day at 08:00 local time. Log: $LOG_FILE"
echo "Kick one off now: launchctl kickstart -k ${GUI_DOMAIN}/${LABEL}"
