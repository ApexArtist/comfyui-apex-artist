/**
 * Apex LoRA Merge Web Extension
 * Dynamic LoRA merge controls for Add, TIES, DARE Linear, DARE-TIES, and SVD
 *
 * Uses the modern ComfyUI extension API:
 * - nodeCreated hook (vs old onNodeCreated prototype patching)
 * - getNodeMenuItems (vs old getExtraMenuOptions prototype patching)
 * - node.properties for serialization (vs custom onSerialize/onConfigure)
 * - widget.hidden for show/hide (still the correct ComfyUI mechanism)
 */

import { app } from "../../../scripts/app.js";

const ALGORITHM_MAP = {
    "Add / Weighted Sum": "add",
    "TIES - Trim, Elect Sign, Merge": "ties",
    "DARE Linear - Drop And REscale": "dare_linear",
    "DARE-TIES - DARE + TIES (Recommended)": "dare_ties",
    "SVD - Rank Reduction": "svd",
    "add": "add",
    "ties": "ties",
    "dare_linear": "dare_linear",
    "dare_ties": "dare_ties",
    "svd": "svd",
};

function normalizeMergeAlgorithm(algorithm) {
    return ALGORITHM_MAP[algorithm] ?? "dare_ties";
}

/**
 * Apply hidden state to LoRA slot widgets without triggering any resize.
 * Safe to call at any time — only touches widget.hidden flags.
 */
function applyLoraSlotHidden(node, count) {
    if (!node.widgets) return;
    for (let i = 0; i < 20; i++) {
        const shouldShow = i < count;
        for (const suffix of ["_enabled", "_name", "_strength", "_tower"]) {
            const w = node.widgets.find(w => w.name === `lora_${i}${suffix}`);
            if (w) w.hidden = !shouldShow;
        }
    }
}

/**
 * Resize the node to fit its visible widgets.
 * Captures the current width BEFORE any layout recalculation so that
 * setSize can never shrink the node horizontally — only grow or keep width.
 *
 * Always deferred to requestAnimationFrame so widget dimensions are settled
 * before computeSize() is called. This prevents the horizontal auto-collapse
 * that occurs when setSize is called mid-layout (e.g. during nodeCreated or
 * immediately after hiding/showing widgets in a callback).
 */
function deferredResize(node) {
    // Capture current width now, before the frame fires, so that user-resized
    // nodes are not shrunk even if the widget list changes in the meantime.
    const capturedWidth = node.size?.[0] ?? 0;

    requestAnimationFrame(() => {
        if (!node.graph) return; // node may have been removed before the frame fires
        const computed = node.computeSize();
        const w = Math.max(capturedWidth, computed[0]);
        node.setSize([w, computed[1]]);
        node.setDirtyCanvas(true, true);
    });
}

/**
 * Update visibility of merge parameter widgets based on selected algorithm.
 * Does NOT resize — caller is responsible for calling deferredResize if needed.
 */
function updateMergeParamVisibility(node) {
    if (!node.widgets) return;

    const algorithmWidget = node.widgets.find(w => w.name === "merge_algorithm");
    const densityWidget   = node.widgets.find(w => w.name === "merge_density");
    const rankWidget      = node.widgets.find(w => w.name === "merge_rank");
    const thresholdWidget = node.widgets.find(w => w.name === "merge_threshold");

    if (!algorithmWidget) return;

    const algorithm = normalizeMergeAlgorithm(algorithmWidget.value);

    // density is used by: ties, dare_linear, dare_ties
    if (densityWidget)   densityWidget.hidden   = algorithm === "add" || algorithm === "svd";
    // rank and threshold are only for svd
    if (rankWidget)      rankWidget.hidden      = algorithm !== "svd";
    if (thresholdWidget) thresholdWidget.hidden = algorithm !== "svd";
}

