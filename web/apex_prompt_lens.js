/**
 * Apex Camera Lens - Simple dropdown preset (browser removed)
 */

import { app } from "../../../scripts/app.js";

// Register the extension
app.registerExtension({
    name: "ApexArtist.LensPreset",
    
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "ApexPromptPreset") {
            // Nothing special needed - just use the default dropdown widget
            // The camera_lens_preset widget will work as a standard ComfyUI dropdown
        }
    }
});
