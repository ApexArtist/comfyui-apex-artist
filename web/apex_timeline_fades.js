export function snapPlacement(origin, candidate, neighbours, threshold) {
    const next = {...candidate};
    let low = 0, high = Infinity;
    for (const clip of neighbours) {
        if (clip.id === origin.id) continue;
        const end = clip.start + clip.duration;
        if (origin.start + origin.duration <= clip.start + 1e-6) high = Math.min(high, clip.start - origin.duration);
        else if (origin.start >= end - 1e-6) low = Math.max(low, end);
        else if (next.start + origin.duration / 2 <= clip.start + clip.duration / 2) high = Math.min(high, clip.start - origin.duration);
        else low = Math.max(low, end);
    }
    if (high < low) return {start:origin.start, track_index:origin.track_index};
    next.start = Math.max(low, Math.min(high, next.start));
    for (const clip of neighbours) {
        if (clip.id === origin.id) continue;
        for (const edge of [clip.start - origin.duration, clip.start + clip.duration])
            if (edge >= low && edge <= high && Math.abs(next.start - edge) <= threshold) next.start = edge;
    }
    return next;
}

export function snapTrim(origin, next, side, neighbours, threshold) {
    let start = next.start ?? origin.start, end = start + (next.duration ?? origin.duration);
    for (const clip of neighbours) {
        if (clip.id === origin.id) continue;
        const edge = side === 'left' ? clip.start + clip.duration : clip.start;
        if (side === 'left' && edge <= origin.start + 1e-6) {
            const snapped = Math.max(start, edge);
            start = Math.abs(snapped - edge) <= threshold ? edge : snapped;
        }
        if (side === 'right' && edge >= origin.start + origin.duration - 1e-6) {
            const snapped = Math.min(end, edge);
            end = Math.abs(snapped - edge) <= threshold ? edge : snapped;
        }
    }
    return side === 'left' ? {start, source_in:(origin.source_in || 0) + start - origin.start, duration:end - start}
        : {duration:end - start};
}

export function addFadeHandles(placement, clip, scale, {begin, end, commit}) {
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.classList.add('apex-fade-curves');
    svg.setAttribute('viewBox', '0 0 100 100');
    svg.setAttribute('preserveAspectRatio', 'none');
    placement.append(svg);
    let incoming = clip.fade_in || 0, outgoing = clip.fade_out || 0;
    const handles = {};
    const display = () => {
        const a = incoming / clip.duration * 100, b = outgoing / clip.duration * 100;
        svg.innerHTML = `<path d="M0,0 L0,100 L${a},0 Z M${100-b},0 L100,100 L100,0 Z"/><polyline points="0,100 ${a},0 ${100-b},0 100,100"/>`;
        handles.in.style.left = `${a}%`; handles.out.style.left = `${100-b}%`;
        for (const side of ['in','out']) {
            const length = side === 'in' ? incoming : outgoing;
            handles[side].title = `Fade ${side}: ${length.toFixed(2)}s · drag; double-click to remove`;
            handles[side].setAttribute('aria-valuenow', String(length));
        }
    };
    for (const side of ['in','out']) {
        const handle = document.createElement('div');
        handle.className = `apex-timeline-fade fade-${side}`;
        handle.tabIndex = 0;
        handle.setAttribute('role','slider'); handle.setAttribute('aria-label',`Fade ${side}`);
        handle.setAttribute('aria-valuemin','0'); handle.setAttribute('aria-valuemax',String(clip.duration));
        handle.onpointerdown = event => {
            if (event.button !== 0) return;
            const initial = side === 'in' ? incoming : outgoing;
            const originX = event.clientX, ratio = placement.getBoundingClientRect().width / placement.offsetWidth || 1;
            const move = event => {
                const value = Math.max(0, Math.min(clip.duration, initial + (event.clientX - originX) / ratio / scale * (side === 'in' ? 1 : -1)));
                if (side === 'in') incoming = value; else outgoing = value;
                display();
            };
            const finish = event => {
                event.stopPropagation();
                window.removeEventListener('pointermove',move);
                window.removeEventListener('pointerup',finish);
                window.removeEventListener('pointercancel',cancel);
                end();
                const value = side === 'in' ? incoming : outgoing;
                if (event.type !== 'pointercancel' && value !== initial) commit(side,value);
                else { if(side==='in')incoming=initial;else outgoing=initial; display(); }
            };
            const cancel = event => finish(event);
            if (!begin(cancel)) return;
            event.preventDefault(); event.stopPropagation();
            window.addEventListener('pointermove',move);
            window.addEventListener('pointerup',finish);
            window.addEventListener('pointercancel',cancel);
        };
        handle.onclick = event => event.stopPropagation();
        handle.ondblclick = event => {event.preventDefault(); event.stopPropagation(); commit(side,0);};
        handle.onkeydown = event => {
            if (!['ArrowLeft','ArrowRight','Home'].includes(event.key)) return;
            event.preventDefault(); event.stopPropagation();
            const value = side==='in' ? incoming : outgoing;
            commit(side,event.key==='Home' ? 0 : Math.max(0,Math.min(clip.duration,value+(event.key==='ArrowRight' ? .05 : -.05))));
        };
        handles[side] = handle; placement.append(handle);
    }
    display();
}

