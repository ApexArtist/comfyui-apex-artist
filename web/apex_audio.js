import { app } from "../../../scripts/app.js";
import { api } from "../../../scripts/api.js";

const style = document.createElement("style");
style.textContent = `
.apex-audio-editor{box-sizing:border-box;width:100%;min-width:0;padding:10px;color:var(--input-text,#ddd);font:12px/1.4 system-ui;background:var(--comfy-menu-bg,#242424);border-radius:8px;display:flex;flex-direction:column;gap:8px}
.apex-audio-editor-bar{display:grid;grid-template-columns:1fr auto 1fr;align-items:center;gap:8px;min-width:0}
.apex-audio-editor-bar>button:first-child{justify-self:start}.apex-audio-editor-bar>button:last-child{justify-self:end}
.apex-audio-editor button{box-sizing:border-box;margin:0;min-height:30px;border:1px solid var(--border-color,#52606f);border-radius:5px;background:var(--comfy-input-bg,#303943);color:inherit;font:inherit;padding:5px 10px;white-space:nowrap;cursor:pointer}
.apex-audio-editor button:disabled{opacity:.5;cursor:default}.apex-audio-editor button:focus-visible{outline:2px solid #78b9cf;outline-offset:2px}
.apex-audio-editor-meter{display:flex;align-items:center;justify-content:space-between;gap:6px 16px;flex-wrap:wrap;min-width:0}
.apex-audio-editor-status{min-height:16px;font-size:11px;color:var(--descrip-text,#adb7c2);overflow-wrap:anywhere}
.apex-audio-editor-volume{display:inline-flex;align-items:center;gap:6px;white-space:nowrap;margin:0}
.apex-audio-editor-volume>span:last-child{min-width:34px;text-align:right;font-variant-numeric:tabular-nums}
.apex-audio-editor-wave{position:relative;flex:0 0 88px;background:#151b22;touch-action:none;cursor:crosshair;overflow:hidden;border-radius:4px}.apex-audio-editor-wave svg{position:absolute;width:100%;height:100%;pointer-events:none}
.apex-audio-editor-shade{position:absolute;top:0;bottom:0;background:#080a0bb0;pointer-events:none}.apex-audio-editor-handle{position:absolute;top:0;bottom:0;width:10px;transform:translateX(-50%);background:#e8b665;cursor:ew-resize;touch-action:none;z-index:2}
.apex-audio-editor-handle:focus{outline:2px solid white}.apex-audio-editor-cursor{position:absolute;top:0;bottom:0;border-left:1px solid white;pointer-events:none}.apex-audio-editor-clock{font-variant-numeric:tabular-nums;white-space:nowrap}
.apex-audio-editor .apex-audio-editor-gain{position:static;box-sizing:border-box;width:90px;min-width:0;height:20px;margin:0;padding:0;accent-color:#78b9cf}
`;
document.head.append(style);

function el(tag, props = {}) { return Object.assign(document.createElement(tag), props); }
const clamp = (value, low, high) => Math.max(low, Math.min(high, value));
const time = value => `${Math.floor(value / 60)}:${(value % 60).toFixed(2).padStart(5, "0")}`;

