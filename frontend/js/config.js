"use strict";

function populateSelect(select, options, emptyMessage) {
  select.replaceChildren();
  if (!options.length) {
    const option = new Option(emptyMessage, "");
    option.disabled = true;
    option.selected = true;
    select.add(option);
    return;
  }
  options.forEach((item) => select.add(new Option(item.name || item.label || item.id, item.id)));
}

window.loadNapasLokaOptions = async function loadNapasLokaOptions() {
  const options = await window.NapasLokaApi.request("/config/options");
  const mappings = {
    location: [options.locations, "Lokasi belum dikonfigurasi"],
    pollutant: [options.pollutants, "Polutan tidak tersedia"],
    scenario: [options.scenarios, "Skenario tidak tersedia"],
    algorithm: [options.algorithms, "Algoritma tidak tersedia"]
  };
  Object.entries(mappings).forEach(([name, [items, message]]) => {
    const select = document.querySelector(`[name="${name}"]`);
    if (select) populateSelect(select, items, message);
  });
  return options;
};
