async function result(response) {
    if (response.status === 404) throw new Error('Restart ComfyUI after the queue finishes to enable Save/Open Project.');
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Could not read the timeline project.');
    return data;
}

export async function saveTimelineProject(api, project, editor) {
    const document = await result(await api.fetchApi(`/apex/timeline/project/save?${new URLSearchParams({project_id:project.project_id,project_name:project.name})}`));
    document.editor = editor;
    const url = URL.createObjectURL(new Blob([JSON.stringify(document,null,2)], {type:'application/json'}));
    const link = window.document.createElement('a');
    link.href = url;
    link.download = (project.name.replace(/[^a-zA-Z0-9._-]+/g,'-') || 'Apex-Timeline') + '.apex-timeline.json';
    window.document.body.append(link); link.click(); link.remove();
    setTimeout(()=>URL.revokeObjectURL(url),1000);
}

export async function openTimelineProject(api, nodeId, file) {
    const document = JSON.parse(await file.text());
    const project = await result(await api.fetchApi('/apex/timeline/project/open', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body:JSON.stringify({node_id:String(nodeId), document}),
    }));
    const saved = document.editor || {};
    const finite = (value,fallback) => Number.isFinite(value) ? value : fallback;
    return {project, editor:{
        playhead:Math.max(0,finite(saved.playhead,0)), selectedId:typeof saved.selectedId==='string' ? saved.selectedId : null,
        scale:Math.max(.01,Math.min(120,finite(saved.scale,18))), fitView:saved.fitView===true,
        snapEnabled:saved.snapEnabled!==false, binVisible:saved.binVisible===true,
        scrollLeft:Math.max(0,finite(saved.scrollLeft,0)), scrollTop:Math.max(0,finite(saved.scrollTop,0)),
    }};
}