function opacityAt(clip, time, skipOut) {
    const local = time - clip.start;
    return (clip.fade_in ? Math.max(0,Math.min(1,local/clip.fade_in)) : 1)
        * (!skipOut && clip.fade_out ? Math.max(0,Math.min(1,(clip.duration-local)/clip.fade_out)) : 1);
}

export function createFadePreview(stage, urlFor) {
    const videos = new Map(), urls = new Map();
    let currentProject = null, currentRevision = null, ordered = [], boundaries = [];
    function sync(record) {
        const {video,source,playing} = record;
        if (video.readyState < 1) return;
        if (Math.abs(video.currentTime-source) > (playing ? .15 : .002)) video.currentTime = source;
        if (playing) {if(video.paused && !video.seeking)video.play().catch(()=>{});}
        else if(!video.paused)video.pause();
    }
    function release(id,record) {
        const cancelled = new DOMException('Preview released','AbortError');
        for (const notify of record.waiters) notify(cancelled);
        record.video.pause(); record.video.removeAttribute('src'); record.video.load(); record.video.remove(); videos.delete(id);
    }
    function clear() {
        for (const [id,record] of videos) release(id,record);
        urls.clear(); currentProject = null; currentRevision = null; ordered = []; boundaries = [];
    }
    function ready(record) {
        if (record.video.error) return Promise.reject(new Error('Could not load timeline preview media.'));
        if (record.video.readyState >= 2 && !record.video.seeking) return Promise.resolve();
        return new Promise((resolve,reject)=>{
            const notify=error=>{
                if (error || record.video.readyState>=2 && !record.video.seeking) {
                    record.waiters.delete(notify);
                    if(error)reject(error);else resolve();
                }
            };
            record.waiters.add(notify);
        });
    }
    const preview = {
        clear,
        pause() {for(const record of videos.values()){record.playing=false; record.video.pause();}},
        async prepare(project,time) {
            preview.update(project,time,false);
            await Promise.all([...videos.values()].filter(record=>record.active && record.hasSource).map(ready));
        },
        update(project, time, playing) {
            if (currentProject!==project || currentRevision!==project.revision) {
                ordered = [...project.tracks].sort((a,b)=>a.index-b.index).flatMap(track=>track.clips);
                boundaries=[...new Set(ordered.flatMap(clip=>[clip.start,clip.start+clip.duration]))].sort((a,b)=>a-b);
                currentProject=project; currentRevision=project.revision; urls.clear();
            }
            let layers = ordered.filter(clip=>clip.start <= time && time < clip.start+clip.duration);
            const incoming = new Set(layers.map(clip=>clip.auto_fade_in).filter(Boolean));
            const opaque = layers.findLastIndex(clip=>opacityAt(clip,time,incoming.has(clip.id))>=1);
            if (opaque >= 0) layers = layers.slice(opaque);
            let upcoming = null, upcomingTime = 0;
            if (playing) for (const boundary of boundaries) {
                if (boundary<=time+.00001) continue;
                if (boundary>time+1) break;
                const next=ordered.findLast(clip=>clip.start<=boundary && boundary<clip.start+clip.duration);
                if (!next) break;
                if (!layers.some(clip=>clip.id===next.id)) {upcoming=next; upcomingTime=boundary; break;}
            }
            const visible = new Set(layers.map(clip=>clip.id));
            const wanted = upcoming ? [...layers,upcoming] : layers;
            for (const [index,clip] of wanted.entries()) {
                let record=videos.get(clip.id);
                if (!record) {
                    const video=document.createElement('video');
                    video.className='apex-fade-player';video.muted=true;video.playsInline=true;video.preload='auto';video.style.opacity='0';
                    record={video,source:0,playing:false,active:false,hasSource:false,opacity:'0',waiters:new Set()};
                    const loaded=()=>{
                        sync(record);
                        if(video.readyState>=2 && !video.seeking)video.style.opacity=record.opacity;
                        for(const notify of record.waiters)notify();
                    };
                    video.onloadedmetadata=loaded;video.onloadeddata=loaded;video.onseeked=loaded;
                    video.onerror=()=>{for(const notify of record.waiters)notify(new Error('Could not load timeline preview media.'));};
                    videos.set(clip.id,record);stage.append(video);
                }
                const {video}=record;
                record.active=visible.has(clip.id);
                record.opacity=record.active && !project.assets[clip.asset_id].missing ? String(opacityAt(clip,time,incoming.has(clip.id))) : '0';
                record.source=Math.max(0,(clip.source_in||0)+(record.active ? time : upcomingTime)-clip.start);
                record.playing=playing && record.active;
                video.style.zIndex=String(index+1);
                if (!project.assets[clip.asset_id].missing) {
                    if(!urls.has(clip.id))urls.set(clip.id,urlFor(project,clip));
                    const url=urls.get(clip.id);record.hasSource=true;
                    if(video.getAttribute('src')!==url)video.src=url;else sync(record);
                }
                video.style.opacity=video.readyState>=2 && !video.seeking ? record.opacity : '0';
            }
            const awaitingFrame=playing && layers.some(clip=>!project.assets[clip.asset_id].missing) && !layers.some(clip=>{
                const record=videos.get(clip.id);return record.video.readyState>=2&&!record.video.seeking;
            });
            let held=false;
            for (const [id,record] of videos) if(!visible.has(id) && id!==upcoming?.id) {
                if(awaitingFrame && !held && Number(record.video.style.opacity)>0) {record.playing=false;record.video.pause();held=true;}
                else release(id,record);
            }
        },
    };
    return preview;
}

export const fadeStyles = `
.apex-fade-curves { position:absolute; inset:0; width:100%; height:100%; pointer-events:none; z-index:3; }
.apex-fade-curves path { fill:#02081388; }
.apex-fade-curves polyline { fill:none; stroke:#ffe4a0; stroke-width:1.2; vector-effect:non-scaling-stroke; }
.apex-timeline-fade { position:absolute; top:0; width:10px; height:10px; background:#ffe4a0; border:1px solid #4c371b; border-radius:2px; z-index:7; cursor:ew-resize; touch-action:none; }
.apex-timeline-fade.fade-out { transform:translateX(-100%); }
.apex-timeline-fade:focus,.apex-timeline-fade:hover { background:white; outline:1px solid #ffc85d; }
.apex-timeline-clip-wrap:has(.apex-timeline-fade)>.apex-timeline-trim { top:12px; }
.apex-timeline-snap[aria-pressed=true] { background:#345a72; border-color:#96ceef; color:white; }
.apex-timeline-stage { position:relative; background:black; }
.apex-fade-player { position:absolute; inset:0; width:100%; height:100%; object-fit:contain; pointer-events:none; }
`;
