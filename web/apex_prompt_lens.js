/**
 * Apex Camera Lens Browser Web Extension
 * Interactive lens browser embedded inside the Apex Prompt node
 */

import { app } from "../../../scripts/app.js";
import { api } from "../../../scripts/api.js";

// Register the extension
app.registerExtension({
    name: "ApexArtist.LensBrowser",
    
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "ApexPromptPreset") {
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            
            nodeType.prototype.onNodeCreated = function() {
                const result = onNodeCreated?.apply(this, arguments);
                
                // Set minimum node width to prevent horizontal resizing
                const minWidth = 450;
                this.size[0] = Math.max(this.size[0], minWidth);
                
                // Store original computeSize to ensure minimum width is maintained
                const originalComputeSize = this.computeSize;
                this.computeSize = function(out) {
                    const size = originalComputeSize ? originalComputeSize.call(this, out) : [this.size[0], this.size[1]];
                    size[0] = Math.max(size[0], minWidth);
                    return size;
                };
                
                // Find the camera_lens_preset widget
                const lensWidget = this.widgets?.find(w => w.name === "camera_lens_preset");
                
                if (lensWidget) {
                    // Store current state
                    this.selectedLens = lensWidget.value || "Disabled";
                    this.selectedLensPreview = null;
                    this.browserExpanded = false;  // Start collapsed
                    this.lensesData = [];  // Store loaded lenses
                    
                    // Add toggle button widget BEFORE setting up the value property hook
                    const toggleWidget = this.addWidget("button", "toggle_lens_browser", "📷 Show Lens Browser", () => {
                        this.browserExpanded = !this.browserExpanded;
                        this.updateBrowserVisibility();
                    });
                    toggleWidget.serialize = false;
                    
                    // Store reference to toggle widget
                    this.lensBrowserToggle = toggleWidget;
                    
                    // Hook into value property to detect changes
                    const nodeRef = this;
                    const internalValueKey = '_apexLensValue';
                    lensWidget[internalValueKey] = lensWidget.value || "Disabled";
                    
                    Object.defineProperty(lensWidget, 'value', {
                        get: function() {
                            return this[internalValueKey];
                        },
                        set: function(newValue) {
                            const oldValue = this[internalValueKey];
                            this[internalValueKey] = newValue;
                            
                            // Update toggle button visibility based on selection
                            nodeRef.updateToggleButtonVisibility(newValue);
                            
                            // Trigger preview update if value changed
                            if (oldValue !== newValue && newValue && newValue !== "Disabled" && newValue !== "Random") {
                                nodeRef.selectedLens = newValue;
                                nodeRef.onLensChanged(newValue);
                            } else if (newValue === "Disabled" || newValue === "Random") {
                                // Clear preview and collapse browser when disabled/random
                                nodeRef.selectedLens = newValue;
                                nodeRef.selectedLensPreview = null;
                                nodeRef.browserExpanded = false;
                                nodeRef.updateBrowserVisibility();
                            }
                        },
                        enumerable: true,
                        configurable: true
                    });
                    
                    // Keep the original dropdown callback
                    const originalCallback = lensWidget.callback;
                    lensWidget.callback = (value) => {
                        if (originalCallback) {
                            originalCallback.call(lensWidget, value);
                        }
                    };
                    
                    // Create the browser widget
                    this.createLensBrowserWidget();
                    
                    // Load lenses data
                    this.loadLensesData();
                    
                    // Set initial toggle button visibility based on current lens value
                    // Use setTimeout to ensure the widget is fully initialized
                    setTimeout(() => {
                        this.updateToggleButtonVisibility(lensWidget.value || "Disabled");
                    }, 0);
                }
                
                return result;
            };
            
            // Create lens browser widget
            nodeType.prototype.createLensBrowserWidget = function() {
                // Create DOM container
                const container = document.createElement("div");
                container.className = "apex-lens-browser-inline";
                container.style.cssText = `
                    width: 100%;
                    max-height: 500px;
                    overflow: hidden;
                    background: #1a1a1a;
                    border: 1px solid #444;
                    border-radius: 5px;
                    display: none;
                    flex-direction: column;
                `;
                
                // Header
                const header = document.createElement("div");
                header.className = "apex-lens-header";
                header.style.cssText = `
                    padding: 8px 10px;
                    background: #252525;
                    border-bottom: 1px solid #444;
                    color: #fff;
                    font-size: 13px;
                    font-weight: bold;
                    flex-shrink: 0;
                `;
                header.textContent = "📷 Camera Lens Browser";
                
                // Content area (scrollable)
                const content = document.createElement("div");
                content.className = "apex-lens-content";
                content.style.cssText = `
                    flex: 1;
                    overflow-y: auto;
                    overflow-x: hidden;
                    padding: 10px;
                    max-height: 450px;
                `;
                
                // Lenses grid with fixed width to prevent node resizing
                const lensesGrid = document.createElement("div");
                lensesGrid.className = "apex-lens-grid";
                lensesGrid.style.cssText = `
                    display: grid;
                    grid-template-columns: repeat(4, 1fr);
                    gap: 10px;
                    width: 100%;
                    min-width: 400px;
                `;
                
                content.appendChild(lensesGrid);
                
                // Assemble container
                container.appendChild(header);
                container.appendChild(content);
                
                // Store references
                this.browserContainer = container;
                this.browserElements = {
                    header,
                    lensesGrid,
                    content
                };
                
                // Create preview display container (shown when browser is collapsed)
                const previewContainer = document.createElement("div");
                previewContainer.className = "apex-lens-preview";
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
                
                // Add DOM widgets
                this.addDOMWidget("lens_browser", "div", container, {
                    getValue: () => this.selectedLens,
                    setValue: (v) => { this.selectedLens = v; },
                    hideOnZoom: false,
                    getHeight: () => this.browserExpanded ? 500 : 0,
                    getMinHeight: () => this.browserExpanded ? 400 : 0,
                    getMaxHeight: () => this.browserExpanded ? 600 : 0
                });
                
                this.addDOMWidget("lens_preview", "div", previewContainer, {
                    getValue: () => this.selectedLensPreview,
                    setValue: (v) => { this.selectedLensPreview = v; },
                    hideOnZoom: false,
                    getHeight: () => (!this.browserExpanded && this.selectedLensPreview) ? 250 : 0,
                    getMinHeight: () => (!this.browserExpanded && this.selectedLensPreview) ? 200 : 0,
                    getMaxHeight: () => (!this.browserExpanded && this.selectedLensPreview) ? 300 : 0
                });
            };
            
            // Update toggle button visibility based on selection
            nodeType.prototype.updateToggleButtonVisibility = function(lensValue) {
                try {
                    const toggleWidget = this.lensBrowserToggle;
                    if (!toggleWidget) return;
                    
                    // Hide toggle button when "Disabled" or "Random" is selected
                    if (lensValue === "Disabled" || lensValue === "Random") {
                        toggleWidget.type = "converted-widget";  // Hide the widget
                        toggleWidget.computeSize = () => [0, 0];  // Make it take no space
                    } else {
                        toggleWidget.type = "button";  // Show the widget
                        toggleWidget.computeSize = undefined;  // Use default size
                    }
                    
                    // Force node to recompute size
                    this.setSize(this.computeSize());
                    
                } catch (err) {
                    console.error("[Apex Lens Browser] Error in updateToggleButtonVisibility:", err);
                }
            };
            
            // Update browser visibility
            nodeType.prototype.updateBrowserVisibility = function() {
                try {
                    if (!this.browserContainer || !this.previewContainer) {
                        return;
                    }
                    
                    // Update toggle button label
                    const toggleWidget = this.widgets?.find(w => w.name === "toggle_lens_browser");
                    if (toggleWidget) {
                        toggleWidget.label = this.browserExpanded ? "📷 Hide Lens Browser" : "📷 Show Lens Browser";
                    }
                    
                    if (this.browserExpanded) {
                        // Show browser, hide preview
                        this.browserContainer.style.display = "flex";
                        this.previewContainer.style.display = "none";
                        this.size[1] = Math.max(this.size[1], 620);
                    } else {
                        // Hide browser, show preview if we have one
                        this.browserContainer.style.display = "none";
                        if (this.selectedLensPreview && this.selectedLensPreview !== "loading") {
                            this.previewContainer.style.display = "flex";
                            this.size[1] = Math.max(this.computeSize()[1], 350);
                        } else {
                            this.previewContainer.style.display = "none";
                            this.size[1] = this.computeSize()[1];
                        }
                    }
                    
                    // Force canvas update
                    requestAnimationFrame(() => {
                        if (this.setDirtyCanvas) {
                            this.setDirtyCanvas(true, true);
                        }
                    });
                } catch (err) {
                    console.error("[Apex Lens Browser] Error in updateBrowserVisibility:", err);
                }
            };
            
            // Load lenses data from API
            nodeType.prototype.loadLensesData = async function() {
                try {
                    const response = await api.fetchApi("/apex/lens_list", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({})
                    });
                    
                    if (!response.ok) {
                        console.error("[Apex Lens Browser] Failed to load lenses");
                        return;
                    }
                    
                    const data = await response.json();
                    this.lensesData = data.lenses || [];
                    
                    // Update grid
                    this.updateLensesGrid();
                    
                } catch (error) {
                    console.error("[Apex Lens Browser] Error loading lenses:", error);
                }
            };
            
            // Update lenses grid
            nodeType.prototype.updateLensesGrid = function() {
                const lensesGrid = this.browserElements.lensesGrid;
                if (!lensesGrid) return;
                
                lensesGrid.innerHTML = "";
                
                this.lensesData.forEach(lens => {
                    const item = this.createLensItem(lens);
                    lensesGrid.appendChild(item);
                });
            };
            
            // Create lens item
            nodeType.prototype.createLensItem = function(lens) {
                const item = document.createElement("div");
                item.className = "apex-lens-item";
                item.style.cssText = `
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    cursor: pointer;
                    padding: 6px;
                    border-radius: 4px;
                    border: 2px solid ${this.selectedLens === lens.name ? '#4a9eff' : 'transparent'};
                    background: ${this.selectedLens === lens.name ? '#2a3a4a' : 'transparent'};
                    transition: all 0.2s;
                `;
                
                item.onmouseover = () => {
                    if (this.selectedLens !== lens.name) {
                        item.style.borderColor = "#555";
                        item.style.background = "#252525";
                    }
                };
                item.onmouseout = () => {
                    if (this.selectedLens !== lens.name) {
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
                    border-radius: 3px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    overflow: hidden;
                    margin-bottom: 4px;
                `;
                
                if (lens.has_preview) {
                    const img = document.createElement("img");
                    img.style.cssText = `
                        max-width: 100%;
                        max-height: 100%;
                        object-fit: contain;
                    `;
                    
                    api.fetchApi("/apex/lens_preview", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ lens_name: lens.name })
                    })
                    .then(res => res.json())
                    .then(data => {
                        if (data.preview_path) {
                            img.src = `/apex/lens_image?path=${encodeURIComponent(data.preview_path)}`;
                        }
                    })
                    .catch(err => console.log("[Apex Lens Browser] Preview load error:", err));
                    
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
                label.textContent = lens.name;
                label.title = lens.description || lens.name;
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
                
                // Click to select
                item.onclick = () => {
                    try {
                        // Update widget value
                        const lensWidget = this.widgets?.find(w => w.name === "camera_lens_preset");
                        if (lensWidget) {
                            lensWidget.value = lens.name;
                            this.selectedLens = lens.name;
                        }
                        
                        // Load preview
                        if (lens.has_preview) {
                            this.selectedLensPreview = "loading";
                            
                            api.fetchApi("/apex/lens_preview", {
                                method: "POST",
                                headers: { "Content-Type": "application/json" },
                                body: JSON.stringify({ lens_name: lens.name })
                            })
                            .then(res => res.json())
                            .then(data => {
                                if (data.preview_path) {
                                    this.selectedLensPreview = data.preview_path;
                                    if (this.previewImg) {
                                        this.previewImg.src = `/apex/lens_image?path=${encodeURIComponent(data.preview_path)}`;
                                    }
                                } else {
                                    this.selectedLensPreview = null;
                                }
                            })
                            .catch(err => {
                                console.log("[Apex Lens Browser] Preview load error:", err);
                                this.selectedLensPreview = null;
                            });
                        } else {
                            this.selectedLensPreview = null;
                        }
                        
                        // Collapse browser with width preservation
                        setTimeout(() => {
                            try {
                                // Store current width before collapsing
                                const currentWidth = this.size[0];
                                
                                this.browserExpanded = false;
                                this.updateBrowserVisibility();
                                
                                // Restore width after collapse to prevent horizontal squishing
                                this.size[0] = Math.max(currentWidth, 450);
                                
                                // Update grid to highlight selection
                                this.updateLensesGrid();
                                
                                // Force canvas update with preserved width
                                if (this.graph && this.graph.canvas) {
                                    this.graph.canvas.setDirty(true, true);
                                }
                            } catch (err) {
                                console.error("[Apex Lens Browser] Error collapsing browser:", err);
                            }
                        }, 50);
                        
                    } catch (err) {
                        console.error("[Apex Lens Browser] Error in item click handler:", err);
                    }
                };
                
                return item;
            };
            
            // Handle lens change from dropdown
            nodeType.prototype.onLensChanged = function(lensName) {
                try {
                    this.selectedLens = lensName;
                    
                    // Load preview if available
                    if (lensName && lensName !== "Disabled" && lensName !== "Random") {
                        this.selectedLensPreview = "loading";
                        
                        api.fetchApi("/apex/lens_preview", {
                            method: "POST",
                            headers: { "Content-Type": "application/json" },
                            body: JSON.stringify({ lens_name: lensName })
                        })
                        .then(res => res.json())
                        .then(data => {
                            if (data.preview_path) {
                                this.selectedLensPreview = data.preview_path;
                                if (this.previewImg) {
                                    this.previewImg.src = `/apex/lens_image?path=${encodeURIComponent(data.preview_path)}`;
                                }
                                // Update visibility to show preview if collapsed
                                if (!this.browserExpanded) {
                                    this.updateBrowserVisibility();
                                }
                            } else {
                                this.selectedLensPreview = null;
                            }
                        })
                        .catch(err => {
                            console.log("[Apex Lens Browser] Preview load error:", err);
                            this.selectedLensPreview = null;
                        });
                    } else {
                        this.selectedLensPreview = null;
                    }
                    
                    // Update canvas
                    requestAnimationFrame(() => {
                        if (this.setDirtyCanvas) {
                            this.setDirtyCanvas(true, true);
                        }
                    });
                } catch (err) {
                    console.error("[Apex Lens Browser] Error in onLensChanged:", err);
                }
            };
        }
    }
});
