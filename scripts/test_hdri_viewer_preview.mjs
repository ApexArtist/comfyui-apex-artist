/**
 * Throwaway harness: runs the real web/apex_hdri_viewer.js logic under Node with
 * stubbed browser globals to verify socket-image loading + drag rendering.
 */
import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";

const ROOT = path.resolve(import.meta.dirname, "..");
const SRC = path.join(ROOT, "web", "apex_hdri_viewer.js");
const TMP = path.join(ROOT, "scripts", "_hdri_under_test.mjs");

const source = fs.readFileSync(SRC, "utf8");
const withoutImport = source.replace(
    /import \{ app \} from "\.\.\/\.\.\/\.\.\/scripts\/app\.js";/,
    "const app = { registerExtension: (ext) => { globalThis.__registeredExt = ext; } };"
);
if (withoutImport.includes("scripts/app.js")) {
    throw new Error("failed to strip the app.js import");
}
const exportNames = [
    "viewUrlFromItem", "loadSocketSource", "ensureSocketSource", "schedulePreviewRefresh",
    "decodePanorama", "renderLocalFrame", "drawWidgetInner", "previewHeight", "addPreviewWidget",
];
fs.writeFileSync(TMP, withoutImport + "\nexport { " + exportNames.join(", ") + " };\n", "utf8");

// ---------------------------------------------------------------- fake browser
const requestedUrls = [];
class FakeImage {
    constructor() {
        this.naturalWidth = 0;
        this.naturalHeight = 0;
        this.onload = null;
        this.onerror = null;
        this.fail = false;
        this._src = "";
    }
    get src() { return this._src; }
    set src(value) {
        this._src = value;
        requestedUrls.push(value);
        queueMicrotask(() => {
            if (this.fail) { this.onerror?.(); return; }
            this.naturalWidth = 8;
            this.naturalHeight = 4;
            this.onload?.();
        });
    }
}

const renderedFrames = [];
function ctx2d() {
    const noop = () => {};
    return {
        drawImage: noop, save: noop, restore: noop, beginPath: noop, rect: noop,
        clip: noop, fillRect: noop, arc: noop, stroke: noop, fill: noop,
        fillText: noop, moveTo: noop, lineTo: noop, closePath: noop,
        translate: noop, setTransform: noop,
        putImageData: (imageData) => { renderedFrames.push(Uint8ClampedArray.from(imageData.data)); },
        // Deterministic spatial gradient so a pano decode is non-uniform and a
        // yaw change visibly re-samples different source pixels.
        getImageData: (x, y, cw, ch) => {
            const data = new Uint8ClampedArray(cw * ch * 4);
            for (let i = 0, p = 0; i < cw * ch; i++, p += 4) {
                const xx = i % cw;
                const yy = (i / cw) | 0;
                const v = (xx * 7 + yy * 13) % 251;
                data[p] = v; data[p + 1] = (v * 3) % 251; data[p + 2] = (v * 5) % 251; data[p + 3] = 255;
            }
            return { data, width: cw, height: ch };
        },
        createImageData: (cw, ch) => ({ data: new Uint8ClampedArray(cw * ch * 4), width: cw, height: ch }),
    };
}

globalThis.Image = FakeImage;
globalThis.requestAnimationFrame = (cb) => setTimeout(cb, 0);
globalThis.document = {
    createElement(tag) {
        if (tag !== "canvas") return {};
        return { width: 0, height: 0, getContext: () => ctx2d() };
    },
};

const mod = await import(pathToFileURL(TMP).href);

// ------------------------------------------------------------------ fake node
function makeNode() {
    return {
        size: [420, 520],
        widgets: [],
        imgs: undefined,
        drawCalls: 0,
        setDirtyCanvas() { this.drawCalls++; },
        setSize(size) { this.size = size; },
        computeSize: () => [420, 700],
        addCustomWidget(w) { this.widgets.push(w); return w; },
        onExecuted: undefined,
    };
}

const results = [];
function check(name, ok, extra = "") {
    results.push({ name, ok });
    console.log(`${ok ? "PASS" : "FAIL"}  ${name}${extra ? "  -> " + extra : ""}`);
}
const flush = () => new Promise((r) => setTimeout(r, 5));
// ------------------------------------------------------------------- 1. urls
check("ResultItem -> /view url",
    mod.viewUrlFromItem({ filename: "a b.png", subfolder: "sub", type: "output" })
    === "/view?filename=a+b.png&type=output&subfolder=sub",
    mod.viewUrlFromItem({ filename: "a b.png", subfolder: "sub", type: "output" }));
