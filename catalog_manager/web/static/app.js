"use strict";

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => Array.from(document.querySelectorAll(sel));

// ── 초기화 ──────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  initMeta();
  initModeTabs();
  initUploads();
  $("#btn-review").addEventListener("click", onReview);
  $("#btn-build").addEventListener("click", onBuild);
});

async function initMeta() {
  try {
    const r = await fetch("/api/meta");
    const meta = await r.json();
    for (const id of ["rv-smst", "bd-smst"]) {
      const sel = $("#" + id);
      sel.innerHTML = "";
      for (const [code, label] of Object.entries(meta.smst_options)) {
        const o = document.createElement("option");
        o.value = code;
        o.textContent = `${code} · ${label}`;
        sel.appendChild(o);
      }
    }
    // 연도 기본값 = 올해
    const yr = String(new Date().getFullYear());
    $("#rv-year").value = yr;
    $("#bd-year").value = yr;
    // 기본 일자 placeholder 채움
    const dz = Object.values(meta.default_dates).join(", ");
    $("#rv-dates").placeholder = dz;
    $("#bd-dates").placeholder = dz;
  } catch (e) {
    console.error("메타 로드 실패", e);
  }
}

// ── 모드 전환 ───────────────────────────────────────────────────────────
function initModeTabs() {
  $$("#modeTabs .tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      $$("#modeTabs .tab").forEach((t) => t.classList.remove("active"));
      tab.classList.add("active");
      const mode = tab.dataset.mode;
      $("#mode-review").hidden = mode !== "review";
      $("#mode-build").hidden = mode !== "build";
    });
  });
}

// ── 업로드 처리 ─────────────────────────────────────────────────────────
function initUploads() {
  $$(".drop").forEach((drop) => {
    const inputId = drop.dataset.for;
    const input = $("#" + inputId);
    const nameEl = $("#name-" + inputId);

    input.addEventListener("change", () => updateFileName(input, drop, nameEl));

    drop.addEventListener("dragover", (e) => { e.preventDefault(); drop.classList.add("dragover"); });
    drop.addEventListener("dragleave", () => drop.classList.remove("dragover"));
    drop.addEventListener("drop", (e) => {
      e.preventDefault();
      drop.classList.remove("dragover");
      if (e.dataTransfer.files.length) {
        input.files = e.dataTransfer.files;
        updateFileName(input, drop, nameEl);
      }
    });
  });
}

function updateFileName(input, drop, nameEl) {
  if (input.files.length) {
    nameEl.textContent = input.files[0].name;
    drop.classList.add("filled");
  } else {
    nameEl.textContent = "파일 선택";
    drop.classList.remove("filled");
  }
}

// ── 오버레이 ────────────────────────────────────────────────────────────
function showOverlay(text) {
  $("#overlay-text").textContent = text || "처리 중...";
  $("#overlay").hidden = false;
}
function hideOverlay() { $("#overlay").hidden = true; }

// ── 검토 실행 ───────────────────────────────────────────────────────────
async function onReview() {
  const planning = $("#rv-planning").files[0];
  const catalog = $("#rv-catalog").files[0];
  const landing = $("#rv-landing").files[0];
  const box = $("#rv-results");

  if (!planning || !catalog || !landing) {
    return showError(box, "기획자료·카탈로그·랜딩주소 세 파일을 모두 업로드해 주세요.");
  }

  const fd = new FormData();
  fd.append("year", $("#rv-year").value);
  fd.append("smst", $("#rv-smst").value);
  fd.append("dates", $("#rv-dates").value);
  fd.append("planning", planning);
  fd.append("catalog", catalog);
  fd.append("landing", landing);

  showOverlay("검토 중입니다... (파일 크기에 따라 수십 초)");
  try {
    const r = await fetch("/api/review", { method: "POST", body: fd });
    const data = await r.json();
    if (!r.ok) return showError(box, data.detail || "검토 실패");
    renderReview(box, data);
  } catch (e) {
    showError(box, "요청 실패: " + e.message);
  } finally {
    hideOverlay();
  }
}

// ── 생성 실행 ───────────────────────────────────────────────────────────
async function onBuild() {
  const template = $("#bd-template").files[0];
  const landing = $("#bd-landing").files[0];
  const planning = $("#bd-planning").files[0];
  const box = $("#bd-results");

  if (!template || !landing) {
    return showError(box, "카탈로그_공란과 랜딩주소 파일은 필수입니다.");
  }

  const fd = new FormData();
  fd.append("year", $("#bd-year").value);
  fd.append("smst", $("#bd-smst").value);
  fd.append("dates", $("#bd-dates").value);
  fd.append("template", template);
  fd.append("landing", landing);
  if (planning) fd.append("planning", planning);

  showOverlay("새 카탈로그 생성 중...");
  try {
    const r = await fetch("/api/build", { method: "POST", body: fd });
    const data = await r.json();
    if (!r.ok) return showError(box, data.detail || "생성 실패");
    renderBuild(box, data);
  } catch (e) {
    showError(box, "요청 실패: " + e.message);
  } finally {
    hideOverlay();
  }
}

