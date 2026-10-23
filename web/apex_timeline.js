import { app } from "../../../scripts/app.js";
import { api } from "../../../scripts/api.js";
import { timelineExportGraph, timelineOutputIds, migrateTimelineGraph } from "./apex_timeline_graph.js";
import { syncTrackInputs, connectTrackInput, videoTrackIndex, maxTracks } from "./apex_timeline_tracks.js";

import { chooseTimelineSources, droppedSourcePaths, missingClipMenu, parentFolder, sourceDialogStyles } from "./apex_timeline_files.js";

import { addAudioWaveform, audioStyles } from "./apex_timeline_audio.js";

import { createVideoThumbnails, thumbnailStyles } from "./apex_timeline_thumbnails.js";

import { snapPlacement, snapTrim, addFadeHandles, createFadePreview, fadeStyles } from "./apex_timeline_fades.js";

const nodes = new Set();

function el(tag, props = {}, children = []) {
    const node = document.createElement(tag);
    Object.assign(node, props);
    for (const child of children) node.append(child);
    return node;
}

function widgetValue(node, name, fallback = "") {
    return node.widgets?.find(widget => widget.name === name)?.value ?? fallback;
}

function seconds(value) {
    const total = Math.max(0, Number(value) || 0);
    const minutes = Math.floor(total / 60);
    return `${minutes}:${(total - minutes * 60).toFixed(1).padStart(4, "0")}`;
}

async function jsonResponse(response) {
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || `Timeline request failed (${response.status}).`);
    return data;
}

function projectQuery(node) {
    return new URLSearchParams({
        project_name: String(widgetValue(node, "project_name", "Apex Timeline")),
        node_id: String(node.id),
    });
}

async function loadProject(node) {
    return jsonResponse(await api.fetchApi(`/apex/timeline/project?${projectQuery(node)}`));
}

async function editClip(node, project, clip, operation, changes = {}) {
    return jsonResponse(await api.fetchApi("/apex/timeline/clip/edit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ project_id: project.project_id, clip_id: clip.id, operation, changes, revision: project.revision, node_id: String(node.id) }),
    }));
}

function mediaUrl(project, clip) {
    const query = new URLSearchParams({ project_id: project.project_id, asset_id: clip.asset_id, v:project.assets[clip.asset_id]?.media_revision || 0 });
    return api.apiURL(`/apex/timeline/media?${query}`);
}

