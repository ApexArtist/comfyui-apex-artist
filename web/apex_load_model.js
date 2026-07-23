/**
 * Apex Load Model Web Extension
 * Adds custom file browser for loading models from anywhere on the system
 * Features:
 * - Browse button to select model files from anywhere
 * - Custom path field visible below the browse controls
 * - Minimum horizontal collapse support
 */

import { app } from "../../../scripts/app.js";

app.registerExtension({
    name: "Apex.LoadModel",
    
    async nodeCreated(node) {
        if (node.comfyClass !== "ApexLoadModel") return;
        
        // Find the custom_path widget
        const customPathWidget = node.widgets?.find(w => w.name === "custom_path");
        if (!customPathWidget) return;
        
        // Store original widget for value updates
        node._apexCustomPathWidget = customPathWidget;
        
        // Create file browser button widget
        const browseButton = node.addWidget(
            "button",
            "browse_model",
            null,
            () => {
                // Create hidden file input
                const fileInput = document.createElement("input");
                fileInput.type = "file";
                fileInput.accept = ".safetensors,.ckpt,.pt,.pth,.bin";
                fileInput.style.display = "none";
                
                fileInput.onchange = (e) => {
                    const file = e.target.files?.[0];
                    if (file) {
                        // Get the full path (available in desktop environments)
                        const fullPath = file.path || file.name;
                        
                        // Update the custom_path widget value
                        customPathWidget.value = fullPath;
                        
                        // Update display label
                        if (node._apexPathLabel) {
                            const fileName = fullPath.split(/[\\/]/).pop();
                            node._apexPathLabel.value = `📁 ${fileName}`;
                        }
                        
                        // Trigger node update
                        if (node.onResize) {
                            node.onResize(node.size);
                        }
                    }
                    
                    // Clean up
                    document.body.removeChild(fileInput);
                };
                
                // Trigger file selection dialog
                document.body.appendChild(fileInput);
                fileInput.click();
            },
            {
                serialize: false // Don't save button state
            }
        );
        
        // Customize button appearance
        browseButton.label = "🗂️ Browse Model...";
        
        // Create clear button widget
        const clearButton = node.addWidget(
            "button",
            "clear_custom_path",
            null,
            () => {
                // Clear the custom_path widget
                customPathWidget.value = "";
                
                // Update display label
                if (node._apexPathLabel) {
                    node._apexPathLabel.value = "No custom file selected";
                }
                
                // Trigger node update
                if (node.onResize) {
                    node.onResize(node.size);
                }
            },
            {
                serialize: false
            }
        );
        
        clearButton.label = "❌ Clear";
        
        // Create display label to show selected file
        const pathLabel = node.addWidget(
            "text",
            "selected_file",
            "No custom file selected",
            () => {},
            {
                serialize: false
            }
        );
        
        // Store label reference
        node._apexPathLabel = pathLabel;
        
        // Make label read-only visually
        pathLabel.disabled = true;
        
        // Reorder widgets: browse button, clear button, path label at top
        // Then custom_path (visible, below the browse controls)
        const widgets = node.widgets;
        
        // Move browse button to position 0
        const browseIdx = widgets.indexOf(browseButton);
        if (browseIdx > 0) {
            widgets.splice(browseIdx, 1);
            widgets.splice(0, 0, browseButton);
        }
        
        // Move clear button to position 1
        const clearIdx = widgets.indexOf(clearButton);
        if (clearIdx > 1) {
            widgets.splice(clearIdx, 1);
            widgets.splice(1, 0, clearButton);
        }
        
        // Move path label to position 2
        const labelIdx = widgets.indexOf(pathLabel);
        if (labelIdx > 2) {
            widgets.splice(labelIdx, 1);
            widgets.splice(2, 0, pathLabel);
        }
        
        // Move custom_path to position 3 (below the browse controls, visible)
        const customPathIdx = widgets.indexOf(customPathWidget);
        if (customPathIdx > 3) {
            widgets.splice(customPathIdx, 1);
            widgets.splice(3, 0, customPathWidget);
        }
        
        // Restore custom_path to be visible (not hidden)
        customPathWidget.type = "STRING";
        if (customPathWidget.computeSize) {
            delete customPathWidget.computeSize;
        }
        
        // Initialize label if there's already a value
        if (customPathWidget.value && customPathWidget.value.trim()) {
            const fileName = customPathWidget.value.split(/[\\/]/).pop();
            pathLabel.value = `📁 ${fileName}`;
        }
        
        // Add visual separator after custom path section
        const separator = node.addWidget(
            "text",
            "separator",
            "────────────────────────",
            () => {},
            {
                serialize: false
            }
        );
        separator.disabled = true;
        
        // Move separator after custom_path (position 4)
        const sepIdx = widgets.indexOf(separator);
        if (sepIdx > 4) {
            widgets.splice(sepIdx, 1);
            widgets.splice(4, 0, separator);
        }
        
        // Monitor custom_path changes (for workflow loading)
        const originalCallback = customPathWidget.callback;
        customPathWidget.callback = function(value) {
            if (originalCallback) {
                originalCallback.call(this, value);
            }
            
            // Update label when value changes
            if (value && value.trim()) {
                const fileName = value.split(/[\\/]/).pop();
                if (node._apexPathLabel) {
                    node._apexPathLabel.value = `📁 ${fileName}`;
                }
            } else {
                if (node._apexPathLabel) {
                    node._apexPathLabel.value = "No custom file selected";
                }
            }
        };
        
        // Enforce minimum node width for proper collapse behavior
        // ComfyUI nodes collapse to a minimum width; we ensure it doesn't go too narrow
        const originalComputeSize = node.computeSize;
        node.computeSize = function(...args) {
            const size = originalComputeSize ? originalComputeSize.apply(this, args) : this.size;
            
            // Enforce minimum width of 300px for usability
            // When collapsed (flags includes 1 or node is small), still keep readable width
            const minWidth = 300;
            if (size[0] < minWidth) {
                size[0] = minWidth;
            }
            
            return size;
        };
        
        // Handle collapse state - ensure minimum width when collapsed
        const originalOnCollapse = node.onCollapse;
        node.onCollapse = function() {
            if (originalOnCollapse) {
                originalOnCollapse.apply(this, arguments);
            }
            // When collapsed, ensure minimum width
            if (this.size[0] < 300) {
                this.size[0] = 300;
                if (this.onResize) {
                    this.onResize(this.size);
                }
            }
        };
    },
    
    async loadedGraphNode(node) {
        // Handle workflow restoration
        if (node.comfyClass !== "ApexLoadModel") return;
        
        // Update display label if custom_path has a value
        const customPathWidget = node.widgets?.find(w => w.name === "custom_path");
        const pathLabel = node._apexPathLabel;
        
        if (customPathWidget && pathLabel) {
            if (customPathWidget.value && customPathWidget.value.trim()) {
                const fileName = customPathWidget.value.split(/[\\/]/).pop();
                pathLabel.value = `📁 ${fileName}`;
            }
        }
    }
});