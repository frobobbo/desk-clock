const fields = {
  enabled: document.querySelector("#enabled"),
  headline: document.querySelector("#headline"),
  subtitle: document.querySelector("#subtitle"),
  showTime: document.querySelector("#showTime"),
  showDate: document.querySelector("#showDate"),
  footerLeft: document.querySelector("#footerLeft"),
  footerRight: document.querySelector("#footerRight"),
  refreshMinutes: document.querySelector("#refreshMinutes"),
  weatherEnabled: document.querySelector("#weatherEnabled"),
  weatherLocation: document.querySelector("#weatherLocation"),
  weatherTemperature: document.querySelector("#weatherTemperature"),
  weatherCondition: document.querySelector("#weatherCondition"),
  weatherHumidity: document.querySelector("#weatherHumidity"),
  weatherWind: document.querySelector("#weatherWind"),
  quoteEnabled: document.querySelector("#quoteEnabled"),
  quoteText: document.querySelector("#quoteText"),
  quoteAuthor: document.querySelector("#quoteAuthor"),
  notes: document.querySelector("#notes"),
};

let config = null;
let activeDisplay = "elecrow";

async function loadConfig() {
  const response = await fetch("/api/config");
  if (!response.ok) {
    throw new Error("Failed to load config");
  }
  config = await response.json();
  render();
}

function render() {
  const display = config.displays[activeDisplay];
  if (!display) {
    return;
  }

  document.querySelector("#updatedAt").textContent = config.updated_at
    ? `Updated ${config.updated_at}`
    : "No saved changes yet";

  fields.enabled.checked = display.enabled;
  fields.headline.value = display.headline;
  fields.subtitle.value = display.subtitle;
  fields.showTime.checked = display.show_time;
  fields.showDate.checked = display.show_date;
  fields.footerLeft.value = display.footer_left;
  fields.footerRight.value = display.footer_right;
  fields.refreshMinutes.value = display.refresh_minutes;
  fields.weatherEnabled.checked = display.weather.enabled;
  fields.weatherLocation.value = display.weather.location_label;
  fields.weatherTemperature.value = display.weather.temperature;
  fields.weatherCondition.value = display.weather.condition;
  fields.weatherHumidity.value = display.weather.humidity;
  fields.weatherWind.value = display.weather.wind;
  fields.quoteEnabled.checked = display.quote.enabled;
  fields.quoteText.value = display.quote.text;
  fields.quoteAuthor.value = display.quote.author;
  fields.notes.value = display.notes;

  document.querySelectorAll(".display-tab").forEach((button) => {
    button.classList.toggle("active", button.dataset.display === activeDisplay);
  });
}

function readForm() {
  return {
    enabled: fields.enabled.checked,
    headline: fields.headline.value.trim(),
    subtitle: fields.subtitle.value.trim(),
    show_time: fields.showTime.checked,
    show_date: fields.showDate.checked,
    footer_left: fields.footerLeft.value.trim(),
    footer_right: fields.footerRight.value.trim(),
    refresh_minutes: Number(fields.refreshMinutes.value || 30),
    weather: {
      enabled: fields.weatherEnabled.checked,
      location_label: fields.weatherLocation.value.trim(),
      temperature: fields.weatherTemperature.value.trim(),
      condition: fields.weatherCondition.value.trim(),
      humidity: fields.weatherHumidity.value.trim(),
      wind: fields.weatherWind.value.trim(),
    },
    quote: {
      enabled: fields.quoteEnabled.checked,
      text: fields.quoteText.value.trim(),
      author: fields.quoteAuthor.value.trim(),
    },
    notes: fields.notes.value.trim(),
  };
}

async function saveConfig() {
  config.displays[activeDisplay] = readForm();
  const response = await fetch(`/api/displays/${encodeURIComponent(activeDisplay)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(config.displays[activeDisplay]),
  });
  if (!response.ok) {
    const error = await response.text();
    throw new Error(error || "Failed to save config");
  }
  config = await response.json();
  render();
  showToast("Saved");
}

function showToast(message) {
  const toast = document.querySelector("#toast");
  toast.textContent = message;
  toast.classList.add("show");
  window.setTimeout(() => toast.classList.remove("show"), 1800);
}

document.querySelector("#saveButton").addEventListener("click", () => {
  saveConfig().catch((error) => showToast(error.message));
});

document.querySelectorAll(".display-tab").forEach((button) => {
  button.addEventListener("click", () => {
    config.displays[activeDisplay] = readForm();
    activeDisplay = button.dataset.display;
    render();
  });
});

loadConfig().catch((error) => showToast(error.message));

