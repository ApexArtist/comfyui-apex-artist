/** Browser-free frontend regression harness; loads the real module in memory. */
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

class Element {
    constructor(tag) { this.tag = tag; this.children = []; this.listeners = {}; this.value = ""; this.textContent = ""; }
    append(...children) { this.children.push(...children); }
    replaceChildren(...children) { this.children = children; }
    addEventListener(name, callback) { this.listeners[name] = callback; }
    showModal() { this.open = true; }
    close() { this.open = false; this.listeners.close?.(); }
    remove() { this.removed = true; }
    click() { return this.onclick?.({ currentTarget: this }); }
}
globalThis.document = { createElement: tag => new Element(tag), body: new Element("body"), head: new Element("head") };
globalThis.confirm = () => true;
let extension;
let callbacks = 0;
let graphChanges = 0;
let requests = [];
let failSave = false;
const categories = ["Apex Environment", "Apex Lighting", "Apex Style", "Apex Camera Lens"];
const snapshot = {
    revision: "r1", factory: {}, user: {}, presets: {},
};
for (const category of categories) {
    snapshot.factory[category] = { Factory: { prompt: "factory text", tags: [], weight: 1 } };
    snapshot.user[category] = { Custom: { prompt: "user text", tags: [], weight: 1 } };
    snapshot.presets[category] = { ...snapshot.factory[category], "User: Custom": snapshot.user[category].Custom };
}
globalThis.__app = {
    registerExtension: value => { extension = value; }, canvas: {}, graph: { change: () => ++graphChanges },
};
const listeners = {};
globalThis.__api = {
    addEventListener: (name, callback) => { listeners[name] = callback; },
    async fetchApi(path, options) {
        requests.push({ path, options });
        if (options && failSave) return { ok: false, status: 409, json: async () => ({ error: "conflict: refresh required" }) };
        return { ok: true, json: async () => structuredClone(snapshot) };
    },
};
const source = (await readFile(new URL("../web/apex_prompt.js", import.meta.url), "utf8"))
    .replace('import { app } from "../../../scripts/app.js";', "const app = globalThis.__app;")
    .replace('import { api } from "../../../scripts/api.js";', "const api = globalThis.__api;");
const module = await import(`data:text/javascript;base64,${Buffer.from(source).toString("base64")}`);

function find(root, predicate) {
    if (predicate(root)) return root;
    for (const child of root.children || []) {
        const result = find(child, predicate);
        if (result) return result;
    }
}
function findAll(root, predicate) {
    return [...(predicate(root) ? [root] : []), ...(root.children || []).flatMap(child => findAll(child, predicate))];
}
function control(ui, label) {
    return find(ui.body, el => el.tag === "label" && el.children[0].textContent === label).children[1];
}
function fieldControl(root, label) {
    const boxes = findAll(root, el => el.tag === "label" && el.children[0]?.textContent === label);
    if (!boxes.length) throw new Error(`missing field: ${label}`);
    return boxes.at(-1).children[1];
}
function makeNode() {
    return {
        widgets: Object.values(module.CATEGORY_WIDGETS).map(name => ({ name, value: "Factory", options: {}, callback() { ++callbacks; } })),
        size: [340, 500], setDirtyCanvas() {},
        addWidget(type, name, value, callback, options) { const widget = { type, name, value, callback, options }; this.widgets.push(widget); return widget; },
    };
}

await extension.setup();
const node = makeNode();
node.widgets[0].value = "User: Missing";
module.refreshNode(node, snapshot);
assert.equal(node.widgets[0].value, "User: Missing");
assert(node.widgets[0].options.values.includes("User: Missing"));
assert(node.widgets[1].options.values.includes("User: Custom"));
assert.deepEqual(node.size, [340, 500]);
module.usePreset(node, "Apex Lighting", "Custom", "user");
assert.equal(node.widgets[1].value, "User: Custom");
assert.equal(callbacks, 1);
assert.equal(graphChanges, 1);
node.inputs = [{ widget: { name: "lighting_preset" }, link: 1 }];
assert.throws(() => module.usePreset(node, "Apex Lighting", "Factory", "factory"), /connected/);
node.inputs = [];

const ui = module.openEditor(node, snapshot);
control(ui, "Name").value = "My New Preset";
control(ui, "Prompt text").value = "new text";
const save = find(ui.body, el => el.tag === "button" && el.textContent === "Save");
failSave = true;
await save.click();
assert.equal(ui.panel.open, true);
assert.match(ui.error.textContent, /conflict/);
assert.equal(control(ui, "Prompt text").value, "new text");
assert.equal(save.disabled, false);
failSave = false;
await save.click();
assert.equal(ui.panel.removed, true);
const payload = JSON.parse(requests.at(-1).options.body);
assert.equal(payload.source, "user");
assert.equal(payload.name, "My New Preset");
assert.equal(payload.revision, "r1");
assert.equal(payload.original, null);

