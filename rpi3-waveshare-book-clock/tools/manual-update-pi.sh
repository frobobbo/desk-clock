#!/usr/bin/env bash
set -euo pipefail

INSTALL_DIR="${INSTALL_DIR:-/opt/desk-clock}"
PROJECT_DIR="${INSTALL_DIR}/rpi3-waveshare-book-clock"
STATE_FILE="${STATE_FILE:-/var/lib/desk-clock-rpi/manual-update-state}"

if [[ "${EUID}" -ne 0 ]]; then
  echo "This update script must run as root." >&2
  exit 1
fi

overlay_enabled() {
  local cmdline="/boot/firmware/cmdline.txt"
  if [[ ! -f "${cmdline}" ]]; then
    cmdline="/boot/cmdline.txt"
  fi
  [[ -f "${cmdline}" ]] && grep -qw 'boot=overlay' "${cmdline}"
}

disable_overlayfs() {
  if ! command -v raspi-config >/dev/null 2>&1; then
    echo "raspi-config is required to disable OverlayFS." >&2
    exit 1
  fi
  raspi-config nonint do_overlayfs 1 || raspi-config nonint disable_overlayfs
}

enable_overlayfs() {
  if ! command -v raspi-config >/dev/null 2>&1; then
    echo "raspi-config is required to enable OverlayFS." >&2
    exit 1
  fi
  raspi-config nonint do_overlayfs 0 || raspi-config nonint enable_overlayfs
}

mkdir -p "$(dirname "${STATE_FILE}")"

if overlay_enabled; then
  echo "OverlayFS is enabled. Disabling it before updating..."
  date -Iseconds >"${STATE_FILE}"
  disable_overlayfs
  echo "Rebooting into writable mode. After reboot, run this command again:"
  echo "  sudo ${PROJECT_DIR}/tools/manual-update-pi.sh"
  reboot
  exit 0
fi

if [[ -f "${STATE_FILE}" ]]; then
  echo "Resuming manual Desk Clock update after OverlayFS disable reboot."
else
  echo "OverlayFS is already disabled; running manual Desk Clock update."
fi

"${PROJECT_DIR}/tools/update-pi.sh"

echo "Re-enabling OverlayFS protection..."
enable_overlayfs
rm -f "${STATE_FILE}"

echo
echo "Manual update complete."
echo "Reboot now to activate OverlayFS protection:"
echo "  sudo reboot"
