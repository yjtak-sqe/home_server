(async () => {
  let regionColors = {};
  let selectedRegion = null;
  let geojson = null;

  const container = document.getElementById("map-container");
  const svg = d3.select("#map");
  let width = container.clientWidth;
  let height = container.clientHeight;

  const g = svg.append("g");
  const projection = d3.geoMercator();
  const pathGen = d3.geoPath().projection(projection);

  const [geoData, colorData] = await Promise.all([
    fetch("/api/geojson").then(r => r.json()),
    fetch("/api/regions").then(r => r.json()),
  ]);
  geojson = geoData;
  regionColors = colorData;

  function render() {
    width = container.clientWidth;
    height = container.clientHeight;
    svg.attr("viewBox", `0 0 ${width} ${height}`);
    projection.fitSize([width, height], geojson);

    g.selectAll(".region").remove();
    g.selectAll(".region")
      .data(geojson.features)
      .join("path")
      .attr("class", "region")
      .attr("d", pathGen)
      .attr("fill", d => regionColors[d.properties.name] || "#ffffff")
      .on("click", onRegionClick);

    updateCounter();
  }

  render();
  window.addEventListener("resize", render);

  function updateCounter() {
    document.getElementById("visit-count").textContent =
      Object.keys(regionColors).length;
  }

  function onRegionClick(event, d) {
    const name = d.properties.name;
    selectedRegion = name;

    const popup = document.getElementById("color-popup");
    document.getElementById("popup-region-name").textContent = name;
    document.getElementById("color-input").value = regionColors[name] || "#4CAF50";

    const rect = container.getBoundingClientRect();
    let x = event.clientX - rect.left + 10;
    let y = event.clientY - rect.top - 20;
    if (x + 170 > width) x = width - 175;
    if (y + 120 > height) y = height - 125;

    popup.style.left = x + "px";
    popup.style.top = y + "px";
    popup.classList.remove("hidden");

    loadPhotos(name);
    event.stopPropagation();
  }

  container.addEventListener("click", () => {
    document.getElementById("color-popup").classList.add("hidden");
  });

  document.getElementById("btn-apply").addEventListener("click", async () => {
    if (!selectedRegion) return;
    const color = document.getElementById("color-input").value;
    await fetch(`/api/regions/${encodeURIComponent(selectedRegion)}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ color }),
    });
    regionColors[selectedRegion] = color;
    g.selectAll(".region")
      .filter(d => d.properties.name === selectedRegion)
      .attr("fill", color);
    document.getElementById("color-popup").classList.add("hidden");
    updateCounter();
  });

  document.getElementById("btn-clear").addEventListener("click", async () => {
    if (!selectedRegion) return;
    await fetch(`/api/regions/${encodeURIComponent(selectedRegion)}`, { method: "DELETE" });
    delete regionColors[selectedRegion];
    g.selectAll(".region")
      .filter(d => d.properties.name === selectedRegion)
      .attr("fill", "#ffffff");
    document.getElementById("color-popup").classList.add("hidden");
    updateCounter();
  });

  document.getElementById("btn-cancel").addEventListener("click", () => {
    document.getElementById("color-popup").classList.add("hidden");
  });

  async function loadPhotos(regionName) {
    const grid = document.getElementById("photo-grid");
    const empty = document.getElementById("panel-empty");

    document.getElementById("panel-region").textContent = "📍 " + regionName;
    document.getElementById("panel-count").textContent = "불러오는 중...";
    grid.innerHTML = "";

    const photos = await fetch(`/api/photos/${encodeURIComponent(regionName)}`)
      .then(r => r.json());

    if (photos.length === 0) {
      document.getElementById("panel-count").textContent = "사진 없음";
      empty.classList.remove("hidden");
      return;
    }

    empty.classList.add("hidden");
    document.getElementById("panel-count").textContent = `사진 ${photos.length}장`;

    photos.forEach(photo => {
      const img = document.createElement("img");
      img.className = "photo-thumb";
      img.src = `/api/thumbnails/${photo.id}`;
      img.alt = photo.date?.slice(0, 10) || "";
      img.title = photo.date?.slice(0, 10) || "";
      img.loading = "lazy";
      img.addEventListener("click", () => {
        window.open(`${location.origin.replace("8094", "2283")}/photos/${photo.id}`, "_blank");
      });
      grid.appendChild(img);
    });
  }
})();
