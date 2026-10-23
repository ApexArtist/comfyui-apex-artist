const prefix = "video_tracks.video_track_";
export const maxTracks = 16;

export function videoTrackIndex(input) {
    if (!input?.name.startsWith(prefix)) return -1;
    const index = Number(input.name.slice(prefix.length));
    return Number.isInteger(index) && index >= 0 && index < maxTracks ? index : -1;
}

export function syncTrackInputs(node, tracks = [], requested = 1, removed = node.properties.apex_timeline_removed_tracks || []) {
    for (let slot = node.inputs.length - 1; slot >= 0; slot--)
        if (node.inputs[slot].name.startsWith("placement_starts.")) node.removeInput(slot);
    removed = removed.filter(index => index > 0);
    node.properties.apex_timeline_removed_tracks = [...removed];
    const highestInput = Math.max(-1, ...node.inputs.map(videoTrackIndex));
    const highestTrack = Math.max(-1, ...tracks.map(track => track.index));
    const count = Math.min(maxTracks, Math.max(1, requested, highestInput + 1, highestTrack + 1,
        node.properties.apex_timeline_track_count || 1));
    for (let index = 0; index < count; index++) {
        const name = prefix + index;
        let input = node.inputs.find(input => input.name === name);
        if (removed.includes(index)) {
            if (input) node.removeInput(node.inputs.indexOf(input));
            continue;
        }
        if (!input) input = node.addInput(name, "VIDEO", { shape:7 });
        input.label = input.localized_name = `Video ${index + 1} → V${index + 1}`;
    }
    const audioSlot = node.inputs.findIndex(input => input.name === "audio");
    if (audioSlot >= 0 && node.inputs.slice(audioSlot + 1).some(input => videoTrackIndex(input) >= 0)) {
        const audio = node.inputs[audioSlot];
        const options = { ...audio, link:null };
        const link = audio.link != null ? node.graph?.links.get(audio.link) : null;
        const source = link ? node.graph.getNodeById(link.origin_id) : null;
        const sourceSlot = link?.origin_slot;
        // Native slot removal keeps all existing video link indices in sync.
        node.removeInput(audioSlot);
        node.addInput(audio.name, audio.type, options);
        if (source) source.connect(sourceSlot, node, node.inputs.length - 1);
    }
    node.properties.apex_timeline_track_count = count;
    node.setDirtyCanvas(true, true);
    return count;
}

export function connectTrackInput(node, slot, connected) {
    const input = node.inputs[slot];
    const index = videoTrackIndex(input);
    if (index < 0) return;
    connected = connected && input.link != null;
    // Keep one matching empty track/socket ready after the last connected input.
    // Existing tracks and their input numbers never compact on disconnection.
    syncTrackInputs(node, [], connected ? index + 2 : 1);
    if (connected && index > 0) {
        const mode = node.widgets.find(widget => widget.name === "mode");
        if (mode && mode.value !== "Multi") {
            mode.value = "Multi";
            mode.callback?.(mode.value);
        }
    }
}
