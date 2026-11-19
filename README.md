# OpenConnect Proxy Manager (OCPM)

OpenConnect Proxy Manager (OCPM) exposes an OpenConnect VPN connection through
HTTP and SOCKS5 proxies. Its web UI manages the connection and interactive 2FA.
OCPM uses OpenConnect, [ocproxy](https://github.com/cernekee/ocproxy), and
[glider](https://github.com/nadoo/glider).

## Motivation

Corporate VPNs are a common way to access internal resources, but routing all
traffic from a machine through the VPN is not always practical.

Even when it is practical, centrally managed split tunneling applies one set
of routes to everyone. Individual users and teams often need different rules.

OCPM lets you choose which domains use the VPN by configuring HTTP and SOCKS5
proxies.

The trade-off is that applications need proxy configuration. Most browsers and
developer tools support HTTP or SOCKS5 proxies.

## Usage

### 1. Check prerequisites

Install Docker Engine with the Docker Compose plugin before starting. The host
must provide `/dev/net/tun`, and the container must have permission to add a
network interface. Published images support `linux/amd64` and `linux/arm64`.

The GHCR package is public, so pulling the image does not require a GHCR login.

Images are published as `latest`, release version tags such as `0.1.0` and
`0.1`, and `edge` for development builds from `main`. The example below uses
`latest`.

### 2. Create a configuration directory

```bash
mkdir -p "$HOME/ocpm"
cd "$HOME/ocpm"
```

### 3. Create `.env`

Create `.env` and add the VPN credentials and settings shown below:

```ini
OPENCONNECT_URL=https://vpn.example.com
OPENCONNECT_USER=your-username
OPENCONNECT_PASSWORD=your-password
OPENCONNECT_OPTIONS="--protocol=fortinet --servercert pin-sha256:... --disable-ipv6 --no-dtls"
# Optional. Set only when static MFA is appropriate.
# OPENCONNECT_MFA_CODE=123456
HEARTBEAT_URL=http://internal.example.com
HEARTBEAT_INTERVAL=30
OCPM_SOCKS_PORT=1080
OCPM_HTTP_PORT=8080
OCPM_WEBUI_PORT=8081
# Optional. Connect automatically after container start.
# AUTO_CONNECT=true
```

Protect these credentials from other users on the host by running:

```bash
chmod 600 .env
```

### Choose the VPN protocol

`OPENCONNECT_OPTIONS` passes options directly to OpenConnect. Change the VPN
protocol by setting `--protocol=<name>` inside that value. For example:

```ini
OPENCONNECT_OPTIONS="--protocol=gp --servercert pin-sha256:... --disable-ipv6 --no-dtls"
```

OpenConnect supports protocols including `anyconnect` (the default), `nc`
(Juniper Network Connect), `pulse` (Pulse Connect Secure), `gp` (Palo Alto
GlobalProtect), `f5` (F5 BIG-IP), `fortinet` (FortiGate), and `array` (Array
Networks). Use the protocol required by your VPN provider. See the
[OpenConnect manual](https://www.infradead.org/openconnect/manual.html) for
supported options and protocol details.

### 4. Create routing rules

Create `rules.rule` with the following example. It routes `example.com` and its
matching traffic through the VPN, while traffic that does not match a rule
remains direct.

```ini
forward=socks5://127.0.0.1:1081
domain=example.com
```

Add one `domain=` line for each domain or subdomain pattern that the VPN must
route.

### 5. Create standalone `compose.yml`

Save the following file beside `.env` and `rules.rule`:

```yaml
services:
  ocpm:
    image: ghcr.io/fardjad/openconnect-proxy-manager:latest
    container_name: ocpm
    env_file: .env
    ports:
      - "${OCPM_SOCKS_PORT:-1080}:${OCPM_SOCKS_PORT:-1080}"
      - "${OCPM_HTTP_PORT:-8080}:${OCPM_HTTP_PORT:-8080}"
      - "${OCPM_WEBUI_PORT:-8081}:${OCPM_WEBUI_PORT:-8081}"
    restart: unless-stopped
    cap_add:
      - NET_ADMIN
    devices:
      - /dev/net/tun
    volumes:
      - ./rules.rule:/etc/ocpm/rules.rule:ro
```

### 6. Start OCPM

```bash
docker compose pull
docker compose up -d
```

Open `http://localhost:8081`, or open the value configured in
`OCPM_WEBUI_PORT`. Select **Connect**, then enter credentials or a 2FA code when
prompted. If `AUTO_CONNECT=true` and credentials are in `.env`, OCPM starts the
connection automatically.

### 7. Verify the UI and proxies

Confirm that the web UI shows the connection status. Configure applications with
the following proxy endpoints:

- Configure SOCKS5 to use `localhost:1080` by default, or the value of
  `OCPM_SOCKS_PORT`.
- Configure HTTP to use `localhost:8080` by default, or the value of
  `OCPM_HTTP_PORT`.

Test a VPN-routed domain through the selected proxy, then test a non-matching
domain to confirm that direct routing works. Applications without proxy support
do not use OCPM automatically.

To monitor VPN reachability, set `HEARTBEAT_URL` to an HTTP or HTTPS endpoint
reachable through the VPN. OCPM probes it through the VPN SOCKS proxy at
`HEARTBEAT_INTERVAL` seconds (30 by default). Any HTTP response counts as
reachable, including errors and redirects; redirects are not followed. Three
consecutive network failures disconnect the VPN. Omit `HEARTBEAT_URL` to disable
the heartbeat.

### 8. Stop or update

```bash
docker compose down
docker compose pull
docker compose up -d
```

The `latest` tag follows the most recent release. Use a version tag when you
need a specific release.

## Troubleshooting

- **TUN or capability errors:** Confirm that `/dev/net/tun` exists on the host
  and that Compose includes both the device mapping and `NET_ADMIN`. Check the
  Docker security policy if those settings are present but OpenConnect cannot
  create a tunnel.
- **Port already in use:** Change `OCPM_SOCKS_PORT`, `OCPM_HTTP_PORT`, or
  `OCPM_WEBUI_PORT` in `.env`, then recreate the container with
  `docker compose up -d`.
- **Credentials, certificates, or options rejected:** Check the spelling and
  quoting in `.env`. Keep multi-word `OPENCONNECT_OPTIONS` values in quotes. Use
  the VPN provider's exact `--servercert` value when certificate pinning is
  required. Omit static `OPENCONNECT_MFA_CODE` to enter a changing code in the
  UI.
- **2FA does not complete:** Connect from the web UI and enter the current code
  when prompted. Static MFA codes can expire or be unsuitable for challenge
  flows.
- **Need logs:** Follow the container output while reproducing the problem:

  ```bash
  docker compose logs -f ocpm
  ```

  Do not paste credentials, MFA codes, or certificate secrets into issue
  reports.

## Proxy Configuration Recipes

### I Want All Supported Application Traffic to Use OCPM

Configure your operating system to use OCPM as its HTTP and HTTPS proxy. Set the
host to `localhost` and use the following HTTP proxy port:

- Host: `localhost`.
- Port: `8080` by default, or the value configured in `OCPM_HTTP_PORT`.

Most applications that respect operating system proxy settings will use OCPM
without further configuration. If your operating system supports a SOCKS proxy,
configure `localhost` on port `1080` by default, or use the value of
`OCPM_SOCKS_PORT`. Applications without proxy support continue to connect
normally.

### I Only Want My Browser to Use OCPM

Configure the browser directly if you do not want to change the system-wide
proxy settings.

#### Chromium-Based Browsers

Install [FoxyProxy](https://getfoxyproxy.org/), then add an HTTP proxy with host
`localhost` and port `8080` by default, or use the value configured in
`OCPM_HTTP_PORT`. Set its rule or mode to proxy all URLs. Other applications
will keep their existing network settings.

#### Firefox

Open **Settings > General > Network Settings > Settings**, then choose
**Manual proxy configuration**. Set **HTTP Proxy** to `localhost` on port
`8080` by default, or use the value configured in `OCPM_HTTP_PORT`, and enable
**Also use this proxy for HTTPS**.

To use SOCKS5 instead, set **SOCKS Host** to `localhost` on port `1080` by
default, or use the value configured in `OCPM_SOCKS_PORT`, and select **SOCKS
v5**.

### I Want Terminal Applications to Use OCPM

For tools that support HTTP proxies, export both uppercase and lowercase
variables by running:

```bash
export HTTP_PROXY=http://localhost:8080 HTTPS_PROXY=http://localhost:8080
export http_proxy="$HTTP_PROXY" https_proxy="$HTTPS_PROXY"
```

Replace `8080` with the value configured in `OCPM_HTTP_PORT` when you use a
non-default port.

For tools that support SOCKS5, set `ALL_PROXY` instead by running:

```bash
export ALL_PROXY=socks5://localhost:1080 all_proxy="$ALL_PROXY"
```

Replace `1080` with the value configured in `OCPM_SOCKS_PORT` when you use a
non-default port.

Add the configuration that you use to your shell startup file to apply it to
every new terminal. To proxy one command at a time, create an alias instead:

```bash
alias ocpm-http='HTTP_PROXY=http://localhost:8080 HTTPS_PROXY=http://localhost:8080 http_proxy=http://localhost:8080 https_proxy=http://localhost:8080'
ocpm-http curl https://example.com
```

Choose either the HTTP variables or `ALL_PROXY` for a command. Setting both can
produce different results in different tools.

### I Need Advanced Routing or Proxy Chaining

OCPM uses Glider for proxying. For information about custom routing rules and
proxy chains, see the [Glider documentation](https://github.com/nadoo/glider).