check("HTMLImageElement -> its src",
    mod.viewUrlFromItem({ src: "/view?filename=x.png&type=output" }) === "/view?filename=x.png&type=output");
check("empty item -> null", mod.viewUrlFromItem(undefined) === null);
check("old-bug shape (no filename) -> null", mod.viewUrlFromItem({ subfolder: "", type: "undefined" }) === null);

// ------------------------------------------------------- 2. onExecuted wiring
const node = makeNode();
mod.addPreviewWidget(node);
check("preview widget registered", node.widgets.length === 1 && node._hdriWidget?.name === "hdri_preview");
check("onExecuted hooked", typeof node.onExecuted === "function");
check("node.imgs empty at onExecuted time (frontend fills it later)", node.imgs === undefined);

node.onExecuted({ images: [{ filename: "hdri_input_ab12cd34.png", subfolder: "", type: "output" }] });
check("loads socket image from ui payload",
    requestedUrls.at(-1) === "/view?filename=hdri_input_ab12cd34.png&type=output", String(requestedUrls.at(-1)));

await flush();
const state = node._hdriState;
check("socket image marked loaded", state.socketImageLoaded === true);
check("panorama decoded for local render", !!state.pano && state.pano.width > 0);
check("srcImg retained", !!state.srcImg && state.srcImg.src === requestedUrls.at(-1));
check("no error state", state.error === null, String(state.error));

// ------------------------------------------------------------- 3. drag renders
const widget = node._hdriWidget;
const yawWidget = { name: "yaw", value: 0 };
const pitchWidget = { name: "pitch", value: 0 };
node.widgets.push(yawWidget, pitchWidget);

// ComfyUI draws the node on the next frame; render through the widget like the
// real canvas would, then drag and render again to compare the produced frames.
mod.drawWidgetInner(node, ctx2d(), 420, 40, 260);
const frameBeforeDrag = renderedFrames.length;

widget.mouse({ type: "pointerdown" }, [10, 10], node);
widget.mouse({ type: "pointermove" }, [60, 30], node);
await flush();
check("drag updates yaw/pitch widgets",
    Math.abs(yawWidget.value - 17.5) < 0.001 && Math.abs(pitchWidget.value - -7) < 0.001,
    `yaw=${yawWidget.value} pitch=${pitchWidget.value}`);

mod.drawWidgetInner(node, ctx2d(), 420, 40, 260);
widget.mouse({ type: "pointerup" }, [60, 30], node);

check("drag renders a live local frame", !!state.frameCanvas && state.frameCanvas.width > 0,
    `${state.frameCanvas?.width}x${state.frameCanvas?.height}`);
check("rendered frame changes while dragging",
    renderedFrames.length > frameBeforeDrag &&
    Buffer.compare(Buffer.from(renderedFrames[0]), Buffer.from(renderedFrames.at(-1))) !== 0,
    `frames=${renderedFrames.length}`);
check("renderLocalFrame returns true with decoded pano", mod.renderLocalFrame(node) === true);

let drawOk = true;
try { mod.drawWidgetInner(node, ctx2d(), 420, 40, 260); } catch (e) { drawOk = false; console.log(e); }
check("drawWidgetInner renders during drag", drawOk);

// ------------------------------------- 4. fallback: node.imgs HTMLImageElement
const node2 = makeNode();
mod.addPreviewWidget(node2);
const element = new FakeImage();
element._src = "/view?filename=from-node-imgs.png&type=output";
node2.imgs = [element];
check("ensureSocketSource falls back to node.imgs", mod.ensureSocketSource(node2) === true);
await flush();
check("fallback image decoded", node2._hdriState.socketImageLoaded === true && !!node2._hdriState.pano,
    String(node2._hdriState.socketSrc));

// --------------------------------------------- 5. missing image -> clear error
const node3 = makeNode();
mod.addPreviewWidget(node3);
node3.onExecuted({ images: [] });
check("empty ui payload reports guidance",
    /connect an image/i.test(String(node3._hdriState.error)), String(node3._hdriState.error));

// ------------------------------------------- 6. failed url is not re-requested
globalThis.Image = class extends FakeImage { constructor() { super(); this.fail = true; } };
const node4 = makeNode();
mod.addPreviewWidget(node4);
mod.loadSocketSource(node4, { filename: "broken.png", subfolder: "", type: "output" });
await flush();
check("failed load stores error", node4._hdriState.socketSrcFailed === "/view?filename=broken.png&type=output",
    String(node4._hdriState.error));
