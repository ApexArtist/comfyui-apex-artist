function ancestors(graph, roots) {
    const kept = {};
    function visit(id) {
        if (kept[id]) return;
        const node = graph[id];
        if (!node) throw new Error(`Missing connected node ${id}.`);
        kept[id] = structuredClone(node);
        for (const value of Object.values(node.inputs))
            if (Array.isArray(value) && value.length === 2 && typeof value[1] === "number" && graph[value[0]]) visit(value[0]);
    }
    roots.forEach(visit);
    return kept;
}

// Saved timeline graph loading and export selection.
export function migrateTimelineGraph(graph) {
    const ports = [["VIDEO", "VIDEO"], ["IMAGE", "IMAGE"], ["AUDIO", "AUDIO"], ["FPS", "FLOAT"],
        ["timeline", "APEX_TIMELINE"], ["duration", "FLOAT"], ["clip count", "INT"]];
    const aliases = {video:"VIDEO", images:"IMAGE", audio:"AUDIO", fps:"FPS", clip_count:"clip count"};
    for (const node of graph.nodes || []) {
        if (node.type !== "ApexTimelineEditor") continue;
        const removedLinks = new Set();
        for (let slot = (node.inputs?.length || 0) - 1; slot >= 0; slot--) {
            const input = node.inputs[slot];
            if (!input.name.startsWith("placement_starts.")) continue;
            if (input.link != null) removedLinks.add(input.link);
            node.inputs.splice(slot, 1);
            for (const link of graph.links || []) {
                const array = Array.isArray(link);
                if (String(array ? link[3] : link.target_id) !== String(node.id)) continue;
                const target = array ? link[4] : link.target_slot;
                if (target === slot) removedLinks.add(array ? link[0] : link.id);
                else if (target > slot) {
                    if (array) link[4]--;
                    else link.target_slot--;
                }
            }
        }
        graph.links = (graph.links || []).filter(link => !removedLinks.has(Array.isArray(link) ? link[0] : link.id));
        for (const source of graph.nodes || []) for (const output of source.outputs || [])
            if (output.links) output.links = output.links.filter(id => !removedLinks.has(id));
        const old = node.outputs || [];
        const names = old.map(output => aliases[output.name] || output.name);
        const mapping = names.map(name => ports.findIndex(([label]) => label === name));
        for (const link of graph.links || []) {
            if (Array.isArray(link)) {
                if (String(link[1]) === String(node.id) && mapping[link[2]] >= 0) link[2] = mapping[link[2]];
            } else if (String(link.origin_id) === String(node.id) && mapping[link.origin_slot] >= 0) {
                link.origin_slot = mapping[link.origin_slot];
            }
        }
        node.outputs = ports.map(([name, type], index) => ({
            ...old[names.indexOf(name)], name, localized_name:name, type, slot_index:index,
            links:old[names.indexOf(name)]?.links || null,
        }));
        const removed = node.inputs?.findIndex(input => input.name === "capture_track") ?? -1;
        if (removed >= 0) {
            node.inputs.splice(removed, 1);
            for (const link of graph.links || []) {
                if (Array.isArray(link)) {
                    if (String(link[3]) === String(node.id) && link[4] > removed) link[4]--;
                } else if (String(link.target_id) === String(node.id) && link.target_slot > removed) {
                    link.target_slot--;
                }
            }
            if (Array.isArray(node.widgets_values)) node.widgets_values.splice(6, 1);
            else if (node.widgets_values) delete node.widgets_values.capture_track;
            if (node.widgets_values_named) delete node.widgets_values_named.capture_track;
        }
        if (!node.inputs?.some(input => input.name === "placement_offset")) {
            const slot = node.inputs?.findIndex(input => input.name === "placement_start") ?? -1;
            node.inputs ||= [];
            node.inputs.splice(slot + 1, 0, {name:"placement_offset", type:"FLOAT", shape:7,
                widget:{name:"placement_offset"}, link:null});
            for (const link of graph.links) {
                if (Array.isArray(link)) {
                    if (String(link[3]) === String(node.id) && link[4] > slot) link[4]++;
                } else if (String(link.target_id) === String(node.id) && link.target_slot > slot) link.target_slot++;
            }
            if (Array.isArray(node.widgets_values)) node.widgets_values.splice(6, 0, 0);
            else if (node.widgets_values) node.widgets_values.placement_offset = 0;
            if (node.widgets_values_named) node.widgets_values_named.placement_offset = 0;
        }
        for (const input of node.inputs || []) {
            const match = /^video_tracks\.video_track_(\d+)$/.exec(input.name);
            if (match) input.label = input.localized_name = `Video ${Number(match[1]) + 1} → V${Number(match[1]) + 1}`;
        }
    }
    for (const subgraph of graph.definitions?.subgraphs || []) migrateTimelineGraph(subgraph);
}

export function timelineOutputIds(graph, timeline) {
    return Object.keys(graph).filter(id => ["SaveVideo", "VHS_VideoCombine", "SaveWEBM"].includes(graph[id].class_type)
        && graph[id].inputs.save_output !== false && ancestors(graph, [id])[timeline]);
}

export function timelineExportGraph(source, timeline, output, projectName) {
    const graph = structuredClone(source);
    const inputs = graph[timeline].inputs;
    for (const key of Object.keys(inputs)) if (key.startsWith("video_tracks.")) delete inputs[key];
    delete inputs.placement_start;
    delete inputs.placement_offset;
    delete inputs.audio;
    inputs.project_name = projectName;
    inputs.prepare_outputs = true;
    inputs.capture_policy = "Read Saved";
    for (const node of Object.values(graph)) for (const [key, value] of Object.entries(node.inputs)) {
        let link = value;
        while (Array.isArray(link) && graph[link[0]]?.class_type === "EndLoop")
            link = graph[link[0]].inputs.output_value;
        node.inputs[key] = link;
    }
    return ancestors(graph, [output]);
}
