#!/bin/bash
source .env

set -euo pipefail  # Exit on errors, undefined variables

: "${LIGHTHOUSE_WIREGUARD_PUBLIC_KEY:?Environment variable LIGHTHOUSE_WIREGUARD_PUBLIC_KEY not set}"
: "${LIGHTHOUSE_WIREGUARD_LISTEN_PORT:?Environment variable LIGHTHOUSE_WIREGUARD_LISTEN_PORT not set}"
: "${LIGHTHOUSE_SSH_PORT:?Environment variable LIGHTHOUSE_SSH_PORT not set}"
: "${LIGHTHOUSE_DUMMY_USER:?Environment variable LIGHTHOUSE_DUMMY_USER not set}"
: "${LIGHTHOUSE_IP:?Environment variable LIGHTHOUSE_IP not set}"
: "${PROXY_ID:?Environment variable PROXY_ID not set}"

sudo apt install wireguard wireguard-tools

if sudo test -f /etc/wireguard/private.key; then
	echo Private key already exists!
else
	wg genkey | sudo tee /etc/wireguard/private.key
	sudo chmod 600 /etc/wireguard/private.key
fi

if sudo test -f /etc/wireguard/public.key; then
	echo Public key already exists!
else
	sudo cat /etc/wireguard/private.key | wg pubkey | sudo tee /etc/wireguard/public.key
fi

PROXY_PRIVATE_KEY=$(sudo cat /etc/wireguard/private.key)
PROXY_PUBLIC_KEY=$(sudo cat /etc/wireguard/public.key)

sudo bash -c "cat >/etc/wireguard/wg0.conf" << EOF
[Interface]
PrivateKey = ${PROXY_PRIVATE_KEY}
Address = 10.0.0.$(printf "%02d" "$PROXY_ID")/24
ListenPort = ${LIGHTHOUSE_WIREGUARD_LISTEN_PORT}

[Peer]
# Lighthouse server
PublicKey = ${LIGHTHOUSE_WIREGUARD_PUBLIC_KEY}
Endpoint = ${LIGHTHOUSE_IP}:${LIGHTHOUSE_WIREGUARD_LISTEN_PORT}
AllowedIPs = 10.0.0.0/24
PersistentKeepalive = 25
EOF

echo "Public key to add to Lighthouse: $PROXY_PUBLIC_KEY"

sudo systemctl enable wg-quick@wg0
sudo systemctl restart wg-quick@wg0
sudo wg show
