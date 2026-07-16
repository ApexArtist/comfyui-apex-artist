/**
 * Apex Prompt Preset Web Extension
 * Enhances the prompt preset selector with advanced UI features
 */

import { app } from "../../../scripts/app.js";
import { api } from "../../../scripts/api.js";

function $el(selector, propsOrChildren, children) {
    const match = selector.match(/^([^.#]+)?((?:[.#][^.#]+)*)$/);
    const element = document.createElement(match?.[1] || "div");
    const modifiers = match?.[2] || "";

    for (const modifier of modifiers.matchAll(/([.#])([^.#]+)/g)) {
        if (modifier[1] === ".") {
            element.classList.add(modifier[2]);
        } else if (modifier[1] === "#") {
            element.id = modifier[2];
        }
    }

    let childNodes = children;
    if (Array.isArray(propsOrChildren) || propsOrChildren instanceof Node || typeof propsOrChildren === "string") {
        childNodes = propsOrChildren;
    } else if (propsOrChildren) {
        for (const [key, value] of Object.entries(propsOrChildren)) {
            if (key === "style" && value && typeof value === "object") {
                Object.assign(element.style, value);
            } else if (key.startsWith("on") && typeof value === "function") {
                element.addEventListener(key.slice(2), value);
            } else if (key in element) {
                element[key] = value;
            } else {
                element.setAttribute(key, value);
            }
        }
    }

    const appendChild = (child) => {
        if (child === null || child === undefined) return;
        element.appendChild(child instanceof Node ? child : document.createTextNode(String(child)));
    };

    if (Array.isArray(childNodes)) {
        childNodes.forEach(appendChild);
    } else {
        appendChild(childNodes);
    }

    return element;
}

class ApexPromptPresetManager {
    constructor() {
        this.presets = {};
        this.searchTerm = "";
        this.selectedCategory = "All";
        this.currentNode = null;
    }

    async loadPresets() {
        try {
            const response = await api.fetchApi("/apex/prompt_presets");
            if (response.ok) {
                this.presets = await response.json();
            }
        } catch (error) {
            console.log("Using default presets");
        }
    }

    createPresetManagerDialog() {
        const dialog = $el("div.comfy-modal", [
            $el("div.comfy-modal-content", [
                $el("h2", { textContent: "Apex Prompt Preset Manager" }),
                
                // Search and filter section
                $el("div.apex-preset-controls", [
                    $el("input", {
                        type: "text",
                        placeholder: "Search presets...",
                        style: {
                            width: "200px",
                            marginRight: "10px",
                            padding: "5px"
                        },
                        oninput: (e) => {
                            this.searchTerm = e.target.value.toLowerCase();
                            this.updatePresetList();
                        }
                    }),
                    $el("select", {
                        style: {
                            marginRight: "10px",
                            padding: "5px"
                        },
                        onchange: (e) => {
                            this.selectedCategory = e.target.value;
                            this.updatePresetList();
                        }
                    }, [
                        $el("option", { value: "All", textContent: "All Categories" }),
                        ...Object.keys(this.presets).map(cat => 
                            $el("option", { value: cat, textContent: cat })
                        )
                    ]),
                    $el("button", {
                        textContent: "Add New",
                        onclick: () => this.showAddPresetDialog()
                    })
                ]),

                // Preset list
                $el("div.apex-preset-list", {
                    style: {
                        maxHeight: "400px",
                        overflowY: "auto",
                        border: "1px solid #666",
                        marginTop: "10px"
                    }
                }),

                // Controls
                $el("div.apex-preset-dialog-controls", {
                    style: {
                        marginTop: "15px",
                        textAlign: "right"
                    }
                }, [
                    $el("button", {
                        textContent: "Import",
                        onclick: () => this.importPresets()
                    }),
                    $el("button", {
                        textContent: "Export",
                        style: { marginLeft: "10px" },
                        onclick: () => this.exportPresets()
                    }),
                    $el("button", {
                        textContent: "Close",
                        style: { marginLeft: "10px" },
                        onclick: () => dialog.remove()
                    })
                ])
            ])
        ]);

        this.presetListElement = dialog.querySelector(".apex-preset-list");
        this.updatePresetList();
        
        document.body.appendChild(dialog);
        return dialog;
    }

    updatePresetList() {
        if (!this.presetListElement) return;

        const filteredPresets = this.getFilteredPresets();
        
        this.presetListElement.replaceChildren(
            ...filteredPresets.map(({ category, name, data }) => 
                this.createPresetItem(category, name, data)
            )
        );
    }

    getFilteredPresets() {
        const filtered = [];
        
        Object.entries(this.presets).forEach(([category, presets]) => {
            if (this.selectedCategory !== "All" && category !== this.selectedCategory) {
                return;
            }

            Object.entries(presets).forEach(([name, data]) => {
                const searchableText = `${category} ${name} ${data.description || ""} ${(data.tags || []).join(" ")}`.toLowerCase();
                
                if (!this.searchTerm || searchableText.includes(this.searchTerm)) {
                    filtered.push({ category, name, data });
                }
            });
        });

        return filtered.sort((a, b) => {
            if (a.category !== b.category) {
                return a.category.localeCompare(b.category);
            }
            return a.name.localeCompare(b.name);
        });
    }

    createPresetItem(category, name, data) {
        return $el("div.apex-preset-item", {
            style: {
                padding: "10px",
                borderBottom: "1px solid #444",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "flex-start"
            }
        }, [
            $el("div.apex-preset-info", [
                $el("div.apex-preset-header", [
                    $el("span.apex-preset-category", {
                        textContent: category,
                        style: {
                            fontSize: "12px",
                            color: "#888",
                            marginRight: "10px"
                        }
                    }),
                    $el("strong", { textContent: name })
                ]),
                $el("div.apex-preset-description", {
                    textContent: data.description || "",
                    style: {
                        fontSize: "13px",
                        color: "#ccc",
                        marginTop: "3px"
                    }
                }),
                $el("div.apex-preset-prompt", {
                    textContent: data.prompt,
                    style: {
                        fontSize: "12px",
                        color: "#aaa",
                        marginTop: "5px",
                        fontFamily: "monospace",
                        maxWidth: "400px",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap"
                    }
                }),
                data.tags && data.tags.length > 0 ? $el("div.apex-preset-tags", {
                    style: { marginTop: "5px" }
                }, data.tags.map(tag => 
                    $el("span.apex-preset-tag", {
                        textContent: tag,
                        style: {
                            backgroundColor: "#444",
                            color: "#fff",
                            padding: "2px 6px",
                            marginRight: "5px",
                            borderRadius: "3px",
                            fontSize: "10px"
                        }
                    })
                )) : null
            ]),
            $el("div.apex-preset-actions", [
                $el("button", {
                    textContent: "Use",
                    style: {
                        backgroundColor: "#007acc",
                        color: "white",
                        border: "none",
                        padding: "5px 10px",
                        marginRight: "5px",
                        borderRadius: "3px",
                        cursor: "pointer"
                    },
                    onclick: () => this.usePreset(category, name)
                }),
                $el("button", {
                    textContent: "Edit",
                    style: {
                        backgroundColor: "#666",
                        color: "white",
                        border: "none",
                        padding: "5px 10px",
                        marginRight: "5px",
                        borderRadius: "3px",
                        cursor: "pointer"
                    },
                    onclick: () => this.editPreset(category, name, data)
                }),
                $el("button", {
                    textContent: "Delete",
                    style: {
                        backgroundColor: "#cc4444",
                        color: "white",
                        border: "none",
                        padding: "5px 10px",
                        borderRadius: "3px",
                        cursor: "pointer"
                    },
                    onclick: () => this.deletePreset(category, name)
                })
            ])
        ]);
    }

    usePreset(category, name) {
        if (this.currentNode) {
            // Update the node's widget values
            const categoryWidget = this.currentNode.widgets.find(w => w.name === "category");
            const presetWidget = this.currentNode.widgets.find(w => w.name === "preset_name");
            
            if (categoryWidget) categoryWidget.value = category;
            if (presetWidget) presetWidget.value = `${category}/${name}`;
            
            app.graph.setDirtyCanvas(true, true);
        }
    }

    editPreset(category, name, data) {
        this.showEditPresetDialog(category, name, data);
    }

    deletePreset(category, name) {
        if (confirm(`Are you sure you want to delete the preset "${name}" from category "${category}"?`)) {
            delete this.presets[category][name];
            
            // Remove category if empty
            if (Object.keys(this.presets[category]).length === 0) {
                delete this.presets[category];
            }
            
            this.savePresets();
            this.updatePresetList();
        }
    }

    showAddPresetDialog() {
        this.showEditPresetDialog("General", "", {
            prompt: "",
            description: "",
            tags: [],
            weight: 1.0
        }, true);
    }

    showEditPresetDialog(category, name, data, isNew = false) {
        const dialog = $el("div.comfy-modal", [
            $el("div.comfy-modal-content", [
                $el("h3", { textContent: isNew ? "Add New Preset" : "Edit Preset" }),
                
                $el("div.apex-preset-form", [
                    $el("label", [
                        "Category:",
                        $el("input", {
                            type: "text",
                            value: category,
                            style: {
                                width: "100%",
                                marginTop: "5px",
                                padding: "5px"
                            },
                            id: "preset-category"
                        })
                    ]),
                    
                    $el("label", {
                        style: { marginTop: "10px", display: "block" }
                    }, [
                        "Name:",
                        $el("input", {
                            type: "text",
                            value: name,
                            style: {
                                width: "100%",
                                marginTop: "5px",
                                padding: "5px"
                            },
                            id: "preset-name"
                        })
                    ]),
                    
                    $el("label", {
                        style: { marginTop: "10px", display: "block" }
                    }, [
                        "Description:",
                        $el("input", {
                            type: "text",
                            value: data.description || "",
                            style: {
                                width: "100%",
                                marginTop: "5px",
                                padding: "5px"
                            },
                            id: "preset-description"
                        })
                    ]),
                    
                    $el("label", {
                        style: { marginTop: "10px", display: "block" }
                    }, [
                        "Prompt:",
                        $el("textarea", {
                            value: data.prompt || "",
                            style: {
                                width: "100%",
                                height: "100px",
                                marginTop: "5px",
                                padding: "5px"
                            },
                            id: "preset-prompt"
                        })
                    ]),
                    
                    $el("label", {
                        style: { marginTop: "10px", display: "block" }
                    }, [
                        "Tags (comma-separated):",
                        $el("input", {
                            type: "text",
                            value: (data.tags || []).join(", "),
                            style: {
                                width: "100%",
                                marginTop: "5px",
                                padding: "5px"
                            },
                            id: "preset-tags"
                        })
                    ]),
                    
                    $el("label", {
                        style: { marginTop: "10px", display: "block" }
                    }, [
                        "Weight:",
                        $el("input", {
                            type: "number",
                            value: data.weight || 1.0,
                            min: 0.1,
                            max: 2.0,
                            step: 0.1,
                            style: {
                                width: "100%",
                                marginTop: "5px",
                                padding: "5px"
                            },
                            id: "preset-weight"
                        })
                    ])
                ]),
                
                $el("div.apex-preset-dialog-controls", {
                    style: {
                        marginTop: "20px",
                        textAlign: "right"
                    }
                }, [
                    $el("button", {
                        textContent: "Cancel",
                        onclick: () => dialog.remove()
                    }),
                    $el("button", {
                        textContent: isNew ? "Add" : "Save",
                        style: {
                            marginLeft: "10px",
                            backgroundColor: "#007acc",
                            color: "white",
                            border: "none",
                            padding: "8px 16px",
                            borderRadius: "3px"
                        },
                        onclick: () => {
                            this.savePresetFromDialog(dialog, isNew ? null : { category, name });
                            dialog.remove();
                        }
                    })
                ])
            ])
        ]);
        
        document.body.appendChild(dialog);
    }

    savePresetFromDialog(dialog, original) {
        const category = dialog.querySelector("#preset-category").value.trim();
        const name = dialog.querySelector("#preset-name").value.trim();
        const description = dialog.querySelector("#preset-description").value.trim();
        const prompt = dialog.querySelector("#preset-prompt").value.trim();
        const tags = dialog.querySelector("#preset-tags").value.split(",").map(t => t.trim()).filter(t => t);
        const weight = parseFloat(dialog.querySelector("#preset-weight").value) || 1.0;
        
        if (!category || !name || !prompt) {
            alert("Category, name, and prompt are required!");
            return;
        }
        
        // Remove original if name/category changed
        if (original && (original.category !== category || original.name !== name)) {
            delete this.presets[original.category][original.name];
            if (Object.keys(this.presets[original.category]).length === 0) {
                delete this.presets[original.category];
            }
        }
        
        // Add/update preset
        if (!this.presets[category]) {
            this.presets[category] = {};
        }
        
        this.presets[category][name] = {
            prompt,
            description,
            tags,
            weight
        };
        
        this.savePresets();
        this.updatePresetList();
    }

    async savePresets() {
        try {
            await api.fetchApi("/apex/prompt_presets", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(this.presets)
            });
        } catch (error) {
            console.error("Error saving presets:", error);
        }
    }

    exportPresets() {
        const data = JSON.stringify(this.presets, null, 2);
        const blob = new Blob([data], { type: "application/json" });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement("a");
        a.href = url;
        a.download = "apex_prompt_presets.json";
        a.click();
        
        URL.revokeObjectURL(url);
    }

    importPresets() {
        const input = document.createElement("input");
        input.type = "file";
        input.accept = ".json";
        
        input.onchange = (e) => {
            const file = e.target.files[0];
            if (!file) return;
            
            const reader = new FileReader();
            reader.onload = (e) => {
                try {
                    const imported = JSON.parse(e.target.result);
                    
                    // Merge with existing presets
                    Object.entries(imported).forEach(([category, presets]) => {
                        if (!this.presets[category]) {
                            this.presets[category] = {};
                        }
                        Object.assign(this.presets[category], presets);
                    });
                    
                    this.savePresets();
                    this.updatePresetList();
                    alert("Presets imported successfully!");
                } catch (error) {
                    alert("Error importing presets: " + error.message);
                }
            };
            reader.readAsText(file);
        };
        
        input.click();
    }
}

const presetManager = new ApexPromptPresetManager();

app.registerExtension({
    name: "Apex.PromptPreset",
    
    async setup() {
        await presetManager.loadPresets();
        
        // Add stylesheet
        const style = document.createElement("style");
        style.textContent = `
            .apex-preset-controls {
                display: flex;
                align-items: center;
                margin-bottom: 15px;
                flex-wrap: wrap;
                gap: 10px;
            }
            
            .apex-preset-item:hover {
                background-color: rgba(255, 255, 255, 0.05);
            }
            
            .apex-preset-form label {
                display: block;
                margin-bottom: 10px;
                color: #fff;
            }
            
            .apex-preset-form input,
            .apex-preset-form textarea {
                background-color: #333;
                border: 1px solid #666;
                color: #fff;
                border-radius: 3px;
            }
            
            .apex-preset-form input:focus,
            .apex-preset-form textarea:focus {
                outline: none;
                border-color: #007acc;
            }
        `;
        document.head.appendChild(style);
    },
    
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "ApexPromptPreset") {
            const onAdded = nodeType.prototype.onAdded;
            nodeType.prototype.onAdded = function() {
                onAdded?.apply(this, arguments);
            };
        }
    }
});