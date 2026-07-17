/**
 * Apex LoRA Loader Web Extension
 * Interactive folder browser embedded inside the node
 *
 * Modern ComfyUI extension API:
 * - nodeCreated for per-instance setup (replaces beforeRegisterNodeDef + onNodeCreated patching)
 * - loadedGraphNode for workflow restore
 * - Object.defineProperty on widget.value to intercept ALL value changes
 * - addDOMWidget for embedded HTML panel
 * - serialize = false on button widget
 */

import { app } from "../../../scripts/app.js";
import { api } from "../../../scripts/api.js";

// ── Helpers ──────────────────────────────────────────────────────────────────

async function fetchLoraPreview(loraName) {
    const res = await api.fetchApi("/apex/lora_preview", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ lora_name: loraName })
    });
    if (!res.ok) return null;
    const data = await res.json();
    return data.preview_path ?? null;
}

function buildBrowserDOM() {
    const container = document.createElement("div");
    container.style.cssText = `
        width: 100%;
        max-height: 500px;
        overflow: hidden;
        background: #1a1a1a;
        border: 1px solid #444;
        border-radius: 5px;
        display: flex;
        flex-direction: column;
    `;

    const header = document.createElement("div");
    header.style.cssText = `
        padding: 8px 10px;
        background: #252525;
        border-bottom: 1px solid #444;
        color: #aaa;
        font-size: 12px;
        display: flex;
        align-items: center;
        gap: 5px;
        flex-shrink: 0;
    `;

    const content = document.createElement("div");
    content.style.cssText = `
        flex: 1;
        overflow-y: auto;
        overflow-x: hidden;
        padding: 10px;
        max-height: 400px;
    `;

    const foldersSection = document.createElement("div");
    foldersSection.style.marginBottom = "10px";

    const foldersTitle = document.createElement("h4");
    foldersTitle.textContent = "Folders:";
    foldersTitle.style.cssText = "color:#fff;margin:0 0 8px 0;font-size:12px;";

    const foldersGrid = document.createElement("div");
    foldersGrid.style.cssText = "display:flex;flex-wrap:wrap;gap:8px;";

    foldersSection.appendChild(foldersTitle);
    foldersSection.appendChild(foldersGrid);

    const lorasSection = document.createElement("div");

    const lorasTitle = document.createElement("h4");
    lorasTitle.textContent = "LoRAs:";
    lorasTitle.style.cssText = "color:#fff;margin:0 0 8px 0;font-size:12px;";

    const lorasGrid = document.createElement("div");
    lorasGrid.style.cssText = `
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(80px, 1fr));
        gap: 10px;
        margin-bottom: 10px;
    `;

    lorasSection.appendChild(lorasTitle);
    lorasSection.appendChild(lorasGrid);

    const pagination = document.createElement("div");
    pagination.style.cssText = `
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 8px;
        padding: 8px;
        flex-shrink: 0;
    `;

    content.appendChild(foldersSection);
    content.appendChild(lorasSection);
    content.appendChild(pagination);
    container.appendChild(header);
    container.appendChild(content);

    const previewContainer = document.createElement("div");
    previewContainer.style.cssText = `
        width: 100%;
        min-height: 200px;
        background: #1a1a1a;
        border: 1px solid #444;
        border-radius: 5px;
        display: none;
        align-items: center;
        justify-content: center;
        overflow: hidden;
        padding: 10px;
    `;

    const previewImg = document.createElement("img");
    previewImg.style.cssText = `
        max-width: 100%;
        max-height: 100%;
        object-fit: contain;
        border-radius: 4px;
    `;
    previewContainer.appendChild(previewImg);

    return { container, header, foldersGrid, lorasGrid, pagination, previewContainer, previewImg };
}

// ── Node setup ────────────────────────────────────────────────────────────────

