const API_BASE = ""; // same-origin, since FastAPI serves this frontend directly

const fileInput = document.getElementById("file-input");
const dropzone = document.getElementById("dropzone");
const dropzoneEmpty = document.getElementById("dropzone-empty");
const previewImage = document.getElementById("preview-image");
const fileMeta = document.getElementById("file-meta");
const assetTypeSelect = document.getElementById("asset-type-select");
const specHint = document.getElementById("spec-hint");
const submitBtn = document.getElementById("submit-btn");
const formError = document.getElementById("form-error");
const form = document.getElementById("review-form");

const reportEmpty = document.getElementById("report-empty");
const reportLoading = document.getElementById("report-loading");
const reportContent = document.getElementById("report-content");

let selectedFile = null;
let assetSpecs = {}; // populated after we know the asset type list; widths/heights shown as hints

// ---- Asset type loading ----

async function loadAssetTypes() {
  try {
    const res = await fetch(`${API_BASE}/api/asset-types`);
    if (!res.ok) throw new Error("Failed to load asset types");
    const data = await res.json();

    assetTypeSelect.innerHTML = '<option value="" disabled selected>Select an asset type&hellip;</option>';
    data.asset_types.forEach((type) => {
      const opt = document.createElement("option");
      opt.value = type;
      opt.textContent = type;
      assetTypeSelect.appendChild(opt);
    });
  } catch (err) {
    assetTypeSelect.innerHTML = '<option value="" disabled selected>Could not load asset types</option>';
    showFormError("Could not reach the backend to load asset types. Is the server running?");
  }
}

assetTypeSelect.addEventListener("change", () => {
  specHint.textContent = ""; // dimension specs are validated server-side; kept simple here
  updateSubmitState();
});

// ---- File selection / drag & drop ----

dropzone.addEventListener("click", () => fileInput.click());

dropzone.addEventListener("dragover", (e) => {
  e.preventDefault();
  dropzone.classList.add("drag-over");
});

dropzone.addEventListener("dragleave", () => {
  dropzone.classList.remove("drag-over");
});

dropzone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropzone.classList.remove("drag-over");
  if (e.dataTransfer.files.length) {
    handleFileSelected(e.dataTransfer.files[0]);
  }
});

fileInput.addEventListener("change", () => {
  if (fileInput.files.length) {
    handleFileSelected(fileInput.files[0]);
  }
});

function handleFileSelected(file) {
  const validTypes = ["image/png", "image/jpeg", "image/webp"];
  if (!validTypes.includes(file.type)) {
    showFormError("Unsupported file type. Please upload a PNG, JPG, or WEBP.");
    return;
  }
  clearFormError();
  selectedFile = file;

  const reader = new FileReader();
  reader.onload = (e) => {
    previewImage.src = e.target.result;
    previewImage.hidden = false;
    dropzoneEmpty.hidden = true;
  };
  reader.readAsDataURL(file);

  const img = new Image();
  img.onload = () => {
    fileMeta.textContent = `${file.name} — ${img.width}\u00d7${img.height}px — ${(file.size / 1024).toFixed(0)} KB`;
  };
  img.src = URL.createObjectURL(file);

  updateSubmitState();
}

function updateSubmitState() {
  submitBtn.disabled = !(selectedFile && assetTypeSelect.value);
}

function showFormError(message) {
  formError.textContent = message;
  formError.hidden = false;
}

function clearFormError() {
  formError.hidden = true;
  formError.textContent = "";
}

// ---- Submit ----

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  if (!selectedFile || !assetTypeSelect.value) return;

  clearFormError();
  setLoadingState();

  const formData = new FormData();
  formData.append("file", selectedFile);
  formData.append("asset_type", assetTypeSelect.value);

  try {
    const res = await fetch(`${API_BASE}/api/review`, {
      method: "POST",
      body: formData,
    });

    if (!res.ok) {
      const errBody = await res.json().catch(() => ({}));
      throw new Error(errBody.detail || `Request failed with status ${res.status}`);
    }

    const report = await res.json();
    renderReport(report);
  } catch (err) {
    setEmptyState();
    showFormError(err.message || "Something went wrong running the review.");
  }
});

function setLoadingState() {
  submitBtn.disabled = true;
  submitBtn.textContent = "Running Review…";
}

function setEmptyState() {
  reportContent.hidden = true;
  reportEmpty.hidden = false;
  submitBtn.disabled = !(selectedFile && assetTypeSelect.value);
  submitBtn.textContent = "Run Compliance Review";
}

// ---- Rendering ----

function renderReport(report) {
  reportEmpty.hidden = true;
  reportContent.hidden = false;
  submitBtn.disabled = !(selectedFile && assetTypeSelect.value);
  submitBtn.textContent = "Run Compliance Review";

  const tv = report.technical_validation;

  const html = `
    <div class="report-hero">
      <div class="report-hero-meta">
        <h3>${escapeHtml(report.filename)}</h3>
        <p>${escapeHtml(report.asset_type)}</p>
      </div>
      <span class="stamp stamp-lg status-${report.overall_status}">${report.overall_status}</span>
    </div>

    <div class="summary-strip">
      <div class="summary-chip pass">
        <span class="count">${report.summary.passed}</span>
        <span class="label">Passed</span>
      </div>
      <div class="summary-chip warn">
        <span class="count">${report.summary.warnings}</span>
        <span class="label">Warnings</span>
      </div>
      <div class="summary-chip fail">
        <span class="count">${report.summary.failed}</span>
        <span class="label">Failed</span>
      </div>
    </div>

    <div class="report-section-title">Technical Validation</div>
    <div class="tech-grid">
      ${renderRuleCard(tv.dimension_check)}
      ${renderRuleCard(tv.aspect_ratio_check)}
    </div>

    <div class="report-section-title">Visual Compliance</div>
    ${report.visual_compliance.map(renderRuleCard).join("")}
  `;

  reportContent.innerHTML = html;
}

function renderRuleCard(rule) {
  const evidenceHtml = rule.evidence && rule.evidence.length
    ? `<ul class="rule-card-evidence">${rule.evidence.map((e) => `<li>${escapeHtml(e)}</li>`).join("")}</ul>`
    : "";

  const recommendationHtml = rule.recommendation
    ? `<p class="rule-card-recommendation"><strong>Fix:</strong> ${escapeHtml(rule.recommendation)}</p>`
    : "";

  return `
    <div class="rule-card status-${rule.status}">
      <div class="rule-card-head">
        <div>
          <div class="rule-card-title">${escapeHtml(rule.title)}</div>
          <div class="rule-card-category">${escapeHtml(rule.category)} &middot; ${escapeHtml(rule.severity)}</div>
        </div>
        <span class="stamp stamp-sm status-${rule.status}">${rule.status}</span>
      </div>
      <p class="rule-card-reason">${escapeHtml(rule.reason)}</p>
      ${evidenceHtml}
      ${recommendationHtml}
    </div>
  `;
}

function escapeHtml(str) {
  if (str === null || str === undefined) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

// ---- Init ----

loadAssetTypes();
