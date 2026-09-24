/** Factory/user preset manager. No build dependencies and no workflow input changes. */
import { app } from "../../../scripts/app.js";
import { api } from "../../../scripts/api.js";

export const CATEGORY_WIDGETS = {
    "Apex Environment": "environment_preset",
    "Apex Lighting": "lighting_preset",
    "Apex Style": "style_preset",
    "Apex Camera Lens": "camera_lens_preset",
    "Apex Color": "color_preset",
};
const USER_PREFIX = "User: ";
const nodes = new Set();
let library = null;
let requestSequence = 0;

function element(tag, props = {}, children = []) {
    const el = document.createElement(tag);
    Object.assign(el, props);
    for (const child of children) el.append(child);
    return el;
}

export function refreshNode(node, snapshot) {
    for (const [category, widgetName] of Object.entries(CATEGORY_WIDGETS)) {
        const widget = node.widgets?.find(w => w.name === widgetName);
        if (!widget) continue;
        const values = ["Disabled", "Random", ...Object.keys(snapshot.presets[category] || {})];
        // Do not silently replace a workflow's missing preset with something else.
        if (typeof widget.value === "string" && !values.includes(widget.value)) values.push(widget.value);
        widget.options = { ...widget.options, values };
    }
    node.setDirtyCanvas?.(true, true);
}

export function usePreset(node, category, name, source) {
    const widget = node.widgets?.find(w => w.name === CATEGORY_WIDGETS[category]);
    if (!widget) throw new Error("The target category widget is unavailable.");
    const index = node.widgets.indexOf(widget);
    if (node.inputs?.some(input => input.widget?.name === widget.name && input.link != null)) {
        throw new Error("This category is connected to another node. Disconnect it before using a preset.");
    }
    const previous = widget.value;
    widget.value = source === "user" ? USER_PREFIX + name : name;
    widget.callback?.call(widget, widget.value, app.canvas, node, undefined, undefined);
    node.onWidgetChanged?.(widget.name, widget.value, previous, widget, index);
    node.setDirtyCanvas?.(true, true);
    app.graph?.change?.();
}

async function responseJson(response) {
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || `Preset request failed (${response.status}).`);
    return data;
}

function accept(snapshot) {
    library = snapshot;
    for (const node of nodes) refreshNode(node, snapshot);
    return snapshot;
}

async function loadLibrary() {
    const sequence = ++requestSequence;
    const data = await responseJson(await api.fetchApi("/apex/prompt_library"));
    if (sequence === requestSequence) accept(data);
    return data;
}

async function mutate(operation, payload) {
    const data = await responseJson(await api.fetchApi(`/apex/prompt_library/${operation}`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
    }));
    ++requestSequence;
    return accept(data);
}

function toast(message) {
    try {
        const note = element("div", { className: "apex-prompt-toast", textContent: message, role: "status" });
        document.body.append(note);
        setTimeout(() => note.remove(), 3200);
    } catch { /* headless harness: no-op */ }
}

function debounce(fn, wait = 150) {
    let timer = 0;
    return (...args) => {
        clearTimeout(timer);
        timer = setTimeout(() => fn(...args), wait);
    };
}

