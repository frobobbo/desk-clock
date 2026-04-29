const fields = {
  esvApiKey: document.querySelector("#esvApiKey"),
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
  upperEnabled: document.querySelector("#upperEnabled"),
  upperSource: document.querySelector("#upperSource"),
  upperTitle: document.querySelector("#upperTitle"),
  upperText: document.querySelector("#upperText"),
  upperAuthor: document.querySelector("#upperAuthor"),
  lowerEnabled: document.querySelector("#lowerEnabled"),
  lowerSource: document.querySelector("#lowerSource"),
  lowerTitle: document.querySelector("#lowerTitle"),
  lowerText: document.querySelector("#lowerText"),
  lowerAuthor: document.querySelector("#lowerAuthor"),
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
  writeSection("upper", display.upper || defaultUpperSection());
  writeSection("lower", display.lower || defaultLowerSection());
  fields.notes.value = display.notes;
  fields.esvApiKey.value = config.settings?.esv_api_key || "";

  setSectionVisibility();

  document.querySelectorAll(".display-tab").forEach((button) => {
    button.classList.toggle("active", button.dataset.display === activeDisplay);
  });
}

function setSectionVisibility() {
  const isElecrowDisplay = activeDisplay === "elecrow";
  const isPiDisplay = activeDisplay === "waveshare-rpi3";

  document.querySelector("#displaySection").hidden = isElecrowDisplay;
  document.querySelector("#weatherSection").hidden = !isElecrowDisplay;
  document.querySelector("#piSections").hidden = !isPiDisplay;
  document.querySelector("#notesSection").hidden = isElecrowDisplay;
}

function defaultUpperSection() {
  return {
    enabled: true,
    source: "daily_author_quote",
    title: "Literary Quote of the Day",
    text: "I declare after all there is no enjoyment like reading!",
    author: "Jane Austen",
  };
}

function defaultLowerSection() {
  return {
    enabled: true,
    source: "quotes_from_literature",
    title: "Quotes from Literature",
    text: "There is no charm equal to tenderness of heart.",
    author: "Jane Austen, Emma",
  };
}

function writeSection(name, section) {
  fields[`${name}Enabled`].checked = section.enabled;
  fields[`${name}Source`].value = section.source || "daily_author_quote";
  fields[`${name}Title`].value = section.title || "";
  fields[`${name}Text`].value = section.text || "";
  fields[`${name}Author`].value = section.author || "";
}

function readSection(name) {
  return {
    enabled: fields[`${name}Enabled`].checked,
    source: fields[`${name}Source`].value,
    title: fields[`${name}Title`].value.trim(),
    text: fields[`${name}Text`].value.trim(),
    author: fields[`${name}Author`].value.trim(),
  };
}

function readForm() {
  const current = config.displays[activeDisplay] || {};
  const isPiDisplay = activeDisplay === "waveshare-rpi3";
  const quote = current.quote || defaultUpperSection();
  const upper = isPiDisplay ? readSection("upper") : stripDebug(current.upper || defaultUpperSection());
  const lower = isPiDisplay ? readSection("lower") : stripDebug(current.lower || defaultLowerSection());

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
    },
    quote: stripDebug(quote),
    upper,
    lower,
    notes: fields.notes.value.trim(),
  };
}

function stripDebug(section) {
  const { debug, ...clean } = section;
  return clean;
}

function readSettings() {
  return {
    ...(config.settings || {}),
    esv_api_key: fields.esvApiKey.value.trim(),
  };
}

async function saveConfig() {
  config.displays[activeDisplay] = readForm();
  config.settings = readSettings();

  const response = await fetch("/api/config", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(config),
  });
  if (!response.ok) {
    const error = await response.text();
    throw new Error(error || "Failed to save config");
  }
  config = await response.json();
  render();
  showToast("Saved");
}

async function resolveSectionSource(name) {
  const source = fields[`${name}Source`];
  const section = readSection(name);
  source.disabled = true;
  const response = await fetch("/api/quote/resolve", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(section),
  });
  source.disabled = false;

  if (!response.ok) {
    const error = await response.text();
    throw new Error(error || "Failed to fetch section source");
  }

  const resolved = await response.json();
  fields[`${name}Title`].value = resolved.title || fields[`${name}Title`].value;
  fields[`${name}Text`].value = resolved.text || fields[`${name}Text`].value;
  fields[`${name}Author`].value = resolved.author || "";
  showToast(`${name === "upper" ? "Upper" : "Lower"} source loaded`);
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

fields.upperSource.addEventListener("change", () => {
  resolveSectionSource("upper").catch((error) => {
    fields.upperSource.disabled = false;
    showToast(error.message);
  });
});

fields.lowerSource.addEventListener("change", () => {
  resolveSectionSource("lower").catch((error) => {
    fields.lowerSource.disabled = false;
    showToast(error.message);
  });
});

document.querySelectorAll(".display-tab").forEach((button) => {
  button.addEventListener("click", () => {
    config.displays[activeDisplay] = readForm();
    config.settings = readSettings();
    activeDisplay = button.dataset.display;
    render();
  });
});

loadConfig().catch((error) => showToast(error.message));