// ── 렌더링: 검토 ────────────────────────────────────────────────────────
function renderReview(box, data) {
  const s = data.stats, u = data.url_stats;
  const dl = (key, label, primary) =>
    data.files[key]
      ? `<a class="dl ${primary ? "primary" : ""}" href="/api/download/${data.job_id}/${encodeURIComponent(data.files[key])}">⬇ ${label}</a>`
      : "";

  box.hidden = false;
  box.innerHTML = `
    <h2>검토 결과</h2>
    <div class="stat-grid">
      <div class="stat"><div class="num">${s.total}</div><div class="lbl">전체</div></div>
      <div class="stat mismatch"><div class="num">${s.mismatch}</div><div class="lbl">불일치</div></div>
      <div class="stat fuzzy"><div class="num">${s.fuzzy}</div><div class="lbl">유사매칭</div></div>
      <div class="stat nomatch"><div class="num">${s.no_match}</div><div class="lbl">미매칭</div></div>
      <div class="stat ok"><div class="num">${s.ok}</div><div class="lbl">정상</div></div>
      <div class="stat err"><div class="num">${u.error + u.missing}</div><div class="lbl">URL오류</div></div>
    </div>
    <div class="downloads">
      ${dl("corrected", "교정 카탈로그", true)}
      ${dl("fuzzy", "유사강좌명 검토")}
      ${dl("url_errors", "URL 오류목록")}
      ${dl("csv", "비교결과 CSV")}
    </div>
    <div class="subtabs" id="rv-subtabs">
      <button class="subtab active" data-tab="comp">비교결과</button>
      <button class="subtab" data-tab="url">URL 검토</button>
      <button class="subtab" data-tab="fuzzy">유사강좌명 (${data.fuzzy.length})</button>
    </div>
    <div id="rv-tab-comp"></div>
    <div id="rv-tab-url" hidden></div>
    <div id="rv-tab-fuzzy" hidden></div>
    ${renderLogs(data.logs)}
  `;

  renderCompTable($("#rv-tab-comp"), data.comparison);
  renderUrlTable($("#rv-tab-url"), data.urls);
  renderFuzzyTable($("#rv-tab-fuzzy"), data.fuzzy);

  $$("#rv-subtabs .subtab").forEach((t) => {
    t.addEventListener("click", () => {
      $$("#rv-subtabs .subtab").forEach((x) => x.classList.remove("active"));
      t.classList.add("active");
      $("#rv-tab-comp").hidden = t.dataset.tab !== "comp";
      $("#rv-tab-url").hidden = t.dataset.tab !== "url";
      $("#rv-tab-fuzzy").hidden = t.dataset.tab !== "fuzzy";
    });
  });

  box.scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderCompTable(container, rows) {
  const filters = `
    <div class="filters" data-target="comp">
      <button class="chip active" data-f="all">전체</button>
      <button class="chip" data-f="mismatch">불일치만</button>
      <button class="chip" data-f="fuzzy">유사매칭</button>
      <button class="chip" data-f="no_match">미매칭</button>
    </div>`;
  container.innerHTML = filters + buildCompTable(rows, "all");
  wireFilters(container, rows, buildCompTable);
}

function buildCompTable(rows, filter) {
  let filtered = rows;
  if (filter === "mismatch") filtered = rows.filter((r) => r.mismatches.length);
  else if (filter === "fuzzy") filtered = rows.filter((r) => r.match_type === "fuzzy");
  else if (filter === "no_match") filtered = rows.filter((r) => r.match_type === "no_match");

  if (!filtered.length) return `<div class="tbl-wrap"><div class="empty">해당 항목이 없습니다.</div></div>`;

  const body = filtered.map((r) => {
    const cls = r.mismatches.length ? "row-mm" : (r.match_type === "fuzzy" ? "row-fz" : "");
    const mm = r.mismatches.length
      ? `<div class="mm-list">${r.mismatches.map((m) =>
          `<div class="mm-item"><span class="f">${esc(m.field)}</span>: ${esc(m.catalog)}<span class="arrow">→</span>${esc(m.planning)}</div>`
        ).join("")}</div>`
      : '<span style="color:var(--text3)">—</span>';
    return `<tr class="${cls}">
      <td>${esc(r.sheet)}</td>
      <td>${esc(r.course)}</td>
      <td><span class="badge ${r.match_type}">${matchLabel(r.match_type)}</span>${
        r.match_type === "fuzzy" ? ` <small style="color:var(--text3)">${Math.round(r.fuzzy_score * 100)}%</small>` : ""
      }</td>
      <td>${mm}</td>
    </tr>`;
  }).join("");

  return `<div class="tbl-wrap"><table>
    <thead><tr><th>시트</th><th>강좌명</th><th>매칭</th><th>불일치 항목</th></tr></thead>
    <tbody>${body}</tbody></table></div>`;
}

function renderUrlTable(container, rows) {
  const filters = `
    <div class="filters" data-target="url">
      <button class="chip active" data-f="all">전체</button>
      <button class="chip" data-f="error">오류만</button>
    </div>`;
  container.innerHTML = filters + buildUrlTable(rows, "all");
  wireFilters(container, rows, buildUrlTable);
}

function buildUrlTable(rows, filter) {
  let filtered = rows;
  if (filter === "error") filtered = rows.filter((r) => r.status !== "ok");
  if (!filtered.length) return `<div class="tbl-wrap"><div class="empty">해당 항목이 없습니다.</div></div>`;

  const body = filtered.map((r) => {
    const cls = r.status !== "ok" ? "row-mm" : "";
    const issues = r.issues.length
      ? r.issues.map((i) => esc(i)).join("<br>")
      : '<span style="color:var(--text3)">—</span>';
    return `<tr class="${cls}">
      <td>${esc(r.sheet)}</td>
      <td>${esc(r.course)}</td>
      <td class="mono">${esc(r.lect_code)}</td>
      <td><span class="badge ${r.status}">${urlLabel(r.status)}</span></td>
      <td>${issues}</td>
    </tr>`;
  }).join("");

  return `<div class="tbl-wrap"><table>
    <thead><tr><th>시트</th><th>강좌명</th><th>lectCode</th><th>상태</th><th>이슈</th></tr></thead>
    <tbody>${body}</tbody></table></div>`;
}

function renderFuzzyTable(container, rows) {
  if (!rows.length) {
    container.innerHTML = `<div class="tbl-wrap"><div class="empty">유사매칭 항목이 없습니다.</div></div>`;
    return;
  }
  const body = rows.map((r) => {
    const has = (f) => r.mismatches.some((m) => m.field === f);
    const chk = (f) => has(f) ? '<span style="color:var(--error)">✗</span>' : '<span style="color:var(--success)">✓</span>';
    return `<tr class="row-fz">
      <td>${esc(r.sheet)}</td>
      <td>${esc(r.course)}</td>
      <td>${esc(r.plan_name)}</td>
      <td>${Math.round(r.fuzzy_score * 100)}%</td>
      <td style="text-align:center">${chk("요일")}</td>
      <td style="text-align:center">${chk("강좌시간")}</td>
      <td style="text-align:center">${chk("강사명")}</td>
    </tr>`;
  }).join("");
  container.innerHTML = `<p class="hint">강좌명이 정확히 일치하지 않아 유사도로 매칭된 항목입니다. 직접 확인하세요.</p>
    <div class="tbl-wrap"><table>
    <thead><tr><th>시트</th><th>카탈로그 강좌명</th><th>기획자료 강좌명</th><th>유사도</th><th>요일</th><th>시간</th><th>강사</th></tr></thead>
    <tbody>${body}</tbody></table></div>`;
}

function wireFilters(container, rows, builder) {
  const chips = container.querySelector(".filters");
  chips.addEventListener("click", (e) => {
    const chip = e.target.closest(".chip");
    if (!chip) return;
    chips.querySelectorAll(".chip").forEach((c) => c.classList.remove("active"));
    chip.classList.add("active");
    const tableHtml = builder(rows, chip.dataset.f);
    // 필터 div는 유지하고 테이블만 교체
    const existing = container.querySelector(".tbl-wrap");
    if (existing) existing.outerHTML = tableHtml;
    else container.insertAdjacentHTML("beforeend", tableHtml);
  });
}

// ── 렌더링: 생성 ────────────────────────────────────────────────────────
function renderBuild(box, data) {
  box.hidden = false;
  box.innerHTML = `
    <h2>생성 완료 ✅</h2>
    <p class="hint">랜딩주소 ${data.landing_count}개 기준으로 카탈로그를 생성했습니다.
      ${data.used_planning ? "기획자료를 사용해 요일·시간·강사명·강좌비까지 채웠습니다." : "기획자료 없이 URL 열만 채웠습니다."}</p>
    <div class="downloads">
      <a class="dl primary" href="/api/download/${data.job_id}/${encodeURIComponent(data.files.catalog)}">⬇ 완성된 카탈로그 다운로드</a>
    </div>
    ${renderLogs(data.logs)}
  `;
  box.scrollIntoView({ behavior: "smooth", block: "start" });
}

// ── 공통 ────────────────────────────────────────────────────────────────
function renderLogs(logs) {
  if (!logs || !logs.length) return "";
  const lines = logs.map((l) => {
    const m = l.match(/^\[(\w+)\]\s*(.*)$/);
    const lvl = m ? m[1] : "INFO";
    const txt = m ? m[2] : l;
    return `<div class="l-${lvl}">[${lvl}] ${esc(txt)}</div>`;
  }).join("");
  return `<div class="logbox">${lines}</div>`;
}

function showError(box, msg) {
  box.hidden = false;
  box.innerHTML = `<div class="err-banner">⚠ ${esc(msg)}</div>`;
  box.scrollIntoView({ behavior: "smooth", block: "start" });
}

function matchLabel(t) {
  return { exact: "정확", fuzzy: "유사", no_match: "미매칭" }[t] || t;
}
function urlLabel(s) {
  return { ok: "정상", mismatch: "오류", url_missing: "URL없음" }[s] || s;
}
function esc(s) {
  return String(s == null ? "" : s)
    .replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
}
