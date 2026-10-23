const waveforms = new Map();
const pendingWaveforms = new Map(), waveformQueue = [], waveformJobs = new WeakMap();
let activeWaveforms = 0;
const waveformObserver = new IntersectionObserver(entries => {
    for (const entry of entries) if (entry.isIntersecting) {
        waveformObserver.unobserve(entry.target);
        waveformJobs.get(entry.target)?.();
    }
}, {rootMargin:"80px 160px"});

function pumpWaveforms() {
    while (activeWaveforms < 2 && waveformQueue.length) {
        const job = waveformQueue.shift();
        if (!job.clients.some(valid=>valid())) {
            pendingWaveforms.delete(job.key); job.resolve(null); continue;
        }
        activeWaveforms++;
        job.api.fetchApi(`/apex/timeline/waveform?${job.key}`).then(async response=>{
            const data = await response.json();
            if (!response.ok) throw new Error(data.error);
            waveforms.set(job.key,data);
            while (waveforms.size > 64) waveforms.delete(waveforms.keys().next().value);
            job.resolve(data);
        }).catch(job.reject).finally(()=>{
            pendingWaveforms.delete(job.key); activeWaveforms--; pumpWaveforms();
        });
    }
}

function waveformData(api, key, valid) {
    if (waveforms.has(key)) {
        const data = waveforms.get(key); waveforms.delete(key); waveforms.set(key,data);
        return Promise.resolve(data);
    }
    let job = pendingWaveforms.get(key);
    if (job) {job.clients=job.clients.filter(client=>client()); job.clients.push(valid); return job.promise;}
    job = {api,key,clients:[valid]};
    job.promise = new Promise((resolve,reject)=>Object.assign(job,{resolve,reject}));
    pendingWaveforms.set(key,job); waveformQueue.push(job); pumpWaveforms();
    return job.promise;
}

export function addAudioWaveform(api, card, project, clip, {begin, commit, end}) {
    const asset = project.assets[clip.asset_id];
    const line = document.createElement("div");
    line.className = "apex-audio-volume";
    line.setAttribute("role", "slider");
    line.setAttribute("tabindex", "0");
    line.setAttribute("aria-label", `${asset.name || "Audio clip"} volume`);
    line.setAttribute("aria-valuemin", "0");
    line.setAttribute("aria-valuemax", "200");
    let gain = clip.volume ?? 1;
    let waveform, disposed = false, cancelActive = null;
    const cleanup = () => {disposed=true; waveformObserver.unobserve(card); waveformJobs.delete(card); cancelActive?.();};
    const display = () => {
        line.style.top = `${(1 - Math.min(2, gain) / 2) * 100}%`;
        line.setAttribute("aria-valuenow", String(Math.round(gain * 100)));
        line.title = `${Math.round(gain * 100)}% · drag up/down; double-click to reset`;
        if (waveform) waveform.style.transform = `scaleY(${gain})`;
    };
    line.onpointerdown = event => {
        if (event.button !== 0) return;
        const original = gain;
        const rect = card.getBoundingClientRect();
        const move = event => { gain = Math.max(0, Math.min(2, original + (eventStart - event.clientY) / rect.height * 2)); display(); };
        const eventStart = event.clientY;
        const finish = async event => {
            event.stopPropagation();
            window.removeEventListener("pointermove", move);
            window.removeEventListener("pointerup", finish);
            window.removeEventListener("pointercancel", cancel);
            cancelActive = null;
            end();
            if (gain !== original) await commit(gain);
        };
        const cancel = event => {gain = original; display(); finish(event);};
        if (!begin(cancel)) return;
        event.preventDefault(); event.stopPropagation();
        cancelActive = ()=>cancel({stopPropagation(){}});
        window.addEventListener("pointermove", move);
        window.addEventListener("pointerup", finish);
        window.addEventListener("pointercancel", cancel);
    };
    line.onclick = event => event.stopPropagation();
    line.ondblclick = event => {event.stopPropagation(); commit(1);};
    line.onkeydown = event => {
        if (!["ArrowUp", "ArrowDown", "Home"].includes(event.key)) return;
        event.preventDefault(); event.stopPropagation();
        commit(event.key === "Home" ? 1 : Math.max(0, Math.min(2, gain + (event.key === "ArrowUp" ? .05 : -.05))));
    };
    card.append(line); display();
    if (asset.missing) return cleanup;
    const query = new URLSearchParams({project_id:project.project_id, asset_id:clip.asset_id, v:asset.media_revision || 0});
    const valid = ()=>!disposed && card.isConnected && !document.hidden;
    waveformJobs.set(card,async()=>{
      try {
        const data = await waveformData(api, query.toString(), valid);
        if (!data || !valid()) return;
        const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
        svg.classList.add("apex-audio-waveform");
        svg.setAttribute("viewBox", `${(clip.source_in || 0) / data.duration * data.peaks.length} 0 ${clip.duration / data.duration * data.peaks.length} 1`);
        svg.setAttribute("preserveAspectRatio", "none");
        const path = document.createElementNS(svg.namespaceURI, "path");
        const first = Math.max(0,Math.floor((clip.source_in || 0)/data.duration*data.peaks.length)-1);
        const last = Math.min(data.peaks.length,Math.ceil(((clip.source_in || 0)+clip.duration)/data.duration*data.peaks.length)+1);
        path.setAttribute("d", data.peaks.slice(first,last).map((peak,index)=>`M${first+index},${.5-Math.min(1,peak)*.45}V${.5+Math.min(1,peak)*.45}`).join(""));
        path.setAttribute("vector-effect", "non-scaling-stroke");
        svg.append(path); card.prepend(svg); waveform = svg; display();
      } catch (error) { if(valid())card.title += `\nWaveform unavailable: ${error.message}`; }
    });
    waveformObserver.observe(card);
    return cleanup;
}

export const audioStyles = `
.apex-timeline-track { grid-template-columns:130px max-content 30px; }
.apex-timeline-track-label { display:flex; gap:7px; flex-wrap:wrap; align-content:center; justify-content:center; }
.apex-timeline-track-label button { font-size:11px; padding:3px 5px; }
.apex-audio-clip { position:relative; background:linear-gradient(135deg,#245d4b,#244239); }
.apex-audio-clip.muted { opacity:.45; }
.apex-audio-clip strong,.apex-audio-clip span { position:relative; z-index:1; pointer-events:none; }
.apex-audio-clip strong { align-self:flex-start; font-size:10px; }
.apex-audio-waveform { position:absolute; inset:2px 0; width:100%; height:calc(100% - 4px); pointer-events:none; transform-origin:center; }
.apex-audio-waveform path { stroke:#83d6ad; stroke-width:1; }
.apex-audio-volume { position:absolute; left:0; right:0; height:2px; background:#f2d47a; z-index:3; cursor:ns-resize; touch-action:none; }
.apex-audio-volume::before { content:""; position:absolute; inset:-5px 0; }
.apex-audio-volume:hover,.apex-audio-volume:focus { background:white; box-shadow:0 0 0 1px #f2d47a; }
.apex-timeline-toolbar select { color:#eee; background:#303640; border:1px solid #59606b; padding:4px; }
.apex-timeline-toolbar>input[type=number] { width:42px; }
`;
