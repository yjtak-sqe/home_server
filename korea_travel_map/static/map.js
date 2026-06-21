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
      .style("fill", d => regionColors[d.properties.name] || null)
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

  // 팝업 내부 클릭은 container로 버블링되지 않도록
  document.getElementById("color-popup").addEventListener("click", (e) => {
    e.stopPropagation();
  });

  document.getElementById("btn-apply").addEventListener("click", async () => {
    if (!selectedRegion) return;
    const color = document.getElementById("color-input").value;
    const region = selectedRegion;
    regionColors[region] = color;
    g.selectAll(".region")
      .filter(d => d.properties.name === region)
      .style("fill", color);
    document.getElementById("color-popup").classList.add("hidden");
    updateCounter();
    fetch(`/api/regions/${encodeURIComponent(region)}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ color }),
    });
  });

  document.getElementById("btn-clear").addEventListener("click", async () => {
    if (!selectedRegion) return;
    const region = selectedRegion;
    delete regionColors[region];
    g.selectAll(".region")
      .filter(d => d.properties.name === region)
      .style("fill", null);
    document.getElementById("color-popup").classList.add("hidden");
    updateCounter();
    fetch(`/api/regions/${encodeURIComponent(region)}`, { method: "DELETE" });
  });

  document.getElementById("btn-cancel").addEventListener("click", () => {
    document.getElementById("color-popup").classList.add("hidden");
  });

  let photoAbortController = null;

  async function loadPhotos(regionName) {
    if (photoAbortController) photoAbortController.abort();
    photoAbortController = new AbortController();
    const signal = photoAbortController.signal;

    const grid = document.getElementById("photo-grid");
    const loading = document.getElementById("panel-loading");
    const empty = document.getElementById("panel-empty");

    document.getElementById("panel-region").textContent = "📍 " + regionName;
    document.getElementById("panel-count").textContent = "";
    grid.innerHTML = "";
    empty.classList.add("hidden");
    loading.classList.remove("hidden");

    let photos;
    try {
      const resp = await fetch(`/api/photos/${encodeURIComponent(regionName)}`, { signal });
      photos = await resp.json();
    } catch (e) {
      if (e.name === "AbortError") return;
      loading.classList.add("hidden");
      document.getElementById("panel-count").textContent = "오류 발생";
      return;
    }

    loading.classList.add("hidden");

    if (photos.length === 0) {
      document.getElementById("panel-count").textContent = "사진 없음";
      empty.classList.remove("hidden");
      return;
    }

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
  // ── 패널 크기 조절 ─────────────────────────────────────
  const resizer = document.getElementById("resizer");
  const panel = document.getElementById("photo-panel");

  resizer.addEventListener("mousedown", (e) => {
    e.preventDefault();
    resizer.classList.add("dragging");
    document.body.style.userSelect = "none";
    document.body.style.cursor = "col-resize";
    svg.style("pointer-events", "none");

    const startX = e.clientX;
    const startWidth = panel.offsetWidth;

    function onMove(e) {
      const newWidth = startWidth - (e.clientX - startX);
      if (newWidth >= 200 && newWidth <= window.innerWidth * 0.7) {
        panel.style.width = newWidth + "px";
      }
    }

    function onUp() {
      resizer.classList.remove("dragging");
      document.body.style.userSelect = "";
      document.body.style.cursor = "";
      svg.style("pointer-events", null);
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseup", onUp);
    }

    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseup", onUp);
  });
})();
