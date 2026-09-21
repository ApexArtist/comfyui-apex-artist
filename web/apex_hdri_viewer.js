import { app } from "../../../scripts/app.js";

const DRAG_SENSITIVITY = 0.35;
const FOV_WHEEL_STEP = 3;
const PREVIEW_MIN_H = 360;
const PREVIEW_MAX_H = 720;
const PREVIEW_DEFAULT_H = 420;
const PREVIEW_MIN_W = 420;
const RENDER_MAX_W = 480;      // internal render resolution cap (upscaled on draw)
const PANO_MAX_W = 2048;       // decode cap for the source panorama
const PREVIEW_REFRESH_DEBOUNCE_MS = 100;  // 10 req/sec max during drag

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
        const cx = cv.getContext("2d");  // Default context for single-read decode
        cx.drawImage(img, 0, 0, w, h);
        const data = cx.getImageData(0, 0, w, h).data;
        state.pano = { data, width: w, height: h };
    } catch (e) {
        state.pano = null; // tainted canvas or decode failure -> server mode
    }
}

function viewUrlFromItem(item) {
    if (!item?.filename) return item?.src || null;
    const params = new URLSearchParams({ filename: item.filename, type: item.type || "temp" });
    if (item.subfolder) params.set("subfolder", item.subfolder);
    const url = "/view?" + params;
    return app.api?.apiURL ? app.api.apiURL(url) : url;
}

function loadSocketSource(node, item) {
    const state = (node._hdriState ||= {});
    const url = viewUrlFromItem(item);
    if (!url || state.removed) return false;
    if (state.socketSrc === url) return true;
    state.socketSrc = url;
    state.socketImageLoaded = false;
    state.pano = null;
    state.srcImg = null;
    state.error = "Loading panorama…";
    const token = state.loadToken = (state.loadToken || 0) + 1;
    const img = new Image();
    img.onload = () => {
        if (state.removed || state.loadToken !== token) return;
        state.srcImg = img;
        decodePanorama(node, img);
        state.socketImageLoaded = !!state.pano;
        state.error = state.pano ? null : "Could not decode the panorama preview.";
        node.setDirtyCanvas?.(true, true);
    };
    img.onerror = () => {
        if (state.removed || state.loadToken !== token) return;
        state.socketSrcFailed = url;
        state.error = "Could not load panorama. Run the workflow again.";
        node.setDirtyCanvas?.(true, true);
    };
    img.src = url;
    return true;
}

function ensureSocketSource(node) {
    // Never use node.imgs: those are projected outputs, not panoramas.
    return loadSocketSource(node, node._hdriState?.sourceItem);
}

function schedulePreviewRefresh(node) {
    const state = (node._hdriState ||= {});
    clearTimeout(state.refreshTimer);
    state.refreshTimer = setTimeout(() => {
        if (!state.removed) node.setDirtyCanvas?.(true, true);
    }, PREVIEW_REFRESH_DEBOUNCE_MS);
}

