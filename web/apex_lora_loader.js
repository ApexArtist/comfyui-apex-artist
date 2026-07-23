/**
 * Apex LoRA Loader Web Extension
 * Floating browser panel - native ComfyUI approach without DOM widgets
 *
 * Uses floating panel attached to document.body instead of addDOMWidget
 * This prevents canvas blocking issues entirely
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

function refreshNodePreview(node) {
    if (node.setDirtyCanvas) node.setDirtyCanvas(true, true);
    else node.graph?.setDirtyCanvas(true, true);
}

// ── Floating Panel Creation ──────────────────────────────────────────────────

function createFloatingBrowser(node) {
    const panel = document.createElement("div");
    panel.className = "apex-lora-browser-panel";
    panel.style.cssText = `
        position: fixed;
        width: 600px;
        max-height: 500px;
        background: #1a1a1a;
        border: 2px solid #4a9eff;
        border-radius: 8px;
        box-shadow: 0 8px 32px rgba(0,0,0,0.8);
        z-index: 10000;
        display: flex;
        flex-direction: column;
        overflow: hidden;
    `;

    // Header with breadcrumb and close button
    const header = document.createElement("div");
    header.style.cssText = `
        padding: 10px 12px;
        background: #252525;
        border-bottom: 1px solid #444;
        color: #aaa;
        font-size: 12px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        cursor: move;
        user-select: none;
    `;

    const breadcrumb = document.createElement("div");
    breadcrumb.style.cssText = "flex: 1; display: flex; align-items: center; gap: 5px;";
    
    const closeBtn = document.createElement("button");
    closeBtn.textContent = "✕";
    closeBtn.style.cssText = `
        background: #c44;
        border: none;
        border-radius: 3px;
        color: #fff;
        cursor: pointer;
        padding: 4px 8px;
        font-size: 14px;
        line-height: 1;
    `;
    closeBtn.onclick = () => closeBrowser(node);
    
    header.appendChild(breadcrumb);
    header.appendChild(closeBtn);

    // Content area
    const content = document.createElement("div");
    content.style.cssText = `
        flex: 1;
        overflow-y: auto;
        overflow-x: hidden;
        padding: 12px;
        max-height: 440px;
    `;

    const foldersSection = document.createElement("div");
    foldersSection.style.marginBottom = "12px";

    const foldersTitle = document.createElement("h4");
    foldersTitle.textContent = "Folders:";
    foldersTitle.style.cssText = "color:#fff;margin:0 0 8px 0;font-size:13px;";

    const foldersGrid = document.createElement("div");
    foldersGrid.style.cssText = "display:flex;flex-wrap:wrap;gap:8px;";

    foldersSection.appendChild(foldersTitle);
    foldersSection.appendChild(foldersGrid);

    const lorasSection = document.createElement("div");

    const lorasTitle = document.createElement("h4");
    lorasTitle.textContent = "LoRAs:";
    lorasTitle.style.cssText = "color:#fff;margin:0 0 8px 0;font-size:13px;";

    const lorasGrid = document.createElement("div");
    lorasGrid.style.cssText = `
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(90px, 1fr));
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
    `;

    content.appendChild(foldersSection);
    content.appendChild(lorasSection);
    content.appendChild(pagination);

    panel.appendChild(header);
    panel.appendChild(content);

    // Store references
    panel._breadcrumb = breadcrumb;
    panel._foldersGrid = foldersGrid;
    panel._lorasGrid = lorasGrid;
    panel._pagination = pagination;

    // Make draggable
    makeDraggable(panel, header);

    // Close on ESC
    const escHandler = (e) => {
        if (e.key === "Escape") closeBrowser(node);
    };
    document.addEventListener("keydown", escHandler);
    panel._escHandler = escHandler;

    return panel;
}

function makeDraggable(element, handle) {
    let pos1 = 0, pos2 = 0, pos3 = 0, pos4 = 0;
    
    handle.onmousedown = dragMouseDown;

    function dragMouseDown(e) {
        e.preventDefault();
        pos3 = e.clientX;
        pos4 = e.clientY;
        document.onmouseup = closeDragElement;
        document.onmousemove = elementDrag;
    }

    function elementDrag(e) {
        e.preventDefault();
        pos1 = pos3 - e.clientX;
        pos2 = pos4 - e.clientY;
        pos3 = e.clientX;
        pos4 = e.clientY;
        element.style.top = (element.offsetTop - pos2) + "px";
        element.style.left = (element.offsetLeft - pos1) + "px";
    }

    function closeDragElement() {
        document.onmouseup = null;
        document.onmousemove = null;
    }
}

// ── Panel Management ──────────────────────────────────────────────────────────

function openBrowser(node) {
    const s = node._loraState;
    if (s.browserOpen || s._floatingPanel) return;

    s.browserOpen = true;
    
    // Create floating panel
    const panel = createFloatingBrowser(node);
    s._floatingPanel = panel;
    document.body.appendChild(panel);

    // Position near node
    positionPanelNearNode(node, panel);

    // Load content
    loadBrowserFolder(node, s.currentFolder || "");

    // Update button label
    const toggleBtn = node.widgets?.find(w => w.name === "toggle_browser");
    if (toggleBtn) toggleBtn.label = "📁 Hide Browser";
}

function closeBrowser(node) {
    const s = node._loraState;
    if (!s.browserOpen) return;

    s.browserOpen = false;

    // Remove panel
    if (s._floatingPanel) {
        if (s._floatingPanel._escHandler) {
            document.removeEventListener("keydown", s._floatingPanel._escHandler);
        }
        s._floatingPanel.remove();
        s._floatingPanel = null;
    }

    // Update button label
    const toggleBtn = node.widgets?.find(w => w.name === "toggle_browser");
    if (toggleBtn) toggleBtn.label = "📁 Show Browser";
}

function positionPanelNearNode(node, panel) {
    // Get node position on canvas
    const canvasRect = app.canvas.canvas.getBoundingClientRect();
    const scale = app.canvas.ds.scale;
    
    // Convert node position to screen coordinates
    const nodeX = (node.pos[0] * scale) + canvasRect.left + app.canvas.ds.offset[0] * scale;
    const nodeY = (node.pos[1] * scale) + canvasRect.top + app.canvas.ds.offset[1] * scale;
    const nodeWidth = node.size[0] * scale;
    
    // Position to the right of node, or centered if not enough space
    let left = nodeX + nodeWidth + 20;
    let top = nodeY;
    
    // Check if panel would go off-screen
    if (left + 600 > window.innerWidth) {
        left = Math.max(20, (window.innerWidth - 600) / 2);
    }
    if (top + 500 > window.innerHeight) {
        top = Math.max(20, (window.innerHeight - 500) / 2);
    }
    
    panel.style.left = left + "px";
    panel.style.top = top + "px";
}

// ── Node Setup ────────────────────────────────────────────────────────────────

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
        browserOpen: false,
        loras: [],
        _floatingPanel: null,
    };

    const s = node._loraState;

    // Intercept widget value changes
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
                if (s.browserOpen) {
                    closeBrowser(node);
                }
            }
        },
        enumerable: true,
        configurable: true,
    });

    // Toggle button
    const toggleBtn = node.addWidget("button", "toggle_browser", "📁 Show Browser", () => {
        if (s.browserOpen) {
            closeBrowser(node);
        } else {
            openBrowser(node);
        }
    });
    toggleBtn.serialize = false;

    // Store original onRemoved to cleanup
    const origOnRemoved = node.onRemoved;
    node.onRemoved = function() {
        closeBrowser(node);
        if (origOnRemoved) origOnRemoved.apply(this, arguments);
    };

    if (loraWidget.value) {
        onLoraChanged(node, loraWidget.value);
    }
}

// ── Folder Loading ────────────────────────────────────────────────────────────

async function loadBrowserFolder(node, folderPath) {
    const s = node._loraState;
    const panel = s._floatingPanel;
    if (!panel) return;

    try {
        s.currentFolder = folderPath;
        s.currentPage = 0;

        const res = await api.fetchApi("/apex/lora_list_folder", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ folder_path: folderPath })
        });

        if (!res.ok) {
            console.error("[Apex LoRA] Failed to load folder");
            return;
        }

        const data = await res.json();
        s.loras = data.loras;

        updateBreadcrumb(node, panel, folderPath, data.parent_folder);
        updateFolders(node, panel, data.folders, data.parent_folder);
        updateLorasGrid(node, panel);
        updatePagination(node, panel);
    } catch (err) {
        console.error("[Apex LoRA] loadBrowserFolder error:", err);
    }
}

// ── Breadcrumb ────────────────────────────────────────────────────────────────

function updateBreadcrumb(node, panel, folderPath, parentFolder) {
    const breadcrumb = panel._breadcrumb;
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

function updateFolders(node, panel, folders, parentFolder) {
    const s = node._loraState;
    const foldersGrid = panel._foldersGrid;
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
        padding: 6px 12px;
        background: #2a2a2a;
        border: 1px solid #444;
        border-radius: 4px;
        color: #fff;
        cursor: pointer;
        font-size: 11px;
        transition: all 0.15s;
    `;
    btn.onmouseover = () => { btn.style.background = "#3a3a3a"; btn.style.borderColor = "#4a9eff"; };
    btn.onmouseout  = () => { btn.style.background = "#2a2a2a"; btn.style.borderColor = "#444"; };
    btn.onclick = () => loadBrowserFolder(node, path);
    return btn;
}

// ── LoRA Grid ─────────────────────────────────────────────────────────────────

function updateLorasGrid(node, panel) {
    const s = node._loraState;
    const lorasGrid = panel._lorasGrid;
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
        padding: 8px;
        border-radius: 6px;
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
        width: 90px;
        height: 90px;
        background: #0a0a0a;
        border: 1px solid #333;
        border-radius: 4px;
        display: flex;
        align-items: center;
        justify-content: center;
        overflow: hidden;
        margin-bottom: 6px;
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
        ph.style.cssText = "color:#555;font-size:9px;text-align:center;padding:4px;";
        thumbnail.appendChild(ph);
    }

    // Label
    const label = document.createElement("div");
    label.textContent = lora.name;
    label.title = lora.name;
    label.style.cssText = `
        font-size: 11px;
        color: #ddd;
        text-align: center;
        word-break: break-word;
        max-width: 100%;
        overflow: hidden;
        text-overflow: ellipsis;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        line-height: 1.3;
    `;

    item.appendChild(thumbnail);
    item.appendChild(label);

    item.onclick = () => {
        const loraWidget = node.widgets?.find(w => w.name === "lora_name");
        if (loraWidget) {
            loraWidget.value = lora.relative_path;
            s.selectedLora = lora.relative_path;
        }
        closeBrowser(node);
    };

    return item;
}

// ── Pagination ────────────────────────────────────────────────────────────────

function updatePagination(node, panel) {
    const s = node._loraState;
    const pagination = panel._pagination;
    pagination.innerHTML = "";

    const totalPages = Math.ceil(s.loras.length / s.itemsPerPage);
    if (totalPages <= 1) return;

    const paginationBtn = (text, disabled, onClick) => {
        const btn = document.createElement("button");
        btn.textContent = text;
        btn.disabled = disabled;
        btn.style.cssText = `
            padding: 5px 10px;
            background: ${disabled ? "#1a1a1a" : "#2a2a2a"};
            border: 1px solid #444;
            border-radius: 4px;
            color: ${disabled ? "#555" : "#fff"};
            cursor: ${disabled ? "not-allowed" : "pointer"};
            font-size: 11px;
        `;
        if (!disabled) btn.onclick = onClick;
        return btn;
    };

    pagination.appendChild(paginationBtn("◀", s.currentPage === 0, () => {
        s.currentPage--;
        updateLorasGrid(node, panel);
        updatePagination(node, panel);
    }));

    const pageInfo = document.createElement("span");
    pageInfo.textContent = `${s.currentPage + 1}/${totalPages}`;
    pageInfo.style.cssText = "color:#bbb;font-size:12px;padding:0 10px;";
    pagination.appendChild(pageInfo);

    pagination.appendChild(paginationBtn("▶", s.currentPage >= totalPages - 1, () => {
        s.currentPage++;
        updateLorasGrid(node, panel);
        updatePagination(node, panel);
    }));
}

// ── LoRA Changed ──────────────────────────────────────────────────────────────

function onLoraChanged(node, loraName) {
    const s = node._loraState;
    if (!s || !loraName) return;
    
    s.selectedLora = loraName;
    s.selectedLoraPreview = "loading";
    node.imgs = [];
    
    // Fetch and display preview
    fetchLoraPreview(loraName)
        .then(path => {
            if (!path) {
                s.selectedLoraPreview = null;
                s._previewImage = null;
                node.imgs = [];
                refreshNodePreview(node);
                return;
            }
            
            s.selectedLoraPreview = path;
            
            // Load image
            const img = new Image();
            img.onload = () => {
                s._previewImage = img;
                node.imgs = [img];
                node.imageIndex = 0;
                refreshNodePreview(node);
            };
            img.onerror = () => {
                s.selectedLoraPreview = null;
                s._previewImage = null;
                node.imgs = [];
                refreshNodePreview(node);
            };
            img.src = `/apex/lora_image?path=${encodeURIComponent(path)}`;
        })
        .catch(() => {
            s.selectedLoraPreview = null;
            s._previewImage = null;
            node.imgs = [];
            refreshNodePreview(node);
        });
}

// ── Extension Registration ────────────────────────────────────────────────────

app.registerExtension({
    name: "ApexArtist.LoraLoader",

    nodeCreated(node) {
        if (node.comfyClass !== "ApexLoraLoader") return;
        setupLoraLoaderNode(node);
    },

    loadedGraphNode(node) {
        if (node.type !== "ApexLoraLoader") return;
        const s = node._loraState;
        if (!s) return;
        const loraWidget = node.widgets?.find(w => w.name === "lora_name");
        if (loraWidget?.value) {
            s.selectedLora = loraWidget.value;
            onLoraChanged(node, loraWidget.value);
        }
    }
});
