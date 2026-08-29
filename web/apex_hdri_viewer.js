import { app } from "../../../scripts/app.js";

const DRAG_SENSITIVITY = 0.35;
const FOV_WHEEL_STEP = 3;
const PREVIEW_MIN_H = 360;
const PREVIEW_MAX_H = 720;
const PREVIEW_DEFAULT_H = 420;
const PREVIEW_MIN_W = 420;
const RENDER_MAX_W = 480;      // internal render resolution cap (upscaled on draw)
const PANO_MAX_W = 2048;       // decode cap for the source panorama

function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
}

function wrapAngle(deg) {
    while (deg > 180) deg -= 360;
    while (deg < -180) deg += 360;
    return deg;
}

function findWidget(node, name) {
    return node.widgets?.find((w) => w.name === name);
}

function getWidgetValue(node, name, fallback) {
    const w = findWidget(node, name);
    return w ? Number(w.value) : fallback;
}

function setWidgetValue(node, name, value) {
    const widget = findWidget(node, name);
    if (!widget) return;
    const rounded = Math.round(value * 1000) / 1000;
    if (widget.value === rounded) return;
    widget.value = rounded;
    node.setDirtyCanvas?.(true, true);
}

function commitWidgetChange(node) {
    const names = ["yaw", "pitch", "roll", "fov"];
    for (const name of names) {
        const widget = findWidget(node, name);
        widget?.callback?.(Number(widget.value));
    }
    node.setDirtyCanvas?.(true, true);
}

function previewHeight(w, node) {
    return clamp(PREVIEW_DEFAULT_H, PREVIEW_MIN_H, PREVIEW_MAX_H);
}

function fmtDeg(v) {
    return Number(v).toFixed(1) + "\u00B0";
}

function buildPreviewUrl(node) {
    const name = findWidget(node, "hdri_image")?.value;
    if (!name) return null;
    const qs = new URLSearchParams();
    qs.set("filename", String(name));
    qs.set("yaw", getWidgetValue(node, "yaw", 0));
    qs.set("pitch", getWidgetValue(node, "pitch", 0));
    qs.set("roll", getWidgetValue(node, "roll", 0));
    qs.set("fov", getWidgetValue(node, "fov", 90));
    qs.set("lens", String(findWidget(node, "lens_type")?.value ?? "rectilinear"));
    return "/apex/hdri_preview?" + qs.toString();
}

function buildRawUrl(node) {
    const name = findWidget(node, "hdri_image")?.value;
    if (!name) return null;
    return "/view?filename=" + encodeURIComponent(String(name)) + "&type=input&subfolder=";
}

// Decode the source panorama locally for realtime rendering. Works for
// browser-decodable formats (jpg/png/webp); .hdr/.exr fall back to the
// server-rendered snapshot.
function decodePanorama(node, img) {
    const state = (node._hdriState = node._hdriState || {});
    try {
        const iw = img.naturalWidth || img.width;
        const ih = img.naturalHeight || img.height;
        if (!iw || !ih) throw new Error("empty image");
        const scale = Math.min(1, PANO_MAX_W / iw);
        const w = Math.max(4, Math.round(iw * scale));
        const h = Math.max(4, Math.round(ih * scale));
        const cv = document.createElement("canvas");
        cv.width = w; cv.height = h;
        const cx = cv.getContext("2d", { willReadFrequently: true });
        cx.drawImage(img, 0, 0, w, h);
        const data = cx.getImageData(0, 0, w, h).data;
        state.pano = { data, width: w, height: h };
    } catch (e) {
        state.pano = null; // tainted canvas or decode failure -> server mode
    }
}

// Server snapshot: final quality sync + .hdr/.exr support.
let refreshTimer = null;
let loadToken = 0;

function schedulePreviewRefresh(node) {
    clearTimeout(refreshTimer);
    refreshTimer = setTimeout(() => { loadPreview(node); }, 150);
}

function loadPreview(node) {
    const url = buildPreviewUrl(node);
    const state = (node._hdriState = node._hdriState || {});
    if (!url) { state.error = "No image selected"; node.setDirtyCanvas?.(true, true); return; }
    const sep = url.indexOf("?") >= 0 ? "&" : "?";
    const src = url + sep + "ts=" + Date.now();
    if (state.serverSrc === src) return;
    state.serverSrc = src;
    const token = ++loadToken;
    const img = new Image();
    img.onload = () => {
        if (token !== loadToken) return;
        state.serverImg = img;
        node.setDirtyCanvas?.(true, true);
    };
    img.onerror = () => { if (token === loadToken) state.serverImg = null; };
    img.src = src;
}

