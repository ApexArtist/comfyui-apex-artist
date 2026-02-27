/**
 * ApexRGBCurve Web Interface
 * Interactive Photoshop-style RGB curve editor for ComfyUI
 */

import { app } from "/scripts/app.js";
import { ComfyWidgets } from "/scripts/widgets.js";

// Custom ComfyUI Widget Type
function RGBCurveWidgetComfy(node, inputName, inputData, app) {
    // Define cinematic and film presets
    const CURVE_PRESETS = {
        "Linear (Reset)": {
            "RGB": [[0, 0], [255, 255]],
            "Red": [[0, 0], [255, 255]],
            "Green": [[0, 0], [255, 255]],
            "Blue": [[0, 0], [255, 255]]
        },
        "Film Noir": {
            "RGB": [[0, 15], [64, 45], [128, 128], [192, 200], [255, 240]],
            "Red": [[0, 0], [128, 140], [255, 255]],
            "Green": [[0, 0], [128, 120], [255, 255]],
            "Blue": [[0, 10], [128, 115], [255, 240]]
        },
        "Warm Sunset": {
            "RGB": [[0, 0], [128, 140], [255, 255]],
            "Red": [[0, 20], [128, 160], [255, 255]],
            "Green": [[0, 0], [128, 130], [255, 245]],
            "Blue": [[0, 0], [128, 100], [255, 220]]
        },
        "Cool Teal & Orange": {
            "RGB": [[0, 5], [128, 128], [255, 250]],
            "Red": [[0, 0], [64, 80], [128, 140], [192, 180], [255, 255]],
            "Green": [[0, 0], [128, 125], [255, 255]],
            "Blue": [[0, 15], [64, 70], [128, 115], [192, 160], [255, 240]]
        },
        "Vintage Film": {
            "RGB": [[0, 20], [64, 70], [128, 140], [192, 200], [255, 235]],
            "Red": [[0, 15], [128, 145], [255, 245]],
            "Green": [[0, 10], [128, 135], [255, 240]],
            "Blue": [[0, 25], [128, 120], [255, 220]]
        },
        "Cyberpunk": {
            "RGB": [[0, 0], [128, 115], [255, 255]],
            "Red": [[0, 20], [128, 160], [255, 255]],
            "Green": [[0, 0], [128, 100], [255, 255]],
            "Blue": [[0, 30], [128, 140], [255, 255]]
        },
        "Bleach Bypass": {
            "RGB": [[0, 30], [64, 80], [128, 150], [192, 200], [255, 240]],
            "Red": [[0, 25], [128, 155], [255, 250]],
            "Green": [[0, 20], [128, 145], [255, 245]],
            "Blue": [[0, 15], [128, 140], [255, 240]]
        },
        "Day for Night": {
            "RGB": [[0, 0], [128, 80], [255, 180]],
            "Red": [[0, 0], [128, 85], [255, 190]],
            "Green": [[0, 0], [128, 75], [255, 175]],
            "Blue": [[0, 15], [128, 100], [255, 200]]
        },
        "Golden Hour": {
            "RGB": [[0, 10], [128, 145], [255, 255]],
            "Red": [[0, 25], [128, 170], [255, 255]],
            "Green": [[0, 15], [128, 150], [255, 250]],
            "Blue": [[0, 0], [128, 110], [255, 230]]
        },
        "Moonlight": {
            "RGB": [[0, 0], [128, 110], [255, 240]],
            "Red": [[0, 0], [128, 115], [255, 245]],
            "Green": [[0, 5], [128, 120], [255, 250]],
            "Blue": [[0, 20], [128, 140], [255, 255]]
        },
        "High Contrast": {
            "RGB": [[0, 0], [64, 40], [128, 128], [192, 215], [255, 255]],
            "Red": [[0, 0], [128, 128], [255, 255]],
            "Green": [[0, 0], [128, 128], [255, 255]],
            "Blue": [[0, 0], [128, 128], [255, 255]]
        }
    };

    const widget = {
        type: "apex_rgb_curve",
        name: inputName,
        value: JSON.stringify({
            "RGB": [[0, 0], [255, 255]],
            "Red": [[0, 0], [255, 255]],
            "Green": [[0, 0], [255, 255]],
            "Blue": [[0, 0], [255, 255]]
        }),
        draw: function(ctx, node, widgetWidth, y, widgetHeight) {
            // Draw the curve editor interface directly on the node canvas
            const margin = 10;
            const curveSize = Math.min(widgetWidth - margin * 2, 256);
            const startX = margin;
            const startY = y + 60; // Extra space for preset selector
            
            // Parse current curves
            let curves;
            try {
                curves = JSON.parse(this.value);
            } catch (e) {
                curves = CURVE_PRESETS["Linear (Reset)"];
                this.value = JSON.stringify(curves);
            }
            
            // Draw preset selector background
            const presetHeight = 25;
            ctx.fillStyle = "#333";
            ctx.fillRect(startX, y + 5, curveSize, presetHeight);
            ctx.strokeStyle = "#555";
            ctx.lineWidth = 1;
            ctx.strokeRect(startX, y + 5, curveSize, presetHeight);
            
            // Draw preset selector text
            ctx.fillStyle = "#ddd";
            ctx.font = "12px Arial";
            ctx.textAlign = "left";
            ctx.fillText("Preset: " + (this.selectedPreset || "Custom"), startX + 8, y + 22);
            
            // Draw dropdown arrow
            ctx.fillStyle = "#999";
            ctx.beginPath();
            ctx.moveTo(startX + curveSize - 20, y + 12);
            ctx.lineTo(startX + curveSize - 10, y + 22);
            ctx.lineTo(startX + curveSize - 20, y + 22);
            ctx.fill();
            
            // Store preset area for clicking
            this.presetArea = {
                x: startX,
                y: y + 5,
                width: curveSize,
                height: presetHeight
            };
            
            // Store drawing area for mouse events
            this.curveArea = {
                x: startX,
                y: startY,
                width: curveSize,
                height: curveSize
            };
            
            // Draw tabs
            const tabWidth = curveSize / 4;
            const tabHeight = 25;
            this.activeChannel = this.activeChannel || "RGB";
            
            const channels = ["RGB", "Red", "Green", "Blue"];
            const colors = ["#ffffff", "#ff4444", "#44ff44", "#4444ff"];
            
            // Draw tab background
            ctx.fillStyle = "#333";
            ctx.fillRect(startX, startY - tabHeight, curveSize, tabHeight);
            
            // Draw individual tabs
            channels.forEach((channel, i) => {
                const tabX = startX + i * tabWidth;
                const isActive = this.activeChannel === channel;
                
                // Tab background
                ctx.fillStyle = isActive ? "#444" : "#333";
                ctx.fillRect(tabX, startY - tabHeight, tabWidth, tabHeight);
                
                // Tab border
                ctx.strokeStyle = isActive ? colors[i] : "#555";
                ctx.lineWidth = isActive ? 2 : 1;
                ctx.strokeRect(tabX, startY - tabHeight, tabWidth, tabHeight);
                
                // Tab text
                ctx.fillStyle = colors[i];
                ctx.font = "11px Arial";
                ctx.textAlign = "center";
                ctx.fillText(channel, tabX + tabWidth / 2, startY - tabHeight / 2 + 4);
            });
            
            // Store tab area for clicking
            this.tabArea = {
                x: startX,
                y: startY - tabHeight,
                width: curveSize,
                height: tabHeight
            };
            
            // Draw curve background
            ctx.fillStyle = "#1a1a1a";
            ctx.fillRect(startX, startY, curveSize, curveSize);
            
            // Draw histogram in background
            this.drawHistogram(ctx, startX, startY, curveSize, curveSize, node);
            
            // Draw grid
            ctx.strokeStyle = "#333";
            ctx.lineWidth = 1;
            ctx.setLineDash([2, 2]);
            for (let i = 0; i <= 4; i++) {
                const pos = startX + (i * curveSize) / 4;
                ctx.beginPath();
                ctx.moveTo(pos, startY);
                ctx.lineTo(pos, startY + curveSize);
                ctx.stroke();
                
                const posY = startY + (i * curveSize) / 4;
                ctx.beginPath();
                ctx.moveTo(startX, posY);
                ctx.lineTo(startX + curveSize, posY);
                ctx.stroke();
            }
            
            // Draw diagonal reference line
            ctx.strokeStyle = "#555";
            ctx.setLineDash([]);
            ctx.beginPath();
            ctx.moveTo(startX, startY + curveSize);
            ctx.lineTo(startX + curveSize, startY);
            ctx.stroke();
            
            // Draw the current curve with smooth interpolation
            const currentCurve = curves[this.activeChannel] || [[0, 0], [255, 255]];
            const activeColor = colors[channels.indexOf(this.activeChannel)];
            
            ctx.strokeStyle = activeColor;
            ctx.lineWidth = 2;
            ctx.beginPath();
            
            // Draw smooth curve with ultra-high resolution for professional quality
            const resolution = curveSize * 4; // Ultra-high resolution for smoothest possible curves
            for (let i = 0; i <= resolution; i++) {
                const curveX = (i / resolution) * 255;
                const curveY = this.interpolateCurve(currentCurve, curveX);
                const screenX = startX + (i / resolution) * curveSize;
                const screenY = startY + curveSize - (curveY / 255) * curveSize;
                
                if (i === 0) {
                    ctx.moveTo(screenX, screenY);
                } else {
                    ctx.lineTo(screenX, screenY);
                }
            }
            ctx.stroke();
            
            // Draw control points
            ctx.fillStyle = activeColor;
            ctx.strokeStyle = "#fff";
            ctx.lineWidth = 1;
            
            currentCurve.forEach((point, i) => {
                const screenX = startX + (point[0] / 255) * curveSize;
                const screenY = startY + curveSize - (point[1] / 255) * curveSize;
                const isSelected = i === this.selectedPoint;
                
                ctx.beginPath();
                ctx.arc(screenX, screenY, isSelected ? 5 : 3, 0, Math.PI * 2);
                ctx.fill();
                
                if (isSelected) {
                    ctx.stroke();
                }
            });
            
            // Draw border
            ctx.strokeStyle = "#444";
            ctx.lineWidth = 1;
            ctx.strokeRect(startX, startY, curveSize, curveSize);
            
            // Draw detailed histogram panel below curve
            const histogramHeight = 80;
            const histogramY = startY + curveSize + 10;
            this.drawHistogramPanel(ctx, startX, histogramY, curveSize, histogramHeight, node);
            
            // Store histogram area for interactions
            this.histogramArea = {
                x: startX,
                y: histogramY,
                width: curveSize,
                height: histogramHeight
            };
        },
        
        interpolateCurve: function(curve, x) {
            if (curve.length < 2) return x;
            
            // Sort points by x coordinate
            const sortedCurve = [...curve].sort((a, b) => a[0] - b[0]);
            
            // For smooth interpolation between adjacent points using Hermite splines
            for (let i = 0; i < sortedCurve.length - 1; i++) {
                const p1 = sortedCurve[i];
                const p2 = sortedCurve[i + 1];
                
                if (x >= p1[0] && x <= p2[0]) {
                    if (p2[0] === p1[0]) return p1[1];
                    
                    // Normalize t to [0, 1]
                    const t = (x - p1[0]) / (p2[0] - p1[0]);
                    
                    // Calculate tangents for smooth interpolation
                    let m1 = 0, m2 = 0;
                    
                    // Left tangent
                    if (i > 0) {
                        const p0 = sortedCurve[i - 1];
                        m1 = (p2[1] - p0[1]) / (p2[0] - p0[0]);
                    } else {
                        m1 = (p2[1] - p1[1]) / (p2[0] - p1[0]);
                    }
                    
                    // Right tangent
                    if (i + 2 < sortedCurve.length) {
                        const p3 = sortedCurve[i + 2];
                        m2 = (p3[1] - p1[1]) / (p3[0] - p1[0]);
                    } else {
                        m2 = (p2[1] - p1[1]) / (p2[0] - p1[0]);
                    }
                    
                    // Hermite interpolation (smooth like Photoshop)
                    const t2 = t * t;
                    const t3 = t2 * t;
                    
                    const h00 = 2*t3 - 3*t2 + 1;
                    const h10 = t3 - 2*t2 + t;
                    const h01 = -2*t3 + 3*t2;
                    const h11 = t3 - t2;
                    
                    const dx = p2[0] - p1[0];
                    
                    return h00 * p1[1] + h10 * m1 * dx + h01 * p2[1] + h11 * m2 * dx;
                }
            }
            
            // Clamp to bounds
            if (x < sortedCurve[0][0]) return sortedCurve[0][1];
            return sortedCurve[sortedCurve.length - 1][1];
        },
        
        // Removed complex spline functions that were causing weird curves
        // Using simple linear interpolation for natural, predictable behavior
        
        smoothStep: function(t) {
            // Simple smoothstep for gentle easing
            return t * t * (3 - 2 * t);
        },
        
        extrapolatePoint: function(p1, p2, factor) {
            // Create virtual control points for smoother edge behavior
            const dx = p2[0] - p1[0];
            const dy = p2[1] - p1[1];
            return [
                p1[0] + dx * factor,
                p1[1] + dy * factor
            ];
        },
        
        drawHistogram: function(ctx, x, y, width, height, node) {
            // Draw histogram overlay on curve background
            if (!node.inputs || !node.inputs[0] || !node.inputs[0].link) {
                return; // No input image connected
            }
            
            // Create sample histogram data (in real implementation, this would come from the actual image)
            const histogramData = this.generateSampleHistogram();
            const maxValue = Math.max(...histogramData.luminance);
            
            if (maxValue === 0) return;
            
            // Draw luminance histogram as background
            ctx.save();
            ctx.globalAlpha = 0.3;
            ctx.fillStyle = "#666";
            
            const barWidth = width / 256;
            for (let i = 0; i < 256; i++) {
                const barHeight = (histogramData.luminance[i] / maxValue) * (height * 0.6);
                ctx.fillRect(x + i * barWidth, y + height - barHeight, barWidth, barHeight);
            }
            
            // Draw RGB channel histograms based on active channel
            if (this.activeChannel === "Red" || this.activeChannel === "RGB") {
                ctx.fillStyle = "#ff4444";
                ctx.globalAlpha = this.activeChannel === "Red" ? 0.6 : 0.2;
                for (let i = 0; i < 256; i++) {
                    const barHeight = (histogramData.red[i] / maxValue) * (height * 0.4);
                    ctx.fillRect(x + i * barWidth, y + height - barHeight, barWidth, barHeight);
                }
            }
            
            if (this.activeChannel === "Green" || this.activeChannel === "RGB") {
                ctx.fillStyle = "#44ff44";
                ctx.globalAlpha = this.activeChannel === "Green" ? 0.6 : 0.2;
                for (let i = 0; i < 256; i++) {
                    const barHeight = (histogramData.green[i] / maxValue) * (height * 0.4);
                    ctx.fillRect(x + i * barWidth, y + height - barHeight, barWidth, barHeight);
                }
            }
            
            if (this.activeChannel === "Blue" || this.activeChannel === "RGB") {
                ctx.fillStyle = "#4444ff";
                ctx.globalAlpha = this.activeChannel === "Blue" ? 0.6 : 0.2;
                for (let i = 0; i < 256; i++) {
                    const barHeight = (histogramData.blue[i] / maxValue) * (height * 0.4);
                    ctx.fillRect(x + i * barWidth, y + height - barHeight, barWidth, barHeight);
                }
            }
            
            ctx.restore();
        },
        
        drawHistogramPanel: function(ctx, x, y, width, height, node) {
            // Draw detailed histogram panel below the curve
            ctx.fillStyle = "#222";
            ctx.fillRect(x, y, width, height);
            ctx.strokeStyle = "#555";
            ctx.strokeRect(x, y, width, height);
            
            // Generate histogram data
            const histogramData = this.generateSampleHistogram();
            const maxValue = Math.max(...histogramData.luminance);
            
            if (maxValue === 0) {
                ctx.fillStyle = "#666";
                ctx.font = "12px Arial";
                ctx.textAlign = "center";
                ctx.fillText("No image data", x + width/2, y + height/2);
                return;
            }
            
            const barWidth = width / 256;
            const channels = ["red", "green", "blue"];
            const colors = ["#ff4444", "#44ff44", "#4444ff"];
            
            // Draw RGB histograms
            channels.forEach((channel, i) => {
                ctx.globalAlpha = this.activeChannel === channel.charAt(0).toUpperCase() + channel.slice(1) ? 0.8 : 0.4;
                ctx.fillStyle = colors[i];
                
                for (let j = 0; j < 256; j++) {
                    const barHeight = (histogramData[channel][j] / maxValue) * (height - 10);
                    ctx.fillRect(x + j * barWidth, y + height - 5 - barHeight, Math.max(1, barWidth), barHeight);
                }
            });
            
            // Draw luminance histogram
            if (this.activeChannel === "RGB") {
                ctx.globalAlpha = 0.6;
                ctx.fillStyle = "#ffffff";
                
                for (let i = 0; i < 256; i++) {
                    const barHeight = (histogramData.luminance[i] / maxValue) * (height - 10);
                    ctx.fillRect(x + i * barWidth, y + height - 5 - barHeight, Math.max(1, barWidth), barHeight);
                }
            }
            
            ctx.globalAlpha = 1.0;
            
            // Draw statistics
            const stats = this.calculateHistogramStats(histogramData);
            ctx.fillStyle = "#ddd";
            ctx.font = "10px Arial";
            ctx.textAlign = "left";
            
            const activeChannelData = this.activeChannel === "RGB" ? "luminance" : this.activeChannel.toLowerCase();
            const channelStats = stats[activeChannelData] || stats.luminance;
            
            ctx.fillText(`Mean: ${channelStats.mean.toFixed(1)}`, x + 5, y + 12);
            ctx.fillText(`Median: ${channelStats.median}`, x + 5, y + 24);
            ctx.fillText(`Mode: ${channelStats.mode}`, x + 5, y + 36);
            
            ctx.textAlign = "right";
            ctx.fillText(`Min: ${channelStats.min}`, x + width - 5, y + 12);
            ctx.fillText(`Max: ${channelStats.max}`, x + width - 5, y + 24);
            ctx.fillText(`Std: ${channelStats.std.toFixed(1)}`, x + width - 5, y + 36);
        },
        
        generateSampleHistogram: function() {
            // Try to get histogram data from node's cached histogram output
            if (this.cachedHistogramData) {
                try {
                    const histData = JSON.parse(this.cachedHistogramData);
                    return {
                        red: histData.red || new Array(256).fill(0),
                        green: histData.green || new Array(256).fill(0),
                        blue: histData.blue || new Array(256).fill(0),
                        luminance: histData.luminance || new Array(256).fill(0)
                    };
                } catch (e) {
                    console.log("Failed to parse cached histogram data");
                }
            }
            
            // Fallback: Generate sample histogram data
            const histogram = {
                red: new Array(256).fill(0),
                green: new Array(256).fill(0),
                blue: new Array(256).fill(0),
                luminance: new Array(256).fill(0)
            };
            
            // Generate realistic-looking histogram data
            for (let i = 0; i < 256; i++) {
                // Bell curve with some noise for realism
                const t = i / 255;
                const base = Math.exp(-Math.pow((t - 0.5) * 3, 2)) * 1000;
                const noise = Math.random() * 100;
                
                histogram.red[i] = Math.floor(base * (0.8 + Math.sin(t * Math.PI) * 0.3) + noise);
                histogram.green[i] = Math.floor(base * (0.9 + Math.cos(t * Math.PI * 1.5) * 0.2) + noise);
                histogram.blue[i] = Math.floor(base * (0.7 + Math.sin(t * Math.PI * 2) * 0.4) + noise);
                histogram.luminance[i] = Math.floor((histogram.red[i] + histogram.green[i] + histogram.blue[i]) / 3);
            }
            
            return histogram;
        },
        
        calculateHistogramStats: function(histogramData) {
            const stats = {};
            
            Object.keys(histogramData).forEach(channel => {
                const data = histogramData[channel];
                let total = 0;
                let sum = 0;
                let max = 0;
                let maxIndex = 0;
                
                // Calculate basic stats
                for (let i = 0; i < data.length; i++) {
                    total += data[i];
                    sum += i * data[i];
                    if (data[i] > max) {
                        max = data[i];
                        maxIndex = i;
                    }
                }
                
                const mean = total > 0 ? sum / total : 0;
                
                // Calculate median
                let runningSum = 0;
                let median = 0;
                for (let i = 0; i < data.length; i++) {
                    runningSum += data[i];
                    if (runningSum >= total / 2) {
                        median = i;
                        break;
                    }
                }
                
                // Calculate standard deviation
                let variance = 0;
                for (let i = 0; i < data.length; i++) {
                    if (data[i] > 0) {
                        variance += data[i] * Math.pow(i - mean, 2);
                    }
                }
                variance = total > 0 ? variance / total : 0;
                const std = Math.sqrt(variance);
                
                // Find min and max values
                let min = 0, maxVal = 255;
                for (let i = 0; i < data.length; i++) {
                    if (data[i] > 0) {
                        min = i;
                        break;
                    }
                }
                for (let i = data.length - 1; i >= 0; i--) {
                    if (data[i] > 0) {
                        maxVal = i;
                        break;
                    }
                }
                
                stats[channel] = {
                    mean: mean,
                    median: median,
                    mode: maxIndex,
                    std: std,
                    min: min,
                    max: maxVal
                };
            });
            
            return stats;
        },
        
        mouse: function(event, pos, node) {
            if (!this.curveArea || !this.tabArea) return false;
            
            // Check preset dropdown clicks
            if (this.presetArea && pos[1] >= this.presetArea.y && pos[1] <= this.presetArea.y + this.presetArea.height &&
                pos[0] >= this.presetArea.x && pos[0] <= this.presetArea.x + this.presetArea.width) {
                
                if (event.type === "pointerdown" || event.type === "click") {
                    this.showPresetMenu(event, pos, node);
                    return true;
                }
                return true;
            }
            
            const localX = pos[0] - this.curveArea.x;
            const localY = pos[1] - this.curveArea.y;
            
            // Check tab clicks
            if (pos[1] >= this.tabArea.y && pos[1] <= this.tabArea.y + this.tabArea.height &&
                pos[0] >= this.tabArea.x && pos[0] <= this.tabArea.x + this.tabArea.width) {
                
                if (event.type === "pointerdown" || event.type === "click") {
                    const channels = ["RGB", "Red", "Green", "Blue"];
                    const tabIndex = Math.floor((pos[0] - this.tabArea.x) / (this.tabArea.width / 4));
                    if (tabIndex >= 0 && tabIndex < channels.length) {
                        this.activeChannel = channels[tabIndex];
                        this.selectedPoint = -1;
                        node.setDirtyCanvas(true, false);
                        return true;
                    }
                }
                return true;
            }
            
            // Check curve area
            if (localX >= 0 && localX <= this.curveArea.width && localY >= 0 && localY <= this.curveArea.height) {
                let curves = JSON.parse(this.value);
                const currentCurve = curves[this.activeChannel];
                
                if (event.type === "pointerdown" || event.type === "mousedown") {
                    const curveX = (localX / this.curveArea.width) * 255;
                    const curveY = 255 - (localY / this.curveArea.height) * 255;
                    
                    // Find existing point within 15 pixel radius
                    this.selectedPoint = -1;
                    for (let i = 0; i < currentCurve.length; i++) {
                        const pointScreenX = (currentCurve[i][0] / 255) * this.curveArea.width;
                        const pointScreenY = this.curveArea.height - (currentCurve[i][1] / 255) * this.curveArea.height;
                        const dx = localX - pointScreenX;
                        const dy = localY - pointScreenY;
                        if (Math.sqrt(dx * dx + dy * dy) < 15) {
                            this.selectedPoint = i;
                            break;
                        }
                    }
                    
                    // Add new point if none selected
                    if (this.selectedPoint === -1) {
                        const newPoint = [Math.round(curveX), Math.round(curveY)];
                        currentCurve.push(newPoint);
                        currentCurve.sort((a, b) => a[0] - b[0]);
                        this.selectedPoint = currentCurve.findIndex(p => 
                            p[0] === newPoint[0] && p[1] === newPoint[1]
                        );
                        this.selectedPreset = "Custom"; // Mark as custom when manually edited
                    }
                    
                    this.isDragging = true;
                    this.value = JSON.stringify(curves);
                    node.setDirtyCanvas(true, false);
                    return true;
                }
                
                if ((event.type === "pointermove" || event.type === "mousemove") && this.isDragging && this.selectedPoint !== -1) {
                    const curveX = Math.max(0, Math.min(255, (localX / this.curveArea.width) * 255));
                    const curveY = Math.max(0, Math.min(255, 255 - (localY / this.curveArea.height) * 255));
                    
                    // Constrain movement to prevent crossing points
                    let newX = Math.round(curveX);
                    if (this.selectedPoint > 0) {
                        newX = Math.max(currentCurve[this.selectedPoint - 1][0] + 1, newX);
                    }
                    if (this.selectedPoint < currentCurve.length - 1) {
                        newX = Math.min(currentCurve[this.selectedPoint + 1][0] - 1, newX);
                    }
                    
                    // Lock endpoints to edges
                    if (this.selectedPoint === 0) newX = 0;
                    if (this.selectedPoint === currentCurve.length - 1) newX = 255;
                    
                    currentCurve[this.selectedPoint] = [newX, Math.round(curveY)];
                    this.selectedPreset = "Custom"; // Mark as custom when manually edited
                    this.value = JSON.stringify(curves);
                    node.setDirtyCanvas(true, false);
                    return true;
                }
                
                if (event.type === "pointerup" || event.type === "mouseup") {
                    this.isDragging = false;
                    return true;
                }
                
                // Handle double click to remove points
                if (event.type === "dblclick") {
                    if (this.selectedPoint > 0 && this.selectedPoint < currentCurve.length - 1) {
                        currentCurve.splice(this.selectedPoint, 1);
                        this.selectedPoint = -1;
                        this.selectedPreset = "Custom"; // Mark as custom when manually edited
                        this.value = JSON.stringify(curves);
                        node.setDirtyCanvas(true, false);
                        return true;
                    }
                }
                
                return true;
            }
            
            return false;
        },
        
        showPresetMenu: function(event, pos, node) {
            // Create context menu for presets
            const menu = document.createElement("div");
            menu.style.cssText = `
                position: fixed;
                background: #2a2a2a;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 4px 0;
                z-index: 10000;
                max-height: 300px;
                overflow-y: auto;
                box-shadow: 0 4px 12px rgba(0,0,0,0.5);
            `;
            
            // Position menu
            menu.style.left = (event.clientX || pos[0]) + "px";
            menu.style.top = (event.clientY || pos[1]) + "px";
            
            // Add preset options
            Object.keys(CURVE_PRESETS).forEach(presetName => {
                const option = document.createElement("div");
                option.textContent = presetName;
                option.style.cssText = `
                    padding: 6px 12px;
                    cursor: pointer;
                    color: #ddd;
                    font-size: 12px;
                    white-space: nowrap;
                    min-width: 120px;
                `;
                
                option.onmouseenter = () => option.style.background = "#444";
                option.onmouseleave = () => option.style.background = "transparent";
                
                option.onclick = () => {
                    this.applyPreset(presetName);
                    node.setDirtyCanvas(true, false);
                    document.body.removeChild(menu);
                };
                
                menu.appendChild(option);
            });
            
            document.body.appendChild(menu);
            
            // Close menu when clicking outside
            const closeMenu = (e) => {
                if (!menu.contains(e.target)) {
                    document.body.removeChild(menu);
                    document.removeEventListener("click", closeMenu);
                }
            };
            
            setTimeout(() => document.addEventListener("click", closeMenu), 100);
        },
        
        applyPreset: function(presetName) {
            if (CURVE_PRESETS[presetName]) {
                this.value = JSON.stringify(CURVE_PRESETS[presetName]);
                this.selectedPreset = presetName;
                this.selectedPoint = -1;
                this.activeChannel = "RGB";
            }
        },
        
        computeSize: function(width) {
            return [Math.max(280, width), 450]; // Extra height for preset dropdown and histogram panel
        }
    };
    
    // Initialize widget state
    widget.selectedPoint = -1;
    widget.isDragging = false;
    widget.activeChannel = "RGB";
    widget.selectedPreset = "Linear (Reset)";
    
    return widget;
}

