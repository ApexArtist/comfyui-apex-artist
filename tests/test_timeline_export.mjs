import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const source = await readFile(new URL("../web/apex_timeline_graph.js", import.meta.url), "utf8");
const { timelineExportGraph, timelineOutputIds } = await import(
    `data:text/javascript;base64,${Buffer.from(source).toString("base64")}`
);

function graph() {
    return {
        audio: { class_type: "ApexAudio", inputs: { audio_file: "song.wav" } },
        start: { class_type: "StartLoop", inputs: { mode: "simple", "mode.num_iterations": 7 } },
        generate: { class_type: "GenerateVideo", inputs: { iteration: ["start", 0] } },
        timeline: { class_type: "ApexTimelineEditor", inputs: {
            project_name: "Old project", audio: ["audio", 0],
            "video_tracks.video_track_0": ["generate", 0],
            placement_start: ["start", 0], placement_offset: 0,
            prepare_outputs: ["start", 2], capture_policy: "Every Queue",
        } },
        end: { class_type: "EndLoop", inputs: { output_value: ["timeline", 0] } },
        full: { class_type: "SaveVideo", inputs: { video: ["end", 0], filename_prefix: "full", format: "mp4" } },
        native: { class_type: "SaveVideo", inputs: { video: ["timeline", 0], filename_prefix: "native", format: "auto" } },
        disabled: { class_type: "VHS_VideoCombine", inputs: { images: ["timeline", 1], save_output: false } },
        unrelated: { class_type: "SaveVideo", inputs: { video: ["generate", 0] } },
    };
}

test("finds both timeline save branches and excludes disabled or unrelated saves", () => {
    assert.deepEqual(timelineOutputIds(graph(), "timeline"), ["full", "native"]);
});

test("exports every selected saver using saved clips without entering generation", () => {
    const original = graph();
    const snapshot = structuredClone(original);
    const result = timelineExportGraph(original, "timeline", timelineOutputIds(original, "timeline"), "Saved project");
    assert.deepEqual(Object.keys(result).sort(), ["full", "native", "timeline"]);
    assert.deepEqual(result.full.inputs.video, ["timeline", 0]);
    assert.deepEqual(result.native.inputs.video, ["timeline", 0]);
    assert.equal(result.full.inputs.format, "mp4");
    assert.equal(result.native.inputs.format, "auto");
    assert.deepEqual(result.timeline.inputs, {
        project_name: "Saved project", prepare_outputs: true, capture_policy: "Read Saved",
    });
    assert.deepEqual(original, snapshot);
});

test("keeps single-output callers working", () => {
    const result = timelineExportGraph(graph(), "timeline", "native", "Saved project");
    assert.deepEqual(Object.keys(result).sort(), ["native", "timeline"]);
});

test("keeps multiple native IMAGE AUDIO FPS combine inputs", () => {
    const original = graph();
    original.combine = { class_type: "VHS_VideoCombine", inputs: {
        images: ["timeline", 1], audio: ["timeline", 2], frame_rate: ["timeline", 3], save_output: true,
    } };
    const ids = timelineOutputIds(original, "timeline");
    assert.deepEqual(ids, ["full", "native", "combine"]);
    const result = timelineExportGraph(original, "timeline", ids, "Saved project");
    assert.deepEqual(result.combine, original.combine);
    assert.deepEqual(Object.keys(result).sort(), ["combine", "full", "native", "timeline"]);
});
