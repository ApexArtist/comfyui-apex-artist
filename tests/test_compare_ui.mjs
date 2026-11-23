import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

class Element {
    constructor(tag){this.tag=tag;this.children=[];this.style={};this.events={};this.attrs={};this.captured=new Set();}
    append(...items){this.children.push(...items);}
    setAttribute(k,v){this.attrs[k]=v;}
    removeAttribute(k){delete this.attrs[k];if(k==="src")this._src="";}
    addEventListener(k,fn){(this.events[k]??=[]).push(fn);}
    fire(k,data={}){for(const fn of this.events[k]??[])fn({button:0,pointerId:1,clientX:0,preventDefault(){},stopPropagation(){},...data});}
    getBoundingClientRect(){return {left:100,width:400};}
    setPointerCapture(id){this.captured.add(id);}
    hasPointerCapture(id){return this.captured.has(id);}
    releasePointerCapture(id){this.captured.delete(id);}
    remove(){this.removed=true;}
}
let loads=0,extension;const app={registerExtension:x=>{extension=x;}};
class ImageMock extends Element {
    constructor(){super("img");}
    set src(value){this._src=value;++loads;queueMicrotask(()=>value.includes("missing")?this.onerror?.():this.onload?.());}
    get src(){return this._src;}
}
const source=fs.readFileSync(new URL("../web/apex_compare.js",import.meta.url),"utf8").replace(/^import .*;\r?\n/gm,"");
vm.runInNewContext(source,{document:{createElement:tag=>new Element(tag),head:new Element("head")},Image:ImageMock,URLSearchParams,Promise,app,api:{apiURL:x=>x}});
function node(properties={}){
    return {comfyClass:"ApexCompare",properties,size:[300,200],widgets:[{name:"label_a",value:"Input"},{name:"label_b",value:"Upscale"}],
        addDOMWidget(name,type,element,options){this.dom={name,type,element,options};},setSize(size){this.size=size;}};
}
const n=node({apex_compare_wipe:25});extension.nodeCreated(n);
assert.equal(n.dom.options.serialize,false);assert.deepEqual(Array.from(n.size),[560,530]);
const [stage,controls,status]=n.dom.element.children;
const [bottom,top,line,badgeA,badgeB]=stage.children;
const [slider,reset]=controls.children;
assert.equal(top.style.clipPath,"inset(0 75% 0 0)");assert.equal(badgeA.textContent,"A · Input");assert.equal(badgeB.textContent,"B · Upscale");
stage.fire("pointerdown",{clientX:400});assert.equal(n.properties.apex_compare_wipe,75);
stage.fire("pointerup");assert.equal(stage.hasPointerCapture(1),false);
slider.value="110";slider.fire("input");assert.equal(n.properties.apex_compare_wipe,100);
reset.fire("click");assert.equal(n.properties.apex_compare_wipe,50);
const output={apex_compare:[{a:{filename:"a.png",type:"temp"},b:{filename:"b.png",type:"temp"},label_a:"Before <b>",label_b:"After",size_a:[1920,1080],size_b:[3840,2160],frame_a:0,frame_b:0}]};
n.onExecuted(output);await new Promise(resolve=>setTimeout(resolve,0));
assert.equal(badgeA.textContent,"A · Before <b>");assert.equal(badgeB.textContent,"B · After");
assert.match(top.children[0].src,/filename=a.png/);assert.match(bottom.children[0].src,/filename=b.png/);
assert.match(status.textContent,/1920 × 1080/);assert.equal(loads,2);
app.rootGraph={getNodeById:id=>String(id)==='1'?n:null};extension.onNodeOutputsUpdated({'1':output});await new Promise(resolve=>setTimeout(resolve,0));assert.equal(loads,2);
n.properties.apex_compare_wipe=12;n.onConfigure();assert.equal(line.style.left,"12%");
// Output restoration also works on a newly-created/cached node.
const cached=node();extension.nodeCreated(cached);
app.rootGraph={getNodeById:id=>String(id)==='100'?{subgraph:{getNodeById:id=>String(id)==='2'?cached:null}}:null};extension.onNodeOutputsUpdated({'100:2':output});
await new Promise(resolve=>setTimeout(resolve,0));assert.match(cached.dom.element.children[2].textContent,/original outputs unchanged/);
const failed={apex_compare:[{...output.apex_compare[0],a:{filename:"missing.png"}}]};
n.onExecuted(failed);await new Promise(resolve=>setTimeout(resolve,0));assert.match(status.textContent,/Preview unavailable/);
n.onExecuted(output);n.onRemoved();await new Promise(resolve=>setTimeout(resolve,0));assert.equal(n._apexCompare,null);assert.equal(n.dom.element.removed,true);
console.log("Apex Compare UI: wipe, labels, pointer scaling, keyboard slider, cached restoration, expiry and disposal passed.");
