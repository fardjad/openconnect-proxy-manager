# Contributing

## Development environment

- Full VPN stack: Docker with Compose.
- Webapp and test loop: Python 3.14 and [uv](https://docs.astral.sh/uv/).
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

`just test` and `just dev` run webapp commands through `uv`. `uv` manages Python
3.14 for local commands and the container; Ubuntu's system Python is not used
by the image. `just start` and
`just stop` control full Compose VPN stack. `just clean` also removes Compose
containers, networks, and volumes, but retains images.

`just dev` starts local `glider` with shared `glider/glider.conf` and
`glider/rules.rule`. Stop Docker stack first; local Glider and Docker expose
same ports.

### Python dependencies

`webapp/pyproject.toml` requires Python `>=3.14` and declares dependency floors:
Mako `>=1.3.12`, Uvicorn `>=0.52`, FastAPI `>=0.141`, and PySocks `>=1.7.1`.
Keep these floors as compatibility policy; dependency upgrades may resolve newer
versions in the committed lockfile. Commit `webapp/uv.lock` with dependency
changes and refresh it from `webapp/` with:

```bash
uv lock
```

Run `uv sync --locked` or `just test` after refreshing the lockfile. CI and the
runtime both use Python 3.14.

## Updating auxiliary images

The Dockerfile copies `uv` and `glider` from these locations:

- `ghcr.io/astral-sh/uv:<tag>` in `Dockerfile`
- `nadoo/glider:<tag>` in `Dockerfile`

Update either auxiliary image as follows:

1. Select a reviewed version tag with both `linux/amd64` and `linux/arm64`
   support.
2. Update only its tag in `Dockerfile`.
3. Run build checks on native hosts: run the amd64 command on a native amd64
   host and the arm64 command on a native arm64 host. Run `just test` once:

   ```bash
   docker build --platform linux/amd64 -t ocpm-update-check:amd64 .
   docker build --platform linux/arm64 -t ocpm-update-check:arm64 .
   just test
   ```

4. Record the update in release notes or relevant documentation.

## First public image release

After first release publishes, change
`openconnect-proxy-manager` visibility to **Public** in its GHCR package
settings. GitHub provides no supported API to automate this one-time action.

## Tests and changes

- Put module tests beside module; name files `*_test.py`.
- Run `just test` before opening pull request.
- Keep changes focused; update docs when behavior or setup changes.