function setupLoraLoaderNode(node) {
    const loraWidget = node.widgets?.find(w => w.name === "lora_name");
    if (!loraWidget) return;

    // Per-instance state
    node._loraState = {
        currentFolder: "",
        selectedLora: loraWidget.value || "",
        selectedLoraPreview: null,
        currentPage: 0,
        itemsPerPage: 50,
        browserExpanded: true,
        loras: [],         // cache for pagination
    };

    const s = node._loraState;

    // ── Intercept ALL widget value changes (including workflow restore, arrow keys) ──
    const _key = "_apexLoraValue";
    loraWidget[_key] = loraWidget.value ?? "";

    Object.defineProperty(loraWidget, "value", {
        get() { return this[_key]; },
        set(newVal) {
            const old = this[_key];
            this[_key] = newVal;
            if (old !== newVal && newVal) {
                s.selectedLora = newVal;
                onLoraChanged(node, newVal);
                if (s.browserExpanded) {
                    setTimeout(() => {
                        s.browserExpanded = false;
                        updateBrowserVisibility(node);
                    }, 100);
                }
            }
        },
        enumerable: true,
        configurable: true,
    });

    // ── Build DOM ────────────────────────────────────────────────────────────
    const dom = buildBrowserDOM();
    node._loraDom = dom;

    // ── Toggle button ────────────────────────────────────────────────────────
    const toggleBtn = node.addWidget("button", "toggle_browser", "📁 Hide Browser", () => {
        s.browserExpanded = !s.browserExpanded;
        updateBrowserVisibility(node);
    });
    toggleBtn.serialize = false;

    // ── DOM widgets ──────────────────────────────────────────────────────────
    node.addDOMWidget("lora_browser", "div", dom.container, {
        getValue: () => s.selectedLora,
        setValue: (v) => { s.selectedLora = v; },
        hideOnZoom: false,
        getHeight:    () => s.browserExpanded ? 500 : 0,
        getMinHeight: () => s.browserExpanded ? 400 : 0,
        getMaxHeight: () => s.browserExpanded ? 600 : 0,
    });

    node.addDOMWidget("lora_preview", "div", dom.previewContainer, {
        getValue: () => s.selectedLoraPreview,
        setValue: (v) => { s.selectedLoraPreview = v; },
        hideOnZoom: false,
        getHeight:    () => (!s.browserExpanded && s.selectedLoraPreview) ? 250 : 0,
        getMinHeight: () => (!s.browserExpanded && s.selectedLoraPreview) ? 200 : 0,
        getMaxHeight: () => (!s.browserExpanded && s.selectedLoraPreview) ? 400 : 0,
    });

    // ── Initial load ─────────────────────────────────────────────────────────
    loadBrowserFolder(node, "");
    updateBrowserVisibility(node);
}

// ── Browser visibility ────────────────────────────────────────────────────────

function updateBrowserVisibility(node) {
    try {
        const s = node._loraState;
        const dom = node._loraDom;
        if (!s || !dom) return;

        const toggleWidget = node.widgets?.find(w => w.name === "toggle_browser");
        if (toggleWidget) {
            toggleWidget.label = s.browserExpanded ? "📁 Hide Browser" : "📁 Show Browser";
        }

        if (s.browserExpanded) {
            dom.container.style.display = "flex";
            dom.previewContainer.style.display = "none";
            node.size[1] = Math.max(node.size[1], 620);
        } else {
            dom.container.style.display = "none";
            if (s.selectedLoraPreview && s.selectedLoraPreview !== "loading") {
                dom.previewContainer.style.display = "flex";
                node.size[1] = Math.max(node.computeSize()[1], 350);
            } else {
                dom.previewContainer.style.display = "none";
                node.size[1] = node.computeSize()[1];
            }
        }

        requestAnimationFrame(() => node.setDirtyCanvas?.(true, true));
    } catch (err) {
        console.error("[Apex LoRA Browser] updateBrowserVisibility error:", err);
    }
}

// ── Folder loading ────────────────────────────────────────────────────────────

async function loadBrowserFolder(node, folderPath) {
    const s = node._loraState;
    const dom = node._loraDom;
    if (!s || !dom) return;

    try {
        s.currentFolder = folderPath;
        s.currentPage = 0;

        const res = await api.fetchApi("/apex/lora_list_folder", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ folder_path: folderPath })
        });

        if (!res.ok) {
            console.error("[Apex LoRA Browser] Failed to load folder");
            return;
        }

        const data = await res.json();
        s.loras = data.loras;

        updateBreadcrumb(node, folderPath, data.parent_folder);
        updateFolders(node, data.folders, data.parent_folder);
        updateLorasGrid(node);
        updatePagination(node);
    } catch (err) {
        console.error("[Apex LoRA Browser] loadBrowserFolder error:", err);
    }
}

// ── Breadcrumb ────────────────────────────────────────────────────────────────

