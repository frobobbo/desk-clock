#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/frobobbo/desk-clock.git}"
BRANCH="${BRANCH:-main}"
INSTALL_DIR="${INSTALL_DIR:-/opt/desk-clock}"
APP_USER="${APP_USER:-${SUDO_USER:-$USER}}"
APP_GROUP="${APP_GROUP:-$(id -gn "${APP_USER}" 2>/dev/null || true)}"
PROJECT_DIR="${INSTALL_DIR}/rpi3-waveshare-book-clock"
VENV_DIR="${PROJECT_DIR}/.venv"
WAVESHARE_DIR="${WAVESHARE_DIR:-/opt/waveshare-e-Paper}"
CREATE_SERVICE="${CREATE_SERVICE:-1}"
RUN_ON_INSTALL="${RUN_ON_INSTALL:-0}"

if [[ "${EUID}" -ne 0 ]]; then
  echo "This installer must run as root. Use: curl -fsSL <url> | sudo bash" >&2
  exit 1
fi

if ! id "${APP_USER}" >/dev/null 2>&1; then
  echo "APP_USER '${APP_USER}' does not exist" >&2
  exit 1
fi
if [[ -z "${APP_GROUP}" ]]; then
  APP_GROUP="$(id -gn "${APP_USER}")"
fi

export DEBIAN_FRONTEND=noninteractive

echo "Installing OS packages..."
apt-get update
apt-get install -y \
  git \
  python3 \
  python3-pip \
  python3-venv \
  python3-dev \
  python3-pil \
  python3-numpy \
  python3-spidev \
  python3-rpi.gpio \
  python3-smbus \
  libopenjp2-7 \
  fonts-gfs-baskerville \
  fonts-dejavu-core \
  fonts-liberation \
  ca-certificates

echo "Enabling SPI..."
if command -v raspi-config >/dev/null 2>&1; then
  raspi-config nonint do_spi 0 || true
fi

CONFIG_TXT="/boot/firmware/config.txt"
if [[ ! -f "${CONFIG_TXT}" ]]; then
  CONFIG_TXT="/boot/config.txt"
fi
if [[ -f "${CONFIG_TXT}" ]] && ! grep -q '^dtparam=spi=on' "${CONFIG_TXT}"; then
  printf '\n# Enabled by desk-clock installer\ndtparam=spi=on\n' >> "${CONFIG_TXT}"
fi

echo "Cloning or updating ${REPO_URL}..."
mkdir -p "${INSTALL_DIR}"
if [[ -d "${INSTALL_DIR}/.git" ]]; then
  git -C "${INSTALL_DIR}" fetch origin "${BRANCH}"
  git -C "${INSTALL_DIR}" checkout "${BRANCH}"
  git -C "${INSTALL_DIR}" pull --ff-only origin "${BRANCH}"
else
  if [[ -n "$(find "${INSTALL_DIR}" -mindepth 1 -maxdepth 1 -print -quit)" ]]; then
    echo "${INSTALL_DIR} exists and is not a git checkout. Set INSTALL_DIR to another path." >&2
    exit 1
  fi
  git clone --branch "${BRANCH}" "${REPO_URL}" "${INSTALL_DIR}"
fi

echo "Creating Python virtual environment..."
python3 -m venv --system-site-packages "${VENV_DIR}"
"${VENV_DIR}/bin/python" -m pip install --upgrade pip wheel
"${VENV_DIR}/bin/python" -m pip install -r "${PROJECT_DIR}/requirements.txt"

echo "Checking Waveshare Python driver..."
if ! "${VENV_DIR}/bin/python" - <<'PY'
try:
    from waveshare_epd import epd7in5_V2  # noqa: F401
except ImportError:
    from waveshare_epd import epd7in5  # noqa: F401
PY
then
  echo "PyPI driver import failed; cloning Waveshare's official e-Paper repo..."
  if [[ -d "${WAVESHARE_DIR}/.git" ]]; then
    git -C "${WAVESHARE_DIR}" pull --ff-only
  else
    git clone https://github.com/waveshare/e-Paper.git "${WAVESHARE_DIR}"
  fi
fi

PYTHONPATH_VALUE=""
WAVESHARE_LIB="${WAVESHARE_DIR}/RaspberryPi_JetsonNano/python/lib"
if [[ -d "${WAVESHARE_LIB}" ]]; then
  PYTHONPATH_VALUE="${WAVESHARE_LIB}"
fi

echo "Writing runtime environment..."
cat >/etc/desk-clock-rpi.env <<EOF
PYTHONUNBUFFERED=1
PYTHONPATH=${PYTHONPATH_VALUE}
EOF

chown -R "${APP_USER}:${APP_GROUP}" "${INSTALL_DIR}"
if [[ -d "${WAVESHARE_DIR}" ]]; then
  chown -R "${APP_USER}:${APP_GROUP}" "${WAVESHARE_DIR}"
fi

if [[ "${CREATE_SERVICE}" == "1" ]]; then
  echo "Installing systemd service and timer..."
  cat >/etc/systemd/system/desk-clock-rpi.service <<EOF
[Unit]
Description=Render Desk Clock to Waveshare 7.5 inch e-ink display
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=${APP_USER}
Group=${APP_GROUP}
WorkingDirectory=${PROJECT_DIR}
EnvironmentFile=-/etc/desk-clock-rpi.env
ExecStart=${VENV_DIR}/bin/python ${PROJECT_DIR}/src/display_book_clock.py --display
EOF

  cat >/etc/systemd/system/desk-clock-rpi.timer <<'EOF'
[Unit]
Description=Refresh Desk Clock e-ink display hourly

[Timer]
OnBootSec=2min
OnUnitActiveSec=1h
Persistent=true
Unit=desk-clock-rpi.service

[Install]
WantedBy=timers.target
EOF

  systemctl daemon-reload
  systemctl enable desk-clock-rpi.timer
fi

echo "Rendering a preview..."
sudo -u "${APP_USER}" env PYTHONPATH="${PYTHONPATH_VALUE}" "${VENV_DIR}/bin/python" \
  "${PROJECT_DIR}/src/display_book_clock.py" --preview-only

if [[ "${RUN_ON_INSTALL}" == "1" ]]; then
  echo "Running an immediate display refresh..."
  systemctl start desk-clock-rpi.service
fi

echo
echo "Install complete."
echo
echo "Next steps:"
echo "  1. Reboot if SPI was not already enabled: sudo reboot"
echo "  2. Verify SPI after reboot: ls -l /dev/spidev*"
echo "  3. Render to the display once: sudo systemctl start desk-clock-rpi.service"
echo "  4. Watch logs: journalctl -u desk-clock-rpi.service -n 100 --no-pager"
echo "  5. Timer status: systemctl status desk-clock-rpi.timer"