function loadSource(node) {
    const state = (node._hdriState = node._hdriState || {});
    const raw = buildRawUrl(node);
    if (!raw) { state.pano = null; state.srcImg = null; return; }
    const img = new Image();
    img.onload = () => {
        state.srcImg = img;
        decodePanorama(node, img);
        node.setDirtyCanvas?.(true, true);
    };
    img.onerror = () => {
        state.srcImg = null;
        state.pano = null;
        state.error = "Could not load the panorama image.";
        node.setDirtyCanvas?.(true, true);
    };
    img.src = raw;
}

// Realtime local renderer: equirect -> perspective reprojection in JS.
// Ray unit vectors depend only on size/fov/roll (precomputed); per frame we
// rotate them by pitch (about camera X) and yaw (about world Y), matching the
// backend rotation order R = Ry @ Rx @ Rz, then convert to equirect lon/lat.
function ensureRayMap(state, w, h, fovDeg, rollDeg) {
    const key = w + "x" + h + "|" + fovDeg.toFixed(2) + "|" + rollDeg.toFixed(2);
    if (state.rayKey === key) return;
    state.rayKey = key;
    const fovR = (fovDeg * Math.PI) / 180;
    const rollR = (rollDeg * Math.PI) / 180;
    const f = w / 2 / Math.tan(fovR / 2);
    const cosR = Math.cos(rollR), sinR = Math.sin(rollR);
    const rx = new Float32Array(w * h);
    const ryy = new Float32Array(w * h);
    const rz = new Float32Array(w * h);
    let i = 0;
    for (let yy = 0; yy < h; yy++) {
        const dy = h / 2 - yy - 0.5;            // screen y down; camera up is +y
        for (let xx = 0; xx < w; xx++, i++) {
            const dx = xx - w / 2 + 0.5;
            const a = dx * cosR - dy * sinR;    // roll in screen plane
            const b = dx * sinR + dy * cosR;
            const wx = a, wy = b, wz = -f;      // camera forward is -Z
            const len = Math.hypot(wx, wy, wz);
            rx[i] = wx / len; ryy[i] = wy / len; rz[i] = wz / len;
        }
    }
    state.rayX = rx; state.rayY = ryy; state.rayZ = rz;
}

function renderLocalFrame(node) {
    const state = node._hdriState;
    const pano = state && state.pano;
    if (!pano) return false;
    const boxW = Math.max(64, Math.round(state.boxW || 420));
    const boxH = Math.max(64, Math.round(state.boxH || 320));
    const scale = Math.min(1, RENDER_MAX_W / boxW);
    const w = Math.max(32, Math.round(boxW * scale));
    const h = Math.max(32, Math.round(boxH * scale));

    if (!state.frameCanvas || state.frameCanvas.width !== w || state.frameCanvas.height !== h) {
        state.frameCanvas = document.createElement("canvas");
        state.frameCanvas.width = w;
        state.frameCanvas.height = h;
        state.frameCtx = state.frameCanvas.getContext("2d");
        state.frameData = state.frameCtx.createImageData(w, h);
        state.rayKey = null;
    }

    ensureRayMap(state, w, h, getWidgetValue(node, "fov", 90), getWidgetValue(node, "roll", 0));

    const yawR = (getWidgetValue(node, "yaw", 0) * Math.PI) / 180;
    const pitchR = (getWidgetValue(node, "pitch", 0) * Math.PI) / 180;
    const pw = pano.width, ph = pano.height, sd = pano.data;
    const out = state.frameData.data;
    const rayX = state.rayX, rayY = state.rayY, rayZ = state.rayZ;
    const TWO_PI = Math.PI * 2;

    // Rotate camera-space rays to world space: R = Ry(yaw) @ Rx(pitch),
    // matching the backend (_rotation_matrix with roll pre-applied to rays).
    const cy = Math.cos(yawR), sy = Math.sin(yawR);
    const cp = Math.cos(pitchR), sp = Math.sin(pitchR);

    for (let i = 0, p = 0; i < w * h; i++, p += 4) {
        const x0r = rayX[i], y0r = rayY[i], z0r = rayZ[i];
        // Pitch: rotate about camera X axis (Rx @ ray)
        const y1 = y0r * cp - z0r * sp;
        const z1 = y0r * sp + z0r * cp;
        // Yaw: rotate about world Y axis (Ry @ ray)
        const wx = x0r * cy + z1 * sy;
        const wy = y1;
        const wz = -x0r * sy + z1 * cy;

        // Equirect mapping: lon = atan2(dx, -dz), lat = asin(dy)
        const lon = Math.atan2(wx, -wz);
        const lat = Math.asin(wy < -1 ? -1 : wy > 1 ? 1 : wy);

        let u = lon / TWO_PI + 0.5;
        u -= Math.floor(u);
        const fx = u * pw;
        const sx0 = fx | 0;
        const sx1 = (sx0 + 1) % pw;
        const tx = fx - sx0;

        const v = 0.5 - lat / Math.PI;   // 0..1, 0 = top
        const fy = v * (ph - 1);
        const sy0 = fy | 0;
        const sy1 = sy0 < ph - 1 ? sy0 + 1 : sy0;
        const ty = fy - sy0;

        const r0 = (sy0 * pw + sx0) * 4;
        const r1 = (sy0 * pw + sx1) * 4;
        const r2 = (sy1 * pw + sx0) * 4;
        const r3 = (sy1 * pw + sx1) * 4;
        const topw = 1 - tx, botw = 1 - ty;
        out[p]     = sd[r0] * topw * botw + sd[r1] * tx * botw + sd[r2] * topw * ty + sd[r3] * tx * ty;
        out[p + 1] = sd[r0 + 1] * topw * botw + sd[r1 + 1] * tx * botw + sd[r2 + 1] * topw * ty + sd[r3 + 1] * tx * ty;
        out[p + 2] = sd[r0 + 2] * topw * botw + sd[r1 + 2] * tx * botw + sd[r2 + 2] * topw * ty + sd[r3 + 2] * tx * ty;
        out[p + 3] = 255;
    }
    state.frameCtx.putImageData(state.frameData, 0, 0);
    return true;
}