function updateBreadcrumb(node, folderPath, parentFolder) {
    const breadcrumb = node._loraDom.header;
    breadcrumb.innerHTML = "";

    const homeBtn = document.createElement("span");
    homeBtn.textContent = "🏠";
    homeBtn.style.cssText = "cursor:pointer;color:#4a9eff;padding:2px 5px;";
    homeBtn.onclick = () => loadBrowserFolder(node, "");
    breadcrumb.appendChild(homeBtn);

    if (folderPath) {
        const parts = folderPath.split("/");
        let currentPath = "";
        for (let i = 0; i < parts.length; i++) {
            const sep = document.createElement("span");
            sep.textContent = " › ";
            sep.style.color = "#666";
            breadcrumb.appendChild(sep);

            currentPath += (i > 0 ? "/" : "") + parts[i];
            const btn = document.createElement("span");
            btn.textContent = parts[i];

            if (i === parts.length - 1) {
                btn.style.color = "#fff";
            } else {
                const btnPath = currentPath;
                btn.style.cssText = "cursor:pointer;color:#4a9eff;padding:2px 5px;";
                btn.onclick = () => loadBrowserFolder(node, btnPath);
            }
            breadcrumb.appendChild(btn);
        }
    }
}

// ── Folders ───────────────────────────────────────────────────────────────────

function updateFolders(node, folders, parentFolder) {
    const s = node._loraState;
    const foldersGrid = node._loraDom.foldersGrid;
    foldersGrid.innerHTML = "";

    if (parentFolder !== null) {
        foldersGrid.appendChild(createFolderButton(node, "⬆️ ..", parentFolder));
    }

    folders.forEach(folder => {
        const folderPath = s.currentFolder ? `${s.currentFolder}/${folder}` : folder;
        foldersGrid.appendChild(createFolderButton(node, `📁 ${folder}`, folderPath));
    });
}

function createFolderButton(node, label, path) {
    const btn = document.createElement("button");
    btn.textContent = label;
    btn.style.cssText = `
        padding: 6px 10px;
        background: #2a2a2a;
        border: 1px solid #444;
        border-radius: 4px;
        color: #fff;
        cursor: pointer;
        font-size: 11px;
    `;
    btn.onmouseover = () => { btn.style.background = "#3a3a3a"; btn.style.borderColor = "#4a9eff"; };
    btn.onmouseout  = () => { btn.style.background = "#2a2a2a"; btn.style.borderColor = "#444"; };
    btn.onclick = () => loadBrowserFolder(node, path);
    return btn;
}

// ── LoRA grid ─────────────────────────────────────────────────────────────────

function updateLorasGrid(node) {
    const s = node._loraState;
    const lorasGrid = node._loraDom.lorasGrid;
    lorasGrid.innerHTML = "";

    const start = s.currentPage * s.itemsPerPage;
    const pageItems = s.loras.slice(start, start + s.itemsPerPage);

    pageItems.forEach(lora => lorasGrid.appendChild(createLoraItem(node, lora)));
}

function createLoraItem(node, lora) {
    const s = node._loraState;
    const isSelected = s.selectedLora === lora.relative_path;

    const item = document.createElement("div");
    item.style.cssText = `
        display: flex;
        flex-direction: column;
        align-items: center;
        cursor: pointer;
        padding: 6px;
        border-radius: 4px;
        border: 2px solid ${isSelected ? "#4a9eff" : "transparent"};
        background: ${isSelected ? "#2a3a4a" : "transparent"};
        transition: all 0.2s;
    `;

    item.onmouseover = () => {
        if (s.selectedLora !== lora.relative_path) {
            item.style.borderColor = "#555";
            item.style.background = "#252525";
        }
    };
    item.onmouseout = () => {
        if (s.selectedLora !== lora.relative_path) {
            item.style.borderColor = "transparent";
            item.style.background = "transparent";
        }
    };

    // Thumbnail
    const thumbnail = document.createElement("div");
    thumbnail.style.cssText = `
        width: 80px; height: 80px;
        background: #0a0a0a;
        border: 1px solid #333;
        border-radius: 3px;
        display: flex;
        align-items: center;
        justify-content: center;
        overflow: hidden;
        margin-bottom: 4px;
    `;

    if (lora.has_preview) {
        const img = document.createElement("img");
        img.style.cssText = "max-width:100%;max-height:100%;object-fit:contain;";
        fetchLoraPreview(lora.relative_path)
            .then(path => { if (path) img.src = `/apex/lora_image?path=${encodeURIComponent(path)}`; })
            .catch(() => {});
        thumbnail.appendChild(img);
    } else {
        const ph = document.createElement("div");
        ph.textContent = "No Preview";
        ph.style.cssText = "color:#555;font-size:9px;text-align:center;";
        thumbnail.appendChild(ph);
    }

    // Label
    const label = document.createElement("div");
    label.textContent = lora.name;
    label.title = lora.name;
    label.style.cssText = `
        font-size: 10px;
        color: #ccc;
        text-align: center;
        word-break: break-word;
        max-width: 100%;
        overflow: hidden;
        text-overflow: ellipsis;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        line-height: 1.2;
    `;

    item.appendChild(thumbnail);
    item.appendChild(label);

    item.onclick = () => {
        try {
            const loraWidget = node.widgets?.find(w => w.name === "lora_name");
            if (loraWidget) {
                loraWidget.value = lora.relative_path;
                s.selectedLora = lora.relative_path;
            }

            if (lora.has_preview) {
                s.selectedLoraPreview = "loading";
                fetchLoraPreview(lora.relative_path)
                    .then(path => {
                        s.selectedLoraPreview = path;
                        if (path && node._loraDom?.previewImg) {
                            node._loraDom.previewImg.src = `/apex/lora_image?path=${encodeURIComponent(path)}`;
                        }
                    })
                    .catch(() => { s.selectedLoraPreview = null; });
            } else {
                s.selectedLoraPreview = null;
            }

            // Collapse browser with slight delay to prevent UI freeze
            setTimeout(() => {
                try {
                    s.browserExpanded = false;
                    updateBrowserVisibility(node);
                } catch (err) {
                    console.error("[Apex LoRA Browser] Error collapsing:", err);
                }
            }, 50);
        } catch (err) {
            console.error("[Apex LoRA Browser] Item click error:", err);
        }
    };

    return item;
}