mod.loadSocketSource(node4, { filename: "broken.png", subfolder: "", type: "output" });
check("failed url is not retried in a loop",
    requestedUrls.filter((u) => u.includes("broken.png")).length === 1);
globalThis.Image = FakeImage;

// ------------------------------------------------- 7. computeSize consistency
const widgetNode = makeNode();
mod.addPreviewWidget(widgetNode);
const layoutHeight = widgetNode._hdriWidget.computeSize()[1];
const hitHeight = widgetNode._hdriWidget.computeSize(widgetNode.size[0])[1];
check("computeSize stable with and without width", layoutHeight === hitHeight,
    `layout=${layoutHeight} hit=${hitHeight}`);

// ------------------------------------- 8. camera height (flat ground plane)
// Synthetic panorama whose red channel encodes the source row, so the row a
// rendered pixel sampled can be read straight back out of the output frame.
const TEST_PANO = (() => {
    const pw = 256, ph = 128;
    const data = new Uint8ClampedArray(pw * ph * 4);
    for (let yy = 0; yy < ph; yy++) {
        for (let xx = 0; xx < pw; xx++) {
            const p = (yy * pw + xx) * 4;
            data[p] = yy;                 // red = source row, 0 = zenith
            data[p + 3] = 255;
        }
    }
    return { data, width: pw, height: ph };
})();
const TEST_PANO_PH = TEST_PANO.height;
const MID_ROW = (TEST_PANO_PH - 1) / 2;   // equator row = the horizon
const GROUND_PX = 210, GROUND_PY = 250;   // probe ~23deg below the horizon
const SKY_PX = 210, SKY_PY = 60;          // probe ~25deg above it
const CAPTURE_M = 1.6;                    // assumed source capture height

function heightNode(cameraHeight, captureHeight, fov, groundRange) {
    const n = makeNode();
    n.widgets.push(
        { name: "yaw", value: 0 }, { name: "pitch", value: 0 },
        { name: "roll", value: 0 }, { name: "fov", value: fov === undefined ? 90 : fov },
    );
    if (cameraHeight !== undefined) n.widgets.push({ name: "camera_height", value: cameraHeight });
    if (captureHeight !== undefined) n.widgets.push({ name: "capture_height", value: captureHeight });
    // Pure-plane tests pin ground_range = 0 (fade disabled); the fade-range
    // checks below pass explicit ranges instead.
    n.widgets.push({ name: "ground_range", value: groundRange === undefined ? 0 : groundRange });
    n._hdriState = { pano: TEST_PANO, boxW: 420, boxH: 320 };
    return n;
}

// Render, then read the source row that landed on a given output pixel.
function sampledRow(node, px, py) {
    if (!mod.renderLocalFrame(node)) throw new Error("renderLocalFrame returned false");
    const frame = renderedFrames.at(-1);
    const w = node._hdriState.frameCanvas.width;
    return frame[(py * w + px) * 4];
}

// A row maps to a latitude: row 0 is the zenith, row (H-1)/2 the horizon.
const rowToLat = (row) => (0.5 - row / (TEST_PANO_PH - 1)) * Math.PI;
const latToRow = (lat) => (0.5 - lat / Math.PI) * (TEST_PANO_PH - 1);

const rowCentre = sampledRow(heightNode(CAPTURE_M, CAPTURE_M), 210, 160);
check("camera_height == capture_height keeps the capture-point view (identity)",
    Math.abs(rowCentre - MID_ROW) <= 1.5, `row=${rowCentre}, horizon row=${MID_ROW}`);

const rowCentreNoWidgets = sampledRow(heightNode(undefined, undefined), 210, 160);
check("absent height widgets fall back to the capture-point view",
    Math.abs(rowCentreNoWidgets - rowCentre) <= 1, `row=${rowCentreNoWidgets}`);

// Flat ground plane: the camera sees a ray at depression a hit the plane at
// cam*tan(a) from the camera, and the capture point saw that spot (capture
// metres up) at depression atan(capture*tan(a)/cam). That predicted row is the
// independent solution the render must match.
const rowGroundIdentity = sampledRow(heightNode(CAPTURE_M, CAPTURE_M), GROUND_PX, GROUND_PY);
const alpha = -rowToLat(rowGroundIdentity);            // ray depression, radians
const planeRow = (cameraHeight) =>
    latToRow(-Math.atan((CAPTURE_M / cameraHeight) * Math.tan(alpha)));

