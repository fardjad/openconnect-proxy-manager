# Contributing

## Source development setup

Clone the repository, then change into its directory:

```bash
git clone https://github.com/fardjad/openconnect-proxy-manager.git
cd openconnect-proxy-manager
```

Install the following local prerequisites before starting development:

- Install Docker Engine with the Docker Compose plugin to run the full VPN
  stack.
- Install `just` to run the repository commands.
- Install Python 3.14 and [uv](https://docs.astral.sh/uv/) to work on the webapp
  and run its tests.
- Install `glider`, `openconnect`, and `ocproxy` for local development outside
  the container.

Create the local configuration from the checked-in examples:

```bash
cp .env.example .env
cp glider/rules.example.rule glider/rules.rule
```

Edit `.env` and `glider/rules.rule` to provide local credentials and VPN domains.
Quote multi-word `OPENCONNECT_OPTIONS` values as shown here:

```ini
OPENCONNECT_OPTIONS="--protocol=fortinet --servercert pin-sha256:... --disable-ipv6 --no-dtls"
```

The public ports default to SOCKS5 `1080`, HTTP `8080`, and web UI `8081`. Set
`OCPM_SOCKS_PORT`, `OCPM_HTTP_PORT`, and `OCPM_WEBUI_PORT` in `.env` to override
the Compose ports. You can also provide inline overrides to `just dev`:

```bash
OCPM_HTTP_PORT=18080 OCPM_SOCKS_PORT=11080 OCPM_WEBUI_PORT=18081 just dev
```

## Build and run source

Build and start the source image by using Docker Compose:

```bash
docker compose build
docker compose up -d
```

The repository Compose file builds from the local `Dockerfile`, passes `.env`,
mounts `glider/rules.rule`, adds `NET_ADMIN`, and exposes `/dev/net/tun`.
Alternatively, you can use `just start` to start the same Compose stack. Stop
the stack with `just stop` or `docker compose down`.

## Commands

```bash
just test
just dev
just start
just stop
just clean
```

The `just test` and `just dev` commands run webapp commands through `uv`. The
`uv` tool manages Python 3.14 for local commands and for the container. The
`just start` and `just stop` commands control the full Compose VPN stack. The
`just clean` command also removes Compose containers, networks, and volumes, but
retains images.

The `just dev` command starts local `glider` with the shared
`glider/glider.conf` and `glider/rules.rule` files. Stop the Docker stack first,
because local Glider and Docker expose the same ports.

## Python dependencies

The `webapp/pyproject.toml` file requires Python `>=3.14` and declares these
dependency floors: Mako `>=1.3.12`, Uvicorn `>=0.52`, FastAPI `>=0.141`, and
PySocks `>=1.7.1`. Keep these floors as compatibility policy. Dependency
upgrades may resolve newer versions in the committed lockfile. Commit
`webapp/uv.lock` with dependency changes and refresh it from `webapp/` with:

```bash
uv lock
```

After refreshing the lockfile, run `uv sync --locked` or `just test`. CI and the
runtime use Python 3.14.

## Updating auxiliary images

The Dockerfile copies `uv` and `glider` from the following locations:

- The `Dockerfile` uses `ghcr.io/astral-sh/uv:<tag>` for `uv`.
- The `Dockerfile` uses `nadoo/glider:<tag>` for `glider`.

Update either auxiliary image by following these steps:

1. Select a reviewed version tag with support for both `linux/amd64` and
   `linux/arm64`.
2. Update only its tag in `Dockerfile`.
3. Run build checks on native hosts. Run the amd64 command on a native amd64
   host and the arm64 command on a native arm64 host, then run `just test` once:

   ```bash
   docker build --platform linux/amd64 -t ocpm-update-check:amd64 .
   docker build --platform linux/arm64 -t ocpm-update-check:arm64 .
   just test
   ```

4. Record the update in the release notes or in the relevant documentation.

## Tests and changes

- Put each module's tests beside that module, and name the files `*_test.py`.
- Run `just test` before opening a pull request.
- Keep changes focused, and update the documentation when behavior or setup
  changes.