let createdCalls = 0;
let removedCalls = 0;
function NodeType() { Object.assign(this, makeNode()); }
NodeType.prototype.onNodeCreated = function () { ++createdCalls; };
NodeType.prototype.onRemoved = function () { ++removedCalls; };
await extension.beforeRegisterNodeDef(NodeType, { name: "ApexPromptPreset" });
const instance = new NodeType();
instance.onNodeCreated();
assert.equal(createdCalls, 1);
const buttons = instance.widgets.filter(widget => widget.type === "button");
assert.equal(buttons.length, 2);
assert(buttons.every(widget => widget.options.serialize === false));
await buttons[1].callback();
const manager = document.body.children.at(-1);
const managerHeader = manager.children[0];
assert.equal(managerHeader.className, "apex-prompt-dialog-header");
assert.equal(managerHeader.children[0].textContent, "Apex Prompt Preset Manager");
const managerClose = find(managerHeader, el => el.tag === "button" && el.textContent === "Close");
assert(managerClose, "Close must be in the top header, before the scrolling preset content");
assert.equal(findAll(manager, el => el.tag === "button" && el.textContent === "Close").length, 1);
const styles = document.head.children.map(el => el.textContent).join("\n");
assert.match(styles, /\.apex-prompt-dialog-header\s*\{[^}]*position:\s*sticky;[^}]*top:\s*-20px;/);
const rows = findAll(manager, el => el.className === "apex-prompt-row");
assert.equal(rows.length, 8);
for (const row of rows.slice(0, 4)) {
    assert(!find(row, el => el.tag === "button" && el.textContent === "Delete"));
    assert(!find(row, el => el.tag === "button" && el.textContent === "Edit / Rename"));
    assert(find(row, el => el.tag === "button" && el.textContent === "Save a Copy"));
}
for (const row of rows.slice(4)) assert(find(row, el => el.tag === "button" && el.textContent === "Delete"));
instance.onRemoved();
assert.equal(removedCalls, 1);
assert(listeners["apex-presets-changed"]);

// --- New usability coverage: prefill, validation, Save & Use, manager grouping/search ---
const node2 = makeNode();
const editor = module.openEditor(node2, snapshot);
assert.equal(fieldControl(editor.body, "Name").value, "Factory Copy");
assert.equal(fieldControl(editor.body, "Prompt text").value, "factory text");
assert.match(fieldControl(editor.body, "Category").value, /Apex Environment/);
assert(editor.body.children.some(el => el.tag === "small" && /Name: \d+\/120/.test(el.textContent)));

const draftEditor = module.openEditor(makeNode(), snapshot);
const draftRequests = requests.length;
fieldControl(draftEditor.body, "Name").value = "";
fieldControl(draftEditor.body, "Prompt text").value = "some text";
await find(draftEditor.body, el => el.tag === "button" && el.textContent === "Save").click();
assert.match(draftEditor.error.textContent, /name/i);
assert.equal(draftEditor.panel.open, true);
assert.equal(requests.length, draftRequests);
fieldControl(draftEditor.body, "Name").value = "  spaced  ";
await find(draftEditor.body, el => el.tag === "button" && el.textContent === "Save").click();
assert.match(draftEditor.error.textContent, /leading\/trailing|spaces/i);
fieldControl(draftEditor.body, "Name").value = "Valid Name";
fieldControl(draftEditor.body, "Weight — user Random only").value = "abc";
await find(draftEditor.body, el => el.tag === "button" && el.textContent === "Save").click();
assert.match(draftEditor.error.textContent, /Weight/);
assert.equal(requests.length, draftRequests);

const node3 = makeNode();
const useEditor = module.openEditor(node3, snapshot);
fieldControl(useEditor.body, "Name").value = "Applied Preset";
fieldControl(useEditor.body, "Prompt text").value = "applied text";
await find(useEditor.body, el => el.tag === "button" && el.textContent === "Save & Use").click();
assert.equal(useEditor.panel.removed, true);
assert.equal(node3.widgets[0].value, "User: Applied Preset");
assert.equal(JSON.parse(requests.at(-1).options.body).name, "Applied Preset");

const headers = findAll(manager, el => el.tag === "h3");
assert(headers.length >= 2);
const status = find(manager, el => el.tag === "p" && /of \d+ presets/.test(el.textContent || ""));
assert(status);
assert.match(status.textContent, /Showing 8 of 8 presets/);
const searchBox = fieldControl(manager, "Search");
searchBox.value = "user text";
searchBox.listeners.input();
await new Promise(resolve => setTimeout(resolve, 300));
assert.equal(findAll(manager, el => el.className === "apex-prompt-row").length, 4);
const emptyNote = find(manager, el => el.tag === "p" && /No presets match/.test(el.textContent || ""));
assert(!emptyNote);
searchBox.value = "zzz-no-such-preset";
searchBox.listeners.input();
await new Promise(resolve => setTimeout(resolve, 300));
assert.equal(findAll(manager, el => el.className === "apex-prompt-row").length, 0);
assert(find(manager, el => el.tag === "p" && /No presets match/.test(el.textContent || "")));
await managerClose.click();
assert.equal(manager.open, false);
assert.equal(manager.removed, true);
assert.equal(editor.panel.children[0].className, "apex-prompt-dialog-header");
await find(editor.panel.children[0], el => el.tag === "button" && el.textContent === "Close").click();
assert.equal(editor.panel.removed, true);
console.log("PASS: dropdown refresh, missing selections, widget mapping, connected inputs, save/failure draft retention, API payload, lifecycle hooks, factory/user actions, nonserialized buttons and sticky-header Close controls.");