// Realtime local renderer: equirect -> perspective reprojection in JS.
// Ray unit vectors depend only on size/fov/roll (precomputed); per frame we
// rotate them by pitch (about camera X) and yaw (about world Y), matching the
// backend rotation order R = Ry @ Rx @ Rz, then convert to equirect lon/lat.
function ensureRayMap(state, w, h, fovDeg, rollDeg, lens, aspect) {
    const key = [w, h, fovDeg, rollDeg, lens, aspect].join("|");
    if (state.rayKey === key) return;
    state.rayKey = key;
    const fovR = (fovDeg * Math.PI) / 180;
    const rollR = (rollDeg * Math.PI) / 180;
    const cosR = Math.cos(rollR), sinR = Math.sin(rollR);
    const rx = new Float32Array(w * h);
    const ryy = new Float32Array(w * h);
    const rz = new Float32Array(w * h);
    let i = 0;
    for (let yy = 0; yy < h; yy++) {
        const gy = 1 - 2 * yy / (h - 1);
        for (let xx = 0; xx < w; xx++, i++) {
            const gx = 2 * xx / (w - 1) - 1;
            let dx = gx * Math.tan(fovR / 2);
            let dy = gy * Math.tan(fovR / 2) * aspect;
            let wz = -1;
            if (lens === "fisheye") {
                const theta = Math.min(1, Math.hypot(gx, gy)) * fovR / 2;
                const phi = Math.atan2(gy, gx);
                dx = Math.sin(theta) * Math.cos(phi);
                dy = Math.sin(theta) * Math.sin(phi);
                wz = -Math.cos(theta);
            }
            const wx = dx * cosR - dy * sinR;
            const wy = dx * sinR + dy * cosR;
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
    const ow = getWidgetValue(node, "output_width", boxW);
    const oh = getWidgetValue(node, "output_height", boxH);
    const scale = Math.min(boxW / ow, boxH / oh, RENDER_MAX_W / Math.max(ow, oh));
    const w = Math.max(2, Math.round(ow * scale));
    const h = Math.max(2, Math.round(oh * scale));

    if (!state.frameCanvas || state.frameCanvas.width !== w || state.frameCanvas.height !== h) {
        state.frameCanvas = document.createElement("canvas");
        state.frameCanvas.width = w;
        state.frameCanvas.height = h;
        state.frameCtx = state.frameCanvas.getContext("2d");
        state.frameData = state.frameCtx.createImageData(w, h);
        state.rayKey = null;
    }

    ensureRayMap(state, w, h, getWidgetValue(node, "fov", 90), getWidgetValue(node, "roll", 0),
        findWidget(node, "lens_type")?.value || "rectilinear", oh / ow);
    const gain = (state.sourceScale || 1) * 2 ** getWidgetValue(node, "exposure", 0);

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
        const fx = u * (pw - 1);
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
        out[p + 3] = 255;
        // Apply gain before Uint8ClampedArray truncation/clipping.
        for (let channel = 0; channel < 3; channel++) {
            out[p + channel] = gain * (sd[r0 + channel] * topw * botw +
                sd[r1 + channel] * tx * botw + sd[r2 + channel] * topw * ty + sd[r3 + channel] * tx * ty);
        }
    }
    state.frameCtx.putImageData(state.frameData, 0, 0);
    return true;
}

// Fit the complete output in the preview without cropping or distortion.
function drawImageCover(ctx, img, x, y, w, h) {
    const iw = img.naturalWidth || img.width;
    const ih = img.naturalHeight || img.height;
    if (!iw || !ih) return;
    const scale = Math.min(w / iw, h / ih);
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
        ctx.fillText("Connect an IMAGE and run the workflow to preview", width / 2, y + height / 2);
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
    // Add onExecuted hook to load socket images
    const origExecuted = node.onExecuted;
    node.onExecuted = function(message) {
        if (origExecuted) origExecuted.apply(this, arguments);

        const state = node._hdriState;
        state.sourceItem = message?.hdri_source?.[0];
        state.sourceScale = Number(message?.hdri_source_scale?.[0]) || 1;
        state.socketSrc = null;
        state.loadToken = (state.loadToken || 0) + 1;
        state.pano = state.srcImg = null;
        state.socketImageLoaded = false;
        state.error = "Connect an IMAGE and run the workflow to preview";
        ensureSocketSource(node);
        node.setDirtyCanvas?.(true, true);
    };

    const origRemoved = node.onRemoved;
    node.onRemoved = function (...args) {
        node._hdriState.removed = true;
        clearTimeout(node._hdriState.refreshTimer);
        node._hdriState.pano = node._hdriState.srcImg = null;
        return origRemoved?.apply(this, args);
    };
    let dragging = false;
    let lastPos = null;
    let rafPending = false;

    // rAF-throttled local redraw: realtime without flooding the canvas.
    function requestRender(n) {
        if (rafPending) return;
        rafPending = true;
        requestAnimationFrame(() => {
            rafPending = false;
            if (!n._hdriState.removed) n.setDirtyCanvas?.(true, false);
        });
    }

    const widget = node.addCustomWidget({
        name: "hdri_preview",
        type: "hdri_preview",
        serialize: false,
        options: { serialize: false },
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

    // Numeric edits use the same local renderer as dragging.
    for (const name of ["yaw", "pitch", "roll", "fov", "lens_type", "exposure", "output_width", "output_height"]) {
        const wt = findWidget(node, name);
        if (wt && !wt._hdriHooked) {
            const orig = wt.callback;
            wt.callback = function (...args) {
                const result = orig?.apply(this, args);
                node.setDirtyCanvas?.(true, true);
                return result;
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