export function createAudioEditor(node, client = api) {
    const root = el("section", {className:"apex-audio-editor", tabIndex:-1});
    root.setAttribute("aria-label", "Apex Audio");
    const upload = el("button", {textContent:"Upload audio"});
    const play = el("button", {textContent:"▶ Play", disabled:true});
    const reset = el("button", {textContent:"Full source"});
    const clock = el("span", {className:"apex-audio-editor-clock"});
    const gain = el("input", {type:"range", min:0, max:200, step:1, className:"apex-audio-editor-gain"});
    gain.setAttribute("aria-label", "Volume percent");
    const gainLabel = el("span");
    const status = el("div", {className:"apex-audio-editor-status", textContent:"Choose a file or connect AUDIO."});
    const wave = el("div", {className:"apex-audio-editor-wave"});
    wave.setAttribute("aria-label", "Audio waveform; drag the yellow trim handles");
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("viewBox", "0 0 1200 100"); svg.setAttribute("preserveAspectRatio", "none");
    const path = document.createElementNS(svg.namespaceURI, "path");
    path.setAttribute("fill", "#78b9cf"); svg.append(path);
    const leftShade = el("div", {className:"apex-audio-editor-shade"});
    const rightShade = el("div", {className:"apex-audio-editor-shade"});
    const cursor = el("div", {className:"apex-audio-editor-cursor"});
    const handles = ["Trim start", "Trim end"].map(label => {
        const h = el("div", {className:"apex-audio-editor-handle", tabIndex:0});
        h.setAttribute("role", "slider"); h.setAttribute("aria-label", label); return h;
    });
    wave.append(svg,leftShade,rightShade,cursor,...handles);
    const volumeControl = el("label", {className:"apex-audio-editor-volume", textContent:"Volume"}); volumeControl.append(gain,gainLabel);
    const bar = el("div", {className:"apex-audio-editor-bar"}); bar.append(upload,play,reset);
    const meter = el("div", {className:"apex-audio-editor-meter"}); meter.append(clock,volumeControl);
    root.append(wave,bar,meter,status);
    const player = el("audio", {preload:"metadata"});
    let data = null, destroyed = false, request = null, generation = 0, raf = null, sourceKey = null;
    let context = null, amplifier = null, draft = null, drag = null;
    const widget = name => node.widgets?.find(w => w.name === name);
    const value = name => linked(name) && data?.selection?.[name] != null ? data.selection[name] : widget(name)?.value;
    const connected = () => node.inputs?.some(p => p.name === "audio" && p.link != null);
    const linked = name => node.inputs?.some(p => p.name === name && p.link != null);
    const set = (name, v) => { const w = widget(name); if (w) {w.value = v; w.callback?.(v); } };
    const selection = () => {
        if (draft) return draft;
        const total = data?.source_duration || 0, start = clamp(Number(value("start_seconds")) || 0, 0, total);
        const length = Number(value("duration_seconds")) || 0;
        return [start, length === 0 ? total : Math.min(total, start + length)];
    };
    const stop = () => { player.pause(); cancelAnimationFrame(raf); raf = null; play.textContent = "▶ Play"; };
    const paintCursor = () => {
        cancelAnimationFrame(raf); raf = null;
        const [start,end] = selection();
        if (!player.paused && player.currentTime >= end) {stop(); player.currentTime = start;}
        cursor.style.left = `${data ? clamp(player.currentTime / data.source_duration * 100, 0, 100) : 0}%`;
        clock.textContent = `${time(player.currentTime || start)} / ${time(end)} · ${time(end - start)} selected`;
        if (!player.paused) raf = requestAnimationFrame(paintCursor);
    };
    function paint() {
        const total = data?.source_duration || 1, [start,end] = selection(), volume = Number(value("volume_percent") ?? 100);
        gain.value = volume; gainLabel.textContent = `${volume}%`; gain.disabled = linked("volume_percent");
        if (amplifier) amplifier.gain.value = volume / 100;
        leftShade.style.left = "0"; leftShade.style.width = `${start / total * 100}%`;
        rightShade.style.left = `${end / total * 100}%`; rightShade.style.right = "0";
        handles.forEach((h,i) => {
            h.style.left = `${[start,end][i] / total * 100}%`;
            h.setAttribute("aria-valuemin", "0"); h.setAttribute("aria-valuemax", String(total));
            h.setAttribute("aria-valuenow", String([start,end][i])); h.setAttribute("aria-valuetext", time([start,end][i]));
            h.setAttribute("aria-disabled", String(!data || linked("start_seconds") || linked("duration_seconds")));
        });
        const peaks = data?.peaks || [], coords = peaks.map((p,i) => [i * 1200 / Math.max(1,peaks.length - 1), Math.min(49, p * volume / 100 * 49)]);
        path.setAttribute("d", coords.length ? "M" + coords.map(([x,y]) => `${x},${50-y}`).join(" L") + " L" + coords.slice().reverse().map(([x,y]) => `${x},${50+y}`).join(" L") + "Z" : "");
        paintCursor();
    }
    function show(info) {
        request?.abort(); request = null; generation++;
        stop(); data = info;
        const query = new URLSearchParams(info.media || {filename:info.filename, v:info.version});
        player.src = client.apiURL(`${info.media ? "/view" : "/apex/audio/media"}?${query}`);
        player.currentTime = selection()[0];
        play.disabled = false;
        status.textContent = `${time(info.source_duration)} source · ${info.sample_rate} Hz · ${info.channels} channel${info.channels === 1 ? "" : "s"}`;
        paint();
    }
    async function loadFile() {
        const key = JSON.stringify([value("preview"),value("audio_file"),node.inputs?.find(p => p.name === "audio")?.link]);
        if (key === sourceKey) {paint(); return;}
        sourceKey = key;
        request?.abort(); request = null; const current = ++generation;
        stop(); data = null; player.removeAttribute("src"); player.load(); play.disabled = true; paint();
        if (!value("preview")) {status.textContent = "Preview off."; return;}
        if (connected()) {status.textContent = "Connected AUDIO takes priority. Run upstream nodes to preview it."; return;}
        const filename = value("audio_file");
        if (!filename || filename.startsWith("(none")) {status.textContent = "Choose a file or connect AUDIO."; return;}
        request = new AbortController(); status.textContent = "Loading waveform…";
        try {
            const response = await client.fetchApi(`/apex/audio/info?${new URLSearchParams({filename})}`, {signal:request.signal});
            const info = await response.json(); if (!response.ok) throw new Error(info.error || "Could not load audio.");
            if (!destroyed && current === generation) show(info);
        } catch (error) {
            if (!destroyed && current === generation && error.name !== "AbortError") {sourceKey = null; status.textContent = error.message;}
        }
    }
    function commit(bounds) {
        draft = null; set("start_seconds", bounds[0]); set("duration_seconds", bounds[1] - bounds[0]);
        player.currentTime = bounds[0]; paint(); node.graph?.setDirtyCanvas(true,true);
    }
    function boundsAt(i, position, original) {
        const step = 1 / data.sample_rate, bounds = [...original];
        bounds[i] = i === 0 ? clamp(position,0,bounds[1] - step) : clamp(position,bounds[0] + step,data.source_duration);
        return bounds;
    }
    const point = event => clamp((event.clientX - wave.getBoundingClientRect().left) / wave.getBoundingClientRect().width,0,1) * data.source_duration;
    function finish(event) {
        if (!drag || event.pointerId !== drag.id) return;
        const bounds = draft; const canceled = event.type === "pointercancel";
        drag = null; draft = null;
        if (canceled) paint(); else commit(bounds);
    }
    function move(event) {
        if (!drag || event.pointerId !== drag.id) return;
        draft = boundsAt(drag.i,point(event),drag.original); paint();
    }
    handles.forEach((h,i) => {
        h.onpointerdown = event => {
            if (event.button !== 0 || h.getAttribute("aria-disabled") === "true") return;
            event.preventDefault(); event.stopPropagation(); stop(); h.focus();
            const original = selection(); drag = {id:event.pointerId,i,original}; draft = [...original];
            h.setPointerCapture(event.pointerId);
        };
        h.onkeydown = event => {
            if (h.getAttribute("aria-disabled") === "true") return;
            if (!["ArrowLeft","ArrowRight","Home","End"].includes(event.key)) return;
            event.preventDefault(); event.stopPropagation(); stop(); const bounds = selection();
            const next = event.key === "Home" ? 0 : event.key === "End" ? data.source_duration : bounds[i] + (event.key === "ArrowRight" ? 1 : -1) * (event.shiftKey ? 1 : .01);
            commit(boundsAt(i,next,bounds));
        };
    });
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", finish);
    window.addEventListener("pointercancel", finish);
    wave.onpointerdown = event => {
        if (!data || event.button !== 0) return;
        event.preventDefault(); event.stopPropagation(); root.focus();
        const [start,end] = selection(); player.currentTime = clamp(point(event),start,end); paintCursor();
    };
    play.onclick = async () => {
        if (!player.paused) {stop(); return;}
        try {
            if (!context) {
                context = new AudioContext(); amplifier = context.createGain();
                context.createMediaElementSource(player).connect(amplifier).connect(context.destination);
            }
            await context.resume(); amplifier.gain.value = Number(value("volume_percent")) / 100;
            const [start,end] = selection(); if (player.currentTime < start || player.currentTime >= end) player.currentTime = start;
            await player.play(); play.textContent = "■ Stop"; cancelAnimationFrame(raf); paintCursor();
        } catch (error) {stop(); status.textContent = `Preview: ${error.message}`;}
    };
    player.onended = stop; player.onpause = () => {cancelAnimationFrame(raf); raf = null; play.textContent = "▶ Play";};
    player.ontimeupdate = () => {cancelAnimationFrame(raf); paintCursor();};
    player.onerror = () => {stop(); status.textContent = "This source cannot play in the browser. Connect AUDIO and run it to create a FLAC preview.";};
    reset.onclick = () => {if (data && !linked("start_seconds") && !linked("duration_seconds")) {stop(); commit([0,data.source_duration]);}};
    gain.oninput = () => set("volume_percent", Number(gain.value));
    const picker = el("input", {type:"file", accept:"audio/*,video/*"});
    upload.onclick = () => picker.click();
    picker.onchange = async () => {
        const file = picker.files[0]; if (!file) return;
        upload.disabled = true;
        try {
            const form = new FormData(); form.append("image",file); form.append("type","input");
            const response = await client.fetchApi("/upload/image", {method:"POST",body:form});
            const result = await response.json(); if (!response.ok) throw new Error(result.error || "Upload failed.");
            const filename = [result.subfolder,result.name].filter(Boolean).join("/");
            const w = widget("audio_file"); if (!w.options.values.includes(filename)) w.options.values.push(filename);
            set("audio_file",filename);
        } catch (error) {status.textContent = error.message;}
        finally {upload.disabled = false; picker.value = "";}
    };
    root.onkeydown = event => {
        if (event.key === "Escape" && drag) {drag = null; draft = null; paint(); event.stopPropagation();}
        if (event.code === "Space" && !["INPUT","BUTTON","SELECT","TEXTAREA"].includes(event.target.tagName)) {
            event.preventDefault(); event.stopPropagation(); if (!play.disabled) play.click();
        }
    };
    const callbacks = [];
    for (const name of ["audio_file","start_seconds","duration_seconds","volume_percent","preview"]) {
        const w = widget(name); if (!w) continue;
        const original = w.callback;
        const callback = function(...args) {original?.apply(this,args); if (name === "audio_file" || name === "preview") loadFile(); else paint();};
        w.callback = callback; callbacks.push([w,original,callback]);
    }
    paint();
    return {element:root, loadFile, show, refresh:paint, destroy() {
        destroyed = true; generation++; request?.abort(); stop(); player.removeAttribute("src"); player.load(); context?.close();
        window.removeEventListener("pointermove",move); window.removeEventListener("pointerup",finish); window.removeEventListener("pointercancel",finish);
        for (const [w,original,callback] of callbacks) if (w.callback === callback) w.callback = original;
    }};
}

