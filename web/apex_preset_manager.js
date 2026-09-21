/**
 * Apex Preset Manager
 * Reusable preset management dialog for Apex Artist preset stores.
 *
 * Usage:
 *   import { openPresetManager } from "./apex_preset_manager.js";
 *   openPresetManager({
 *       apiPath: "/apex/character_presets",
 *       title: "Apex Character Preset Manager",
 *       onUse: (category, name) => { ... }
 *   });
 */

import { api } from "../../../scripts/api.js";

/**
 * Minimal DOM helper (element, class, id, props, children).
 */
export function $el(selector, propsOrChildren, children) {
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

export const BUTTON_STYLES = {
    primary: { backgroundColor: "#007acc", color: "white" },
    secondary: { backgroundColor: "#666", color: "white" },
    danger: { backgroundColor: "#cc4444", color: "white" },
};

/**
 * Preset manager bound to a single API store (e.g. /apex/character_presets).
 */
export class ApexPresetManager {
    constructor({ apiPath, title = "Apex Preset Manager", onUse = null, useLabel = "Use" }) {
        this.apiPath = apiPath;
        this.title = title;
        this.onUse = onUse;
        this.useLabel = useLabel;
        this.presets = {};
        this.searchTerm = "";
        this.selectedCategory = "All";
        this.presetListElement = null;
        this.dialog = null;
    }

    async loadPresets() {
        try {
            const response = await api.fetchApi(this.apiPath);
            if (response.ok) {
                const data = await response.json();
                if (data && !data.error) {
                    this.presets = data;
                }
            } else {
                console.error("[Apex Preset Manager] Failed to load presets:", response.status);
            }
        } catch (error) {
            console.error("[Apex Preset Manager] Error loading presets:", error);
        }
    }

    /** Load presets and open the dialog. */
    async open() {
        ensurePresetStyles();
        await this.loadPresets();
        this.dialog = this.createDialog();
        return this.dialog;
    }

    createDialog() {
        const dialog = $el("div.comfy-modal", [
            $el("div.comfy-modal-content", { style: { maxWidth: "900px", width: "90%" } }, [
                $el("h2", { textContent: this.title }),

                // Search and filter
                $el("div.apex-preset-controls", [
                    $el("input", {
                        type: "text",
                        placeholder: "Search presets...",
                        value: this.searchTerm,
                        style: { width: "220px", marginRight: "10px", padding: "5px" },
                        oninput: (e) => {
                            this.searchTerm = e.target.value.toLowerCase();
                            this.updatePresetList();
                        }
                    }),
                    $el("select", {
                        style: { marginRight: "10px", padding: "5px" },
                        onchange: (e) => {
                            this.selectedCategory = e.target.value;
                            this.updatePresetList();
                        }
                    }, [
                        $el("option", { value: "All", textContent: "All Categories" }),
                        ...Object.keys(this.presets).map((category) =>
                            $el("option", { value: category, textContent: category })
                        )
                    ]),
                    $el("button", { textContent: "Add New", onclick: () => this.showAddDialog() })
                ]),

                // Preset list
                $el("div.apex-preset-list", {
                    style: {
                        maxHeight: "420px",
                        overflowY: "auto",
                        border: "1px solid #666",
                        marginTop: "10px"
                    }
                }),

                // Dialog controls
                $el("div.apex-preset-dialog-controls", {
                    style: { marginTop: "15px", textAlign: "right" }
                }, [
                    $el("button", { textContent: "Import", onclick: () => this.importPresets() }),
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
        const actions = [];

        if (this.onUse) {
            actions.push($el("button", {
                textContent: this.useLabel,
                style: { ...BUTTON_STYLES.primary, padding: "5px 10px", marginRight: "5px", border: "none", borderRadius: "3px", cursor: "pointer" },
                onclick: () => this.usePreset(category, name)
            }));
        }

        actions.push($el("button", {
            textContent: "Edit",
            style: { ...BUTTON_STYLES.secondary, padding: "5px 10px", marginRight: "5px", border: "none", borderRadius: "3px", cursor: "pointer" },
            onclick: () => this.editPreset(category, name, data)
        }));

        actions.push($el("button", {
            textContent: "Delete",
            style: { ...BUTTON_STYLES.danger, padding: "5px 10px", border: "none", borderRadius: "3px", cursor: "pointer" },
            onclick: () => this.deletePreset(category, name)
        }));

        return $el("div.apex-preset-item", {
            style: {
                padding: "10px",
                borderBottom: "1px solid #444",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "flex-start",
                gap: "10px"
            }
        }, [
            $el("div.apex-preset-info", { style: { minWidth: "0", flex: "1" } }, [
                $el("div.apex-preset-header", [
                    $el("span.apex-preset-category", {
                        textContent: category,
                        style: { fontSize: "12px", color: "#888", marginRight: "10px" }
                    }),
                    $el("strong", { textContent: name })
                ]),
                $el("div.apex-preset-description", {
                    textContent: data.description || "",
                    style: { fontSize: "13px", color: "#ccc", marginTop: "3px" }
                }),
                $el("div.apex-preset-prompt", {
                    textContent: data.prompt || "",
                    style: {
                        fontSize: "12px",
                        color: "#aaa",
                        marginTop: "5px",
                        fontFamily: "monospace",
                        maxWidth: "520px",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap"
                    }
                }),
                data.tags && data.tags.length > 0 ? $el("div.apex-preset-tags", {
                    style: { marginTop: "5px" }
                }, data.tags.map((tag) =>
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
            $el("div.apex-preset-actions", { style: { whiteSpace: "nowrap" } }, actions)
        ]);
    }

    usePreset(category, name) {
        if (this.onUse) {
            this.onUse(category, name);
        }
    }

    editPreset(category, name, data) {
        this.showEditPresetDialog(category, name, data, false);
    }

    deletePreset(category, name) {
        if (!confirm(`Delete the preset "${name}" from "${category}"?`)) return;

        delete this.presets[category][name];

        if (Object.keys(this.presets[category]).length === 0) {
            delete this.presets[category];
        }

        this.savePresets();
        this.refreshCategoryOptions();
        this.updatePresetList();
    }

    /** Rebuild the category dropdown after presets/categories change. */
    refreshCategoryOptions() {
        const select = this.categorySelect || (this.dialog && this.dialog.querySelector("select"));
        if (!select) return;

        this.categorySelect = select;
        const previous = this.selectedCategory;

        select.replaceChildren(
            $el("option", { value: "All", textContent: "All Categories" }),
            ...Object.keys(this.presets).map((category) =>
                $el("option", { value: category, textContent: category })
            )
        );

        if (previous !== "All" && !this.presets[previous]) {
            this.selectedCategory = "All";
        }
        select.value = this.selectedCategory;
    }

    showAddDialog() {
        const categories = Object.keys(this.presets);
        const category = this.selectedCategory !== "All" ? this.selectedCategory : (categories[0] || "Apex Character Top");

        this.showEditPresetDialog(category, "", {
            prompt: "",
            description: "",
            tags: [],
            weight: 1.0
        }, true);
    }

    showEditPresetDialog(category, name, data, isNew = false) {
        const dialog = $el("div.comfy-modal", [
            $el("div.comfy-modal-content", { style: { maxWidth: "640px", width: "90%" } }, [
                $el("h3", { textContent: isNew ? "Add New Preset" : "Edit Preset" }),

                $el("div.apex-preset-form", [
                    $el("label", { style: { display: "block" } }, [
                        "Category:",
                        $el("input", {
                            type: "text",
                            value: category,
                            id: "apex-preset-category",
                            style: { width: "100%", marginTop: "5px", padding: "5px" }
                        })
                    ]),
                    $el("label", { style: { marginTop: "10px", display: "block" } }, [
                        "Name:",
                        $el("input", {
                            type: "text",
                            value: name,
                            id: "apex-preset-name",
                            style: { width: "100%", marginTop: "5px", padding: "5px" }
                        })
                    ]),
                    $el("label", { style: { marginTop: "10px", display: "block" } }, [
                        "Description:",
                        $el("input", {
                            type: "text",
                            value: data.description || "",
                            id: "apex-preset-description",
                            style: { width: "100%", marginTop: "5px", padding: "5px" }
                        })
                    ]),
                    $el("label", { style: { marginTop: "10px", display: "block" } }, [
                        "Prompt:",
                        $el("textarea", {
                            value: data.prompt || "",
                            id: "apex-preset-prompt",
                            style: { width: "100%", height: "140px", marginTop: "5px", padding: "5px" }
                        })
                    ]),
                    $el("label", { style: { marginTop: "10px", display: "block" } }, [
                        "Tags (comma-separated):",
                        $el("input", {
                            type: "text",
                            value: (data.tags || []).join(", "),
                            id: "apex-preset-tags",
                            style: { width: "100%", marginTop: "5px", padding: "5px" }
                        })
                    ]),
                    $el("label", { style: { marginTop: "10px", display: "block" } }, [
                        "Weight (0.1 - 2.0, higher = more likely when Random):",
                        $el("input", {
                            type: "number",
                            value: data.weight || 1.0,
                            min: 0.1,
                            max: 2.0,
                            step: 0.1,
                            id: "apex-preset-weight",
                            style: { width: "100%", marginTop: "5px", padding: "5px" }
                        })
                    ])
                ]),

                $el("div.apex-preset-dialog-controls", {
                    style: { marginTop: "20px", textAlign: "right" }
                }, [
                    $el("button", { textContent: "Cancel", onclick: () => dialog.remove() }),
                    $el("button", {
                        textContent: isNew ? "Add" : "Save",
                        style: { ...BUTTON_STYLES.primary, marginLeft: "10px", padding: "8px 16px", border: "none", borderRadius: "3px", cursor: "pointer" },
                        onclick: () => {
                            if (this.savePresetFromDialog(dialog, isNew ? null : { category, name })) {
                                dialog.remove();
                            }
                        }
                    })
                ])
            ])
        ]);

        document.body.appendChild(dialog);
        return dialog;
    }

    savePresetFromDialog(dialog, original) {
        const category = dialog.querySelector("#apex-preset-category").value.trim();
        const name = dialog.querySelector("#apex-preset-name").value.trim();
        const description = dialog.querySelector("#apex-preset-description").value.trim();
        const prompt = dialog.querySelector("#apex-preset-prompt").value.trim();
        const tags = dialog.querySelector("#apex-preset-tags").value.split(",").map((t) => t.trim()).filter((t) => t);
        const weight = parseFloat(dialog.querySelector("#apex-preset-weight").value) || 1.0;

        if (!category || !name || !prompt) {
            alert("Category, name, and prompt are required!");
            return false;
        }

        // Remove the original entry when the name or category changed
        if (original && (original.category !== category || original.name !== name)) {
            delete this.presets[original.category][original.name];
            if (Object.keys(this.presets[original.category]).length === 0) {
                delete this.presets[original.category];
            }
        }

        if (!this.presets[category]) {
            this.presets[category] = {};
        }

        this.presets[category][name] = { prompt, description, tags, weight };

        this.savePresets();
        this.refreshCategoryOptions();
        this.updatePresetList();
        return true;
    }

    async savePresets() {
        try {
            const response = await api.fetchApi(this.apiPath, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(this.presets)
            });
            if (!response.ok) {
                console.error("[Apex Preset Manager] Error saving presets:", response.status);
            }
        } catch (error) {
            console.error("[Apex Preset Manager] Error saving presets:", error);
        }
    }

    exportPresets() {
        const data = JSON.stringify(this.presets, null, 2);
        const blob = new Blob([data], { type: "application/json" });
        const url = URL.createObjectURL(blob);

        const a = document.createElement("a");
        a.href = url;
        a.download = `${this.apiPath.split("/").filter(Boolean).pop() || "apex_presets"}.json`;
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
            reader.onload = (event) => {
                try {
                    const imported = JSON.parse(event.target.result);

                    // Merge imported categories into the current store
                    Object.entries(imported).forEach(([category, presets]) => {
                        if (!this.presets[category]) {
                            this.presets[category] = {};
                        }
                        Object.assign(this.presets[category], presets);
                    });

                    this.savePresets();
                    this.refreshCategoryOptions();
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

/**
 * Inject the shared preset manager stylesheet once.
 */
export function ensurePresetStyles() {
    if (document.getElementById("apex-preset-manager-styles")) return;

    const style = document.createElement("style");
    style.id = "apex-preset-manager-styles";
    style.textContent = `
        .apex-preset-controls {
            display: flex;
            align-items: center;
            flex-wrap: wrap;
            gap: 10px;
            margin-bottom: 15px;
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
}

/**
 * Convenience entry point: open a manager dialog for a store.
 */
export function openPresetManager(options) {
    const manager = new ApexPresetManager(options);
    return manager.open();
}