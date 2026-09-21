/** Dependency-free regression tests for the socket-based HDRI preview. */
import fs from "node:fs";
import assert from "node:assert/strict";

const pending = [];
globalThis.Image = class {
    naturalWidth = 16;
    naturalHeight = 8;
    set src(value) { this._src = value; pending.push(this); }
    get src() { return this._src; }
};
globalThis.requestAnimationFrame = (callback) => setTimeout(callback, 0);
const context = () => ({
    drawImage() {},
    getImageData(x, y, width, height) {
        return { data: Uint8ClampedArray.from({ length: width * height * 4 }, (_, i) =>
            i % 4 === 3 ? 255 : ((i / 4 | 0) % width) * 8) };
    },
    createImageData(width, height) { return { data: new Uint8ClampedArray(width * height * 4) }; },
    putImageData() {},
});
globalThis.document = { createElement: () => ({ getContext: context }) };
const file = new URL("../web/apex_hdri_viewer.js", import.meta.url);
const source = fs.readFileSync(file, "utf8").replace(
    /import \{ app \} from "[^"]+";/,
    "const app = { registerExtension() {} };"
);
const mod = await import("data:text/javascript;base64," + Buffer.from(source +
    "\nexport { addPreviewWidget, loadSocketSource, ensureSocketSource, renderLocalFrame, schedulePreviewRefresh, viewUrlFromItem, ensureRayMap };").toString("base64"));
function node() {
    const n = {
        size: [500, 800], dirty: 0,
        widgets: Object.entries({ yaw: 0, pitch: 0, roll: 0, fov: 90,
            lens_type: "rectilinear", exposure: 0, output_width: 128, output_height: 64 })
            .map(([name, value]) => ({ name, value })),
        addCustomWidget(w) { this.widgets.push(w); return w; },
        setDirtyCanvas() { this.dirty++; },
        computeSize() { return this.size; },
        setSize(size) { this.size = size; },
    };
    mod.addPreviewWidget(n);
    return n;
}
const item = (filename) => ({ filename, type: "temp", subfolder: "" });
const payload = (filename) => ({ hdri_source: [item(filename)], hdri_source_scale: [1],
    images: [item("front.png"), item("back.png")] });
let checks = 0;
function test(name, fn) { fn(); checks++; console.log("PASS", name); }
const a = node(), b = node();
test("source metadata, not projected outputs, drives preview", () => {
    a.onExecuted(payload("pano.png"));
    assert.match(pending.at(-1).src, /filename=pano.png/);
    pending.at(-1).onload();
    assert.ok(a._hdriState.pano);
    assert.equal(a._hdriState.error, null);
});
test("projected node.imgs is never a panorama fallback", () => {
    b.imgs = [{ src: "/view?filename=front.png" }];
    assert.equal(mod.ensureSocketSource(b), false);
    b.onExecuted({ images: [item("front.png")] });
    assert.match(b._hdriState.error, /Connect an IMAGE/);
});
test("nodes load independently and stale loads cannot replace the source", () => {
    a.onExecuted(payload("old.png")); const old = pending.at(-1);
    a.onExecuted(payload("new.png")); const latest = pending.at(-1);
    b.onExecuted(payload("other.png")); const other = pending.at(-1);
    latest.onload(); other.onload(); old.onload();
    assert.equal(a._hdriState.srcImg, latest);
    assert.equal(b._hdriState.srcImg, other);
});
test("failed loads do not loop and a new execution retries", () => {
    a.onExecuted(payload("bad.png")); pending.at(-1).onerror();
    const count = pending.length;
    mod.ensureSocketSource(a); mod.ensureSocketSource(a);
    assert.equal(pending.length, count);
    a.onExecuted(payload("bad.png"));
    assert.equal(pending.length, count + 1);
    pending.at(-1).onload();
});
test("drag changes orientation and preview pixels", () => {
    mod.renderLocalFrame(a);
    const before = a._hdriState.frameData.data.slice();
    a._hdriWidget.mouse({ type: "pointerdown" }, [10, 10], a);
    a._hdriWidget.mouse({ type: "pointermove" }, [60, 30], a);
    a._hdriWidget.mouse({ type: "pointerup" }, [60, 30], a);
    assert.equal(a.widgets.find(w => w.name === "yaw").value, 17.5);
    assert.equal(a.widgets.find(w => w.name === "pitch").value, -7);
    mod.renderLocalFrame(a);
    assert.notDeepEqual(a._hdriState.frameData.data, before);
});
test("preview respects output aspect ratio and lens changes", () => {
    const state = a._hdriState;
    assert.equal(state.frameCanvas.width / state.frameCanvas.height, 2);
    const before = state.frameData.data.slice();
    a.widgets.find(w => w.name === "lens_type").value = "fisheye";
    mod.renderLocalFrame(a);
    assert.notDeepEqual(state.frameData.data, before);
});
test("exposure and HDR source scale both affect the local preview", () => {
    const state = a._hdriState;
    const before = state.frameData.data.slice();
    a.widgets.find(w => w.name === "exposure").value = -1;
    mod.renderLocalFrame(a);
    assert.ok(state.frameData.data[0] < before[0]);
    state.sourceScale = 2;
    mod.renderLocalFrame(a);
    assert.deepEqual(state.frameData.data, before);
});
test("rays match backend endpoint convention", () => {
    const state = {};
    mod.ensureRayMap(state, 3, 3, 90, 0, "rectilinear", 1);
    assert.ok(Math.abs(state.rayX[0] + 1 / Math.sqrt(3)) < 1e-6);
    assert.equal(state.rayZ[4], -1);
    mod.ensureRayMap(state, 3, 3, 90, 0, "fisheye", 1);
    assert.ok(Math.abs(state.rayZ[0] + Math.SQRT1_2) < 1e-6);
});
test("URLs escape special characters and preview widgets do not serialize", () => {
    const url = mod.viewUrlFromItem({ filename: "a & b.png", type: "temp", subfolder: "x/y & z" });
    const params = new URL(url, "http://localhost").searchParams;
    assert.equal(params.get("filename"), "a & b.png");
    assert.equal(params.get("subfolder"), "x/y & z");
    assert.equal(a._hdriWidget.options.serialize, false);
    assert.deepEqual(a.size, [500, 800]);
});
mod.schedulePreviewRefresh(a); mod.schedulePreviewRefresh(b);
const ad = a.dirty, bd = b.dirty;
await new Promise(resolve => setTimeout(resolve, 180));
test("refresh timers are per node", () => { assert.ok(a.dirty > ad); assert.ok(b.dirty > bd); });
test("removal rejects pending image loads", () => {
    a.onExecuted(payload("late.png")); const late = pending.at(-1);
    a.onRemoved(); late.onload();
    assert.equal(a._hdriState.pano, null);
});
b.onRemoved();
console.log(`${checks} HDRI frontend regressions passed`);