function makeEditor(node) {
    const editor = el("section", { className: "apex-timeline-editor", tabIndex: -1 });
    editor.setAttribute("aria-label", "Apex Timeline Editor");
    const status = el("div", { className: "apex-timeline-status" });
    const tracksHost = el("div", { className: "apex-timeline-tracks" });
    const videoThumbnails = createVideoThumbnails(tracksHost);
    const player = el("video", { className: "apex-timeline-player", preload: "metadata" });
    const mixPlayer = el("audio", {preload:"none"});
    player.muted = true;
    const previewStage = el("div", {className:"apex-timeline-stage"}, [player]);
    const fadePreview = createFadePreview(previewStage, mediaUrl);
    const error = el("div", { className: "apex-timeline-error" });
    const previewLabel = el("div", { className: "apex-timeline-preview-label" });
    const selectedControls = el("div", { className: "apex-timeline-selection" });
    const selectionActions = el("div", {className:"apex-timeline-clip-actions"});
    const toolbar = el("div", { className: "apex-timeline-toolbar" });
    const transport = el("div", {className:"apex-timeline-transport"});
    const transportControls = el("div", {className:"apex-timeline-transport-controls"});
    transport.append(transportControls);
    const scrub = el("input", { type: "range", min: 0, max: 1, step: 1 / 24, value: 0 });
    scrub.setAttribute("aria-label", "Timeline playhead");
    const clock = el("span", { textContent: "0:00.0" });
    const zoom = el("input", { type: "range", min: .01, max: 120, step: .01, value: 18 });
    zoom.setAttribute("aria-label", "Timeline zoom");
    const zoomLabel = el("span");
    const importTrack = el("input", { type: "number", min: 1, max: 16, value: 2 });
    importTrack.setAttribute("aria-label", "Import to track");
    const header = el("div", { className: "apex-timeline-header" }, [
        el("h2", { textContent: "Apex Timeline Editor" }), status,
    ]);
    const mediaBin = el("div", { className: "apex-timeline-media-bin", hidden: true });
    editor.append(header,
        el("div", { className: "apex-timeline-viewer" }, [previewStage,
            el("aside", { className: "apex-timeline-inspector" }, [previewLabel, selectedControls])]),
        el("div", { className: "apex-timeline-tools" }, [transport, toolbar,
            el("div", { className: "apex-timeline-scrub" }, [el("span", { textContent: "Playhead" }), scrub, clock]), mediaBin]),
        tracksHost, mixPlayer, error);
    let destroyed = false, visible = false, redrawFrame = null;
    let videoClips = [], hasVideoFades = false, playheadLines = [], waveformCleanups = [];
    let project = null, selectedId = null, scale = 18, playhead = 0, busy = false, dragging = false;
    let fitView = false;
    let previewClip = null, suppressClick = false;
    let cancelGesture = null;
    let snapEnabled = node.properties?.apex_timeline_snap !== false;
    const fadesActive = () => hasVideoFades || playing;
    function previewFades(time, autoplay=false) {
        if (!fadesActive()) { fadePreview.clear(); player.style.visibility = ""; return false; }
        if (player.style.visibility !== "hidden") {
            player.pause(); player.removeAttribute("src"); player.load(); player.style.visibility = "hidden";
        }
        fadePreview.update(project,time,autoplay);
        if (playing) {
            const clip=visibleClip(time);
            if (previewClip?.id!==clip?.id) {
                previewClip=clip || null;
                previewLabel.textContent=clip ? clipLabel(clip) : "Timeline gap · black on export";
            }
        }
        return true;
    }
    let playing = false, playbackFrame = null, playbackToken = 0;
    let playbackStart = 0, playbackTime = 0, playbackAudio = false;

    function button(text, action, parent = toolbar) {
        const control = el("button", { textContent: text });
        control.onclick = action;
        parent.append(control);
        return control;
    }
    async function post(path, body) {
        if (path === "import" || path === "asset/place") body = {...body,
            placement_options:{snap:snapEnabled,auto_fade:!snapEnabled && project.fade_support}};
        return jsonResponse(await api.fetchApi(`/apex/timeline/${path}`, {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ project_id: project.project_id, project_name:project.name,
                node_id: String(node.id), revision: project.revision, ...body }),
        }));
    }
    async function mutate(action) {
        if (busy) return;
        busy = true;
        pausePlayback();
        editor.classList.add("busy");
        error.textContent = "";
        try { await refresh(await action()); }
        catch (exc) { error.textContent = exc.message; }
        finally { busy = false; editor.classList.remove("busy"); }
    }
    const clips = () => [...(project?.tracks || []), ...(project?.audio_tracks || [])].flatMap(track => track.clips);
    const fps = () => Number(project?.fps || 24);
    const snap = value => Math.round(value * fps()) / fps();
    function visibleClip(time) {
        for (let index=videoClips.length-1; index>=0; index--) {
            const clip=videoClips[index];
            if (clip.start<=time && clip.start+clip.duration>time) return clip;
        }
    }
    function clipLabel(clip) {
        const asset=project.assets[clip.asset_id];
        if (asset.missing) return `Missing clip · ${asset.source_name || asset.filename}\n${asset.source_path}\nRight-click the red clip to locate its source.`;
        return `${asset.name || "Clip preview"} · V${clip.track_index + 1}\n${seconds(clip.start)} – ${seconds(clip.start + clip.duration)}\nSource ${seconds(clip.source_in || 0)} – ${seconds((clip.source_in || 0) + clip.duration)}`;
    }
    function clearPreview(label) {
        player.pause(); player.removeAttribute("src"); player.load();
        previewClip = null; previewLabel.textContent = label;
    }
    function setPlayhead(time, preview = true) {
        if (preview && playing) pausePlayback();
        playhead = Math.max(0, Math.min(Number(time), project?.duration || 0));
        if (!visible || document.hidden) return;
        scrub.value = playhead;
        clock.textContent = seconds(playhead);
        for (const line of playheadLines) line.style.left = `${playhead * scale}px`;
        if (preview) {
            const previewTime = Math.max(0, Math.min(playhead, (project?.duration || 0) - 1 / fps()));
            if (previewFades(previewTime)) return;
            const visible = visibleClip(previewTime);
            if (visible) showClip(visible, false, (visible.source_in || 0) + previewTime - visible.start);
            else clearPreview("Timeline gap · black on export");
        }
    }
    function showClip(clip, autoplay = false, sourceTime = clip.source_in || 0) {
        previewClip = clip;
        const asset = project.assets[clip.asset_id];
        if (asset.missing) {
            player.pause(); player.removeAttribute("src"); player.load();
            previewLabel.textContent = clipLabel(clip);
            return;
        }
        previewLabel.textContent = clipLabel(clip);
        if (previewFades(clip.start + sourceTime - (clip.source_in || 0), playing || autoplay)) return;
        const seek = () => {
            if (previewClip?.id !== clip.id) return;
            player.currentTime = playing ? (clip.source_in || 0) + playhead - clip.start : sourceTime;
            if (playing || autoplay) playVideo(clip);
        };
        const url = mediaUrl(project, clip);
        player.onloadedmetadata = seek;
        if (player.getAttribute("src") !== url) player.src = url;
        else if (player.readyState >= 1) seek();
    }
    function playVideo(clip) {
        player.play().catch(exc => {
            if (playing && previewClip?.id === clip.id && exc.name !== "AbortError") {
                error.textContent = exc.message;
                pausePlayback();
            }
        });
    }
    function playbackButton() {
        previewPlay.textContent = playing ? "❚❚ Pause" : "▶ Play";
        previewPlay.title = playing ? "Pause timeline" : "Play timeline";
        previewPlay.setAttribute("aria-label", previewPlay.title);
        previewPlay.setAttribute("aria-pressed", String(playing));
    }
    function pausePlayback() {
        playing = false;
        playbackToken++;
        cancelAnimationFrame(playbackFrame);
        playbackFrame = null;
        player.pause(); mixPlayer.pause(); fadePreview.pause();
        playbackButton();
    }
    function playbackTick() {
        if (!playing || destroyed) return;
        const time = playbackAudio ? (mixPlayer.ended ? project.duration : mixPlayer.currentTime)
            : playbackTime + (performance.now() - playbackStart) / 1000;
        setPlayhead(time, false);
        if (playhead >= project.duration) {
            pausePlayback();
            return;
        }
        if (!visible || document.hidden) {
            playbackFrame = requestAnimationFrame(playbackTick);
            return;
        }
        if (previewFades(playhead,true)) {
            playbackFrame = requestAnimationFrame(playbackTick);
            return;
        }
        const activeClip = visibleClip(playhead);
        if (activeClip) {
            if (previewClip?.id !== activeClip.id) showClip(activeClip, true);
            else if (!project.assets[activeClip.asset_id].missing && player.readyState >= 1) {
                const sourceTime = (activeClip.source_in || 0) + playhead - activeClip.start;
                if (Math.abs(player.currentTime - sourceTime) > .15) player.currentTime = sourceTime;
                if (player.paused && !player.seeking) playVideo(activeClip);
            }
        } else if (previewClip || player.getAttribute("src")) clearPreview("Timeline gap · black on export");
        playbackFrame = requestAnimationFrame(playbackTick);
    }
    async function startPlayback() {
        if (destroyed) return;
        if (busy) { error.textContent = "Wait for the current timeline edit to finish."; return; }
        if (!project?.duration) { error.textContent = "No timeline clips are loaded. Check the project name and press Reload."; return; }
        error.textContent = "";
        pausePlayback();
        if (playhead >= project.duration) setPlayhead(0, false);
        const token = ++playbackToken;
        playing = true;
        playbackButton();
        playbackAudio = project.audio_tracks?.some(track => !track.muted && (track.volume ?? 1) > 0
            && track.clips.some(clip => (clip.volume ?? 1) > 0 && !project.assets[clip.asset_id]?.missing));
        try {
            await fadePreview.prepare(project,playhead);
            if (token !== playbackToken || destroyed) return;
            if (playbackAudio) {
                mixPlayer.currentTime = playhead;
                await mixPlayer.play();
            }
            if (token !== playbackToken || destroyed) {
                if (!playing) mixPlayer.pause();
                return;
            }
            playbackTime = playhead;
            playbackStart = performance.now();
            playbackTick();
        } catch (exc) {
            if (token === playbackToken) {
                pausePlayback();
                error.textContent = `Playback unavailable: ${exc.message}`;
            }
        }
    }
    async function importPaths(paths, track, start, kind="video") {
        await mutate(async () => {
            let updated = project;
            for (const sourcePath of paths) {
                const previous = new Set([...updated.tracks, ...updated.audio_tracks].flatMap(track => track.clips).map(clip => clip.id));
                updated = await post("import", {source_path:sourcePath, track_index:track, start, kind});
                const added = [...updated.tracks, ...updated.audio_tracks].flatMap(track => track.clips).find(clip => !previous.has(clip.id));
                selectedId = added.id;
                start = added.start + added.duration;
            }
            return updated;
        });
    }
    async function chooseSources(track, start, names=[], kind="video") {
        const result = await chooseTimelineSources(api,{names});
        if (result) await importPaths(result.paths, track, start, kind);
    }
    async function recoverSource(asset, search=false) {
        const result = await chooseTimelineSources(api,{
            title:search?"Search for missing clips":"Locate missing clip",
            initialPath:parentFolder(asset.source_path), names:[asset.source_name || asset.filename], search,
        });
        if (!result) return;
        if (!search) await mutate(()=>post("media/relink",{asset_id:asset.id, source_path:result.paths[0]}));
        else {
            let report;
            await mutate(async()=>{
                report=await post("media/search",result);
                return report.project;
            });
            if (report?.unresolved.length) error.textContent=`Relinked ${report.relinked}. Still missing: ${report.unresolved.map(item=>`${item.name} (${item.reason})`).join(", ")}`;
        }
    }
    function missingMenu(event,asset) {
        if (!asset.missing) return;
        missingClipMenu(event,{locate:()=>recoverSource(asset),search:()=>recoverSource(asset,true)});
    }
    const canvasScale = element => element.getBoundingClientRect().width / element.offsetWidth || 1;
    const timeAt = (element, clientX) => snap((clientX - element.getBoundingClientRect().left) / canvasScale(element) / scale);
    function beginScrub(event, lane, handle = false) {
        if (event.button !== 0 || busy || dragging) return;
        event.preventDefault(); event.stopPropagation(); editor.focus({preventScroll:true}); pausePlayback();
        const offset = handle ? event.clientX - lane.getBoundingClientRect().left - playhead * scale * canvasScale(lane) : 0;
        let x=event.clientX, frame=null;
        dragging=true;
        const update=()=>{frame=null;const time=timeAt(lane,x-offset);if(time!==playhead)setPlayhead(time);};
        const move=event=>{x=event.clientX;if(frame===null)frame=requestAnimationFrame(update);};
        const finish=()=>{
            window.removeEventListener("pointermove",move);window.removeEventListener("pointerup",finish);window.removeEventListener("pointercancel",finish);
            cancelAnimationFrame(frame);update();dragging=false;cancelGesture=null;
        };
        cancelGesture=finish;
        window.addEventListener("pointermove",move);window.addEventListener("pointerup",finish);window.addEventListener("pointercancel",finish);
        update();
    }
    function setupDrop(lane, track, kind="video") {
        lane.dataset.trackIndex = track; lane.dataset.kind = kind;
        lane.ondragover = event => { event.preventDefault(); event.stopPropagation(); lane.classList.add("drop-target"); };
        lane.ondragleave = () => lane.classList.remove("drop-target");
        lane.ondrop = event => {
            event.preventDefault(); event.stopPropagation(); lane.classList.remove("drop-target");
            const start = Math.max(0, timeAt(lane, event.clientX));
            const paths = droppedSourcePaths(event.dataTransfer);
            if (paths.length) importPaths(paths, track, start, kind);
            else if (event.dataTransfer.files.length) chooseSources(track, start, [...event.dataTransfer.files].map(file=>file.name), kind);
            else {
                const assetId = event.dataTransfer.getData("application/x-apex-asset");
                if (assetId) mutate(() => post("asset/place", { asset_id: assetId, track_index: track, start, kind }));
            }
        };
    }
    function setupDrag(placement, clip) {
        placement.onpointerdown = event => {
            if (busy || event.button !== 0) return;
            event.preventDefault(); event.stopPropagation();
            editor.focus({ preventScroll: true });
            const side = event.target.closest(".apex-timeline-trim")?.dataset.side;
            const origin = { x: event.clientX, scroll: tracksHost.scrollLeft, canvasScale: canvasScale(placement), ...clip };
            const revision = project.revision;
            let next = {}, moved = false;
            dragging = true;
            pausePlayback();
            placement.classList.add("dragging");
            function move(event) {
                let delta = snap(((event.clientX - origin.x) / origin.canvasScale + tracksHost.scrollLeft - origin.scroll) / scale);
                moved ||= Math.abs(event.clientX - origin.x) > 3;
                if (!moved) return;
                if (side === "left") {
                    delta = Math.max(-Math.min(origin.source_in || 0, origin.start), Math.min(delta, origin.duration - 1 / fps()));
                    next = { start: origin.start + delta, source_in: (origin.source_in || 0) + delta, duration: origin.duration - delta };
                } else if (side === "right") {
                    next = { duration: Math.max(1 / fps(), Math.min(origin.duration + delta,
                        project.assets[clip.asset_id].duration - (origin.source_in || 0))) };
                } else {
                    const lane = document.elementsFromPoint(event.clientX, event.clientY).find(item => item.classList.contains("apex-timeline-timed-lane") && item.dataset.kind === (clip.kind || "video"));
                    next = { start: Math.max(0, origin.start + delta), track_index: lane ? Number(lane.dataset.trackIndex) : origin.track_index };
                    if (lane && placement.parentElement !== lane) lane.append(placement);
                }
                if (snapEnabled) {
                    const neighbours = (clip.kind === "audio" ? project.audio_tracks : project.tracks)
                        .find(track=>track.index === (next.track_index ?? origin.track_index))?.clips || [];
                    next = side ? snapTrim(origin,next,side,neighbours,6/scale)
                        : snapPlacement(origin,next,neighbours,6/scale);
                }
                placement.style.left = `${(next.start ?? origin.start) * scale}px`;
                placement.style.width = `${(next.duration ?? origin.duration) * scale}px`;
                clock.textContent = `${side ? "Trim" : "Move"} ${seconds(next.start ?? origin.start)} · ${seconds(next.duration ?? origin.duration)}`;
                const rect = tracksHost.getBoundingClientRect();
                if (event.clientX > rect.right - 28) tracksHost.scrollLeft += 12;
                if (event.clientX < rect.left + 78) tracksHost.scrollLeft -= 12;
            }
            function finish(event) {
                window.removeEventListener("pointermove", move);
                window.removeEventListener("pointerup", finish);
                window.removeEventListener("pointercancel", cancel);
                dragging = false;
                cancelGesture = null;
                suppressClick = moved;
                selectedId = clip.id;
                if (moved && event.type !== "pointercancel") mutate(() => editClip(node, { ...project, revision }, clip, "update", {...next, snap:snapEnabled, auto_fade:!snapEnabled && project.fade_support}));
                else { renderTracks(); showClip(clip, false); }
            }
            function cancel(event) { moved = false; finish(event); }
            cancelGesture = () => cancel({ type: "pointercancel" });
            window.addEventListener("pointermove", move);
            window.addEventListener("pointerup", finish);
            window.addEventListener("pointercancel", cancel);
        };
    }
    function renderTracks() {
        if (!project || dragging || destroyed || !visible || document.hidden) return;
        const scrollTop = tracksHost.scrollTop, scrollLeft = tracksHost.scrollLeft;
        const padding = getComputedStyle(tracksHost);
        const availableWidth = Math.max(1, tracksHost.clientWidth - parseFloat(padding.paddingLeft) - parseFloat(padding.paddingRight) - 162);
        if (fitView) scale = Math.max(Number(zoom.min), Math.min(Number(zoom.max), availableWidth / Math.max(project.duration, 1 / fps())));
        for (const cleanup of waveformCleanups) cleanup();
        waveformCleanups = []; playheadLines = [];
        videoThumbnails.reset();
        snapButton.title = project.fade_support
            ? "On: stop at clip edges. Off: overlap to crossfade; touching edges receive short fades."
            : "On: stop at clip edges. Off: allow overlap. Restart ComfyUI to enable automatic fades.";
        projectFps.value = project.fps || 24;
        zoom.value = scale; zoomLabel.textContent = `${Number(scale.toFixed(2))} px/s`;
        scrub.max = project.duration || 1; scrub.step = 1 / fps();
        undo.disabled = !project.can_undo; redo.disabled = !project.can_redo;
        const selected = clips().find(clip => clip.id === selectedId);
        selectedControls.replaceChildren();
        selectionActions.replaceChildren();
        if (selected) {
            if (!playing && selected.kind !== "audio") {
                if (previewClip?.id !== selected.id || previewClip?.source_in !== selected.source_in || previewClip?.duration !== selected.duration
                    || previewClip?.start !== selected.start || previewClip?.track_index !== selected.track_index) showClip(selected);
                else previewClip = selected;
            }
            const fields = {};
            for (const [key, label, value] of [["start", "Timeline start", selected.start], ["source_in", "Source in", selected.source_in || 0],
                    ["duration", "Duration", selected.duration], ["track_index", "Track", selected.track_index + 1]]) {
                const input = el("input", { type: "number", min: key === "track_index" ? 1 : 0,
                    step: key === "track_index" ? 1 : 1 / fps(), value: Number(value.toFixed(6)) });
                input.setAttribute("aria-label", label);
                fields[key] = input;
                selectedControls.append(el("label", {}, [el("span", { textContent: label }), input]));
            }
            button("Apply trim / position", () => mutate(() => editClip(node, project, selected, "update", {
                start: Number(fields.start.value), source_in: Number(fields.source_in.value), duration: Number(fields.duration.value),
                track_index: Number(fields.track_index.value) - 1, snap:snapEnabled,
                auto_fade:!snapEnabled && project.fade_support })), selectionActions);
            button("Split at playhead", () => mutate(() => editClip(node, project, selected, "split", { position: snap(playhead) })), selectionActions);
            button("Duplicate", () => mutate(() => editClip(node, project, selected, "duplicate")), selectionActions);
            if (selected.link_id) button("Unlink audio/video", () => mutate(() => editClip(node, project, selected, "unlink")), selectionActions);
            button("Remove placement", () => mutate(() => editClip(node, project, selected, "delete")), selectionActions);
        }
        tracksHost.replaceChildren();
        const width = Math.max(availableWidth, (project.duration + (fitView ? 0 : 10)) * scale);
        const ruler = el("div", { className: "apex-timeline-ruler" });
        ruler.style.width = `${width}px`;
        const tick = [0.5, 1, 2, 5, 10, 15, 30, 60, 120, 300].find(value => value * scale >= 65) || 600;
        for (let time = 0; time <= width / scale; time += tick) {
            const mark = el("span", { textContent: seconds(time) }); mark.style.left = `${time * scale}px`; ruler.append(mark);
        }
        ruler.onpointerdown = event => beginScrub(event,ruler);
        tracksHost.append(el("div", { className: "apex-timeline-track apex-timeline-ruler-row" }, [
            el("div", { className: "apex-timeline-track-label", textContent: "TIME" }), ruler]));
        const highest = syncTrackInputs(node, project.tracks, 1, project.removed_tracks || []) - 1;
        addTrack.disabled = node.inputs.filter(input => videoTrackIndex(input) >= 0).length >= maxTracks;
        const lanes = [];
        for (let index = highest; index >= 0; index--) {
            if (index > 0 && project.removed_tracks?.includes(index)) continue;
            lanes.push({index, kind:"video", track:project.tracks.find(track=>track.index === index) || {index, clips:[]}});
        }
        const audioIndices = [...new Set([0, ...(project.audio_tracks || []).map(track=>track.index)])].sort((a,b)=>a-b);
        for (const index of audioIndices) lanes.push({index, kind:"audio", track:project.audio_tracks.find(track=>track.index === index) || {index, clips:[]}});
        for (const {index, kind, track} of lanes) {
            const lane = el("div", { className: "apex-timeline-lane apex-timeline-timed-lane" });
            lane.style.width = `${width}px`; lane.style.backgroundSize = `${scale}px 100%`;
            setupDrop(lane, index, kind);
            lane.onpointerdown = event => {if(event.target===lane)beginScrub(event,lane);};
            lane.onclick = event => { if (event.target === lane) setPlayhead(timeAt(lane, event.clientX)); };
            const line = el("div", { className: "apex-timeline-playhead" }); line.style.left = `${playhead * scale}px`; lane.append(line); playheadLines.push(line);
            line.onpointerdown = event => beginScrub(event,lane,true);
            line.onclick = event => event.stopPropagation();
            for (let n = 0; n < track.clips.length; n++) {
                const clip = track.clips[n], asset = project.assets[clip.asset_id];
                const card = el("button", { className: `apex-timeline-clip${kind === "audio" ? " apex-audio-clip" : ""}${track.muted ? " muted" : ""}${selectedId === clip.id ? " selected" : ""}${asset.missing ? " missing" : ""}`,
                    title: `${asset.name || `Clip ${n + 1}`} · ${clip.start.toFixed(3)}s · ${clip.duration.toFixed(3)}s\nDrag to move; drag edges to trim` });
                card.oncontextmenu = event=>missingMenu(event,asset);
                card.append(el("strong", { textContent: asset.missing ? `Missing · ${asset.source_name || asset.filename}` : asset.name || `Clip ${n + 1}` }),
                    el("span", { textContent: `${seconds(clip.start)} – ${seconds(clip.start + clip.duration)}` }));
                if (kind === "video") videoThumbnails.add(card, clip, asset, clip.duration * scale, mediaUrl(project, clip));
                if (kind === "audio") waveformCleanups.push(addAudioWaveform(api, card, project, clip, {
                    begin:cancel=>{if(busy || dragging)return false; pausePlayback(); dragging=true;
                        cancelGesture=()=>cancel({stopPropagation(){}}); return true;},
                    end:()=>{dragging=false; suppressClick=true; cancelGesture=null;},
                    commit:volume=>mutate(()=>editClip(node, project, clip, "volume", {volume})),
                }));
                card.onclick = () => {
                    if (suppressClick) { suppressClick = false; return; }
                    pausePlayback();
                    selectedId = clip.id; renderTracks(); setPlayhead(clip.start); startPlayback();
                };
                const placement = el("div", { className: "apex-timeline-clip-wrap" }, [card]);
                placement.style.cssText = `position:absolute;left:${clip.start * scale}px;width:${clip.duration * scale}px;min-width:0;top:9px`;
                for (const side of ["left", "right"]) {
                    const handle = el("div", { className: `apex-timeline-trim ${side}`, title: `Trim ${side === "left" ? "in" : "out"}` });
                    handle.dataset.side = side; placement.append(handle);
                }
                if (project.fade_support) addFadeHandles(placement,clip,scale,{
                    begin:cancel=>{if(busy || dragging)return false; pausePlayback(); dragging=true;
                        cancelGesture=()=>cancel({type:"pointercancel",stopPropagation(){}}); return true;},
                    end:()=>{dragging=false; suppressClick=true; cancelGesture=null;},
                    commit:(side,duration)=>mutate(()=>editClip(node,project,clip,"fade",{side,duration:snap(duration)})),
                });
                setupDrag(placement, clip); lane.append(placement);
            }
            const label = `${kind === "audio" ? "A" : "V"}${index + 1}`;
            const actions = el("div", {className:"apex-timeline-track-actions"});
            if (index > 0) {
                const remove = el("button", { className:"apex-timeline-track-delete", textContent:"−", title:`Delete ${label}` });
                remove.setAttribute("aria-label", `Delete ${label}`);
                remove.onclick = () => {
                    if (confirm(`Delete ${label} and its ${track.clips.length} clip placement(s)? Source media is kept. You can undo this.`))
                        mutate(() => post(kind === "audio" ? "audio/track" : "track/edit", {track_index:index, operation:"delete"}));
                };
                actions.append(remove);
            }
            const trackLabel = el("div", {className:"apex-timeline-track-label"}, [el("span", {textContent:label})]);
            if (kind === "audio") {
                const mute = el("button", {textContent:track.muted ? "Unmute" : "Mute"});
                mute.setAttribute("aria-label", `${track.muted ? "Unmute" : "Mute"} ${label}`);
                mute.onclick = () => mutate(()=>post("audio/track",{track_index:index, operation:"update", changes:{muted:!track.muted}}));
                trackLabel.append(mute);
            }
            tracksHost.append(el("div", { className:"apex-timeline-track" }, [trackLabel, lane, actions]));
        }
        mediaBin.replaceChildren();
        for (const asset of Object.values(project.assets)) {
            const card = el("button", { className: `apex-timeline-bin-asset${asset.missing?" missing":""}`, draggable: true,
                textContent: `${asset.name || asset.id.slice(0, 8)} · ${seconds(asset.duration)}`, title: "Drag into a track, or click to place at the playhead" });
            card.oncontextmenu = event=>missingMenu(event,asset);
            card.ondragstart = event => event.dataTransfer.setData("application/x-apex-asset", asset.id);
            card.onclick = () => mutate(() => post("asset/place", { asset_id: asset.id, track_index: Number(importTrack.value) - 1, start: snap(playhead), kind:importKind.value }));
            mediaBin.append(card);
        }
        tracksHost.scrollTop = scrollTop;
        tracksHost.scrollLeft = scrollLeft;
    }
    async function refresh(replacement = null) {
        if (replacement && replacement.name !== String(widgetValue(node, "project_name", "Apex Timeline"))) return;
        try {
            const requestedName = String(widgetValue(node, "project_name", "Apex Timeline"));
            const loaded = replacement || await loadProject(node);
            if (destroyed || loaded.name !== requestedName || requestedName !== String(widgetValue(node, "project_name", "Apex Timeline"))) return;
            if (project && loaded.project_id === project.project_id && loaded.revision < project.revision) return;
            if (previewClip) {
                const before=project?.assets[previewClip.asset_id], after=loaded.assets[previewClip.asset_id];
                if (before?.missing !== after?.missing || before?.source_path !== after?.source_path || before?.media_revision !== after?.media_revision) previewClip=null;
            }
            if (!project || loaded.project_id !== project.project_id || loaded.revision !== project.revision) {
                pausePlayback();
                fadePreview.clear(); player.style.visibility = "";
                mixPlayer.src = api.apiURL(`/apex/timeline/audio-preview?${new URLSearchParams({project_id:loaded.project_id, revision:loaded.revision})}`);
                mixPlayer.load();
            }
            project = loaded;
            videoClips = [...project.tracks].sort((a,b)=>a.index-b.index).flatMap(track=>track.clips);
            hasVideoFades = videoClips.some(clip=>clip.fade_in || clip.fade_out);
            error.textContent = "";
            status.textContent = `${project.clip_count} video · ${project.audio_tracks.reduce((total,track)=>total+track.clips.length,0)} audio · ${seconds(project.duration)}${project.fade_support ? "" : " · Restart ComfyUI to enable fades"}`;
            if (!clips().some(clip => clip.id === selectedId)) selectedId = clips()[0]?.id || null;
            if (!selectedId) { player.pause(); player.removeAttribute("src"); player.load(); previewClip = null; previewLabel.textContent = "Import videos or queue the workflow to start"; }
            renderTracks();
            setPlayhead(Math.min(playhead, project.duration));
        } catch (exc) { error.textContent = exc.message; }
    }
    function seekBoundary(end) {
        setPlayhead(end ? project?.duration || 0 : 0);
        tracksHost.scrollLeft = end ? tracksHost.scrollWidth - tracksHost.clientWidth : 0;
    }
    const previewHome = button("|◀", () => seekBoundary(false), transportControls);
    previewHome.title = "Go to start (Home)";
    previewHome.setAttribute("aria-label", "Go to timeline start");
    const previewPlay = button("▶ Play", () => playing ? pausePlayback() : startPlayback(), transportControls);
    previewPlay.className = "apex-timeline-play";
    playbackButton();
    const previewEnd = button("▶|", () => seekBoundary(true), transportControls);
    previewEnd.title = "Go to end (End)";
    previewEnd.setAttribute("aria-label", "Go to timeline end");
    const previewStop = button("■ Stop", () => { pausePlayback(); setPlayhead(0); }, transport);
    previewStop.className = "apex-timeline-stop";
    previewStop.setAttribute("aria-label", "Stop timeline");
    button("Reload", () => refresh());
    button("Clear video cache", () => mutate(() => post("cache/clear", {})));
    button("Clear", () => {
        if (confirm("Remove all placements? Media files are kept and you can undo this.")) mutate(() => post("project/clear", {}));
    });
    const undo = button("Undo", () => mutate(() => post("history", { operation: "undo" })));
    const redo = button("Redo", () => mutate(() => post("history", { operation: "redo" })));
    const importKind = el("select", {}, [el("option", {value:"video", textContent:"Video"}), el("option", {value:"audio", textContent:"Audio"})]);
    importKind.setAttribute("aria-label", "Import media lane");
    importKind.onchange = () => {importTrack.value = importKind.value === "audio" ? 1 : 2;};
    button("Link clips", () => chooseSources(Number(importTrack.value)-1,snap(playhead),[],importKind.value));
    toolbar.append(importKind, importTrack);
    button("Media bin", () => { mediaBin.hidden = !mediaBin.hidden; });
    const addTrack = button("+ Track", () => mutate(() => {
        const index = Array.from({length:maxTracks}, (_, index) => index)
            .find(index => !node.inputs.some(input => videoTrackIndex(input) === index));
        return post("track/edit", {track_index:index, operation:"add"});
    }));
    button("+ Audio", () => mutate(()=>{
        const index = Array.from({length:maxTracks},(_,index)=>index).find(index=>index>0 && !project.audio_tracks.some(track=>track.index===index));
        if (index == null) throw new Error("The timeline already has 16 audio lanes.");
        return post("audio/track",{track_index:index,operation:"add"});
    }));
    const projectFps = el("input", {type:"number", min:1, max:240, step:.001, value:24});
    projectFps.setAttribute("aria-label", "Project FPS");
    projectFps.onchange = () => mutate(()=>post("settings",{fps:Number(projectFps.value)}));
    toolbar.append(el("label",{},[el("span",{textContent:"FPS"}),projectFps]));
    const snapButton = button(snapEnabled ? "SNAP ON" : "SNAP OFF", () => {
        snapEnabled = !snapEnabled;
        node.properties ||= {};
        node.properties.apex_timeline_snap = snapEnabled;
        snapButton.textContent = snapEnabled ? "SNAP ON" : "SNAP OFF";
        snapButton.setAttribute("aria-pressed",String(snapEnabled));
    });
    snapButton.className = "apex-timeline-snap";
    snapButton.setAttribute("aria-pressed",String(snapEnabled));
    snapButton.title = "On: stop at clip edges. Off: overlap to crossfade; touching edges receive short fades.";
    const zoomControls = el("div", {className:"apex-timeline-zoom"});
    const fitButton = button("Fit", () => { fitView = true; tracksHost.scrollLeft = 0; scheduleRender(); }, zoomControls);
    fitButton.title = "Fit the whole timeline to the window";
    zoomControls.append(zoom, zoomLabel);
    toolbar.append(zoomControls);
    toolbar.append(selectionActions);
    button("Export", async () => {
        if (busy || !project?.clip_count) return;
        try {
            const prompt = await app.graphToPrompt();
            const saveId = timelineOutputIds(prompt.output, String(node.id))[0];
            if (!saveId) throw new Error("Connect VIDEO to Save Video, or IMAGE / AUDIO / FPS to a Video Combine output.");
            prompt.output = timelineExportGraph(prompt.output, String(node.id), saveId, project.name);
            const response = await api.queuePrompt(0, prompt);
            if (response.node_errors && Object.keys(response.node_errors).length) throw new Error(JSON.stringify(response.node_errors));
            error.textContent = "Export queued from the saved timeline.";
        } catch (exc) { error.textContent = exc.message; }
    });
    scrub.oninput = () => setPlayhead(Number(scrub.value));
    zoom.oninput = () => { fitView = false; scale = Number(zoom.value); scheduleRender(); };
    editor.addEventListener("keydown", event => {
        if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "s") return;
        event.stopPropagation();
        if (event.target.matches("input,select,textarea")) return;
        if (event.code === "Space" && !event.repeat) {
            event.preventDefault();
            if (playing) pausePlayback(); else startPlayback();
        }
        if (event.key === "Home" || event.key === "End") { event.preventDefault(); seekBoundary(event.key === "End"); }
        if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
            event.preventDefault();
            const frame = Math.floor(playhead * fps() + .000001);
            setPlayhead((frame + (event.key === "ArrowRight" ? 1 : -1)) / fps());
        }
        if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "z") { event.preventDefault(); (event.shiftKey ? redo : undo).click(); }
        if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "y") { event.preventDefault(); redo.click(); }
        if (event.key === "Delete" && selectedId) { event.preventDefault(); const clip = clips().find(clip => clip.id === selectedId); if (clip) mutate(() => editClip(node, project, clip, "delete")); }
    });
    editor.addEventListener("pointerdown", event => {
        if (!event.target.closest("input,select,textarea,button,a")) editor.focus({preventScroll:true});
        event.stopPropagation();
    });
    editor.addEventListener("dblclick", event => event.stopPropagation());
    editor.addEventListener("wheel", event => {
        if (event.target.closest(".apex-timeline-tracks,.apex-timeline-inspector,input,select")) event.stopPropagation();
    });
    let checkingMedia=false;
    const mediaCheck=setInterval(async()=>{
        if (destroyed || !visible || busy || dragging || playing || checkingMedia || document.hidden || !project
            || editor.contains(document.activeElement) && document.activeElement.matches("input")
            || document.querySelector(".apex-source-dialog,.apex-missing-menu")) return;
        checkingMedia=true;
        try {
            const latest=await loadProject(node);
            if (latest.revision!==project.revision || Object.keys(latest.assets).some(key=>latest.assets[key].missing!==project.assets[key]?.missing)) await refresh(latest);
        } catch (exc) { status.textContent="Media check unavailable — use Reload to retry"; }
        finally { checkingMedia=false; }
    },5000);
    function scheduleRender() {
        if (redrawFrame !== null || destroyed) return;
        redrawFrame = requestAnimationFrame(()=>{redrawFrame=null; renderTracks();});
    }
    let editorWidth = 0;
    const observer = new ResizeObserver(([entry]) => {
        const width = Math.round(entry.contentRect.width);
        if (width === editorWidth) return;
        editorWidth=width; scheduleRender();
    });
    observer.observe(editor);
    const updateVisibility = () => {
        videoThumbnails.setEnabled(visible && !document.hidden);
        if (!visible || document.hidden) {
            player.pause(); player.removeAttribute("src"); player.load(); previewClip=null;
            fadePreview.clear();
            for (const cleanup of waveformCleanups) cleanup();
            waveformCleanups=[];
        }
        else {scheduleRender(); if(!playing)setPlayhead(playhead);}
    };
    const viewportObserver = new IntersectionObserver(([entry])=>{
        if (visible === entry.isIntersecting) return;
        visible=entry.isIntersecting; updateVisibility();
    });
    viewportObserver.observe(editor);
    document.addEventListener("visibilitychange",updateVisibility);
    return { element: editor, refresh, renderTracks, destroy() {
        destroyed = true;
        clearInterval(mediaCheck);
        cancelAnimationFrame(redrawFrame);
        document.removeEventListener("visibilitychange",updateVisibility);
        viewportObserver.disconnect();
        cancelGesture?.();
        for (const cleanup of waveformCleanups) cleanup();
        waveformCleanups = []; playheadLines = [];
        videoThumbnails.destroy();
        fadePreview.clear();
        pausePlayback();
        player.pause(); player.removeAttribute("src"); player.load();
        mixPlayer.pause(); mixPlayer.removeAttribute("src"); mixPlayer.load();
        observer.disconnect(); editor.remove();
    } };

}

