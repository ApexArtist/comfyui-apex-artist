export function repairImageInputs(node) {
    const group = node.comfyDynamic?.autogrow?.images;
    if (!group || !node.graph) return false;
    const entries = node.inputs.map((input, slot) => ({ input, link:node.getInputLink(slot), slot }));
    const connected = entries.filter(item => item.link).sort((a,b) => {
        const ordinal = item => Number(item.input.name.match(/image_(\d+)$/)?.[1] ?? item.slot);
        return ordinal(a) - ordinal(b) || a.slot - b.slot;
    });
    const expected = Math.min(group.max, connected.length + 1);
    const canonical = entries.length === expected && entries.every((item,index) =>
        item.input.name === `images.image_${index}` && !!item.link === (index < connected.length));
    if (canonical) {
        for (const {input} of entries) input.localized_name = input.name.slice(7);
        return false;
    }
    const sources = connected.map(({input,link}) => ({
        source:node.graph.getNodeById(link.origin_id), slot:link.origin_slot,
        reroute:link.parentId, label:input.label,
    }));
    if (sources.some(item => !item.source)) return false;
    const changed = node.onConnectionsChange;
    const size = [...node.size];
    try {
        // Native remove/connect keeps the frontend link store synchronized.
        // Suppress queued native compaction while replacing the broken slots.
        node.onConnectionsChange = () => {};
        for (let slot=node.inputs.length-1;slot>=0;slot--) node.removeInput(slot);
        node.addInput('images.image_0','IMAGE',{shape:7,localized_name:'image_0'});
        node.onConnectionsChange = changed;
        for (const [index,item] of sources.entries()) {
            item.source.connect(item.slot,node,index,item.reroute);
            if (item.label) node.inputs[index].label = item.label;
        }
    } finally {
        node.onConnectionsChange = changed;
    }
    node.setSize([size[0],Math.max(size[1],node.computeSize()[1])]);
    node.setDirtyCanvas(true,true);
    return true;
}