function escapeHtml(text) {
    return String(text).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function highlight(text, needle) {
    const query = String(needle || "").trim().toLowerCase();
    if (!query) return escapeHtml(text);
    const lower = String(text).toLowerCase();
    const index = lower.indexOf(query);
    if (index < 0) return escapeHtml(text);
    return escapeHtml(String(text).slice(0, index)) + "<mark>"
        + escapeHtml(String(text).slice(index, index + query.length)) + "</mark>"
        + escapeHtml(String(text).slice(index + query.length));
}

function dialog(title) {
    const panel = element("dialog", { className: "apex-prompt-dialog" });
    const error = element("p", { className: "apex-prompt-error", role: "alert" });
    const body = element("div");
    const close = element("button", { textContent: "Close", onclick: () => panel.close() });
    const header = element("header", { className: "apex-prompt-dialog-header" }, [
        element("h2", { textContent: title }), close,
    ]);
    panel.append(header, body, error);
    try {
        const open = document.querySelectorAll?.("dialog.apex-prompt-dialog[open]")?.length || 0;
        if (open > 0) panel.style.zIndex = String(1000 + open);
    } catch { /* headless harness */ }
    panel.addEventListener("close", () => panel.remove(), { once: true });
    document.body.append(panel);
    panel.showModal();
    return { panel, body, error };
}

function button(label, action, error) {
    return element("button", { textContent: label, onclick: async event => {
        const target = event.currentTarget;
        target.disabled = true;
        error.textContent = "";
        try { await action(); } catch (exc) { error.textContent = exc.message; }
        finally { target.disabled = false; }
    } });
}

function select(values, value) {
    const control = element("select", {}, values.map(v => element("option", { value: v, textContent: v })));
    control.value = value;
    return control;
}

function field(label, control) {
    return element("label", { className: "apex-prompt-field" }, [element("span", { textContent: label }), control]);
}

function selectedCategoryText(node, snapshot, category) {
    const widget = node?.widgets?.find(w => w.name === CATEGORY_WIDGETS[category]);
    const value = widget?.value;
    if (!value || value === "Disabled" || value === "Random") return { value, text: "" };
    return { value, text: snapshot.presets[category]?.[value]?.prompt || "" };
}

function validateDraft(draft) {
    const trimmed = String(draft.name || "").trim();
    if (!trimmed) return "Give the preset a name.";
    if (trimmed !== String(draft.name || "")) return "Remove leading/trailing spaces from the name.";
    if (["Disabled", "Random", "None"].includes(trimmed) || trimmed.startsWith(USER_PREFIX)) return "That name is reserved. Pick another.";
    if (!String(draft.prompt || "").trim()) return "Prompt text cannot be empty.";
    const numeric = Number(draft.weight);
    if (!Number.isFinite(numeric) || numeric <= 0 || numeric > 1000) return "Weight must be a number from 0 to 1000 (exclusive of 0).";
    return "";
}

function counter(label, control, max) {
    const hint = element("small", { className: "apex-prompt-hint" });
    const refresh = () => { hint.textContent = `${label}: ${String(control.value || "").length}/${max}`; };
    control.addEventListener?.("input", refresh);
    refresh();
    return hint;
}

export function openEditor(node, snapshot, entry = null, edit = false, onSaved = null) {
    const ui = dialog(edit ? "Edit User Preset" : "Save User Preset");
    let revision = snapshot.revision;
    const categories = Object.keys(CATEGORY_WIDGETS);
    let initialCategory = entry?.category || categories[0];
    if (!entry && node) {
        for (const cat of categories) {
            const picked = selectedCategoryText(node, snapshot, cat);
            if (picked.value && picked.value !== "Disabled" && picked.value !== "Random" && picked.text) { initialCategory = cat; break; }
        }
    }
    const category = select(categories, initialCategory);
    let prefillName = "";
    let prefillText = "";
    if (entry) {
        prefillName = entry.name + (edit ? "" : " Copy");
        prefillText = entry.data.prompt || "";
    } else {
        const picked = selectedCategoryText(node, snapshot, category.value);
        prefillText = picked.text;
        if (picked.value && picked.value !== "Disabled" && picked.value !== "Random") {
            prefillName = picked.value.startsWith(USER_PREFIX) ? picked.value.slice(USER_PREFIX.length) : `${picked.value} Copy`;
        }
    }
    const name = element("input", { value: prefillName, maxLength: 120 });
    name.setAttribute?.("aria-label", "Preset name");
    const prompt = element("textarea", { value: prefillText, rows: 7, maxLength: 32000 });
    prompt.setAttribute?.("aria-label", "Prompt text");
    const description = element("input", { value: entry?.data.description || "", maxLength: 2000 });
    const tags = element("input", { value: (entry?.data.tags || []).join(", ") });
    const weight = element("input", { type: "number", value: String(entry?.data.weight ?? 1), min: "0.000001", max: "1000", step: "any" });
    ui.body.append(element("p", { textContent: "User presets are shared by this ComfyUI installation. Save one category's text—not the whole combined prompt. Factory presets remain unchanged." }));
    ui.body.append(field("Category", category), field("Name", name), counter("Name", name, 120));
    ui.body.append(field("Prompt text", prompt), counter("Prompt", prompt, 32000));
    ui.body.append(button("Copy selected category text", () => {
        const widget = node.widgets?.find(w => w.name === CATEGORY_WIDGETS[category.value]);
        const data = snapshot.presets[category.value]?.[widget?.value];
        if (!data) throw new Error("Select a named preset first; Random and Disabled do not have fixed text.");
        prompt.value = data.prompt;
    }, ui.error));
    ui.body.append(button("Copy input text", () => {
        const widget = node.widgets?.find(w => w.name === "input_text");
        if (node.inputs?.some(input => input.widget?.name === "input_text" && input.link != null)) {
            throw new Error("Input text is connected; its runtime value is unavailable in this dialog.");
        }
        prompt.value = widget?.value || "";
    }, ui.error));
    ui.body.append(field("Description", description), field("Tags (comma separated)", tags), field("Weight — user Random only", weight));
    ui.body.append(button("Refresh library (keep my draft)", async () => {
        snapshot = await loadLibrary();
        revision = snapshot.revision;
        ui.error.textContent = "Library refreshed. Review your draft before saving; saving an edit replaces that user preset.";
    }, ui.error));
    const submit = async applyToNode => {
        const draft = { name: name.value, prompt: prompt.value, weight: weight.value };
        const problem = validateDraft(draft);
        if (problem) throw new Error(problem);
        const trimmed = draft.name.trim();
        const saved = await mutate("save", {
            revision, source: "user", category: category.value, name: trimmed,
            original: edit ? { category: entry.category, name: entry.name } : null,
            preset: { prompt: draft.prompt, description: description.value,
                tags: tags.value.split(",").map(t => t.trim()).filter(Boolean), weight: Number(draft.weight) },
        });
        onSaved?.(saved);
        if (applyToNode) {
            usePreset(node, category.value, trimmed, "user");
            toast(`Saved and applied User: ${trimmed}`);
        } else {
            toast(`Saved User: ${trimmed} (${category.value})`);
        }
        ui.panel.close();
    };
    ui.body.append(button("Save", () => submit(false), ui.error));
    ui.body.append(button("Save & Use", () => submit(true), ui.error));
    try { (name.value ? prompt : name).focus?.(); } catch { /* headless */ }
    return ui;
}

async function openManager(node) {
    let snapshot = await loadLibrary();
    const ui = dialog("Apex Prompt Preset Manager");
    const search = element("input", { placeholder: "Search presets…", type: "search" });
    const source = select(["All", "Factory", "User"], "All");
    const category = select(["All", ...Object.keys(CATEGORY_WIDGETS)], "All");
    const status = element("p", { className: "apex-prompt-hint", role: "status" });
    const list = element("div", { className: "apex-prompt-list" });
    const moreWrap = element("div");
    let visibleLimit = 100;
    let lastDeleted = null;
    const update = value => { snapshot = value; render(); };
    function matches(data, name, needle) {
        const query = String(needle || "").toLowerCase();
        if (!query) return true;
        return `${name} ${data.prompt} ${data.description || ""} ${(data.tags || []).join(" ")}`.toLowerCase().includes(query);
    }
    function render() {
        list.replaceChildren();
        moreWrap.replaceChildren();
        const needle = search.value;
        let shown = 0;
        let total = 0;
        for (const kind of ["factory", "user"]) {
            if (source.value !== "All" && source.value.toLowerCase() !== kind) continue;
            for (const cat of Object.keys(CATEGORY_WIDGETS)) {
                if (category.value !== "All" && category.value !== cat) continue;
                const entries = Object.entries(snapshot[kind][cat] || {}).filter(([name, data]) => matches(data, name, needle));
                if (!entries.length) continue;
                total += entries.length;
                const groupCount = entries.length;
                const head = element("h3", { textContent: `${kind === "factory" ? "Factory" : "User"} · ${cat} (${groupCount})` });
                head.innerHTML = highlight(head.textContent, "");
                list.append(head);
                for (const [name, data] of entries) {
                    if (shown >= visibleLimit) continue;
                    shown += 1;
                    const entry = { category: cat, name, data, source: kind };
                    const title = element("strong", {});
                    title.innerHTML = highlight(`${kind === "factory" ? "Factory" : "User"} · ${cat} · ${name}`, needle);
                    const preview = element("p", {});
                    preview.innerHTML = highlight(String(data.prompt).slice(0, 400), needle);
                    const row = element("section", { className: "apex-prompt-row" }, [title, preview,
                        button("Use", () => {
                            usePreset(node, cat, name, kind);
                            toast(`Applied ${kind === "user" ? USER_PREFIX + name : name} → ${cat}`);
                        }, ui.error),
                        button("Save a Copy", () => openEditor(node, snapshot, entry, false, update), ui.error),
                    ]);
                    if (kind === "user") row.append(
                        button("Edit / Rename", () => openEditor(node, snapshot, entry, true, update), ui.error),
                        button("Delete", async () => {
                            const confirmRow = element("span", { textContent: `Delete “${name}”? ` });
                            const yes = element("button", { textContent: "Confirm delete" });
                            const no = element("button", { textContent: "Keep" });
                            const inline = element("span", {}, [confirmRow, yes, no]);
                            row.append(inline);
                            no.onclick = () => inline.remove();
                            yes.onclick = async () => {
                                inline.remove();
                                lastDeleted = { category: cat, name, data };
                                update(await mutate("delete", { revision: snapshot.revision, source: "user", category: cat, name }));
                                toast(`Deleted User: ${name}`);
                            };
                        }, ui.error),
                    );
                    list.append(row);
                }
            }
        }
        if (!total) {
            list.append(element("p", { className: "apex-prompt-hint", textContent: "No presets match. Clear the search or choose another filter." }));
        }
        status.textContent = `Showing ${Math.min(shown, total)} of ${total} presets`;
        if (shown < total) {
            moreWrap.append(button(`Show more (${total - shown} remaining)`, () => { visibleLimit += 100; render(); }, ui.error));
        }
        if (lastDeleted) {
            moreWrap.append(button("Undo delete", async () => {
                const backup = lastDeleted;
                lastDeleted = null;
                update(await mutate("save", { revision: snapshot.revision, source: "user",
                    category: backup.category, name: backup.name, original: null, preset: backup.data }));
                toast(`Restored User: ${backup.name}`);
            }, ui.error));
        }
    }
    const debouncedRender = debounce(() => { visibleLimit = 100; render(); });
    for (const control of [source, category]) control.addEventListener("input", () => { visibleLimit = 100; render(); });
    search.addEventListener("input", debouncedRender);
    const file = element("input", { type: "file", accept: ".json,application/json", hidden: true });
    file.addEventListener("change", async () => {
        ui.error.textContent = "";
        try {
            if (!file.files?.length) return;
            if (file.files[0].size > 4 * 1024 * 1024) throw new Error("Import exceeds 4 MiB.");
            const document = JSON.parse(await file.files[0].text());
            const incoming = document?.schema_version ? document.presets : document;
            const counts = { fresh: 0, conflicts: [] };
            for (const [cat, entries] of Object.entries(incoming || {})) {
                for (const name of Object.keys(entries || {})) {
                    const current = snapshot.user[cat]?.[name];
                    if (current && JSON.stringify(current) !== JSON.stringify(entries[name])) counts.conflicts.push(`${cat} · ${name}`);
                    else if (!current) counts.fresh += 1;
                }
            }
            if (counts.conflicts.length && !confirm(`Import ${counts.fresh} new preset(s)? ${counts.conflicts.length} conflict(s) will be rejected:\n${counts.conflicts.slice(0, 10).join("\n")}${counts.conflicts.length > 10 ? "\n…" : ""}`)) return;
            update(await mutate("import", { revision: snapshot.revision, document }));
            toast(`Imported ${counts.fresh} preset(s)`);
        } catch (exc) { ui.error.textContent = exc.message; }
        finally { file.value = ""; }
    });
    ui.body.append(element("p", { textContent: "Factory presets are read-only. User presets are shared across this installation. Random continues to use the original factory pool. Export user presets when sharing workflows." }),
        field("Search", search), field("Library", source), field("Category", category), status,
        button("New User Preset", () => openEditor(node, snapshot, null, false, update), ui.error),
        button("Refresh", async () => update(await loadLibrary()), ui.error),
        button("Import into User Library", () => file.click(), ui.error),
        button("Export User Library", () => {
            const blob = new Blob([JSON.stringify({ schema_version: 1, presets: snapshot.user }, null, 2)], { type: "application/json" });
            const url = URL.createObjectURL(blob);
            const stamp = new Date().toISOString().slice(0, 10).replaceAll("-", "");
            const link = element("a", { href: url, download: `apex_user_prompt_presets_${stamp}.json` });
            link.click();
            setTimeout(() => URL.revokeObjectURL(url), 1000);
            toast("Exported user presets");
        }, ui.error), file, list, moreWrap);
    render();
}

app.registerExtension({
    name: "Apex.PromptPreset",
    async setup() {
        const style = element("style", { textContent: `
            .apex-prompt-dialog { color: var(--input-text, #ddd); background: var(--comfy-menu-bg, #222); border: 1px solid #666; border-radius: 8px; width: min(850px, 90vw); max-height: 85vh; overflow: auto; padding: 20px; }
            .apex-prompt-dialog::backdrop { background: #0009; }
            .apex-prompt-dialog-header { position: sticky; top: -20px; z-index: 1; display: flex; align-items: center; justify-content: space-between; gap: 16px; margin: -20px -20px 16px; padding: 12px 20px; background: var(--comfy-menu-bg, #222); border-bottom: 1px solid #666; }
            .apex-prompt-dialog-header h2 { margin: 0; min-width: 0; overflow-wrap: anywhere; }
            .apex-prompt-dialog-header button { flex-shrink: 0; }
            .apex-prompt-dialog button, .apex-prompt-dialog select { margin: 4px; padding: 6px; }
            .apex-prompt-field { display: grid; gap: 5px; margin: 12px 0; }
            .apex-prompt-field input, .apex-prompt-field textarea { width: 100%; box-sizing: border-box; }
            .apex-prompt-row { border-bottom: 1px solid #666; padding: 12px 0; }
            .apex-prompt-row p { white-space: pre-wrap; overflow-wrap: anywhere; }
            .apex-prompt-row mark { background: #b58900; color: #111; border-radius: 2px; padding: 0 2px; }
            .apex-prompt-error { color: #ff9090; white-space: pre-wrap; }
            .apex-prompt-hint { color: #9aa; font-size: 12px; margin: 4px 0; }
            .apex-prompt-toast { position: fixed; bottom: 18px; right: 18px; z-index: 3000; background: #2a2a2a; color: #eee; border: 1px solid #666; border-radius: 6px; padding: 10px 14px; max-width: min(420px, 90vw); box-shadow: 0 4px 18px #000a; }
            .apex-prompt-dialog h3 { margin: 16px 0 6px; font-size: 13px; color: #bbb; text-transform: uppercase; letter-spacing: .04em; }
        ` });
        document.head.append(style);
        api.addEventListener("apex-presets-changed", () => loadLibrary().catch(console.error));
        try { await loadLibrary(); } catch (exc) { console.error("[Apex Prompt]", exc); }
    },
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "ApexPromptPreset") return;
        const created = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const result = created?.apply(this, arguments);
            nodes.add(this);
            const launch = action => async () => {
                const host = action.host;
                try {
                    if (host && "value" in host) { host.value = "Working…"; host.disabled = true; }
                    await action();
                } catch (exc) { const ui = dialog("Apex Preset Error"); ui.error.textContent = exc.message; }
                finally { if (host && "value" in host) { host.value = host.label; host.disabled = false; } }
            };
            const saveWidget = this.addWidget("button", "Save Preset…", null, null, { serialize: false });
            const manageWidget = this.addWidget("button", "Manage Presets…", null, null, { serialize: false });
            saveWidget.label = "Save Preset…"; manageWidget.label = "Manage Presets…";
            const saveAction = launch(async () => openEditor(this, await loadLibrary()));
            saveAction.host = saveWidget; saveWidget.callback = saveAction;
            const manageAction = launch(() => openManager(this));
            manageAction.host = manageWidget; manageWidget.callback = manageAction;
            if (library) refreshNode(this, library);
            return result;
        };
        const removed = nodeType.prototype.onRemoved;
        const configured = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function () {
            const result = configured?.apply(this, arguments);
            if (library) refreshNode(this, library);
            return result;
        };
        nodeType.prototype.onRemoved = function () {
            nodes.delete(this);
            return removed?.apply(this, arguments);
        };
    },
});