app.registerExtension({
    name: "ApexArtist.LoraStack",

    /**
     * nodeCreated fires once per node instance — cleaner than patching
     * nodeType.prototype.onNodeCreated and avoids double-binding issues.
     *
     * We apply hidden states immediately (no widget flash), then defer the
     * actual setSize call to the next animation frame. During nodeCreated,
     * widget dimensions have not been computed yet, so computeSize() returns
     * near-zero height and causes the node to appear auto-collapsed.
     */
    nodeCreated(node) {
        if (node.comfyClass !== "ApexLoRAStack") return;

        const loraCountWidget = node.widgets?.find(w => w.name === "lora_count");
        const initialCount = loraCountWidget?.value ?? 3;

        // Apply hidden states immediately so widgets don't flash visible
        applyLoraSlotHidden(node, initialCount);
        updateMergeParamVisibility(node);

        // Defer setSize until after the first render frame
        deferredResize(node);

        // ── Hook lora_count changes ──────────────────────────────────────────
        if (loraCountWidget) {
            const origCallback = loraCountWidget.callback;
            loraCountWidget.callback = function(value) {
                // Apply hidden flags synchronously (no flash on next paint)
                applyLoraSlotHidden(node, value);
                // Defer the actual resize so computeSize() sees settled layout
                deferredResize(node);
                origCallback?.call(this, value);
            };
        }

        // ── Hook merge_algorithm changes ─────────────────────────────────────
        const algorithmWidget = node.widgets?.find(w => w.name === "merge_algorithm");
        if (algorithmWidget) {
            const origCallback = algorithmWidget.callback;
            algorithmWidget.callback = function(value) {
                updateMergeParamVisibility(node);
                deferredResize(node);
                origCallback?.call(this, value);
            };
        }
    },

    /**
     * getNodeMenuItems replaces the old getExtraMenuOptions prototype patching.
     * Return an empty array (not null/undefined) for nodes we don't own.
     */
    getNodeMenuItems(node) {
        if (node.type !== "ApexLoRAStack") return [];

        return [
            {
                content: "Enable All LoRAs",
                callback: () => {
                    if (!node.widgets) return;
                    const loraCountWidget = node.widgets.find(w => w.name === "lora_count");
                    const count = loraCountWidget?.value ?? 20;
                    for (let i = 0; i < count; i++) {
                        const w = node.widgets.find(w => w.name === `lora_${i}_enabled`);
                        if (w) w.value = true;
                    }
                    node.setDirtyCanvas(true, true);
                }
            },
            {
                content: "Disable All LoRAs",
                callback: () => {
                    if (!node.widgets) return;
                    const loraCountWidget = node.widgets.find(w => w.name === "lora_count");
                    const count = loraCountWidget?.value ?? 20;
                    for (let i = 0; i < count; i++) {
                        const w = node.widgets.find(w => w.name === `lora_${i}_enabled`);
                        if (w) w.value = false;
                    }
                    node.setDirtyCanvas(true, true);
                }
            },
            {
                content: "Reset All Strengths to 1.0",
                callback: () => {
                    if (!node.widgets) return;
                    const loraCountWidget = node.widgets.find(w => w.name === "lora_count");
                    const count = loraCountWidget?.value ?? 20;
                    for (let i = 0; i < count; i++) {
                        const w = node.widgets.find(w => w.name === `lora_${i}_strength`);
                        if (w) w.value = 1.0;
                    }
                    node.setDirtyCanvas(true, true);
                }
            }
        ];
    },

    /**
     * loadedGraphNode fires after a node is restored from a saved workflow.
     * Re-apply visibility based on restored widget values, then deferred resize.
     */
    loadedGraphNode(node) {
        if (node.type !== "ApexLoRAStack") return;

        const loraCountWidget = node.widgets?.find(w => w.name === "lora_count");
        const count = loraCountWidget?.value ?? 3;

        applyLoraSlotHidden(node, count);
        updateMergeParamVisibility(node);
        deferredResize(node);
    }
});