app.registerExtension({
    name:"Apex.Audio",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "ApexAudio") return;
        const created = nodeType.prototype.onNodeCreated, configured = nodeType.prototype.onConfigure;
        const executed = nodeType.prototype.onExecuted, removed = nodeType.prototype.onRemoved;
        const connection = nodeType.prototype.onConnectionsChange;
        nodeType.prototype.onNodeCreated = function(...args) {
            const result = created?.apply(this,args); this.apexAudio = createAudioEditor(this);
            this.addDOMWidget("apex_audio_preview","apex_audio",this.apexAudio.element,{serialize:false,hideOnZoom:false,getMinHeight:()=>230,getMaxHeight:()=>230});
            this.setSize([Math.max(this.size[0],540),Math.max(this.size[1],this.computeSize()[1])]);
            queueMicrotask(() => this.apexAudio?.loadFile()); return result;
        };
        nodeType.prototype.onConfigure = function(...args) {
            const result = configured?.apply(this,args);
            this.setSize([Math.max(this.size[0],540),Math.max(this.size[1],this.computeSize()[1])]);
            this.apexAudio?.loadFile(); return result;
        };
        nodeType.prototype.onExecuted = function(message,...args) {
            const result = executed?.call(this,message,...args);
            if (message.apex_audio?.[0]) this.apexAudio?.show(message.apex_audio[0]); return result;
        };
        nodeType.prototype.onConnectionsChange = function(...args) {
            const result = connection?.apply(this,args);
            if (args[0] === 1 && this.inputs?.[args[1]]?.name === "audio") this.apexAudio?.loadFile();
            else this.apexAudio?.refresh();
            return result;
        };
        nodeType.prototype.onRemoved = function(...args) {this.apexAudio?.destroy(); this.apexAudio = null; return removed?.apply(this,args);};
    },
});