// Draw an image filling the box (cover) without distortion.
function drawImageCover(ctx, img, x, y, w, h) {
    const iw = img.naturalWidth || img.width;
    const ih = img.naturalHeight || img.height;
    if (!iw || !ih) return;
    const scale = Math.max(w / iw, h / ih);
    const dw = iw * scale;
    const dh = ih * scale;
    ctx.drawImage(img, x + (w - dw) / 2, y + (h - dh) / 2, dw, dh);
}

function drawWidget(node, ctx, width, y, height) {
    try {
        drawWidgetInner(node, ctx, width, y, height);
    } catch (e) {
        ctx.fillStyle = "#1b1b22";
        ctx.fillRect(0, y, width, height);
        ctx.fillStyle = "#e0b34f";
        ctx.font = "12px Arial";
        ctx.textAlign = "center";
        ctx.fillText("Preview error: " + String(e && e.message ? e.message : e), width / 2, y + height / 2);
        ctx.textAlign = "left";
    }
}

function drawWidgetInner(node, ctx, width, y, height) {
    const state = (node._hdriState = node._hdriState || {});
    state.boxW = width;
    state.boxH = height;
    ctx.fillStyle = "#1b1b22";
    ctx.fillRect(0, y, width, height);

    ctx.save();
    ctx.beginPath();
    ctx.rect(0, y, width, height);
    ctx.clip();

    const hasLocal = renderLocalFrame(node);
    if (hasLocal) {
        ctx.imageSmoothingEnabled = true;
        drawImageCover(ctx, state.frameCanvas, 0, y, width, height);
    } else if (state.serverImg) {
        drawImageCover(ctx, state.serverImg, 0, y, width, height);
    } else if (state.srcImg) {
        drawImageCover(ctx, state.srcImg, 0, y, width, height);
    } else if (state.error) {
        ctx.fillStyle = "#e0b34f";
        ctx.font = "13px Arial";
        ctx.textAlign = "center";
        ctx.fillText(state.error, width / 2, y + height / 2);
        ctx.textAlign = "left";
    } else {
        ctx.fillStyle = "#888";
        ctx.font = "14px Arial";
        ctx.textAlign = "center";
        ctx.fillText("Select an image", width / 2, y + height / 2);
        ctx.textAlign = "left";
    }

    // Center drag ring + dot.
    const cx = width / 2, cy = y + height / 2;
    ctx.strokeStyle = "rgba(255,255,255,0.75)";
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.arc(cx, cy, 15, 0, Math.PI * 2);
    ctx.stroke();
    ctx.fillStyle = "rgba(255,255,255,0.9)";
    ctx.beginPath();
    ctx.arc(cx, cy, 2.5, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();

    // HUD overlay.
    const hud =
        "Yaw " + fmtDeg(getWidgetValue(node, "yaw", 0)) +
        "  Pitch " + fmtDeg(getWidgetValue(node, "pitch", 0)) +
        "  Roll " + fmtDeg(getWidgetValue(node, "roll", 0)) +
        "  FOV " + getWidgetValue(node, "fov", 90).toFixed(0) + "\u00B0";
    ctx.fillStyle = "rgba(0,0,0,0.55)";
    ctx.fillRect(0, y + height - 20, width, 20);
    ctx.fillStyle = "#ddd";
    ctx.font = "11px monospace";
    ctx.textAlign = "left";
    ctx.fillText(hud, 6, y + height - 6);
    ctx.textAlign = "left";
}

function addPreviewWidget(node) {
    if (node._hdriWidget) return;
    node._hdriState = node._hdriState || {};
    loadSource(node);
    loadPreview(node);
    let dragging = false;
    let lastPos = null;
    let rafPending = false;

    // rAF-throttled local redraw: realtime without flooding the canvas.
    function requestRender(n) {
        if (rafPending) return;
        rafPending = true;
        requestAnimationFrame(() => {
            rafPending = false;
            n.setDirtyCanvas?.(true, false);
        });
    }

    const widget = node.addCustomWidget({
        name: "hdri_preview",
        type: "hdri_preview",
        computeSize: (w) => [w ?? 200, previewHeight(w, node)],
        draw: (ctx, node, width, y, height) => {
            const computed = node._hdriWidget?.computedHeight;
            const h = Math.max(Number(computed) || 0, height || 0) - 4;
            drawWidget(node, ctx, width, y, Math.max(h, 60));
        },
        mouse: (event, pos, node) => {
            const t = event.type;
            if (t === "pointerdown" || t === "mousedown") {
                dragging = true;
                lastPos = [pos[0], pos[1]];
                return true;
            }
            if ((t === "pointermove" || t === "mousemove") && dragging && lastPos) {
                const dx = pos[0] - lastPos[0];
                const dy = pos[1] - lastPos[1];
                if (event.shiftKey) {
                    setWidgetValue(node, "roll", clamp(getWidgetValue(node, "roll", 0) + dx * DRAG_SENSITIVITY, -180, 180));
                } else {
                    setWidgetValue(node, "yaw", wrapAngle(getWidgetValue(node, "yaw", 0) + dx * DRAG_SENSITIVITY));
                    setWidgetValue(node, "pitch", clamp(getWidgetValue(node, "pitch", 0) - dy * DRAG_SENSITIVITY, -89, 89));
                }
                lastPos = [pos[0], pos[1]];
                requestRender(node);          // realtime local frame
                schedulePreviewRefresh(node); // server sync while dragging
                return true;
            }
            if (t === "pointerup" || t === "mouseup" || t === "pointerleave" || t === "blur") {
                if (dragging) {
                    commitWidgetChange(node);
                    schedulePreviewRefresh(node);
                }
                dragging = false;
                lastPos = null;
                return true;
            }
            if (t === "wheel") {
                const fov = clamp(getWidgetValue(node, "fov", 90) - Math.sign(event.deltaY) * FOV_WHEEL_STEP, 10, 179);
                setWidgetValue(node, "fov", fov);
                commitWidgetChange(node);
                requestRender(node);
                schedulePreviewRefresh(node);
                return true;
            }
            return false;
        },
    });
    node._hdriWidget = widget;

    // Ensure the node is large enough for a wide, natural preview panel.
    const minW = Math.max(PREVIEW_MIN_W, node.size ? node.size[0] : 0);
    const size = node.computeSize ? node.computeSize([minW, node.size ? node.size[1] : 0]) : null;
    const newW = Math.max(minW, size ? size[0] : 0);
    const newH = Math.max(size ? size[1] : 0, node.size ? node.size[1] : 0);
    if (node.setSize && (newW > node.size[0] || newH > node.size[1])) {
        node.setSize([newW, newH]);
    }
    node.setDirtyCanvas?.(true, true);

    // Reload the source when the image selection changes.
    for (const name of ["hdri_image"]) {
        const wt = findWidget(node, name);
        if (wt && !wt._hdriHooked) {
            const orig = wt.callback;
            wt.callback = function (...args) {
                loadSource(node);
                loadPreview(node);
                node.setDirtyCanvas?.(true, true);
                return orig?.apply(this, args);
            };
            wt._hdriHooked = true;
        }
    }
}

app.registerExtension({
    name: "ApexArtist.HDRIViewer",
    nodeCreated(node) {
        if (node.comfyClass === "ApexHDRIViewer") {
            addPreviewWidget(node);
        }
    }
});
