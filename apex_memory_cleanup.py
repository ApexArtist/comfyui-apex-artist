"""Explicit cleanup boundary after a saved clip or completed image operation."""

import gc
import json
import logging

import comfy.model_management as mm
from comfy_api.latest import io
from .apex_loop_memory import release_completed_outputs


class ApexMemoryCleanup(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="ApexMemoryCleanup", display_name="Apex Memory Cleanup",
            category="Apex Artist/Utilities",
            description="Run after saving a result. Releases finished clip cache in an uncached native loop, or finished upstream intermediates outside a loop. Preserves pending readers and shared models. Does not clear private custom-node caches.",
            inputs=[
                io.AnyType.Input("trigger", tooltip="Connect the save/capture result, then connect value onward to End Loop. Use a file-backed video or small completion value; passing an image/latent keeps that input alive."),
                io.Boolean.Input("release_cache", default=True, tooltip="Release completed outputs. Shared nodes outside the loop and explicit iteration caching are preserved."),
                io.Boolean.Input("gc_collect", default=True, tooltip="Collect unreachable Python objects after releasing cache references."),
                io.Boolean.Input("empty_cache", default=True, tooltip="Release unused device allocations through ComfyUI's memory manager. Live tensors remain allocated."),
                io.Boolean.Input("unload_models", default=False, tooltip="Unload models through ComfyUI. This can force expensive reloads on the next clip; normally leave off."),
            ],
            outputs=[io.AnyType.Output("value"), io.String.Output("report"), io.Int.Output("released_entries")],
            hidden=[io.Hidden.dynprompt, io.Hidden.execution_list, io.Hidden.unique_id],
            is_output_node=True, not_idempotent=True,
        )

    @classmethod
    def execute(cls, trigger, release_cache=True, gc_collect=True, empty_cache=True, unload_models=False):
        device = mm.get_torch_device()
        before = int(mm.get_free_memory(device))
        released, scope = (0, "disabled")
        if release_cache:
            released, scope = release_completed_outputs(cls.hidden.dynprompt, cls.hidden.execution_list, cls.hidden.unique_id)
        if unload_models:
            mm.unload_all_models()
        if gc_collect:
            gc.collect()
        if empty_cache:
            mm.soft_empty_cache()
        after = int(mm.get_free_memory(device))
        report = {"scope": scope, "released_entries": released, "device": str(device),
                  "device_free_before_bytes": before, "device_free_after_bytes": after,
                  "device_free_change_bytes": after - before, "models_unloaded": bool(unload_models)}
        logging.info("Apex Memory Cleanup: %s", json.dumps(report))
        return io.NodeOutput(trigger, json.dumps(report), released)