// ── Pagination ────────────────────────────────────────────────────────────────

function updatePagination(node) {
    const s = node._loraState;
    const pagination = node._loraDom.pagination;
    pagination.innerHTML = "";

    const totalPages = Math.ceil(s.loras.length / s.itemsPerPage);
    if (totalPages <= 1) return;

    const paginationBtn = (text, disabled, onClick) => {
        const btn = document.createElement("button");
        btn.textContent = text;
        btn.disabled = disabled;
        btn.style.cssText = `
            padding: 4px 8px;
            background: ${disabled ? "#1a1a1a" : "#2a2a2a"};
            border: 1px solid #444;
            border-radius: 3px;
            color: ${disabled ? "#555" : "#fff"};
            cursor: ${disabled ? "not-allowed" : "pointer"};
            font-size: 11px;
        `;
        if (!disabled) btn.onclick = onClick;
        return btn;
    };

    pagination.appendChild(paginationBtn("◀", s.currentPage === 0, () => {
        s.currentPage--;
        updateLorasGrid(node);
        updatePagination(node);
    }));

    const pageInfo = document.createElement("span");
    pageInfo.textContent = `${s.currentPage + 1}/${totalPages}`;
    pageInfo.style.cssText = "color:#aaa;font-size:11px;padding:0 8px;";
    pagination.appendChild(pageInfo);

    pagination.appendChild(paginationBtn("▶", s.currentPage >= totalPages - 1, () => {
        s.currentPage++;
        updateLorasGrid(node);
        updatePagination(node);
    }));
}

// ── LoRA changed (dropdown / arrow key / programmatic) ────────────────────────

function onLoraChanged(node, loraName) {
    try {
        const s = node._loraState;
        const dom = node._loraDom;
        if (!s || !loraName) return;

        s.selectedLoraPreview = "loading";

        fetchLoraPreview(loraName)
            .then(path => {
                s.selectedLoraPreview = path;
                if (path && dom?.previewImg) {
                    dom.previewImg.src = `/apex/lora_image?path=${encodeURIComponent(path)}`;
                }
                if (!s.browserExpanded) {
                    updateBrowserVisibility(node);
                }
            })
            .catch(() => { s.selectedLoraPreview = null; });

        requestAnimationFrame(() => node.setDirtyCanvas?.(true, true));
    } catch (err) {
        console.error("[Apex LoRA Browser] onLoraChanged error:", err);
    }
}

// ── Extension registration ────────────────────────────────────────────────────

app.registerExtension({
    name: "ApexArtist.LoraLoader",

    nodeCreated(node) {
        if (node.comfyClass !== "ApexLoraLoader") return;
        setupLoraLoaderNode(node);
    },

    loadedGraphNode(node) {
        if (node.type !== "ApexLoraLoader") return;
        // DOM is already built by nodeCreated — just sync visibility with restored widget values
        const s = node._loraState;
        if (!s) return;
        const loraWidget = node.widgets?.find(w => w.name === "lora_name");
        if (loraWidget?.value) {
            s.selectedLora = loraWidget.value;
        }
        updateBrowserVisibility(node);
    }
});