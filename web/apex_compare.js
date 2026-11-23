import { app } from "../../../scripts/app.js";
import { api } from "../../../scripts/api.js";

const css = document.createElement("style");
css.textContent = `
.apex-compare{box-sizing:border-box;width:100%;min-width:0;padding:8px;background:#171d24;border-radius:6px;color:#e9eef5;font:12px/1.4 system-ui;display:flex;flex-direction:column;gap:8px}
.apex-compare-stage{position:relative;width:100%;height:280px;overflow:hidden;background:repeating-conic-gradient(#20252b 0% 25%,#292f37 0% 50%) 50% / 20px 20px;touch-action:none;cursor:ew-resize;border-radius:4px}
.apex-compare-layer{position:absolute;inset:0;pointer-events:none}.apex-compare-layer img{position:absolute;width:100%;height:100%;object-fit:contain;display:block}
.apex-compare-line{position:absolute;top:0;bottom:0;border-left:2px solid #fff;pointer-events:none;filter:drop-shadow(0 0 2px #000)}
.apex-compare-line::after{content:'↔';position:absolute;top:50%;left:0;transform:translate(-50%,-50%);background:#22313ee8;color:white;padding:5px;border:1px solid white;border-radius:5px}
.apex-compare-badge{position:absolute;top:8px;max-width:42%;padding:4px 8px;border:1px solid #ffffff60;border-radius:4px;font-weight:700;pointer-events:none;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;z-index:2;text-shadow:0 1px 2px #000}
.apex-compare-a{left:8px;background:#1c668de8}.apex-compare-b{right:8px;background:#87572be8}
.apex-compare-controls{display:flex;align-items:center;gap:8px;min-width:0}.apex-compare input[type=range]{position:static;min-width:30px;width:100%;height:20px;margin:0;accent-color:#75c9f5}
.apex-compare button{flex:none;border:1px solid #536577;border-radius:4px;background:#26313e;color:inherit;padding:3px 8px;cursor:pointer}.apex-compare-status{min-height:17px;color:#abb9c7;font-size:11px;overflow-wrap:anywhere}
`;
document.head.append(css);
const el = (tag,props={}) => Object.assign(document.createElement(tag),props);
const clamp = value => Math.max(0,Math.min(100,Number.isFinite(Number(value)) ? Number(value) : 50));

