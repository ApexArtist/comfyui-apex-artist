import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import test from 'node:test';

const source=await readFile(new URL('../web/apex_optional_images_inputs.js',import.meta.url),'utf8');
const {repairImageInputs}=await import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`);

function fixture(ordinals,max=100) {
    let serial=0;
    const links=new Map(),sources=new Map();
    const node={inputs:[],size:[400,600],comfyDynamic:{autogrow:{images:{max}}},
        graph:{getNodeById:id=>sources.get(id)},getInputLink(slot){return links.get(this.inputs[slot]?.link);},
        addInput(name,type,options={}){const input={name,type,link:null,...options};this.inputs.push(input);return input;},
        removeInput(slot){const [input]=this.inputs.splice(slot,1);links.delete(input.link);},
        computeSize(){return [400,50+this.inputs.length*20];},setSize(size){this.size=size;},setDirtyCanvas(){},
        onConnectionsChange(type,slot,connected){
            if(connected&&slot===this.inputs.length-1&&this.inputs.length<max)this.addInput(`images.image_${this.inputs.length}`,'IMAGE');
        }};
    for(const [slot,ordinal] of ordinals.entries()) {
        const input=node.addInput(`images.image_${ordinal==null?slot:ordinal}`,'IMAGE',{localized_name:'stale label'});
        if(ordinal==null)continue;
        const id=`source-${slot}`,origin={connect(output,target,index,parentId){
            const link={id:++serial,origin_id:id,origin_slot:output,parentId};links.set(link.id,link);target.inputs[index].link=link.id;
            target.onConnectionsChange(1,index,true,link);return link;
        }};
        sources.set(id,origin);
        const link={id:++serial,origin_id:id,origin_slot:0,parentId:slot+50};links.set(link.id,link);input.link=link.id;
    }
    return {node,order:()=>node.inputs.map((_,i)=>node.getInputLink(i)?.origin_id).filter(Boolean)};
}

test('restores the missing next socket without losing five image sources or reroutes',()=>{
    const {node,order}=fixture([0,1,2,3,4]);
    assert.equal(repairImageInputs(node),true);
    assert.deepEqual(order(),['source-0','source-1','source-2','source-3','source-4']);
    assert.equal(node.inputs.at(-1).name,'images.image_5');
    assert.equal(node.getInputLink(3).parentId,53);
    assert.deepEqual(node.size,[400,600]);
});

test('repairs double-digit reload order, duplicate names and empty holes',()=>{
    const {node,order}=fixture([0,1,10,11,2,3,4,5,null,6,7,8,9,3]);
    assert.equal(repairImageInputs(node),true);
    assert.deepEqual(order(),[0,1,4,5,13,6,7,9,10,11,12,2,3].map(i=>`source-${i}`));
    assert.deepEqual(node.inputs.map(i=>i.name),Array.from({length:14},(_,i)=>`images.image_${i}`));
    assert.equal(node.inputs.at(-1).link,null);
});

test('leaves healthy links and custom labels intact',()=>{
    const {node}=fixture([0,1,null]);node.inputs[0].label='Singer';
    const links=node.inputs.map(i=>i.link);
    assert.equal(repairImageInputs(node),false);
    assert.deepEqual(node.inputs.map(i=>i.link),links);
    assert.equal(node.inputs[0].label,'Singer');
});

test('accepts an empty node and a full native group',()=>{
    const empty=fixture([null]).node;assert.equal(repairImageInputs(empty),false);
    const full=fixture([0,1,2,3],4).node;assert.equal(repairImageInputs(full),false);
    assert.equal(full.inputs.length,4);
});
