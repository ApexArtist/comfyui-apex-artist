import { app } from '../../../scripts/app.js';
import { repairImageInputs } from './apex_optional_images_inputs.js';

app.registerExtension({
    name:'ApexArtist.OptionalImages',
    nodeCreated(node) {
        if (node.comfyClass !== 'ApexOptionalImages') return;
        let queued=false, repairing=false;
        const schedule = () => {
            if (queued || repairing) return;
            queued=true;
            requestAnimationFrame(() => {
                queued=false;
                if (!node.graph) return;
                repairing=true;
                try { repairImageInputs(node); }
                finally { repairing=false; }
            });
        };
        const changed=node.onConnectionsChange;
        node.onConnectionsChange=function() {
            const result=changed?.apply(this,arguments);
            schedule();
            return result;
        };
        const configured=node.onConfigure;
        node.onConfigure=function() {
            const result=configured?.apply(this,arguments);
            schedule();
            return result;
        };
        schedule();
    },
});