const rowLowered = sampledRow(heightNode(0.8, CAPTURE_M), GROUND_PX, GROUND_PY);
check("lower camera pulls the ground up with true plane perspective",
    rowLowered > rowGroundIdentity + 8 && Math.abs(rowLowered - planeRow(0.8)) <= 2,
    `row=${rowLowered}, plane solution=${planeRow(0.8).toFixed(1)}`);

const rowRaised = sampledRow(heightNode(3.2, CAPTURE_M), GROUND_PX, GROUND_PY);
check("higher camera pushes the ground away",
    rowRaised < rowGroundIdentity - 5 && Math.abs(rowRaised - planeRow(3.2)) <= 2,
    `row=${rowRaised}, plane solution=${planeRow(3.2).toFixed(1)}`);

// The sky is at infinity, so a height change must not touch it. No rotation can
// move the ground while leaving the sky fixed, which makes this positional.
const rowSkyIdentity = sampledRow(heightNode(CAPTURE_M, CAPTURE_M), SKY_PX, SKY_PY);
const rowSkyLowered = sampledRow(heightNode(0.8, CAPTURE_M), SKY_PX, SKY_PY);
check("sky stays put while the ground moves (positional, not a rotation)",
    Math.abs(rowSkyLowered - rowSkyIdentity) <= 1 &&
    Math.abs(rowLowered - rowGroundIdentity) > 8,
    `sky ${rowSkyIdentity}->${rowSkyLowered}, ground ${rowGroundIdentity}->${rowLowered}`);

// Flat-plane ground also anchors the horizon itself: at 5cm eye height the ground
// rushes toward the horizon (a huge shift) while the horizon row barely budges.
const rowGroundFloor = sampledRow(heightNode(0.05, CAPTURE_M), GROUND_PX, GROUND_PY);
const rowCentreFloor = sampledRow(heightNode(0.05, CAPTURE_M), 210, 160);
check("horizon stays anchored at ground level",
    rowGroundFloor - rowGroundIdentity > 15 && Math.abs(rowCentreFloor - rowCentre) <= 5,
    `ground ${rowGroundIdentity}->${rowGroundFloor}, horizon ${rowCentre}->${rowCentreFloor}`);

// ground_range fades the plane back to the untouched dome: near ground follows
// the pure-plane solution, far ground returns to the identity sample. The test
// probes two rays - a steep near-ground ray and a grazing far-ground ray - at a
// small range (2 m) so the near hit sits inside the fade and the far hit outside.
const FADE_CAM = 0.8;
const planeRowUnfaded = (cameraHeight, identityRow) => {
    const a = -rowToLat(identityRow);
    return latToRow(-Math.atan((CAPTURE_M / cameraHeight) * Math.tan(a)));
};
const rowNearIdentity = sampledRow(heightNode(CAPTURE_M, CAPTURE_M, undefined, 2), 210, 250);
const rowNearFaded = sampledRow(heightNode(FADE_CAM, CAPTURE_M, undefined, 2), 210, 250);
const rowFarIdentity = sampledRow(heightNode(CAPTURE_M, CAPTURE_M, undefined, 2), 210, 165);
const rowFarFaded = sampledRow(heightNode(FADE_CAM, CAPTURE_M, undefined, 2), 210, 165);
const expectNear = planeRowUnfaded(FADE_CAM, rowNearIdentity);
check("ground_range keeps near ground on the plane while fading the far field",
    Math.abs(rowNearFaded - expectNear) <= 4 && Math.abs(rowFarFaded - rowFarIdentity) <= 6,
    `near faded=${rowNearFaded} vs plane=${expectNear.toFixed(1)}, far faded=${rowFarFaded} vs identity=${rowFarIdentity}`);
const rowFarZero = sampledRow(heightNode(FADE_CAM, CAPTURE_M, undefined, 0), 210, 175);
check("ground_range = 0 disables the fade (far ground stays remapped)",
    Math.abs(rowFarZero - rowFarIdentity) >= 3,
    `far unfaded=${rowFarZero} vs identity=${rowFarIdentity}`);

// ------------------------------------------------------------------- summary
const failed = results.filter((r) => !r.ok);
console.log(`\n${results.length - failed.length}/${results.length} checks passed`);
fs.rmSync(TMP, { force: true });
process.exit(failed.length ? 1 : 0);