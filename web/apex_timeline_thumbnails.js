const cache = new Map();
const decoders = [];
const pendingFrames = new Map();
let queue = [], active = 0;

export function thumbnailTimes(clip, width, asset) {
    const count = Math.max(1, Math.min(96, Math.ceil(width / 84)));
    const start = Math.max(0, clip.source_in || 0);
    const end = Math.max(start, Math.min(start + clip.duration, asset.duration ?? Infinity) - 1 / (asset.frame_rate || 24));
    return Array.from({length:count}, (_, index) => Math.min(end, start + clip.duration * (index + .5) / count));
}

function mediaEvent(video, event, action, ready) {
    return new Promise((resolve, reject) => {
        const finish = error => {
            clearTimeout(timer);
            video.removeEventListener(event, success);
            video.removeEventListener("error", failure);
            if (error) reject(error); else resolve();
        };
        const success = () => finish();
        const failure = () => finish(new Error("Video preview unavailable."));
        const timer = setTimeout(failure, 6000);
        video.addEventListener(event, success);
        video.addEventListener("error", failure);
        try { action(); if (ready()) finish(); }
        catch (error) { finish(error); }
    });
}

async function decodeFrame(decoder, url, time) {
    const video = decoder.video;
    if (decoder.url !== url) {
        await mediaEvent(video, "loadeddata", () => {
            decoder.url = url;
            video.src = url;
            video.load();
        }, () => video.readyState >= 2);
    }
    const position = Math.max(0, Math.min(time, video.duration - .001));
    if (Math.abs(video.currentTime - position) > .002) {
        await mediaEvent(video, "seeked", () => {video.currentTime = position;},
            () => !video.seeking && video.readyState >= 2);
    }
    if (Math.abs(video.currentTime - position) > .1) throw new Error("Video preview could not seek to this frame.");
    const canvas = document.createElement("canvas");
    canvas.width = 128; canvas.height = 72;
    const scale = Math.max(canvas.width / video.videoWidth, canvas.height / video.videoHeight);
    canvas.getContext("2d").drawImage(video, (canvas.width - video.videoWidth * scale) / 2,
        (canvas.height - video.videoHeight * scale) / 2, video.videoWidth * scale, video.videoHeight * scale);
    return canvas.toDataURL("image/jpeg", .65);
}

function pump() {
    while (active < 2 && queue.length) {
        const job = queue.shift();
        if (!job.valid()) {pendingFrames.delete(job.key); job.resolve(null); continue;}
        let decoder = decoders.find(item => !item.busy);
        if (!decoder) {
            const video = document.createElement("video");
            video.muted = true; video.preload = "auto"; video.playsInline = true;
            decoder = {video, url:null, busy:false};
            decoders.push(decoder);
        }
        decoder.busy = true; active++;
        decodeFrame(decoder, job.url, job.time).then(frame => {
            cache.delete(job.key); cache.set(job.key, frame);
            while (cache.size > 256) cache.delete(cache.keys().next().value);
            job.resolve(frame);
        }).catch(() => {decoder.url = null; job.resolve(null);}).finally(() => {
            pendingFrames.delete(job.key);
            decoder.busy = false; active--;
            pump();
            if (!active && !queue.length) {
                for (const item of decoders) {
                    item.video.removeAttribute("src"); item.video.load(); item.url = null;
                }
            }
        });
    }
}

function frameAt(url, time, valid) {
    const key = `${url}|${time.toFixed(3)}`;
    if (cache.has(key)) {
        const frame = cache.get(key);
        cache.delete(key); cache.set(key, frame);
        return Promise.resolve(frame);
    }
    let job = pendingFrames.get(key);
    if (job) {job.clients=job.clients.filter(client=>client()); job.clients.push(valid); return job.promise;}
    job = {url,time,key,clients:[valid]};
    job.valid = ()=>job.clients.some(client=>client());
    job.promise = new Promise(resolve=>{job.resolve=resolve;});
    pendingFrames.set(key,job); queue.push(job); pump();
    return job.promise;
}

export function createVideoThumbnails(root) {
    let generation = 0, destroyed = false, enabled = true;
    const pending = new WeakMap();
    const observer = new IntersectionObserver(entries => {
        for (const entry of entries) {
            const tile = entry.target, job = pending.get(tile);
            if (!job) continue;
            job.visible=entry.isIntersecting;
            if (!job.visible) {tile.replaceChildren(); continue;}
            const valid = () => enabled && job.visible && !destroyed && generation === job.generation && tile.isConnected && root.contains(tile);
            frameAt(job.url, job.time, valid).then(frame => {
                if (!valid()) return;
                if (!frame) {tile.title = "Thumbnail unavailable"; return;}
                const image = document.createElement("img");
                image.alt = ""; image.draggable = false; image.src = frame;
                tile.replaceChildren(image);
            });
        }
    }, {root, rootMargin:"80px 160px"});
    function reset() {
        generation++;
        observer.disconnect();
        queue = queue.filter(job => {if (job.valid()) return true; pendingFrames.delete(job.key); job.resolve(null); return false;});
    }
    return {
        add(card, clip, asset, width, url) {
            if (destroyed || !enabled || asset.missing) return;
            const strip = document.createElement("div");
            strip.className = "apex-video-thumbnails";
            strip.setAttribute("aria-hidden", "true");
            card.classList.add("apex-video-clip");
            card.prepend(strip);
            for (const time of thumbnailTimes(clip, width, asset)) {
                const tile = document.createElement("div");
                tile.className = "apex-video-thumbnail";
                tile.dataset.sourceTime = time.toFixed(3);
                strip.append(tile);
                pending.set(tile, {url,time,generation,visible:false});
                observer.observe(tile);
            }
        },
        reset,
        setEnabled(value) {enabled=value; if(!enabled){reset(); for(const image of root.querySelectorAll(".apex-video-thumbnail img"))image.remove();}},
        destroy() {destroyed = true; reset();},
    };
}

export const thumbnailStyles = `
.apex-video-clip { position:relative; justify-content:flex-end; }
.apex-video-thumbnails { position:absolute; inset:0; display:flex; pointer-events:none; overflow:hidden; }
.apex-video-thumbnail { flex:1 1 0; min-width:0; height:100%; background:linear-gradient(135deg,#263c53,#1e2633); }
.apex-video-thumbnail img { display:block; width:100%; height:100%; object-fit:cover; pointer-events:none; }
.apex-video-clip strong,.apex-video-clip>span { position:relative; z-index:1; align-self:flex-start; max-width:100%; padding:0 3px; border-radius:2px; background:#0b1525c9; text-shadow:0 1px 2px black; pointer-events:none; }
.apex-video-clip strong { font-size:10px; }
`;
