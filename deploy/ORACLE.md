# Hosting ChongaBot on Oracle Cloud (free)

Oracle's **Always Free** tier includes an ARM virtual machine that never expires. ChongaBot
needs about 200 MB of RAM, so the smallest one is plenty. Total time: about 30 minutes.

Oracle changes its console now and then, so button names below may differ slightly.

## Before you start

- The server downloads the code from GitHub (the `v2` branch), so it must be pushed there.
- **Only one copy of the bot can use a token at a time.** When the server starts, stop the
  bot everywhere else (your PC, the Raspberry Pi), or two copies will answer every command.
  For testing on your PC afterwards, make a second bot in the Developer Portal with its
  own token.

## 1. Create an Oracle Cloud account

1. Sign up at <https://www.oracle.com/cloud/free/>.
2. **Pick your home region carefully.** Always Free machines can only be created there, and
   it can't be changed later. Choose one near you, ideally a large one (e.g. US East
   Ashburn, US West Phoenix, UK South London, Germany Central Frankfurt).
3. Oracle asks for a card to verify you're a real person. Always Free resources are not
   charged.

## 2. Create the server

In the console: **Compute → Instances → Create instance**.

| Setting | Choose |
|---|---|
| Name | `chongabot` |
| Image | **Canonical Ubuntu 24.04** (click *Change image*) |
| Shape | **Ampere → VM.Standard.A1.Flex**, **1 OCPU, 6 GB memory** (should say *Always Free-eligible*) |
| Networking | The defaults (a new network with a public IP address) |
| SSH keys | **Generate a key pair for me**, then **Save private key**. Keep that file safe. |

Click **Create** and wait for the status to turn green (*Running*). Copy the **Public IP
address** from the instance page.

> **"Out of capacity"?** Free ARM machines are popular. Try another *Availability domain*
> in the placement section, or try again later in the day.

The bot only makes outgoing connections to Discord, so you **don't** need to open any
firewall ports.

## 3. Connect to it

On your PC (Windows PowerShell, macOS or Linux terminal), with the key file you saved:

```bash
chmod 600 ~/Downloads/ssh-key-*.key          # macOS/Linux only
ssh -i ~/Downloads/ssh-key-*.key ubuntu@YOUR_PUBLIC_IP
```

Type `yes` the first time it asks about the fingerprint.

## 4. Install ChongaBot

On the server:

```bash
curl -fsSL https://raw.githubusercontent.com/Chaney-Chanti/ChongaBot/v2/deploy/setup.sh -o setup.sh
bash setup.sh v2
```

This runs the `v2` branch. Once it's merged into `main`, use `main` in both places instead.

It installs everything, then asks for:

- **Your bot token**: Developer Portal → your app → **Bot** → **Reset Token**. Resetting
  invalidates the old token, so do it now and paste the new one here. Typing is hidden.
- **Your Discord user ID**: in Discord, Settings → Advanced → turn on **Developer Mode**,
  then right-click your name → **Copy User ID**.

When it finishes, the bot is online.

## 5. Register the slash commands (once)

In any server the bot is in, send:

```
@ChongaBot sync global
```

Slash commands can take up to an hour to appear in every server. Do this again whenever a
command is added, renamed or removed.

## Everyday use

| To | Run on the server |
|---|---|
| Watch the logs | `journalctl -u chongabot -f` (Ctrl+C to stop) |
| Check it's running | `systemctl status chongabot` |
| Update to the latest code | `sudo -iu chonga ~/ChongaBot/deploy/deploy.sh` |
| Restart | `sudo systemctl restart chongabot` |
| Edit settings | `sudo -u chonga nano /home/chonga/ChongaBot/.env`, then restart |

Database upgrades run automatically when the bot starts.

## Backups

A backup of the game database is taken every night at 04:00 UTC into
`/home/chonga/backups`, and the last 14 are kept. Those copies live on the same server,
so **also copy one to your PC now and then**. From your PC:

```bash
ssh -i ~/Downloads/ssh-key-*.key ubuntu@YOUR_PUBLIC_IP \
  'sudo cat /home/chonga/backups/chonga-latest.db.gz' > chonga-backup.db.gz
```

To take a backup right now: `sudo systemctl start chongabot-backup`.

To restore one, on the server:

```bash
sudo systemctl stop chongabot
sudo -u chonga sh -c 'gunzip -c /home/chonga/backups/chonga-latest.db.gz > /home/chonga/ChongaBot/chonga.db'
sudo rm -f /home/chonga/ChongaBot/chonga.db-wal /home/chonga/ChongaBot/chonga.db-shm
sudo systemctl start chongabot
```

## Keeping the free server

Oracle may reclaim Always Free machines it considers **idle** (very low CPU, network and
memory use over a week). A Discord bot is light, so this can happen. Two ways to avoid it:

- **Upgrade the account to Pay As You Go** (*Billing → Upgrade*). Always Free resources stay
  free, and upgraded accounts aren't subject to idle reclamation. Set a **budget alert** of
  $1 under *Billing → Budgets* so you'd hear about any charge at once.
- Or stay on the free account, and keep the off-server backups above up to date so you can
  rebuild quickly if it's ever reclaimed.
