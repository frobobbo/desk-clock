# The Daily Chronicle — Desk Clock

This repository now contains two supported book-clock builds:

| Target | Project |
|---|---|
| Internal configuration API and web UI | [`app/`](app/) |
| Kubernetes Helm chart | [`charts/desk-clock-config/`](charts/desk-clock-config/) |
| ELECROW CrowPanel ESP32 5.79" E-Paper HMI Display | [`elecrow-book-clock/`](elecrow-book-clock/) |
| Raspberry Pi 3 + Waveshare 7.5" e-Paper Module/HAT (B) | [`rpi3-waveshare-book-clock/`](rpi3-waveshare-book-clock/) |

The former Raspberry Pi Pico / MicroPython build has been removed. Use the target-specific README in each project directory for hardware setup, build steps, and display notes.

## Project Layout

```
desk-clock/
├── app/
│   ├── main.py
│   ├── config_store.py
│   └── static/
├── Dockerfile
├── requirements.txt
├── charts/
│   └── desk-clock-config/
├── elecrow-book-clock/
│   ├── README.md
│   ├── platformio.ini
│   ├── include/
│   ├── lib/
│   ├── src/
│   └── tools/
└── rpi3-waveshare-book-clock/
    ├── README.md
    ├── requirements.txt
    ├── src/
    └── tools/
```

## Configuration Service

The root project includes an internal-only web front end and JSON API for managing the data shown on the e-ink screens. It has no login or user management by design, so expose it only on a trusted network.

Run locally:

```bash
docker build -t desk-clock-config .
docker run --rm -p 8000:8000 -v desk-clock-config:/data desk-clock-config
```

Open `http://localhost:8000`.

Useful API endpoints:

| Endpoint | Purpose |
|---|---|
| `GET /healthz` | Container health check |
| `GET /api/config` | Full display configuration |
| `PUT /api/config` | Replace full display configuration |
| `GET /api/displays` | List display IDs |
| `GET /api/displays/elecrow` | Elecrow display payload |
| `GET /api/displays/waveshare-rpi3` | Raspberry Pi 3 Waveshare payload |
| `PUT /api/displays/{display_id}` | Update one display payload |

Configuration is stored as JSON at `/data/display-config.json` in the container. Override the path with `CONFIG_PATH` if needed.

## Container Builds

GitHub Actions builds the API/web Docker image with `.github/workflows/api-web-image.yml`.

On pushes to `main`, the workflow publishes:

```text
ghcr.io/<owner>/<repo>/desk-clock-config
```

Pull requests build the image without pushing it.

## Helm Chart

The Kubernetes chart deploys the internal API/web service with a Deployment, ClusterIP Service, optional Ingress, and optional PersistentVolumeClaim for `/data`.

Install from a local checkout:

```bash
helm install desk-clock-config ./charts/desk-clock-config
```

Example with ingress enabled:

```bash
helm upgrade --install desk-clock-config ./charts/desk-clock-config \
  --set ingress.enabled=true \
  --set ingress.hosts[0].host=desk-clock-config.internal
```

The chart defaults to:

```text
ghcr.io/frobobbo/desk-clock/desk-clock-config:latest
```

GitHub Actions packages the chart with `.github/workflows/helm-chart.yml` and publishes a Helm repository to the `gh-pages` branch. After GitHub Pages is enabled for that branch, install from the published repo with:

```bash
helm repo add desk-clock https://frobobbo.github.io/desk-clock
helm repo update
helm install desk-clock-config desk-clock/desk-clock-config
```

## Targets

### ELECROW CrowPanel

The Elecrow build is an Arduino/PlatformIO firmware project for the ELECROW CrowPanel ESP32 5.79" e-paper display. It uses the bundled ELECROW e-paper driver and renders the clock layout directly on the device.

Start here: [`elecrow-book-clock/README.md`](elecrow-book-clock/README.md)

### Raspberry Pi 3 + Waveshare 7.5" B

The Raspberry Pi 3 build renders the book-clock artwork with Python/Pillow and sends black/red channel buffers to the Waveshare 7.5" B e-paper driver.

Start here: [`rpi3-waveshare-book-clock/README.md`](rpi3-waveshare-book-clock/README.md)