function createCompare(node) {
    const root=el("div",{className:"apex-compare"});
    const stage=el("div",{className:"apex-compare-stage"});
    const bottom=el("div",{className:"apex-compare-layer"});
    const top=el("div",{className:"apex-compare-layer"});
    const imageB=el("img",{alt:"B comparison image",draggable:false});
    const imageA=el("img",{alt:"A comparison image",draggable:false});
    bottom.append(imageB);top.append(imageA);
    const line=el("div",{className:"apex-compare-line"});
    const badgeA=el("div",{className:"apex-compare-badge apex-compare-a",textContent:"A · Original"});
    const badgeB=el("div",{className:"apex-compare-badge apex-compare-b",textContent:"B · Result"});
    stage.append(bottom,top,line,badgeA,badgeB);
    const controls=el("div",{className:"apex-compare-controls"});
    const range=el("input",{type:"range",min:"0",max:"100",step:"0.1",value:"50"});
    range.setAttribute("aria-label","A/B wipe position — A on left, B on right");
    const reset=el("button",{type:"button",textContent:"50 / 50",title:"Center the wipe"});
    const status=el("div",{className:"apex-compare-status",textContent:"Connect images A and B, then run this node."});
    controls.append(range,reset);root.append(stage,controls,status);
    let disposed=false, generation=0, metadata=null, pending=[];
    node.properties ??= {};
    function wipe(value) {
        const at=clamp(value);range.value=String(at);
        top.style.clipPath=`inset(0 ${100-at}% 0 0)`;
        line.style.left=`${at}%`;
        node.properties.apex_compare_wipe=at;
    }
    function labels() {
        const widget=name=>node.widgets?.find(w=>w.name===name)?.value;
        badgeA.textContent=`A · ${metadata?.label_a ?? widget("label_a") ?? "Original"}`;
        badgeB.textContent=`B · ${metadata?.label_b ?? widget("label_b") ?? "Result"}`;
    }
    function point(event) {
        const rect=stage.getBoundingClientRect();
        if(rect.width>0)wipe((event.clientX-rect.left)/rect.width*100);
    }
    stage.addEventListener("pointerdown",event=>{
        if(event.button!==0)return;
        event.preventDefault();event.stopPropagation();stage.setPointerCapture(event.pointerId);point(event);
    });
    stage.addEventListener("pointermove",event=>{if(stage.hasPointerCapture(event.pointerId)){event.stopPropagation();point(event);}});
    for(const type of ["pointerup","pointercancel"])stage.addEventListener(type,event=>{
        if(stage.hasPointerCapture(event.pointerId))stage.releasePointerCapture(event.pointerId);
    });
    // Keep controls from moving/collapsing the parent graph node.
    root.addEventListener("pointerdown",event=>event.stopPropagation());
    root.addEventListener("dblclick",event=>event.stopPropagation());
    range.addEventListener("input",()=>wipe(range.value));reset.addEventListener("click",()=>wipe(50));
    function clearPending() {for(const img of pending){img.onload=null;img.onerror=null;img.removeAttribute("src");}pending=[];}
    function show(message) {
        const info=message?.apex_compare?.[0];
        if(!info?.a?.filename || !info?.b?.filename || disposed)return;
        // Cached output restoration may deliver the same message repeatedly.
        if(metadata && JSON.stringify(info)===JSON.stringify(metadata))return;
        const ticket=++generation;clearPending();metadata=info;labels();status.textContent="Loading A and B…";
        const load=file=>new Promise((resolve,reject)=>{
            const img=new Image();pending.push(img);img.onload=()=>resolve(img);img.onerror=reject;
            img.src=api.apiURL(`/view?${new URLSearchParams({filename:file.filename,subfolder:file.subfolder??"",type:file.type??"temp"})}`);
        });
        Promise.all([load(info.a),load(info.b)]).then(([a,b])=>{
            if(disposed||ticket!==generation)return;
            imageA.src=a.src;imageB.src=b.src;clearPending();
            const size=s=>Array.isArray(s)?s.join(" × "):"?";
            status.textContent=`A: ${size(info.size_a)} · frame ${info.frame_a} | B: ${size(info.size_b)} · frame ${info.frame_b}. Fit view; original outputs unchanged.`;
        }).catch(()=>{
            if(disposed||ticket!==generation)return;
            metadata=null;clearPending();imageA.removeAttribute("src");imageB.removeAttribute("src");
            status.textContent="Preview unavailable. Temporary images may have expired; run this node again.";
        });
    }
    wipe(node.properties.apex_compare_wipe??50);labels();
    return {element:root,show,restore:()=>{wipe(node.properties.apex_compare_wipe??50);labels();},
        destroy:()=>{disposed=true;++generation;clearPending();imageA.removeAttribute("src");imageB.removeAttribute("src");root.remove();}};
}

app.registerExtension({
    name:"Apex.Compare",
    onNodeOutputsUpdated(outputs) {
        // ComfyUI restores cached/history output through an extension hook,
        // rather than the live per-node onExecuted callback.
        const find=(graph,path)=>{
            if(!graph)return null;
            const direct=graph.getNodeById(path);
            if(direct)return direct;
            for(let at=path.indexOf(":");at>=0;at=path.indexOf(":",at+1)){
                const parent=graph.getNodeById(path.slice(0,at));
                if(parent?.subgraph){const result=find(parent.subgraph,path.slice(at+1));if(result)return result;}
            }
            return null;
        };
        for(const [id,output] of Object.entries(outputs??{})){
            if(output?.apex_compare)find(app.rootGraph??app.graph,String(id))?._apexCompare?.show(output);
        }
    },
    nodeCreated(node) {
        if((node.comfyClass??node.constructor.comfyClass)!=="ApexCompare" || node._apexCompare)return;
        node._apexCompare=createCompare(node);
        node.addDOMWidget("apex_compare_view","apex_compare",node._apexCompare.element,{
            serialize:false,hideOnZoom:false,getMinHeight:()=>380,getMaxHeight:()=>380,
            onDraw:widget=>{widget.width=node.size[0];}
        });
        node.setSize([Math.max(node.size[0],560),Math.max(node.size[1],530)]);
        const executed=node.onExecuted,configured=node.onConfigure,removed=node.onRemoved;
        node.onExecuted=function(output,...rest){const result=executed?.call(this,output,...rest);this._apexCompare?.show(output);return result;};
        node.onConfigure=function(...args){const result=configured?.apply(this,args);this._apexCompare?.restore();return result;};
        node.onRemoved=function(...args){this._apexCompare?.destroy();this._apexCompare=null;return removed?.apply(this,args);};
    }
});
