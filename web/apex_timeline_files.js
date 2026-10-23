function el(tag, props = {}, children = []) {
    const node = Object.assign(document.createElement(tag), props);
    node.append(...children);
    return node;
}

const cleanPath = value => value.trim().replace(/^["'](.*)["']$/, "$1");

export function parentFolder(path = "") {
    return path.replace(/[\\/][^\\/]*$/, "") || path;
}

export function droppedSourcePaths(transfer) {
    const paths = [...transfer.files].map(file => file.path).filter(Boolean);
    if (paths.length === transfer.files.length && paths.length) return paths;
    const text = transfer.getData("text/uri-list") || transfer.getData("text/plain");
    return text.split(/\r?\n/).filter(line => line.startsWith("file:") || /^[a-z]:[\\/]/i.test(line) || line.startsWith("\\\\")).map(line => {
        if (!line.startsWith("file:")) return line;
        const url = new URL(line);
        return (url.hostname ? `//${url.hostname}` : "") + decodeURIComponent(url.pathname).replace(/^\/([a-z]:)/i, "$1");
    });
}

export function chooseTimelineSources(api, { title="Link source clips", initialPath="", names=[], search=false } = {}) {
    return new Promise(resolve => {
        const dialog = el("dialog", { className:"apex-source-dialog" });
        dialog.setAttribute("aria-label",title);
        const path = el("input", {type:"text", value:initialPath || localStorage.getItem("apex-timeline-source-folder") || "",
            placeholder:"Full folder path, or a full media path"});
        path.setAttribute("aria-label","Folder or source path");
        const status = el("p", {className:"apex-source-status"});
        const list = el("div", {className:"apex-source-list"});
        const roots = el("div", {className:"apex-source-roots"});
        const recursive = el("input", {type:"checkbox", checked:true});
        recursive.setAttribute("aria-label","Search subfolders");
        const selected = new Set();
        let current = "", parent = "", finished = false;
        const finish = result => {
            if (finished) return;
            finished = true; dialog.close(); dialog.remove(); resolve(result);
        };
        const button = (name, action) => el("button", {type:"button", textContent:name, onclick:action});
        async function browse(directory) {
            status.textContent="Loading folder…";
            try {
                const response = await api.fetchApi(`/apex/timeline/files?${new URLSearchParams({directory:cleanPath(directory)})}`);
                const result = await response.json();
                if (!response.ok) throw new Error(result.error);
                current=result.directory; parent=result.parent; path.value=current;
                localStorage.setItem("apex-timeline-source-folder",current);
                selected.clear(); list.replaceChildren(); roots.replaceChildren();
                for (const root of result.roots) roots.append(button(root,()=>browse(root)));
                for (const entry of result.entries) {
                    if (entry.directory) list.append(button(`📁 ${entry.name}`,()=>browse(entry.path)));
                    else if (!search) {
                        const check=el("input",{type:"checkbox", checked:names.includes(entry.name)});
                        check.setAttribute("aria-label",entry.name);
                        if (check.checked) selected.add(entry.path);
                        check.onchange=()=>check.checked?selected.add(entry.path):selected.delete(entry.path);
                        list.append(el("label",{},[check,el("span",{textContent:entry.name})]));
                    }
                }
                status.textContent=result.truncated?"Showing the first 1,000 entries. Paste a full media path to select another file.":
                    search?"Choose the folder to search. Files are matched by name and saved size; ambiguous matches stay missing.":"Media stay in their original location. Select media or paste a full media path.";
            } catch (error) { status.textContent=error.message; }
        }
        const accept=button(search?"Search this folder":"Link selected files",()=>{
            if (search) finish({directory:cleanPath(path.value) || current, recursive:recursive.checked});
            else {
                const typed=cleanPath(path.value);
                const paths=/\.(mp4|mov|mkv|webm|avi|m4v|wav|mp3|flac|ogg|m4a|aac|opus)$/i.test(typed)?[typed]:[...selected];
                if (!paths.length) {status.textContent="Select media or paste its full original path.";return;}
                finish({paths});
            }
        });
        path.onkeydown=event=>{if(event.key==="Enter"){event.preventDefault();/\.(mp4|mov|mkv|webm|avi|m4v|wav|mp3|flac|ogg|m4a|aac|opus)$/i.test(path.value)?accept.click():browse(path.value);}};
        dialog.append(el("h2",{textContent:title}),
            ...(names.length?[el("p",{textContent:`Locate the original source: ${names.join(", ")}`})]:[]),
            el("div",{className:"apex-source-path"},[path,button("Open folder",()=>browse(path.value)),button("Up",()=>browse(parent)),button("Home",()=>browse(""))]),
            roots,status,list,
            ...(search?[el("label",{},[recursive,el("span",{textContent:"Search subfolders"})])]:[]),
            el("div",{className:"apex-source-footer"},[button("Cancel",()=>finish(null)),accept]));
        dialog.addEventListener("cancel",event=>{event.preventDefault();finish(null);});
        document.body.append(dialog); dialog.showModal(); browse(path.value);
    });
}

export function missingClipMenu(event, {locate, search}) {
    event.preventDefault(); event.stopPropagation();
    document.querySelector(".apex-missing-menu")?.remove();
    const menu=el("div",{className:"apex-missing-menu"});
    menu.setAttribute("role","menu");
    menu.style.left=`${Math.min(event.clientX,window.innerWidth-260)}px`;
    menu.style.top=`${Math.min(event.clientY,window.innerHeight-100)}px`;
    const close=()=>{menu.remove();document.removeEventListener("pointerdown",outside,true);};
    const outside=event=>{if(!menu.contains(event.target))close();};
    for (const [text,action] of [["Locate missing clip…",locate],["Search for missing clips…",search]]) {
        const button=el("button",{textContent:text,onclick:()=>{close();action();}});
        button.setAttribute("role","menuitem"); menu.append(button);
    }
    document.body.append(menu); document.addEventListener("pointerdown",outside,true);
}

export const sourceDialogStyles = `
.apex-source-dialog { width:min(760px,90vw); max-height:86vh; padding:20px; color:#e8edf4; background:#20242b; border:1px solid #66778a; border-radius:10px; font:14px sans-serif; }
.apex-source-dialog::backdrop { background:#0009; }
.apex-source-dialog h2 { margin:0 0 12px; font-size:19px; }
.apex-source-dialog p { line-height:1.4; overflow-wrap:anywhere; }
.apex-source-dialog button { padding:7px 10px; color:#e8edf4; background:#303a48; border:1px solid #566579; border-radius:4px; cursor:pointer; }
.apex-source-path { display:flex; gap:6px; }
.apex-source-path input { flex:1; min-width:0; padding:7px; color:#fff; background:#13171d; border:1px solid #566579; }
.apex-source-roots, .apex-source-footer { display:flex; gap:6px; margin-top:10px; }
.apex-source-footer { justify-content:flex-end; }
.apex-source-status { color:#b6c7dc; }
.apex-source-list { display:grid; gap:3px; max-height:36vh; overflow:auto; border:1px solid #414c5c; padding:6px; }
.apex-source-list button { text-align:left; }
.apex-source-dialog label { display:flex; align-items:center; gap:8px; padding:5px; }
.apex-missing-menu { position:fixed; z-index:100000; display:grid; gap:3px; padding:5px; background:#20242b; border:1px solid #66778a; border-radius:5px; }
.apex-missing-menu button { padding:9px 12px; text-align:left; border:0; color:#e8edf4; background:#303a48; cursor:pointer; }
`;
