#!/usr/bin/env bash
# One-time setup of a fresh Ubuntu server (e.g. an Oracle Cloud Always Free VM) for ChongaBot.
# Run it as the default login user (`ubuntu`, which has sudo). See deploy/ORACLE.md.
#
#   curl -fsSL https://raw.githubusercontent.com/Chaney-Chanti/ChongaBot/main/deploy/setup.sh -o setup.sh
#   bash setup.sh            # or: bash setup.sh <branch>
#
# Safe to re-run: it skips what's already done and never overwrites an existing .env.
set -euo pipefail

BRANCH=${1:-main}
REPO=${REPO:-https://github.com/Chaney-Chanti/ChongaBot.git}
APP_USER=chonga
APP_HOME=/home/$APP_USER
APP_DIR=$APP_HOME/ChongaBot

step() { printf '\n\033[1m==> %s\033[0m\n' "$*"; }
as_app() { sudo -iu "$APP_USER" bash -c "$*"; }

step "Installing system packages"
sudo apt-get update -y
sudo apt-get install -y git sqlite3 curl

step "Creating the '$APP_USER' user"
id "$APP_USER" >/dev/null 2>&1 || sudo useradd --create-home --shell /bin/bash "$APP_USER"

step "Installing uv"
as_app 'test -x ~/.local/bin/uv || curl -LsSf https://astral.sh/uv/install.sh | sh'

step "Getting the code ($BRANCH)"
if [ ! -d "$APP_DIR/.git" ]; then
    as_app "git clone --branch '$BRANCH' '$REPO' '$APP_DIR'"
else
    echo "Already cloned; use deploy/deploy.sh to update."
fi
as_app "cd '$APP_DIR' && ~/.local/bin/uv sync --frozen --no-dev"

step "Bot settings (.env)"
if sudo test -f "$APP_DIR/.env"; then
    echo "$APP_DIR/.env already exists; leaving it alone."
else
    read -rsp "Discord bot token (input hidden): " token
    echo
    read -rp "Your Discord user ID (for owner commands): " owner
    sudo -u "$APP_USER" tee "$APP_DIR/.env" >/dev/null <<ENV
DISCORD_TOKEN=$token
OWNER_IDS=[$owner]
# Switch on "Message Content Intent" in the Developer Portal before setting this to true.
MESSAGE_CONTENT_INTENT=false
LOG_JSON=true
ENV
    sudo chmod 600 "$APP_DIR/.env"
    unset token
fi

step "Installing the services"
sudo cp "$APP_DIR/deploy/chongabot.service" \
    "$APP_DIR/deploy/chongabot-backup.service" \
    "$APP_DIR/deploy/chongabot-backup.timer" /etc/systemd/system/
# Let the app user restart the bot (for deploy.sh) without full sudo.
sudo tee /etc/sudoers.d/chongabot >/dev/null <<SUDO
$APP_USER ALL=(root) NOPASSWD: /usr/bin/systemctl restart chongabot, /usr/bin/systemctl status chongabot
SUDO
sudo chmod 440 /etc/sudoers.d/chongabot
sudo visudo -cf /etc/sudoers.d/chongabot
sudo systemctl daemon-reload
sudo systemctl enable --now chongabot chongabot-backup.timer

step "Done"
sleep 5
systemctl --no-pager status chongabot | head -n 5
cat <<MSG

ChongaBot is running. Next:
  * Logs:          journalctl -u chongabot -f
  * First time:    in Discord, send "@ChongaBot sync global" so slash commands appear
                   everywhere (takes up to an hour to show up).
  * Updates:       sudo -iu $APP_USER $APP_DIR/deploy/deploy.sh
  * Backups:       nightly, in $APP_HOME/backups (last 14 kept)
MSG
