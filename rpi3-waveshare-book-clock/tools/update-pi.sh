#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/frobobbo/desk-clock.git}"
BRANCH="${BRANCH:-main}"
INSTALL_DIR="${INSTALL_DIR:-/opt/desk-clock}"
APP_USER="${APP_USER:-${SUDO_USER:-pi}}"
APP_GROUP="${APP_GROUP:-$(id -gn "${APP_USER}" 2>/dev/null || true)}"
PROJECT_DIR="${INSTALL_DIR}/rpi3-waveshare-book-clock"
VENV_DIR="${PROJECT_DIR}/.venv"
WAVESHARE_DIR="${WAVESHARE_DIR:-/opt/waveshare-e-Paper}"
FONT_DIR="${FONT_DIR:-/usr/local/share/fonts/desk-clock}"
BASKERVVILLE_FONT_PATH="${FONT_DIR}/Baskervville.ttf"

if [[ "${EUID}" -ne 0 ]]; then
  echo "This updater must run as root." >&2
  exit 1
fi

if ! id "${APP_USER}" >/dev/null 2>&1; then
  echo "APP_USER '${APP_USER}' does not exist" >&2
  exit 1
fi
if [[ -z "${APP_GROUP}" ]]; then
  APP_GROUP="$(id -gn "${APP_USER}")"
fi

if [[ ! -d "${INSTALL_DIR}/.git" ]]; then
  echo "${INSTALL_DIR} is not a git checkout. Run install-pi.sh first." >&2
  exit 1
fi

git_as_app_user() {
  sudo -u "${APP_USER}" git "$@"
}

if [[ -n "$(git_as_app_user -C "${INSTALL_DIR}" status --porcelain)" ]]; then
  echo "${INSTALL_DIR} has local changes; refusing to auto-update." >&2
  git_as_app_user -C "${INSTALL_DIR}" status --short >&2
  exit 1
fi

echo "Fetching ${REPO_URL} ${BRANCH}..."
git_as_app_user -C "${INSTALL_DIR}" remote set-url origin "${REPO_URL}"
git_as_app_user -C "${INSTALL_DIR}" fetch origin "${BRANCH}"

current="$(git_as_app_user -C "${INSTALL_DIR}" rev-parse HEAD)"
target="$(git_as_app_user -C "${INSTALL_DIR}" rev-parse "origin/${BRANCH}")"
if [[ "${current}" == "${target}" ]]; then
  echo "Desk Clock is already up to date at ${current}."
  exit 0
fi

echo "Updating Desk Clock from ${current} to ${target}..."
git_as_app_user -C "${INSTALL_DIR}" checkout "${BRANCH}"
git_as_app_user -C "${INSTALL_DIR}" merge --ff-only "origin/${BRANCH}"

echo "Refreshing Python dependencies..."
python3 -m venv --system-site-packages "${VENV_DIR}"
"${VENV_DIR}/bin/python" -m pip install --upgrade pip wheel
"${VENV_DIR}/bin/python" -m pip install -r "${PROJECT_DIR}/requirements.txt"

if [[ -f "${PROJECT_DIR}/assets/source/Baskervville.ttf" ]]; then
  echo "Refreshing Baskervville font..."
  install -d -m 0755 "${FONT_DIR}"
  install -m 0644 "${PROJECT_DIR}/assets/source/Baskervville.ttf" "${BASKERVVILLE_FONT_PATH}"
  fc-cache -f "${FONT_DIR}" || true
fi

if [[ -d "${WAVESHARE_DIR}/.git" ]]; then
  echo "Updating Waveshare e-Paper checkout..."
  git -C "${WAVESHARE_DIR}" pull --ff-only || true
fi

chown -R "${APP_USER}:${APP_GROUP}" "${INSTALL_DIR}"
if [[ -d "${WAVESHARE_DIR}" ]]; then
  chown -R "${APP_USER}:${APP_GROUP}" "${WAVESHARE_DIR}"
fi

echo "Reloading systemd units and restarting display timer..."
systemctl daemon-reload
systemctl restart desk-clock-rpi.timer

echo "Desk Clock update complete."