// Register custom widget type
ComfyWidgets["apex_rgb_curve"] = RGBCurveWidgetComfy;

// Register extension
app.registerExtension({
    name: "ApexArtist.RGBCurve",
    
    beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "ApexRGBCurve") {
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function() {
                onNodeCreated?.apply(this, arguments);
                
                // Find the curve_data widget
                let curveWidgetIndex = -1;
                let originalWidget = null;
                for (let i = 0; i < this.widgets.length; i++) {
                    if (this.widgets[i].name === "curve_data") {
                        curveWidgetIndex = i;
                        originalWidget = this.widgets[i];
                        break;
                    }
                }
                
                if (curveWidgetIndex !== -1 && originalWidget) {
                    // Hide the original widget instead of removing it completely
                    originalWidget.type = "hidden";
                    originalWidget.computeSize = () => [0, 0];
                    originalWidget.draw = () => {}; // Empty draw function
                    
                    // Add our custom widget by replacing the original
                    const customWidget = RGBCurveWidgetComfy(this, "curve_data", null, app);
                    this.widgets.splice(curveWidgetIndex + 1, 0, customWidget);
                    
                    // Add reset button widget
                    const resetWidget = this.addWidget("button", "Reset Curves", null, () => {
                        customWidget.applyPreset("Linear (Reset)");
                        this.setDirtyCanvas(true, false);
                    });
                    resetWidget.serialize = false;
                    
                    // Resize node to accommodate widget and presets
                    this.size = [300, 450];
                    
                    // Store reference for updates
                    this.rgbCurveWidget = customWidget;
                }
            };
        }
    }
});
