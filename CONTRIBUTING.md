# Contributing

## Development environment

- Full VPN stack: Docker with Compose.
- Webapp and test loop: Python 3.14+ and [uv](https://docs.astral.sh/uv/).
- Required for local development: `glider`, `openconnect`, `ocproxy`, and `glider/rules.rule`.

Set local configuration:

```bash
cp .env.example .env
cp glider/rules.example.rule glider/rules.rule
```

Edit `.env` and `glider/rules.rule` with local credentials and VPN domains. Quote multi-word `OPENCONNECT_OPTIONS` values:

```ini
OPENCONNECT_OPTIONS="--protocol=fortinet --servercert pin-sha256:... --disable-ipv6 --no-dtls"
```

Public ports default to SOCKS5 `1080`, HTTP `8080`, and web UI `8081`. Set
`OCPM_SOCKS_PORT`, `OCPM_HTTP_PORT`, and `OCPM_WEBUI_PORT` in `.env` to override
Compose ports. `just dev` uses the same values from `.env`, or accepts them as
inline environment overrides, for example:

```bash
OCPM_HTTP_PORT=18080 OCPM_SOCKS_PORT=11080 OCPM_WEBUI_PORT=18081 just dev
```

## Commands

```bash
just test
just dev
just start
just stop
just clean
```

`just test` and `just dev` run webapp commands through `uv`. `just start` and
`just stop` control full Compose VPN stack. `just clean` also removes Compose
containers, networks, and volumes, but retains images.

`just dev` starts local `glider` with shared `glider/glider.conf` and
`glider/rules.rule`. Stop Docker stack first; local Glider and Docker expose
same ports.

## Tests and changes

- Put module tests beside module; name files `*_test.py`.
- Run `just test` before opening pull request.
- Keep changes focused; update docs when behavior or setup changes.
