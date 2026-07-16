/**
 * Apex LoRA Loader Web Extension
 * Interactive folder browser embedded inside the node
 */

import { app } from "../../../scripts/app.js";
import { api } from "../../../scripts/api.js";

// Register the extension
app.registerExtension({
    name: "ApexArtist.LoraLoader",
    
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "ApexLoraLoader") {
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            
            nodeType.prototype.onNodeCreated = function() {
                const result = onNodeCreated?.apply(this, arguments);
                
                // Find the lora_name widget
                const loraWidget = this.widgets?.find(w => w.name === "lora_name");
                
                if (loraWidget) {
                    // Store current folder and selected lora
                    this.currentFolder = "";  // Start at LoRAs home (root)
                    this.selectedLora = loraWidget.value || "";
                    this.selectedLoraPreview = null;  // Store preview path
                    this.currentPage = 0;
                    this.itemsPerPage = 50;
                    this.browserExpanded = true;  // Start with browser open
                    
                    // Hook into value property to detect ALL changes (arrow keys, dropdown, workflow load)
                    const nodeRef = this;
                    const internalValueKey = '_apexLoraValue';
                    loraWidget[internalValueKey] = loraWidget.value || "";
                    
                    Object.defineProperty(loraWidget, 'value', {
                        get: function() {
                            return this[internalValueKey];
                        },
                        set: function(newValue) {
                            const oldValue = this[internalValueKey];
                            this[internalValueKey] = newValue;
                            
                            // Trigger preview update if value actually changed
                            if (oldValue !== newValue && newValue) {
                                nodeRef.selectedLora = newValue;
                                nodeRef.onLoraChanged(newValue);
                                
                                // Auto-collapse browser to show thumbnail preview
                                if (nodeRef.browserExpanded) {
                                    setTimeout(() => {
                                        nodeRef.browserExpanded = false;
                                        nodeRef.updateBrowserVisibility();
                                    }, 100);
                                }
                            }
                        },
                        enumerable: true,
                        configurable: true
                    });
                    
                    // Keep the original dropdown callback for backwards compatibility
                    const originalCallback = loraWidget.callback;
                    loraWidget.callback = (value) => {
                        // The property setter will handle the update
                        // Just call original callback if it exists
                        if (originalCallback) {
                            originalCallback.call(loraWidget, value);
                        }
                    };
                    
                    // Add toggle button widget BEFORE browser (so it appears at top)
                    const toggleWidget = this.addWidget("button", "toggle_browser", "📁 Hide Browser", () => {
                        this.browserExpanded = !this.browserExpanded;
                        this.updateBrowserVisibility();
                    });
                    toggleWidget.serialize = false;  // Don't save this widget
                    
                    // Create the browser widget (DOM element) AFTER toggle button
                    this.createBrowserWidget();
                }
                
                return result;
            };
            
            // Add browser widget creation
            nodeType.prototype.createBrowserWidget = function() {
                // Create DOM container
                const container = document.createElement("div");
                container.className = "apex-lora-browser-inline";
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
                
                // Header with breadcrumb
                const header = document.createElement("div");
                header.className = "apex-lora-breadcrumb";
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
                
                // Content area (scrollable)
                const content = document.createElement("div");
                content.className = "apex-lora-content";
                content.style.cssText = `
                    flex: 1;
                    overflow-y: auto;
                    overflow-x: hidden;
                    padding: 10px;
                    max-height: 400px;
                `;
                
                // Folders section
                const foldersSection = document.createElement("div");
                foldersSection.className = "apex-lora-folders";
                foldersSection.style.cssText = `
                    margin-bottom: 10px;
                `;
                
                const foldersTitle = document.createElement("h4");
                foldersTitle.textContent = "Folders:";
                foldersTitle.style.cssText = `
                    color: #fff;
                    margin: 0 0 8px 0;
                    font-size: 12px;
                `;
                
                const foldersGrid = document.createElement("div");
                foldersGrid.className = "apex-lora-folders-grid";
                foldersGrid.style.cssText = `
                    display: flex;
                    flex-wrap: wrap;
                    gap: 8px;
                `;
                
                foldersSection.appendChild(foldersTitle);
                foldersSection.appendChild(foldersGrid);
                
                // LoRAs section
                const lorasSection = document.createElement("div");
                lorasSection.className = "apex-lora-loras";
                
                const lorasTitle = document.createElement("h4");
                lorasTitle.textContent = "LoRAs:";
                lorasTitle.style.cssText = `
                    color: #fff;
                    margin: 0 0 8px 0;
                    font-size: 12px;
                `;
                
                const lorasGrid = document.createElement("div");
                lorasGrid.className = "apex-lora-loras-grid";
                lorasGrid.style.cssText = `
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(80px, 1fr));
                    gap: 10px;
                    margin-bottom: 10px;
                `;
                
                lorasSection.appendChild(lorasTitle);
                lorasSection.appendChild(lorasGrid);
                
                // Pagination
                const pagination = document.createElement("div");
                pagination.className = "apex-lora-pagination";
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
                
                // Assemble container
                container.appendChild(header);
                container.appendChild(content);
                
                // Store references
                this.browserContainer = container;
                this.browserElements = {
                    header,
                    foldersGrid,
                    lorasGrid,
                    pagination,
                    content
                };
                
                // Create preview display container (shown when browser is collapsed)
                const previewContainer = document.createElement("div");
                previewContainer.className = "apex-lora-preview";
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
                
                // Store preview references
                this.previewContainer = previewContainer;
                this.previewImg = previewImg;
                
                // Add DOM widgets using ComfyUI's API
                this.addDOMWidget("lora_browser", "div", container, {
                    getValue: () => this.selectedLora,
                    setValue: (v) => { this.selectedLora = v; },
                    hideOnZoom: false,
                    getHeight: () => this.browserExpanded ? 500 : 0,
                    getMinHeight: () => this.browserExpanded ? 400 : 0,
                    getMaxHeight: () => this.browserExpanded ? 600 : 0
                });
                
                this.addDOMWidget("lora_preview", "div", previewContainer, {
                    getValue: () => this.selectedLoraPreview,
                    setValue: (v) => { this.selectedLoraPreview = v; },
                    hideOnZoom: false,
                    getHeight: () => (!this.browserExpanded && this.selectedLoraPreview) ? 250 : 0,
                    getMinHeight: () => (!this.browserExpanded && this.selectedLoraPreview) ? 200 : 0,
                    getMaxHeight: () => (!this.browserExpanded && this.selectedLoraPreview) ? 400 : 0
                });
                
                // Load initial content and show browser
                this.loadBrowserFolder(this.currentFolder);
                this.updateBrowserVisibility();
            };
            
            // Update browser visibility
            nodeType.prototype.updateBrowserVisibility = function() {
                try {
                    if (!this.browserContainer || !this.previewContainer) {
                        return;
                    }
                    
                    // Update toggle button label - simple show/hide only
                    const toggleWidget = this.widgets?.find(w => w.name === "toggle_browser");
                    if (toggleWidget) {
                        toggleWidget.label = this.browserExpanded ? "📁 Hide Browser" : "📁 Show Browser";
                    }
                    
                    if (this.browserExpanded) {
                        // Show browser, hide preview
                        this.browserContainer.style.display = "flex";
                        this.previewContainer.style.display = "none";
                        this.size[1] = Math.max(this.size[1], 620); // Expand node height
                    } else {
                        // Hide browser, show preview if we have one
                        this.browserContainer.style.display = "none";
                        if (this.selectedLoraPreview && this.selectedLoraPreview !== "loading") {
                            this.previewContainer.style.display = "flex";
                            this.size[1] = Math.max(this.computeSize()[1], 350);
                        } else {
                            this.previewContainer.style.display = "none";
                            this.size[1] = this.computeSize()[1]; // Shrink to default
                        }
                    }
                    
                    // Force canvas update with slight delay to prevent race conditions
                    requestAnimationFrame(() => {
                        if (this.setDirtyCanvas) {
                            this.setDirtyCanvas(true, true);
                        }
                    });
                } catch (err) {
                    console.error("[Apex LoRA Browser] Error in updateBrowserVisibility:", err);
                }
            };
            
            // Load folder contents
            nodeType.prototype.loadBrowserFolder = async function(folderPath) {
                if (!this.browserElements) return;
                
                try {
                    this.currentFolder = folderPath;
                    this.currentPage = 0;
                    
                    const response = await api.fetchApi("/apex/lora_list_folder", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ folder_path: folderPath })
                    });
                    
                    if (!response.ok) {
                        console.error("[Apex LoRA Browser] Failed to load folder");
                        return;
                    }
                    
                    const data = await response.json();
                    
                    // Update UI
                    this.updateBreadcrumb(folderPath, data.parent_folder);
                    this.updateFolders(data.folders, data.parent_folder);
                    this.updateLorasGrid(data.loras);
                    this.updatePagination(data.loras.length, data.loras);
                    
                } catch (error) {
                    console.error("[Apex LoRA Browser] Error loading folder:", error);
                }
            };
            
            // Update breadcrumb
            nodeType.prototype.updateBreadcrumb = function(folderPath, parentFolder) {
                const breadcrumb = this.browserElements.header;
                breadcrumb.innerHTML = "";
                
                const homeBtn = document.createElement("span");
                homeBtn.textContent = "🏠";
                homeBtn.style.cssText = `
                    cursor: pointer;
                    color: #4a9eff;
                    padding: 2px 5px;
                `;
                homeBtn.onclick = () => this.loadBrowserFolder("");
                breadcrumb.appendChild(homeBtn);
                
                if (folderPath) {
                    const parts = folderPath.split('/');
                    let currentPath = "";
                    
                    for (let i = 0; i < parts.length; i++) {
                        const separator = document.createElement("span");
                        separator.textContent = " › ";
                        separator.style.color = "#666";
                        breadcrumb.appendChild(separator);
                        
                        currentPath += (i > 0 ? "/" : "") + parts[i];
                        const pathBtn = document.createElement("span");
                        pathBtn.textContent = parts[i];
                        
                        if (i === parts.length - 1) {
                            pathBtn.style.color = "#fff";
                        } else {
                            const btnPath = currentPath;
                            pathBtn.style.cssText = `
                                cursor: pointer;
                                color: #4a9eff;
                                padding: 2px 5px;
                            `;
                            pathBtn.onclick = () => this.loadBrowserFolder(btnPath);
                        }
                        
                        breadcrumb.appendChild(pathBtn);
                    }
                }
            };
            
            // Update folders
            nodeType.prototype.updateFolders = function(folders, parentFolder) {
                const foldersGrid = this.browserElements.foldersGrid;
                foldersGrid.innerHTML = "";
                
                if (parentFolder !== null) {
                    const upBtn = this.createFolderButton("⬆️ ..", parentFolder);
                    foldersGrid.appendChild(upBtn);
                }
                
                folders.forEach(folder => {
                    const currentPath = this.currentFolder;
                    const folderPath = currentPath ? `${currentPath}/${folder}` : folder;
                    const folderBtn = this.createFolderButton(`📁 ${folder}`, folderPath);
                    foldersGrid.appendChild(folderBtn);
                });
            };
            
            // Create folder button
            nodeType.prototype.createFolderButton = function(label, path) {
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
                    transition: all 0.2s;
                `;
                btn.onmouseover = () => {
                    btn.style.background = "#3a3a3a";
                    btn.style.borderColor = "#4a9eff";
                };
                btn.onmouseout = () => {
                    btn.style.background = "#2a2a2a";
                    btn.style.borderColor = "#444";
                };
                btn.onclick = () => this.loadBrowserFolder(path);
                return btn;
            };
            
            // Update LoRAs grid
            nodeType.prototype.updateLorasGrid = function(loras) {
                const lorasGrid = this.browserElements.lorasGrid;
                lorasGrid.innerHTML = "";
                
                const startIdx = this.currentPage * this.itemsPerPage;
                const endIdx = Math.min(startIdx + this.itemsPerPage, loras.length);
                const pageItems = loras.slice(startIdx, endIdx);
                
                pageItems.forEach(lora => {
                    const item = this.createLoraItem(lora);
                    lorasGrid.appendChild(item);
                });
            };
            
            // Create LoRA item
            nodeType.prototype.createLoraItem = function(lora) {
                const item = document.createElement("div");
                item.className = "apex-lora-item";
                item.style.cssText = `
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    cursor: pointer;
                    padding: 6px;
                    border-radius: 4px;
                    border: 2px solid ${this.selectedLora === lora.relative_path ? '#4a9eff' : 'transparent'};
                    background: ${this.selectedLora === lora.relative_path ? '#2a3a4a' : 'transparent'};
                    transition: all 0.2s;
                `;
                
                item.onmouseover = () => {
                    if (this.selectedLora !== lora.relative_path) {
                        item.style.borderColor = "#555";
                        item.style.background = "#252525";
                    }
                };
                item.onmouseout = () => {
                    if (this.selectedLora !== lora.relative_path) {
                        item.style.borderColor = "transparent";
                        item.style.background = "transparent";
                    }
                };
                
                // Thumbnail
                const thumbnail = document.createElement("div");
                thumbnail.style.cssText = `
                    width: 80px;
                    height: 80px;
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
                    img.style.cssText = `
                        max-width: 100%;
                        max-height: 100%;
                        object-fit: contain;
                    `;
                    
                    api.fetchApi("/apex/lora_preview", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ lora_name: lora.relative_path })
                    })
                    .then(res => res.json())
                    .then(data => {
                        if (data.preview_path) {
                            // Request optimized thumbnail for grid view
                            img.src = `/apex/lora_image?path=${encodeURIComponent(data.preview_path)}`;
                        }
                    })
                    .catch(err => console.log("[Apex LoRA Browser] Preview load error:", err));
                    
                    thumbnail.appendChild(img);
                } else {
                    const placeholder = document.createElement("div");
                    placeholder.textContent = "No Preview";
                    placeholder.style.cssText = `
                        color: #555;
                        font-size: 9px;
                        text-align: center;
                    `;
                    thumbnail.appendChild(placeholder);
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
                
                // Click to select - Fixed to prevent freeze
                item.onclick = () => {
                    try {
                        // Update widget value first
                        const loraWidget = this.widgets?.find(w => w.name === "lora_name");
                        if (loraWidget) {
                            loraWidget.value = lora.relative_path;
                            this.selectedLora = lora.relative_path;
                        }
                        
                        // Load preview asynchronously without blocking
                        if (lora.has_preview) {
                            // Set preview to loading state
                            this.selectedLoraPreview = "loading";
                            
                            // Fetch preview in background
                            api.fetchApi("/apex/lora_preview", {
                                method: "POST",
                                headers: { "Content-Type": "application/json" },
                                body: JSON.stringify({ lora_name: lora.relative_path })
                            })
                            .then(res => res.json())
                            .then(data => {
                                if (data.preview_path) {
                                    this.selectedLoraPreview = data.preview_path;
                                    if (this.previewImg) {
                                        // Request optimized thumbnail for preview display
                                        this.previewImg.src = `/apex/lora_image?path=${encodeURIComponent(data.preview_path)}`;
                                    }
                                } else {
                                    this.selectedLoraPreview = null;
                                }
                            })
                            .catch(err => {
                                console.log("[Apex LoRA Browser] Preview load error:", err);
                                this.selectedLoraPreview = null;
                            });
                        } else {
                            this.selectedLoraPreview = null;
                        }
                        
                        // Collapse browser with setTimeout to prevent UI freeze
                        setTimeout(() => {
                            try {
                                this.browserExpanded = false;
                                this.updateBrowserVisibility();
                            } catch (err) {
                                console.error("[Apex LoRA Browser] Error collapsing browser:", err);
                            }
                        }, 50);
                        
                    } catch (err) {
                        console.error("[Apex LoRA Browser] Error in item click handler:", err);
                    }
                };
                
                return item;
            };
            
            // Update pagination
            nodeType.prototype.updatePagination = function(totalItems, loras) {
                const pagination = this.browserElements.pagination;
                pagination.innerHTML = "";
                
                const totalPages = Math.ceil(totalItems / this.itemsPerPage);
                
                if (totalPages <= 1) return;
                
                // Previous button
                const prevBtn = document.createElement("button");
                prevBtn.textContent = "◀";
                prevBtn.disabled = this.currentPage === 0;
                prevBtn.style.cssText = `
                    padding: 4px 8px;
                    background: ${this.currentPage === 0 ? '#1a1a1a' : '#2a2a2a'};
                    border: 1px solid #444;
                    border-radius: 3px;
                    color: ${this.currentPage === 0 ? '#555' : '#fff'};
                    cursor: ${this.currentPage === 0 ? 'not-allowed' : 'pointer'};
                    font-size: 11px;
                `;
                if (this.currentPage > 0) {
                    prevBtn.onclick = () => {
                        this.currentPage--;
                        this.updateLorasGrid(loras);
                        this.updatePagination(totalItems, loras);
                    };
                }
                pagination.appendChild(prevBtn);
                
                // Page info
                const pageInfo = document.createElement("span");
                pageInfo.textContent = `${this.currentPage + 1}/${totalPages}`;
                pageInfo.style.cssText = `
                    color: #aaa;
                    font-size: 11px;
                    padding: 0 8px;
                `;
                pagination.appendChild(pageInfo);
                
                // Next button
                const nextBtn = document.createElement("button");
                nextBtn.textContent = "▶";
                nextBtn.disabled = this.currentPage >= totalPages - 1;
                nextBtn.style.cssText = `
                    padding: 4px 8px;
                    background: ${this.currentPage >= totalPages - 1 ? '#1a1a1a' : '#2a2a2a'};
                    border: 1px solid #444;
                    border-radius: 3px;
                    color: ${this.currentPage >= totalPages - 1 ? '#555' : '#fff'};
                    cursor: ${this.currentPage >= totalPages - 1 ? 'not-allowed' : 'pointer'};
                    font-size: 11px;
                `;
                if (this.currentPage < totalPages - 1) {
                    nextBtn.onclick = () => {
                        this.currentPage++;
                        this.updateLorasGrid(loras);
                        this.updatePagination(totalItems, loras);
                    };
                }
                pagination.appendChild(nextBtn);
            };
            
            // Handle LoRA change from dropdown
            nodeType.prototype.onLoraChanged = function(loraName) {
                try {
                    // Update selected lora
                    this.selectedLora = loraName;
                    
                    // Load preview if available
                    if (loraName) {
                        this.selectedLoraPreview = "loading";
                        
                        api.fetchApi("/apex/lora_preview", {
                            method: "POST",
                            headers: { "Content-Type": "application/json" },
                            body: JSON.stringify({ lora_name: loraName })
                        })
                        .then(res => res.json())
                        .then(data => {
                            if (data.preview_path) {
                                this.selectedLoraPreview = data.preview_path;
                                if (this.previewImg) {
                                    // Request optimized thumbnail for preview display
                                    this.previewImg.src = `/apex/lora_image?path=${encodeURIComponent(data.preview_path)}`;
                                }
                                // Update visibility to show preview if collapsed
                                if (!this.browserExpanded) {
                                    this.updateBrowserVisibility();
                                }
                            } else {
                                this.selectedLoraPreview = null;
                            }
                        })
                        .catch(err => {
                            console.log("[Apex LoRA Browser] Preview load error:", err);
                            this.selectedLoraPreview = null;
                        });
                    } else {
                        this.selectedLoraPreview = null;
                    }
                    
                    // Update canvas
                    requestAnimationFrame(() => {
                        if (this.setDirtyCanvas) {
                            this.setDirtyCanvas(true, true);
                        }
                    });
                } catch (err) {
                    console.error("[Apex LoRA Browser] Error in onLoraChanged:", err);
                }
            };
        }
    }
});