app.registerExtension({
    name: "ApexArtist.Timeline",
    beforeConfigureGraph(graphData) {
        migrateTimelineGraph(graphData);
    },
    nodeCreated(node) {
        if (node.comfyClass !== "ApexTimelineEditor") return;
        const changed = node.onConnectionsChange;
        node.onConnectionsChange = function (type, slot, connected) {
            if (type === 1 && this.inputs[slot]?.name.startsWith("placement_starts.")) return;
            if (type !== 1 || videoTrackIndex(this.inputs[slot]) < 0)
                return changed?.apply(this, arguments);
            const inputName = this.inputs[slot].name;
            // Native autogrow compacts socket numbers on disconnect. Timeline
            // layers have stable numbers, so their editor owns growth instead.
            requestAnimationFrame(() => {
                if (!node.graph) return;
                const currentSlot = node.inputs.findIndex(input => input.name === inputName);
                connectTrackInput(node, currentSlot, connected);
                node._apexTimeline?.renderTracks();
            });
        };
    },
    setup() {
        document.head.append(el("style", { textContent: `${sourceDialogStyles}
            .apex-timeline-editor { box-sizing:border-box; width:100%; height:100%; min-width:0; min-height:0; display:grid; grid-template-rows:auto minmax(180px,1fr) auto minmax(180px,.8fr) auto; padding:0; color:#ddd; background:#17191d; border:1px solid #59606b; border-radius:8px; overflow:hidden; font-family:Arial,sans-serif; }
            .apex-timeline-editor * { box-sizing:border-box; }
            .apex-timeline-header { display:flex; align-items:center; gap:8px; padding:10px 12px; background:#20242a; border-bottom:1px solid #444; }
            .apex-timeline-header h2 { margin:0 auto 0 0; font-size:17px; }
            .apex-timeline-editor button { color:#ddd; background:#303640; border:1px solid #59606b; border-radius:4px; padding:5px 9px; cursor:pointer; }
            .apex-timeline-editor button:hover { background:#424b59; }
            .apex-timeline-toolbar { display:flex; align-items:center; gap:8px; padding:8px 12px; background:#20242a; border-block:1px solid #343a43; }
            .apex-timeline-toolbar label { display:flex; align-items:center; gap:8px; margin-left:auto; font-size:12px; }
            .apex-timeline-toolbar input { width:130px; }
            .apex-timeline-toolbar label span:last-child { min-width:55px; }
            .apex-timeline-viewer { display:grid; grid-template-columns:minmax(0,1fr) 205px; min-height:0; background:#090b0e; }
            .apex-timeline-inspector { overflow:auto; padding:12px; border-left:1px solid #343a43; background:#191d23; }
            .apex-timeline-preview-label { color:#a8c2df; white-space:pre-line; font-size:12px; margin-bottom:12px; line-height:1.6; }
            .apex-timeline-selection { display:grid; gap:7px; }
            .apex-timeline-clip-actions { display:flex; align-items:center; flex-wrap:wrap; gap:5px; }
            .apex-timeline-status { color:#9fb4cc; font-size:12px; }
            .apex-timeline-tracks { overflow:auto; min-height:0; padding:0 12px 12px; background:#111318; overscroll-behavior:contain; }
            .apex-timeline-track { display:grid; grid-template-columns:54px max-content 30px; width:max-content; min-width:100%; min-height:80px; border-bottom:1px solid #30343b; }
            .apex-timeline-track-actions { position:sticky; right:0; z-index:2; display:grid; place-items:center; background:#20242a; }
            .apex-timeline-track-delete { width:20px; height:20px; min-height:20px; padding:0; border:1px solid #55434a; border-radius:3px; background:#242029; color:#e4a4a4; font-size:16px; cursor:pointer; }
            .apex-timeline-track-delete:hover { background:#533039; color:#fff; }
            .apex-timeline-track-label { position:sticky; left:0; z-index:2; display:grid; place-items:center; font-weight:700; color:#8ca5c1; background:#20242a; }
            .apex-timeline-lane { display:flex; align-items:center; gap:5px; padding:9px; background:repeating-linear-gradient(90deg,#171a20 0,#171a20 89px,#252a31 90px); }
            .apex-timeline-timed-lane { position:relative; padding:0; min-height:80px; background-image:linear-gradient(to right,#30343b 1px,transparent 1px); background-color:#171a20; }
            .apex-timeline-ruler-row { position:sticky; top:0; z-index:3; min-height:28px; }
            .apex-timeline-ruler { position:relative; height:28px; overflow:hidden; background:#262c34; color:#aab9ca; font-size:11px; }
            .apex-timeline-ruler span { position:absolute; top:0; height:28px; padding:5px 0 0 4px; border-left:1px solid #5c697a; }
            .apex-timeline-bin { background:repeating-linear-gradient(135deg,#211a16 0,#211a16 16px,#2d241d 16px,#2d241d 32px); }
            .apex-timeline-bin .apex-timeline-clip { background:linear-gradient(135deg,#754b25,#603539); border-color:#a36c3d; }
            .apex-timeline-clip-wrap { flex:none; min-width:90px; overflow:hidden; }
            .apex-timeline-clip { width:100%; min-height:56px; display:flex; flex-direction:column; justify-content:center; color:white; background:linear-gradient(135deg,#285b88,#483b84); border:2px solid #668db4; border-radius:6px; overflow:hidden; }
            .apex-timeline-clip.missing, .apex-timeline-bin-asset.missing { background:repeating-linear-gradient(135deg,#7d222a 0,#7d222a 12px,#5e1b24 12px,#5e1b24 24px); border-color:#f16d75; color:#fff; }
            .apex-timeline-clip.selected { border-color:#ffd166; box-shadow:0 0 0 2px #ffd16655; }
            .apex-timeline-clip span { font-size:11px; opacity:.8; }
            .apex-timeline-stage { position:relative; min-width:0; min-height:0; overflow:hidden; }
            .apex-timeline-transport { display:grid; grid-template-columns:minmax(0,1fr) auto minmax(0,1fr); align-items:center; gap:10px; padding:8px 12px; background:#171b21; border-top:1px solid #343a43; }
            .apex-timeline-transport-controls { grid-column:2; display:flex; align-items:center; gap:8px; }
            .apex-timeline-zoom { display:flex; align-items:center; gap:6px; }
            .apex-timeline-editor .apex-timeline-play { grid-column:2; position:static; display:inline-flex; align-items:center; justify-content:center; min-width:110px; height:44px; padding:8px 16px; background:#344d68; border:1px solid #a0bfdc; border-radius:6px; color:white; font-size:17px; opacity:1; pointer-events:auto; }
            .apex-timeline-editor .apex-timeline-stop { grid-column:3; justify-self:start; min-height:32px; font-size:13px; }
            .apex-timeline-player { display:block; width:100%; height:100%; min-height:0; object-fit:contain; background:#090b0e; }
            .apex-timeline-error { color:#ff9797; white-space:pre-wrap; padding:6px 12px; }
            .apex-timeline-error:empty { display:none; }
            .apex-timeline-toolbar { flex-wrap:wrap; gap:5px; padding:6px 10px; }
            .apex-timeline-toolbar label { margin-left:0; }
            .apex-timeline-toolbar label input[type=number] { width:42px; }
            .apex-timeline-toolbar input[type=range] { width:80px; }
            .apex-timeline-editor input[type=number] { color:#eee; background:#10141a; border:1px solid #59606b; border-radius:3px; padding:4px; box-sizing:border-box; }
            .apex-timeline-selection label { display:grid; grid-template-columns:1fr 85px; align-items:center; gap:6px; font-size:12px; }
            .apex-timeline-scrub { display:flex; align-items:center; gap:10px; padding:4px 12px; font-size:12px; background:#20242a; }
            .apex-timeline-scrub input { flex:1; min-width:0; }
            .apex-timeline-scrub span:last-child { min-width:90px; }
            .apex-timeline-media-bin { display:flex; gap:6px; overflow:auto; padding:8px; max-height:90px; background:#28211b; }
            .apex-timeline-media-bin[hidden] { display:none; }
            .apex-timeline-bin-asset { flex:none; max-width:200px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; cursor:grab !important; }
            .apex-timeline-clip { width:100%; height:58px; min-width:0; white-space:nowrap; padding:4px 8px !important; cursor:grab !important; touch-action:none; }
            .apex-timeline-clip strong,.apex-timeline-clip span { overflow:hidden; text-overflow:ellipsis; max-width:100%; display:block; }
            .apex-timeline-trim { position:absolute; top:0; bottom:0; width:6px; cursor:ew-resize; background:#a9d4ff44; z-index:2; touch-action:none; }
            .apex-timeline-trim.left { left:0; border-radius:4px 0 0 4px; }
            .apex-timeline-trim.right { right:0; border-radius:0 4px 4px 0; }
            .apex-timeline-clip-wrap.dragging { opacity:.8; z-index:6; outline:2px solid #ffd166; }
            .apex-timeline-playhead { position:absolute; top:0; bottom:0; width:11px; transform:translateX(-50%); z-index:5; cursor:ew-resize; touch-action:none; }
            .apex-timeline-playhead::after { content:""; position:absolute; left:5px; top:0; bottom:0; width:1px; background:#ff6767; pointer-events:none; }
            .apex-timeline-timed-lane.drop-target { outline:2px solid #ffd166; outline-offset:-2px; }
            .apex-timeline-editor.busy .apex-timeline-track { opacity:.65; }
            ${audioStyles}
            ${thumbnailStyles}
            ${fadeStyles}
        ` }));
        api.addEventListener("apex-timeline-changed", event => {
            const nodeId = String(event.detail?.node ?? "");
            for (const node of nodes) {
                if (String(node.id) !== nodeId) continue;
                if (node.inputs.some(input => input.name === "project_name" && input.link != null)) {
                    const name = node.widgets.find(widget => widget.name === "project_name");
                    if (name) name.value = event.detail.name;
                }
                node._apexTimeline?.refresh(event.detail).catch(console.error);
            }
        });
    },
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "ApexTimelineEditor") return;
        const created = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const result = created?.apply(this, arguments);
            nodes.add(this);
            this._apexTimeline = makeEditor(this);
            this.addDOMWidget("timeline_editor", "ApexTimelineEditorWidget", this._apexTimeline.element, {
                serialize: false, hideOnZoom: false, getMinHeight: () => 600,
            });
            const projectName = this.widgets.find(widget => widget.name === "project_name");
            const changed = projectName.callback;
            projectName.callback = function () {
                const result = changed?.apply(this, arguments);
                node._apexTimeline.refresh();
                return result;
            };
            const node = this;
            requestAnimationFrame(() => {
                if (!nodes.has(node)) return;
                syncTrackInputs(node);
                node.setSize([Math.max(node.size[0], 1080), Math.max(node.size[1], 880)]);
                node._apexTimeline.refresh();
                app.graph?.setDirtyCanvas(true, true);
            });
            return result;
        };
        const configured = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function () {
            const result = configured?.apply(this, arguments);
            requestAnimationFrame(() => {
                if (!nodes.has(this)) return;
                syncTrackInputs(this);
                this.setSize([Math.max(this.size[0], 1080), Math.max(this.size[1], 880)]);
                this._apexTimeline?.refresh();
                app.graph?.setDirtyCanvas(true, true);
            });
            return result;
        };
        const removed = nodeType.prototype.onRemoved;
        nodeType.prototype.onRemoved = function () {
            nodes.delete(this);
            this._apexTimeline?.destroy();
            return removed?.apply(this, arguments);
        };
    },
});
