Repository for the proxies.

Initiate the connection through SSH and through Wireguard.

Parent repository (lighthouse) is available [here](https://github.com/ahoone/ahoonepi-lighthouse).

## Initialization

To execute the `init_*` shell scripts, you need in the `.env`:

```bash
LIGHTHOUSE_WIREGUARD_PUBLIC_KEY= # displayed by the lighthouse's init script, or using `sudo wg show`
LIGHTHOUSE_WIREGUARD_LISTEN_PORT=
LIGHTHOUSE_DUMMY_USER=
LIGHTHOUSE_SSH_PORT=
LIGHTHOUSE_IP=

PROXY_ID= # heading 0 for single digit integers is no longer required
```

> **As said in the parent repository's notice, proxy_id should be between 2 and 99.
> The code does not trigger warnings cases outside this range.**

## Scraper component

nyi
