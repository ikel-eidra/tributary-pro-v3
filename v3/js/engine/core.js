// ========== CORE CALCULATIONS ==========

        /**
         * Main calculation function
         * Implements: SLAB → BEAMS → COLUMNS load path
         * v2.3: Calculates per-floor and cumulative across all floors
         */
        function calculate() {
            // Clean spans to avoid zero/negative values
            state.xSpans = state.xSpans.map(span => sanitizeSpan(span));
            state.ySpans = state.ySpans.map(span => sanitizeSpan(span));

            // Step 1: Generate grid coordinates
            generateGrid();

            // Step 2: Generate slab panels (MOVED inside loop for per-floor logic)
            // generateSlabs();

            // Reset cumulative column loads
            for (let col of state.columns) {
                col.loadPerFloor = 0;
                col.totalLoad = 0;
                col.floorLoads = [];
            }

            // v2.3: Calculate loads for each floor
            let totalPuSum = 0;
            for (let floor of state.floors) {
                // v2.6: Skip GF if not suspended (ground-bearing slab)
                if (floor.id === 'GF' && !state.gfSuspended) {
                    // Store 0 load for GF to keep array consistent
                    for (let col of state.columns) {
                        col.floorLoads.push({ floorId: floor.id, load: 0 });
                    }
                    continue;
                }

                // Calculate factored load for this floor
                const slabWeight = 24 * (floor.slabThickness / 1000); // kN/m² = kPa
                const pu = 1.2 * (floor.dlSuper + slabWeight) + 1.6 * floor.liveLoad;
                const wallLoad = floor.wallLoad || 0;  // v3.0: Wall load (kN/m)
                totalPuSum += pu;

                // v3.0: Mock global cantilevers to be floor-specific for generation
                const globalCants = state.cantilevers;
                state.cantilevers = getCantilevers(floor.id);

                // v3.0: Generate slabs and beams specific to THIS floor
                generateSlabs(floor.id);
                generateBeams(pu, wallLoad, floor);

                // Step 5: Calculate beam reactions
                calculateBeamReactions();

                // Step 6: Add reactions to columns for this floor
                calculateColumnLoadsForFloor(floor.id);

                // Restore global cantilevers
                state.cantilevers = globalCants;
            }

            // Average pu for display (or use current floor's pu)
            const currentFloor = state.floors[state.currentFloorIndex];
            const currentSlabWeight = 24 * (currentFloor.slabThickness / 1000);
            const puDisplay = 1.2 * (currentFloor.dlSuper + currentSlabWeight) + 1.6 * currentFloor.liveLoad;

            // v2.5: Read footing parameters
            state.footingDepth = parseFloat(document.getElementById('footingDepth').value) || 1.5;
            state.soilBearing = parseFloat(document.getElementById('soilBearing').value) || 150;

            // v3.0: Size all columns and beams FIRST (needed for self-weight calc)
            sizeMembers();

            // v3.0: Calculate footing sizes (includes column/beam/tie beam DL)
            calculateFootingSizes();

            // Update UI
            updateResults(puDisplay);

            // v3.0: Final regeneration for display (Current Floor)
            // This ensures what we see matches the selected floor tab
            const displayCants = state.cantilevers; // UI state
            state.cantilevers = getCantilevers(currentFloor.id);
            generateSlabs(currentFloor.id);
            generateBeams(puDisplay, currentFloor.wallLoad || 0); // Use display PU
            state.cantilevers = displayCants; // Restore UI state

            draw();

            // v3.0: Update concrete volume summary
            updateConcreteVolume();
        }

        /**
         * v3.0: Calculate footing sizes based on total column load
         * Now includes: slab loads + beam DL + column DL + tie beam DL
         * Simple formula: A_req = P / q_allow
         */
        function calculateFootingSizes() {
            const q = state.soilBearing; // kPa
            const numFloors = state.floors.length;
            const floorHeight = state.floors[0]?.height || 3.0;
            const footingDepth = state.footingDepth || 1.5;

            // v2.8: Calculate uniform tie beam sizing from longest span
            const longestSpan = Math.max(...state.xSpans, ...state.ySpans);
            state.tieBeamH = Math.max(0.3, Math.ceil(longestSpan / 10 * 20) / 20);
            state.tieBeamW = 0.25;

            // v3.0: Calculate tie beam DL per column
            // Each column has avg 2 tie beams connecting to it (simplified)
            // Tie beam length approximated as average span
            const avgSpan = (state.xSpans.reduce((a, b) => a + b, 0) + state.ySpans.reduce((a, b) => a + b, 0)) /
                (state.xSpans.length + state.ySpans.length);
            const tieBeamVolume = state.tieBeamW * state.tieBeamH * avgSpan;  // m³ per beam
            const tieBeamWeight = tieBeamVolume * state.concreteDensity;      // kN per beam
            const tieBeamDLPerColumn = tieBeamWeight * 1.2;  // Factored, shared contribution

            for (let col of state.columns) {
                if (col.active === false) {
                    col.footingSize = 0;
                    col.footingThick = 0;
                    continue;
                }

                // v3.0: Planted columns don't get footings (load goes to transfer beam)
                if (col.startFloor) {
                    col.footingSize = 0;
                    col.footingThick = 0;
                    col.isPlanted = true;
                    continue;
                }

                // v3.0: Add column self-weight for all floors
                // Use suggestedB/H if available, else estimate 250×250
                const colB = (col.suggestedB || 250) / 1000;  // m
                const colH = (col.suggestedH || 250) / 1000;  // m
                const colVolume = colB * colH * floorHeight;  // m³ per floor
                const colDL = colVolume * state.concreteDensity * numFloors * 1.2;  // Factored

                // Total load includes: slab+beam (from floors) + column DL + tie beam DL
                const totalFactored = col.totalLoad + colDL + tieBeamDLPerColumn;
                col.totalLoadWithDL = totalFactored;  // Store for display

                // Use unfactored load for footing sizing (service load)
                const P_service = totalFactored / 1.4; // kN

                // Required area
                const A_req = P_service / q; // m²

                // Square footing side (round to 0.1m, min 0.6m)
                let side = Math.sqrt(A_req);
                side = Math.max(0.6, Math.ceil(side * 10) / 10);

                // Thickness estimate (simple: h = side/4, min 0.3m)
                let thick = Math.max(0.3, Math.round(side / 4 * 10) / 10);

                col.footingSize = side;      // m
                col.footingThick = thick;    // m
                col.columnDL = colDL;        // kN (for breakdown)
                col.tieBeamDL = tieBeamDLPerColumn;  // kN (for breakdown)

                // v3.0: Footing self-weight (factored)
                const footingVolume = side * side * thick;  // m³
                col.footingDL = footingVolume * state.concreteDensity * 1.2;  // kN factored
            }

            console.log(`v3.0: Self-weight included - Column DL + Tie beam DL added to footings`);
            console.log(`v3.0: Tie beam sizing - ${(state.tieBeamW * 1000).toFixed(0)}×${(state.tieBeamH * 1000).toFixed(0)}mm`);
        }

        /**
         * v3.0: Check if current floor is at or above the start floor
         * Used for planted columns that don't go to ground
         * @param {string} currentFloorId - The floor being calculated
         * @param {string} startFloorId - The column's starting floor
         * @returns {boolean} true if column exists at this floor
         */
        function isFloorAtOrAbove(currentFloorId, startFloorId) {
            const floorIds = state.floors.map(f => f.id);
            const currentIdx = floorIds.indexOf(currentFloorId);
            const startIdx = floorIds.indexOf(startFloorId);
            // Higher index = higher floor (GF=0, 2F=1, RF=2)
            return currentIdx >= startIdx;
        }

        /**
         * Calculate column loads for a specific floor
         * v3.0: Includes beam reactions AND beam self-weight DL
         * v3.0: Skip planted columns for floors below their startFloor
         * v3.0: Skip columns that are not active on this specific floor
         */
        function calculateColumnLoadsForFloor(floorId) {
            for (let col of state.columns) {
                // v3.0: Skip if column is planted and doesn't exist at this floor
                if (col.startFloor && !isFloorAtOrAbove(floorId, col.startFloor)) {
                    col.floorLoads.push({ floorId, load: 0, isPlanted: true });
                    continue;  // Don't add any load for this floor
                }

                // v3.0: Skip if column is not active on this specific floor
                if (!isColumnActiveOnFloor(col, floorId)) {
                    col.floorLoads.push({ floorId, load: 0, isInactive: true });
                    continue;  // Column removed on this floor
                }

                let floorLoad = 0;
                let beamDL = 0;  // v3.0: Beam self-weight contribution
                for (let beam of state.beams) {
                    // Beam reactions (from slab loads)
                    if (beam.startCol === col.id) floorLoad += beam.Rleft;
                    if (beam.endCol === col.id) floorLoad += beam.Rright;

                    // v3.0: Beam self-weight (half to each end)
                    // selfWeight is total kN, factor by 1.2 for DL
                    if (beam.selfWeight) {
                        const halfWeight = beam.selfWeight / 2 * 1.2;  // Factored
                        if (beam.startCol === col.id) beamDL += halfWeight;
                        if (beam.endCol === col.id) beamDL += halfWeight;
                    }
                }
                const totalFloorLoad = floorLoad + beamDL;
                col.floorLoads.push({ floorId, load: totalFloorLoad, slabLoad: floorLoad, beamDL: beamDL });
                col.totalLoad += totalFloorLoad;
                col.loadPerFloor = totalFloorLoad;
            }
        }

        /**
         * Step 1: Generate grid from spans
         * Creates absolute coordinates for column positions
         */
        function generateGrid() {
            // Build X coordinates
            const xCoords = [0];
            for (let span of state.xSpans) {
                xCoords.push(xCoords[xCoords.length - 1] + span);
            }

            // Build Y coordinates
            const yCoords = [0];
            for (let span of state.ySpans) {
                yCoords.push(yCoords[yCoords.length - 1] + span);
            }

            // Generate columns at intersections
            // v2.7: Preserve active state from existing columns
            const oldColumns = state.columns || [];

            // v3.0: Preserve custom-placed planted columns (not at grid intersections)
            const plantedColumns = oldColumns.filter(c => c.isPlanted === true);

            state.columns = [];
            const letters = 'ABCDEFGHJKLMNPQRSTUVWXYZ'; // Skip I and O

            for (let yi = 0; yi < yCoords.length; yi++) {
                for (let xi = 0; xi < xCoords.length; xi++) {
                    const id = `${letters[xi]}${yi + 1}`;

                    // Determine column type
                    const isCorner = (xi === 0 || xi === xCoords.length - 1) &&
                        (yi === 0 || yi === yCoords.length - 1);
                    const isEdge = !isCorner && (xi === 0 || xi === xCoords.length - 1 ||
                        yi === 0 || yi === yCoords.length - 1);

                    let type = 'interior';
                    if (isCorner) type = 'corner';
                    else if (isEdge) type = 'edge';

                    // v2.7: Check if this column existed before and preserve its active state
                    const oldCol = oldColumns.find(c => c.id === id);
                    const isActive = oldCol ? oldCol.active : true;  // Preserve or default true
                    const startFloor = oldCol?.startFloor || null;   // v3.0: Preserve planted column state
                    const activePerFloor = oldCol?.activePerFloor || null;  // v3.0: Preserve per-floor toggle state
                    const typePerFloor = oldCol?.typePerFloor || null;  // v3.0: Preserve per-floor TYPE state
                    const floorActive = oldCol?.floorActive || null;  // v3.0: Preserve per-floor active state

                    state.columns.push({
                        id,
                        x: xCoords[xi],
                        y: yCoords[yi],
                        xi, yi,
                        type,
                        active: isActive,  // v2.7: Preserved toggle state for L/U shapes
                        startFloor: startFloor,  // v3.0: For planted columns (null = from ground)
                        activePerFloor: activePerFloor,  // v3.0: Per-floor toggle state
                        typePerFloor: typePerFloor,  // v3.0: Per-floor type (corner/edge/interior)
                        floorActive: floorActive,    // v3.0: Per-floor active state
                        loadPerFloor: 0,
                        totalLoad: 0,
                        connectedBeams: [] // Will store beam IDs
                    });
                }
            }

            // v3.0: Re-add planted columns that were placed on beams (not at grid intersections)
            for (const pc of plantedColumns) {
                // Check if this planted column already exists (by position)
                const exists = state.columns.find(c =>
                    Math.abs(c.x - pc.x) < 0.1 && Math.abs(c.y - pc.y) < 0.1
                );
                if (!exists) {
                    // Preserve the planted column with all its properties
                    state.columns.push({
                        ...pc,
                        loadPerFloor: 0,
                        totalLoad: 0
                    });
                    console.log(`v3.0: Preserved planted column ${pc.id} at (${pc.x.toFixed(2)}, ${pc.y.toFixed(2)})`);
                }
            }
        }

        /**
         * Step 2: Generate slab panels
         */
        // v2.7: Helper to get column by grid indices
        function getColumnAt(xi, yi) {
            return state.columns.find(c => c.xi === xi && c.yi === yi);
        }

        /**
         * Step 2: Generate slab panels
         * v3.0: Now accepts floorId to distinct cantilevers
         */
        function generateSlabs(floorId) {
            // v3.0: Preserve existing opening data
            const oldSlabs = state.slabs || [];

            // v3.0: Get per-floor void slabs (FIXED: ensure each floor has its own array)
            const floor = floorId ? state.floors.find(f => f.id === floorId) : state.floors[state.currentFloorIndex];
            if (floor && !floor.voidSlabs) floor.voidSlabs = [];  // Initialize per-floor array
            const floorVoidSlabs = floor ? floor.voidSlabs : [];  // Use per-floor, never fallback to global

            state.slabs = [];
            const xCoords = [0];
            for (let span of state.xSpans) xCoords.push(xCoords[xCoords.length - 1] + span);
            const yCoords = [0];
            for (let span of state.ySpans) yCoords.push(yCoords[yCoords.length - 1] + span);

            for (let yi = 0; yi < state.ySpans.length; yi++) {
                for (let xi = 0; xi < state.xSpans.length; xi++) {
                    // v3.0 FIX: ALWAYS generate all slabs regardless of column state
                    // This prevents cascade deletion when column is toggled

                    const lx = state.xSpans[xi];
                    const ly = state.ySpans[yi];
                    const mainSlabId = `S${yi * state.xSpans.length + xi + 1}`;
                    const x1 = xCoords[xi];
                    const x2 = xCoords[xi + 1];
                    const y1 = yCoords[yi];
                    const y2 = yCoords[yi + 1];

                    // v3.0: Find custom beams that cross this panel
                    const crossingX = [x1, x2];
                    const crossingY = [y1, y2];

                    const floorCustomBeams = floor?.customBeams || [];
                    for (const cb of floorCustomBeams) {
                        // v3.0 FIX: dir='X' means horizontal beam (constant Y), splits Y range
                        // dir='Y' means vertical beam (constant X), splits X range
                        if (cb.dir === 'X' && cb.pos > y1 && cb.pos < y2) {
                            // Horizontal beam at Y=cb.pos splits the Y range
                            if (cb.start < x2 && cb.end > x1) crossingY.push(cb.pos);
                        } else if (cb.dir === 'Y' && cb.pos > x1 && cb.pos < x2) {
                            // Vertical beam at X=cb.pos splits the X range
                            if (cb.start < y2 && cb.end > y1) crossingX.push(cb.pos);
                        }
                    }

                    // Sort unique coordinates
                    const sortedX = [...new Set(crossingX)].sort((a, b) => a - b);
                    const sortedY = [...new Set(crossingY)].sort((a, b) => a - b);

                    // Generate sub-slabs
                    for (let sy = 0; sy < sortedY.length - 1; sy++) {
                        for (let sx = 0; sx < sortedX.length - 1; sx++) {
                            const sx1 = sortedX[sx];
                            const sx2 = sortedX[sx + 1];
                            const sy1 = sortedY[sy];
                            const sy2 = sortedY[sy + 1];
                            const slx = sx2 - sx1;
                            const sly = sy2 - sy1;
                            const subId = (sortedX.length > 2 || sortedY.length > 2)
                                ? `${mainSlabId}_${sx}_${sy}`
                                : mainSlabId;

                            const ratio = Math.max(slx, sly) / Math.min(slx, sly);
                            const isTwoWay = ratio < 2;

                            // Void state from floor's voidSlabs array
                            const isVoid = floorVoidSlabs.includes(subId);

                            state.slabs.push({
                                id: subId,
                                parentId: mainSlabId,
                                x1: sx1, y1: sy1, x2: sx2, y2: sy2,
                                lx: slx, ly: sly,
                                area: slx * sly,
                                isTwoWay,
                                xi, yi, // Grid indices of the parent
                                sx, sy, // Sub-indices
                                isVoid: isVoid
                            });
                        }
                    }
                }
            }

            // v3.0 FIX: Ghost cleanup - remove orphaned voidSlabs references
            // When spans change, slab IDs change and old voidSlabs refs become orphans
            if (floor && floor.voidSlabs && floor.voidSlabs.length > 0) {
                const validSlabIds = state.slabs.map(s => s.id);
                const orphans = floor.voidSlabs.filter(id => !validSlabIds.includes(id));
                if (orphans.length > 0) {
                    orphans.forEach(orphanId => {
                        const idx = floor.voidSlabs.indexOf(orphanId);
                        if (idx >= 0) floor.voidSlabs.splice(idx, 1);
                    });
                    console.log(`v3.0: Cleaned ${orphans.length} orphaned voidSlabs on floor ${floor.id}:`, orphans);
                }
            }

            // v3.0: Generate cantilever slabs (specific to floor if provided)
            generateCantileverSlabs(xCoords, yCoords, floorId);
        }

        // v3.0 FIX: Helper to get effective cantilevers for a floor
        // Now returns per-floor cantilevers ONLY, never falls back to global
        function getCantilevers(floorId) {
            const floor = floorId
                ? state.floors.find(f => f.id === floorId)
                : state.floors[state.currentFloorIndex];

            // GF without suspended mode has no cantilevers
            if (floor?.id === 'GF' && !state.gfSuspended) {
                return { top: [], bottom: [], left: [], right: [] };
            }

            // v3.0 FIX: Return floor-specific cantilevers, or empty if none defined
            // This prevents cantilevers from one floor appearing on all floors
            if (floor?.cantilevers) {
                return floor.cantilevers;
            }

            // v3.0 FIX: No floor-specific cantilevers = return zeros (not global!)
            const numX = state.xSpans.length;
            const numY = state.ySpans.length;
            return {
                top: new Array(numX).fill(0),
                bottom: new Array(numX).fill(0),
                left: new Array(numY).fill(0),
                right: new Array(numY).fill(0)
            };
        }

        // v3.0: Generate cantilever slab panels extending beyond the grid
        function generateCantileverSlabs(xCoords, yCoords, floorId) {
            const cants = getCantilevers(floorId);

            // v3.0: Get per-floor void slabs for cantilevers too
            const currentFloor = state.floors.find(f => f.id === floorId);
            const floorVoidSlabs = currentFloor?.voidSlabs || [];

            // Top cantilevers (above first row, yi = 0)
            for (let xi = 0; xi < state.xSpans.length; xi++) {

                const cantLen = cants.top[xi] || 0;
                if (cantLen > 0) {
                    const spanWidth = state.xSpans[xi];
                    state.slabs.push({
                        id: `SC-T${xi + 1}`,
                        x1: xCoords[xi],
                        y1: -cantLen,  // Extends above grid (negative Y)
                        x2: xCoords[xi + 1],
                        y2: 0,
                        lx: spanWidth,
                        ly: cantLen,
                        area: spanWidth * cantLen,
                        isCantilever: true,
                        cantileverEdge: 'top',
                        spanIndex: xi,
                        supportingBeamId: `BX-1-${xi + 1}`,  // Top edge beam
                        isVoid: floorVoidSlabs.includes(`SC-T${xi + 1}`)
                    });
                }
            }

            // Bottom cantilevers (below last row)
            const maxY = yCoords[yCoords.length - 1];
            const lastYi = state.ySpans.length;  // Last beam row index
            for (let xi = 0; xi < state.xSpans.length; xi++) {
                const cantLen = cants.bottom[xi] || 0;
                if (cantLen > 0) {
                    const spanWidth = state.xSpans[xi];
                    state.slabs.push({
                        id: `SC-B${xi + 1}`,
                        x1: xCoords[xi],
                        y1: maxY,
                        x2: xCoords[xi + 1],
                        y2: maxY + cantLen,  // Extends below grid
                        lx: spanWidth,
                        ly: cantLen,
                        area: spanWidth * cantLen,
                        isCantilever: true,
                        cantileverEdge: 'bottom',
                        spanIndex: xi,
                        supportingBeamId: `BX-${lastYi + 1}-${xi + 1}`,  // Bottom edge beam
                        isVoid: floorVoidSlabs.includes(`SC-B${xi + 1}`)
                    });
                }
            }

            // Left cantilevers (left of first column, xi = 0)
            for (let yi = 0; yi < state.ySpans.length; yi++) {
                const cantLen = cants.left[yi] || 0;
                if (cantLen > 0) {
                    const spanHeight = state.ySpans[yi];
                    state.slabs.push({
                        id: `SC-L${yi + 1}`,
                        x1: -cantLen,  // Extends left of grid (negative X)
                        y1: yCoords[yi],
                        x2: 0,
                        y2: yCoords[yi + 1],
                        lx: cantLen,
                        ly: spanHeight,
                        area: cantLen * spanHeight,
                        isCantilever: true,
                        cantileverEdge: 'left',
                        spanIndex: yi,
                        supportingBeamId: `BY-1-${yi + 1}`,  // Left edge beam
                        isVoid: floorVoidSlabs.includes(`SC-L${yi + 1}`)
                    });
                }
            }

            // Right cantilevers (right of last column)
            const maxX = xCoords[xCoords.length - 1];
            const lastXi = state.xSpans.length;  // Last beam column index
            for (let yi = 0; yi < state.ySpans.length; yi++) {
                const cantLen = cants.right[yi] || 0;
                if (cantLen > 0) {
                    const spanHeight = state.ySpans[yi];
                    state.slabs.push({
                        id: `SC-R${yi + 1}`,
                        x1: maxX,
                        y1: yCoords[yi],
                        x2: maxX + cantLen,  // Extends right of grid
                        y2: yCoords[yi + 1],
                        lx: cantLen,
                        ly: spanHeight,
                        area: cantLen * spanHeight,
                        isCantilever: true,
                        cantileverEdge: 'right',
                        spanIndex: yi,
                        supportingBeamId: `BY-${lastXi + 1}-${yi + 1}`,  // Right edge beam
                        isVoid: floorVoidSlabs.includes(`SC-R${yi + 1}`)
                    });
                }
            }
        }

        // v3.0: Generate cantilever beams (from columns) and edge beams (at cantilever tips)
        function generateCantileverBeams(xCoords, yCoords, letters) {
            const maxX = xCoords[xCoords.length - 1];
            const maxY = yCoords[yCoords.length - 1];

            // TOP CANTILEVERS: Beams extend from columns at yi=0 upward (negative Y)
            for (let xi = 0; xi <= state.xSpans.length; xi++) {
                // Check if any adjacent span has a top cantilever
                const leftCant = xi > 0 ? (state.cantilevers.top[xi - 1] || 0) : 0;
                const rightCant = xi < state.xSpans.length ? (state.cantilevers.top[xi] || 0) : 0;
                const maxCant = Math.max(leftCant, rightCant);

                if (maxCant > 0) {
                    const col = getColumnAt(xi, 0);
                    // v3.0 FIX: Use per-floor check to prevent cascade deletion
                    const currentFloorId = state.floors[state.currentFloorIndex]?.id;
                    if (col && isColumnActiveOnFloor(col, currentFloorId)) {
                        // Cantilever beam from column to edge
                        state.beams.push({
                            id: `BCY-T-${xi + 1}`,
                            direction: 'Y',
                            isCantilever: true,
                            cantileverEdge: 'top',
                            x1: xCoords[xi],
                            y1: -maxCant,
                            x2: xCoords[xi],
                            y2: 0,
                            span: maxCant,
                            startCol: null,  // Free end
                            endCol: col.id,  // Connected to column
                            tributaryWidth: 0,
                            tributaryArea: 0,
                            slices: [],
                            w: 0,
                            Rleft: 0,
                            Rright: 0
                        });
                    }
                }
            }

            // TOP EDGE BEAM: Runs along the top edge of cantilever slabs
            let topEdgeSegments = [];
            for (let xi = 0; xi < state.xSpans.length; xi++) {
                const cantLen = state.cantilevers.top[xi] || 0;
                if (cantLen > 0) {
                    topEdgeSegments.push({ xi, cantLen });
                }
            }
            for (let seg of topEdgeSegments) {
                state.beams.push({
                    id: `BEX-T-${seg.xi + 1}`,
                    direction: 'X',
                    isEdgeBeam: true,
                    cantileverEdge: 'top',
                    x1: xCoords[seg.xi],
                    y1: -seg.cantLen,
                    x2: xCoords[seg.xi + 1],
                    y2: -seg.cantLen,
                    span: state.xSpans[seg.xi],
                    tributaryWidth: 0,
                    tributaryArea: 0,
                    slices: [],
                    w: 0,
                    Rleft: 0,
                    Rright: 0
                });
            }

            // BOTTOM CANTILEVERS: Beams extend from columns at yi=last downward
            const lastYi = state.ySpans.length;
            for (let xi = 0; xi <= state.xSpans.length; xi++) {
                const leftCant = xi > 0 ? (state.cantilevers.bottom[xi - 1] || 0) : 0;
                const rightCant = xi < state.xSpans.length ? (state.cantilevers.bottom[xi] || 0) : 0;
                const maxCant = Math.max(leftCant, rightCant);

                if (maxCant > 0) {
                    const col = getColumnAt(xi, lastYi);
                    // v3.0 FIX: Use per-floor check
                    const currentFloorId = state.floors[state.currentFloorIndex]?.id;
                    if (col && isColumnActiveOnFloor(col, currentFloorId)) {
                        state.beams.push({
                            id: `BCY-B-${xi + 1}`,
                            direction: 'Y',
                            isCantilever: true,
                            cantileverEdge: 'bottom',
                            x1: xCoords[xi],
                            y1: maxY,
                            x2: xCoords[xi],
                            y2: maxY + maxCant,
                            span: maxCant,
                            startCol: col.id,
                            endCol: null,
                            tributaryWidth: 0,
                            tributaryArea: 0,
                            slices: [],
                            w: 0,
                            Rleft: 0,
                            Rright: 0
                        });
                    }
                }
            }

            // BOTTOM EDGE BEAM
            for (let xi = 0; xi < state.xSpans.length; xi++) {
                const cantLen = state.cantilevers.bottom[xi] || 0;
                if (cantLen > 0) {
                    state.beams.push({
                        id: `BEX-B-${xi + 1}`,
                        direction: 'X',
                        isEdgeBeam: true,
                        cantileverEdge: 'bottom',
                        x1: xCoords[xi],
                        y1: maxY + cantLen,
                        x2: xCoords[xi + 1],
                        y2: maxY + cantLen,
                        span: state.xSpans[xi],
                        tributaryWidth: 0,
                        tributaryArea: 0,
                        slices: [],
                        w: 0,
                        Rleft: 0,
                        Rright: 0
                    });
                }
            }

            // LEFT CANTILEVERS: Beams extend from columns at xi=0 leftward
            for (let yi = 0; yi <= state.ySpans.length; yi++) {
                const topCant = yi > 0 ? (state.cantilevers.left[yi - 1] || 0) : 0;
                const bottomCant = yi < state.ySpans.length ? (state.cantilevers.left[yi] || 0) : 0;
                const maxCant = Math.max(topCant, bottomCant);

                if (maxCant > 0) {
                    const col = getColumnAt(0, yi);
                    // v3.0 FIX: Use per-floor check
                    const currentFloorId = state.floors[state.currentFloorIndex]?.id;
                    if (col && isColumnActiveOnFloor(col, currentFloorId)) {
                        state.beams.push({
                            id: `BCX-L-${yi + 1}`,
                            direction: 'X',
                            isCantilever: true,
                            cantileverEdge: 'left',
                            x1: -maxCant,
                            y1: yCoords[yi],
                            x2: 0,
                            y2: yCoords[yi],
                            span: maxCant,
                            startCol: null,
                            endCol: col.id,
                            tributaryWidth: 0,
                            tributaryArea: 0,
                            slices: [],
                            w: 0,
                            Rleft: 0,
                            Rright: 0
                        });
                    }
                }
            }

            // LEFT EDGE BEAM
            for (let yi = 0; yi < state.ySpans.length; yi++) {
                const cantLen = state.cantilevers.left[yi] || 0;
                if (cantLen > 0) {
                    state.beams.push({
                        id: `BEY-L-${yi + 1}`,
                        direction: 'Y',
                        isEdgeBeam: true,
                        cantileverEdge: 'left',
                        x1: -cantLen,
                        y1: yCoords[yi],
                        x2: -cantLen,
                        y2: yCoords[yi + 1],
                        span: state.ySpans[yi],
                        tributaryWidth: 0,
                        tributaryArea: 0,
                        slices: [],
                        w: 0,
                        Rleft: 0,
                        Rright: 0
                    });
                }
            }

            // RIGHT CANTILEVERS: Beams extend from columns at xi=last rightward
            const lastXi = state.xSpans.length;
            for (let yi = 0; yi <= state.ySpans.length; yi++) {
                const topCant = yi > 0 ? (state.cantilevers.right[yi - 1] || 0) : 0;
                const bottomCant = yi < state.ySpans.length ? (state.cantilevers.right[yi] || 0) : 0;
                const maxCant = Math.max(topCant, bottomCant);

                if (maxCant > 0) {
                    const col = getColumnAt(lastXi, yi);
                    // v3.0 FIX: Use per-floor check
                    const currentFloorId = state.floors[state.currentFloorIndex]?.id;
                    if (col && isColumnActiveOnFloor(col, currentFloorId)) {
                        state.beams.push({
                            id: `BCX-R-${yi + 1}`,
                            direction: 'X',
                            isCantilever: true,
                            cantileverEdge: 'right',
                            x1: maxX,
                            y1: yCoords[yi],
                            x2: maxX + maxCant,
                            y2: yCoords[yi],
                            span: maxCant,
                            startCol: col.id,
                            endCol: null,
                            tributaryWidth: 0,
                            tributaryArea: 0,
                            slices: [],
                            w: 0,
                            Rleft: 0,
                            Rright: 0
                        });
                    }
                }
            }

            // RIGHT EDGE BEAM
            for (let yi = 0; yi < state.ySpans.length; yi++) {
                const cantLen = state.cantilevers.right[yi] || 0;
                if (cantLen > 0) {
                    state.beams.push({
                        id: `BEY-R-${yi + 1}`,
                        direction: 'Y',
                        isEdgeBeam: true,
                        cantileverEdge: 'right',
                        x1: maxX + cantLen,
                        y1: yCoords[yi],
                        x2: maxX + cantLen,
                        y2: yCoords[yi + 1],
                        span: state.ySpans[yi],
                        tributaryWidth: 0,
                        tributaryArea: 0,
                        slices: [],
                        w: 0,
                        Rleft: 0,
                        Rright: 0
                    });
                }
            }
        }

        /**
         * Step 3 & 4: Generate beams and calculate tributary widths
         * v2.2: Now creates slices per slab with proper 45° math
         * Short span direction gets MORE load (stiffer)
         * v3.0: Added wallLoad parameter for line loads on beams
         */
        function generateBeams(pu, wallLoad = 0, targetFloor = null) {
            state.beams = [];

            // X-direction beams (horizontal, span in X)
            const xCoords = [0];
            for (let span of state.xSpans) xCoords.push(xCoords[xCoords.length - 1] + span);
            const yCoords = [0];
            for (let span of state.ySpans) yCoords.push(yCoords[yCoords.length - 1] + span);

            // Letters for column IDs (must match generateGrid)
            const letters = 'ABCDEFGHJKLMNPQRSTUVWXYZ';

            // Create beam objects with slices array
            for (let yi = 0; yi < yCoords.length; yi++) {
                for (let xi = 0; xi < state.xSpans.length; xi++) {
                    // v2.7: Skip beams where either endpoint column is inactive
                    const leftCol = getColumnAt(xi, yi);
                    const rightCol = getColumnAt(xi + 1, yi);
                    if (!leftCol || !rightCol || leftCol.active === false || rightCol.active === false) {
                        continue;
                    }

                    const beamSpan = state.xSpans[xi];
                    const beamId = `BX-${yi + 1}-${xi + 1}`;

                    state.beams.push({
                        id: beamId,
                        direction: 'X',
                        xi, yi,
                        x1: xCoords[xi],
                        y1: yCoords[yi],
                        x2: xCoords[xi + 1],
                        y2: yCoords[yi],
                        span: beamSpan,
                        // Column connections for load distribution
                        startCol: `${letters[xi]}${yi + 1}`,
                        endCol: `${letters[xi + 1]}${yi + 1}`,
                        tributaryWidth: 0,
                        tributaryArea: 0,
                        slices: [],  // v2.2: per-slab slices
                        w: 0,
                        Rleft: 0,
                        Rright: 0
                    });
                }
            }

            // Y-direction beams (along gridlines in X direction)
            for (let xi = 0; xi < xCoords.length; xi++) {
                for (let yi = 0; yi < state.ySpans.length; yi++) {
                    // v2.7: Skip beams where either endpoint column is inactive
                    const topCol = getColumnAt(xi, yi);
                    const bottomCol = getColumnAt(xi, yi + 1);
                    if (!topCol || !bottomCol || topCol.active === false || bottomCol.active === false) {
                        continue;
                    }

                    const beamSpan = state.ySpans[yi];
                    const beamId = `BY-${xi + 1}-${yi + 1}`;

                    state.beams.push({
                        id: beamId,
                        direction: 'Y',
                        xi, yi,
                        x1: xCoords[xi],
                        y1: yCoords[yi],
                        x2: xCoords[xi],
                        y2: yCoords[yi + 1],
                        span: beamSpan,
                        // Column connections for load distribution
                        startCol: `${letters[xi]}${yi + 1}`,
                        endCol: `${letters[xi]}${yi + 2}`,
                        tributaryWidth: 0,
                        tributaryArea: 0,
                        slices: [],  // v2.2: per-slab slices
                        w: 0,
                        Rleft: 0,
                    });
                }
            }

            // v3.0: Generate cantilever beams and edge beams
            generateCantileverBeams(xCoords, yCoords, letters);

            // v3.0: Add custom (intermediate framing) beams to state.beams
            const floor = targetFloor || state.floors[state.currentFloorIndex];
            const customBeams = floor?.customBeams || [];
            for (const cb of customBeams) {
                let x1, y1, x2, y2, span, direction;

                // v3.0 FIX: dir='X' means horizontal beam (constant Y), dir='Y' means vertical beam (constant X)
                if (cb.dir === 'X') {
                    // Horizontal beam: runs along X axis, Y is constant = cb.pos
                    x1 = cb.start;
                    x2 = cb.end;
                    y1 = cb.pos;
                    y2 = cb.pos;
                    span = cb.end - cb.start;
                    direction = 'X';  // Spans in X direction
                } else {
                    // Vertical beam: runs along Y axis, X is constant = cb.pos
                    x1 = cb.pos;
                    x2 = cb.pos;
                    y1 = cb.start;
                    y2 = cb.end;
                    span = cb.end - cb.start;
                    direction = 'Y';  // Spans in Y direction
                }

                state.beams.push({
                    id: cb.id,
                    direction: direction,
                    isCustom: true,  // Flag for custom beam
                    x1, y1, x2, y2,
                    span: span,
                    startCol: null,  // Custom beams may not connect to grid columns
                    endCol: null,
                    tributaryWidth: 0,
                    tributaryArea: 0,
                    slices: [],
                    w: 0,
                    Rleft: 0,
                    Rright: 0
                });
            }

            // Map for quick access (now includes cantilever beams + custom beams)
            const beamMap = Object.fromEntries(state.beams.map(beam => [beam.id, beam]));

            // v3.0: Helper to check if a custom beam crosses a slab
            function getCustomBeamsCrossingSlab(slab) {
                const crossing = [];
                for (const cb of customBeams) {
                    // v3.0 FIX: dir='X' means horizontal beam (constant Y), dir='Y' means vertical (constant X)
                    if (cb.dir === 'X') {
                        // Horizontal beam at Y = cb.pos
                        // Check if beam Y is within slab Y range AND beam X overlaps slab X
                        if (cb.pos > slab.y1 && cb.pos < slab.y2 &&
                            cb.start < slab.x2 && cb.end > slab.x1) {
                            crossing.push({
                                ...cb,
                                beamId: cb.id,
                                splitDir: 'Y',  // Splits slab horizontally (Y direction)
                                splitPos: cb.pos
                            });
                        }
                    } else {
                        // Vertical beam at X = cb.pos
                        if (cb.pos > slab.x1 && cb.pos < slab.x2 &&
                            cb.start < slab.y2 && cb.end > slab.y1) {
                            crossing.push({
                                ...cb,
                                beamId: cb.id,
                                splitDir: 'X',  // Splits slab vertically (X direction)
                                splitPos: cb.pos
                            });
                        }
                    }
                }
                return crossing;
            }

            // v2.2: Distribute slab areas with proper slices
            // v3.0: Skip void slabs - they don't contribute load to any beam
            for (let slab of state.slabs) {
                // v3.0: Skip void slabs - no load distribution
                if (slab.isVoid) {
                    console.log(`v3.0: Skipping void slab ${slab.id} in load distribution`);
                    continue;
                }
                // Skip cantilever slabs - handled separately below
                if (slab.isCantilever) continue;
                // Find beams on 4 edges geometrically
                const TOL = 0.05; // 5cm tolerance
                const topBeam = state.beams.find(b => b.direction === 'X' && Math.abs(b.y1 - slab.y1) < TOL && b.x1 <= slab.x1 + TOL && b.x2 >= slab.x2 - TOL);
                const bottomBeam = state.beams.find(b => b.direction === 'X' && Math.abs(b.y1 - slab.y2) < TOL && b.x1 <= slab.x1 + TOL && b.x2 >= slab.x2 - TOL);
                const leftBeam = state.beams.find(b => b.direction === 'Y' && Math.abs(b.x1 - slab.x1) < TOL && b.y1 <= slab.y1 + TOL && b.y2 >= slab.y2 - TOL);
                const rightBeam = state.beams.find(b => b.direction === 'Y' && Math.abs(b.x1 - slab.x2) < TOL && b.y1 <= slab.y1 + TOL && b.y2 >= slab.y2 - TOL);

                const topBeamId = topBeam?.id;
                const bottomBeamId = bottomBeam?.id;
                const leftBeamId = leftBeam?.id;
                const rightBeamId = rightBeam?.id;

                // Slab coordinates
                const x0 = slab.x1, x1 = slab.x2;
                const y0 = slab.y1, y1 = slab.y2;

                // Helper to create polygon and compute centroid
                function makeSlice(beamId, side, areaSide, poly) {
                    const beam = beamMap[beamId];
                    if (!beam) return;

                    const tribWidth = areaSide / beam.span;
                    const w = pu * tribWidth;

                    // Compute centroid for label placement
                    let cx = 0, cy = 0;
                    for (let pt of poly) { cx += pt.x; cy += pt.y; }
                    cx /= poly.length;
                    cy /= poly.length;

                    beam.tributaryArea += areaSide;
                    beam.slices.push({
                        slabId: slab.id,
                        side: side,
                        area: areaSide,
                        w: w,
                        poly: poly,
                        cx: cx,
                        cy: cy
                    });
                }

                if (slab.isTwoWay) {
                    const h = Math.min(slab.lx, slab.ly) / 2;  // 45° inset height

                    // Provisional areas based on 45° triangular/trapezoidal geometry
                    const xSideArea_raw = slab.lx * h / 2; // triangle for X-beams (top/bottom)
                    const trapBase = slab.ly;
                    const trapTop = slab.ly - 2 * h;
                    const ySideArea_raw = trapTop > 0
                        ? (trapBase + trapTop) * h / 2  // trapezoid for Y-beams
                        : slab.ly * h / 2;              // triangle when lines meet

                    // Normalize so total = slab.area
                    const rawTotal = 2 * xSideArea_raw + 2 * ySideArea_raw;
                    const scale = rawTotal > 0 ? slab.area / rawTotal : 0;

                    const A_top = xSideArea_raw * scale;
                    const A_bottom = xSideArea_raw * scale;
                    const A_left = ySideArea_raw * scale;
                    const A_right = ySideArea_raw * scale;

                    let topPoly, bottomPoly, leftPoly, rightPoly;

                    if (slab.lx <= slab.ly) {
                        // Short direction = X
                        // Top/Bottom = Triangles
                        topPoly = [
                            { x: x0, y: y0 },
                            { x: x1, y: y0 },
                            { x: (x0 + x1) / 2, y: y0 + h }
                        ];
                        bottomPoly = [
                            { x: x0, y: y1 },
                            { x: x1, y: y1 },
                            { x: (x0 + x1) / 2, y: y1 - h }
                        ];
                        // Left/Right = Trapezoids
                        leftPoly = [
                            { x: x0, y: y0 },
                            { x: x0, y: y1 },
                            { x: x0 + h, y: y1 - h },
                            { x: x0 + h, y: y0 + h }
                        ];
                        rightPoly = [
                            { x: x1, y: y0 },
                            { x: x1, y: y1 },
                            { x: x1 - h, y: y1 - h },
                            { x: x1 - h, y: y0 + h }
                        ];
                    } else {
                        // Short direction = Y
                        // Left/Right = Triangles
                        leftPoly = [
                            { x: x0, y: y0 },
                            { x: x0, y: y1 },
                            { x: x0 + h, y: (y0 + y1) / 2 }
                        ];
                        rightPoly = [
                            { x: x1, y: y0 },
                            { x: x1, y: y1 },
                            { x: x1 - h, y: (y0 + y1) / 2 }
                        ];
                        // Top/Bottom = Trapezoids
                        topPoly = [
                            { x: x0, y: y0 },
                            { x: x1, y: y0 },
                            { x: x1 - h, y: y0 + h },
                            { x: x0 + h, y: y0 + h }
                        ];
                        bottomPoly = [
                            { x: x0, y: y1 },
                            { x: x1, y: y1 },
                            { x: x1 - h, y: y1 - h },
                            { x: x0 + h, y: y1 - h }
                        ];
                    }

                    makeSlice(topBeamId, 'top', A_top, topPoly);
                    makeSlice(bottomBeamId, 'bottom', A_bottom, bottomPoly);
                    makeSlice(leftBeamId, 'left', A_left, leftPoly);
                    makeSlice(rightBeamId, 'right', A_right, rightPoly);
                } else {
                    // One-way slab: split into 2 rectangles
                    const halfArea = slab.area / 2;

                    if (slab.lx < slab.ly) {
                        // Spanning in Y, supported by left/right beams
                        const midX = (x0 + x1) / 2;
                        const leftPoly = [{ x: x0, y: y0 }, { x: midX, y: y0 }, { x: midX, y: y1 }, { x: x0, y: y1 }];
                        const rightPoly = [{ x: midX, y: y0 }, { x: x1, y: y0 }, { x: x1, y: y1 }, { x: midX, y: y1 }];
                        makeSlice(leftBeamId, 'left', halfArea, leftPoly);
                        makeSlice(rightBeamId, 'right', halfArea, rightPoly);
                    } else {
                        // Spanning in X, supported by top/bottom beams
                        const midY = (y0 + y1) / 2;
                        const topPoly = [{ x: x0, y: y0 }, { x: x1, y: y0 }, { x: x1, y: midY }, { x: x0, y: midY }];
                        const bottomPoly = [{ x: x0, y: midY }, { x: x1, y: midY }, { x: x1, y: y1 }, { x: x0, y: y1 }];
                        makeSlice(topBeamId, 'top', halfArea, topPoly);
                        makeSlice(bottomBeamId, 'bottom', halfArea, bottomPoly);
                    }
                }
            }

            // v3.0: Distribute slab loads to CUSTOM BEAMS that cross them
            // Custom beams receive load from the portions of slabs they cross
            for (let slab of state.slabs) {
                if (slab.isCantilever || slab.isVoid) continue;

                const crossingBeams = getCustomBeamsCrossingSlab(slab);
                for (const cb of crossingBeams) {
                    const customBeam = beamMap[cb.beamId];
                    if (!customBeam) continue;

                    // Calculate the portion of slab area that loads this custom beam
                    // Simplified: the custom beam gets a strip of width = MIN(span_in_direction, half_slab_dimension)
                    let tributaryArea;
                    if (cb.splitDir === 'Y') {
                        // Beam runs horizontally through slab
                        // It receives load from both sides up to 45° line or slab edge
                        const distToTop = cb.splitPos - slab.y1;
                        const distToBottom = slab.y2 - cb.splitPos;
                        const tributaryWidthTop = Math.min(distToTop, slab.lx / 2);
                        const tributaryWidthBottom = Math.min(distToBottom, slab.lx / 2);
                        const beamLengthInSlab = Math.min(cb.end, slab.x2) - Math.max(cb.start, slab.x1);
                        tributaryArea = beamLengthInSlab * (tributaryWidthTop + tributaryWidthBottom);
                    } else {
                        // Beam runs vertically through slab
                        const distToLeft = cb.splitPos - slab.x1;
                        const distToRight = slab.x2 - cb.splitPos;
                        const tributaryWidthLeft = Math.min(distToLeft, slab.ly / 2);
                        const tributaryWidthRight = Math.min(distToRight, slab.ly / 2);
                        const beamLengthInSlab = Math.min(cb.end, slab.y2) - Math.max(cb.start, slab.y1);
                        tributaryArea = beamLengthInSlab * (tributaryWidthLeft + tributaryWidthRight);
                    }

                    customBeam.tributaryArea += tributaryArea;
                    customBeam.slices.push({
                        slabId: slab.id,
                        side: 'custom',
                        area: tributaryArea,
                        w: pu * (tributaryArea / customBeam.span),
                        isCustom: true,
                        poly: [
                            { x: slab.x1, y: slab.y1 },
                            { x: slab.x2, y: slab.y1 },
                            { x: slab.x2, y: slab.y2 },
                            { x: slab.x1, y: slab.y2 }
                        ],
                        cx: (slab.x1 + slab.x2) / 2,
                        cy: (slab.y1 + slab.y2) / 2
                    });

                    console.log(`v3.0: Custom beam ${cb.beamId} receives ${tributaryArea.toFixed(2)} m² from slab ${slab.id}`);
                }
            }

            // v3.0: Distribute cantilever slab loads to beams
            // Load goes to: (1) the main grid edge beam, and (2) the cantilever beams
            // v3.0 FIX: Skip voided cantilever slabs - they shouldn't contribute load
            for (let slab of state.slabs.filter(s => s.isCantilever && !s.isVoid)) {
                const edge = slab.cantileverEdge;
                const spanIndex = slab.spanIndex;
                const slabArea = slab.area;

                // ===== PART 1: Add load to the MAIN GRID EDGE BEAM =====
                // This is the beam along the grid edge that the cantilever extends from
                let mainEdgeBeamId;
                if (edge === 'top') {
                    // Top cantilever is supported by BX-1-* (first row X-beams)
                    mainEdgeBeamId = `BX-1-${spanIndex + 1}`;
                } else if (edge === 'bottom') {
                    // Bottom cantilever is supported by BX-(lastRow+1)-*
                    mainEdgeBeamId = `BX-${state.ySpans.length + 1}-${spanIndex + 1}`;
                } else if (edge === 'left') {
                    // Left cantilever is supported by BY-1-*
                    mainEdgeBeamId = `BY-1-${spanIndex + 1}`;
                } else if (edge === 'right') {
                    // Right cantilever is supported by BY-(lastCol+1)-*
                    mainEdgeBeamId = `BY-${state.xSpans.length + 1}-${spanIndex + 1}`;
                }

                const mainBeam = beamMap[mainEdgeBeamId];
                if (mainBeam) {
                    // Add FULL cantilever area to the supporting edge beam
                    mainBeam.tributaryArea += slabArea;
                    mainBeam.slices.push({
                        slabId: slab.id,
                        side: 'cantilever',
                        area: slabArea,
                        w: 0,
                        isCantilever: true,
                        poly: [
                            { x: slab.x1, y: slab.y1 },
                            { x: slab.x2, y: slab.y1 },
                            { x: slab.x2, y: slab.y2 },
                            { x: slab.x1, y: slab.y2 }
                        ],
                        cx: (slab.x1 + slab.x2) / 2,
                        cy: (slab.y1 + slab.y2) / 2
                    });
                }

                // ===== PART 2: Also add load to CANTILEVER BEAMS (perpendicular) =====
                let cantBeam1Id, cantBeam2Id;
                if (edge === 'top' || edge === 'bottom') {
                    const prefix = edge === 'top' ? 'BCY-T' : 'BCY-B';
                    cantBeam1Id = `${prefix}-${spanIndex + 1}`;
                    cantBeam2Id = `${prefix}-${spanIndex + 2}`;
                } else {
                    const prefix = edge === 'left' ? 'BCX-L' : 'BCX-R';
                    cantBeam1Id = `${prefix}-${spanIndex + 1}`;
                    cantBeam2Id = `${prefix}-${spanIndex + 2}`;
                }

                // Cantilever beams get half the area each (for their own load calc)
                const halfArea = slabArea / 2;
                const cantBeam1 = beamMap[cantBeam1Id];
                const cantBeam2 = beamMap[cantBeam2Id];

                if (cantBeam1) cantBeam1.tributaryArea += halfArea;
                if (cantBeam2) cantBeam2.tributaryArea += halfArea;
            }

            // Finalize tributary widths and loads
            for (let beam of state.beams) {
                // Ensure tributary area doesn't go negative
                beam.tributaryArea = Math.max(0, beam.tributaryArea);
                beam.tributaryWidth = beam.span > 0 ? beam.tributaryArea / beam.span : 0;

                // v3.0: Add wall load to beam load
                // Wall load is kN/m, added FACTORED (1.2 × DL)
                const slabLoad = pu * beam.tributaryWidth;
                const factoredWallLoad = beam.isCantilever || beam.isEdgeBeam ? 0 : 1.2 * wallLoad;
                beam.wallLoad = factoredWallLoad;
                beam.w = slabLoad + factoredWallLoad;
            }
        }

        /**
         * Step 5: Calculate beam reactions
         * For uniform load: R_left = R_right = w * L / 2
         * v3.0: Cantilever beams - all load goes to support column
         */
        function calculateBeamReactions() {
            for (let beam of state.beams) {
                if (beam.isCantilever) {
                    // Cantilever beam: all load goes to the support (connected) end
                    const totalLoad = beam.w * beam.span;
                    if (beam.startCol) {
                        beam.Rleft = totalLoad;
                        beam.Rright = 0;
                    } else {
                        beam.Rleft = 0;
                        beam.Rright = totalLoad;
                    }
                } else if (beam.isEdgeBeam) {
                    // Edge beam: load goes to adjacent cantilever beams (handled separately)
                    beam.Rleft = beam.w * beam.span / 2;
                    beam.Rright = beam.w * beam.span / 2;
                } else {
                    // Simply supported beam with uniform load: R = w * L / 2
                    beam.Rleft = beam.w * beam.span / 2;
                    beam.Rright = beam.w * beam.span / 2;
                }
            }
        }

        /**
         * Step 6: Calculate column loads
         * Column load = Sum of all beam reactions at that column
         * v3.0: Handles cantilever beams using startCol/endCol IDs
         */
        function calculateColumnLoads() {
            // Reset column loads
            for (let col of state.columns) {
                col.loadPerFloor = 0;
                col.connectedBeams = [];
            }

            // Sum beam reactions to columns
            for (let beam of state.beams) {
                // v3.0: Cantilever and edge beams use startCol/endCol IDs
                if (beam.isCantilever || beam.isEdgeBeam) {
                    if (beam.startCol) {
                        const col = state.columns.find(c => c.id === beam.startCol);
                        if (col) {
                            col.loadPerFloor += beam.Rleft;
                            col.connectedBeams.push(beam.id);
                        }
                    }
                    if (beam.endCol) {
                        const col = state.columns.find(c => c.id === beam.endCol);
                        if (col) {
                            col.loadPerFloor += beam.Rright;
                            col.connectedBeams.push(beam.id);
                        }
                    }
                } else {
                    // Normal beams: find columns by xi/yi indices
                    let colLeft, colRight;

                    if (beam.direction === 'X') {
                        // X beam: connects columns at same yi, adjacent xi
                        colLeft = state.columns.find(c => c.xi === beam.xi && c.yi === beam.yi);
                        colRight = state.columns.find(c => c.xi === beam.xi + 1 && c.yi === beam.yi);
                    } else {
                        // Y beam: connects columns at same xi, adjacent yi
                        colLeft = state.columns.find(c => c.xi === beam.xi && c.yi === beam.yi);
                        colRight = state.columns.find(c => c.xi === beam.xi && c.yi === beam.yi + 1);
                    }

                    if (colLeft) {
                        colLeft.loadPerFloor += beam.Rleft;
                        colLeft.connectedBeams.push(beam.id);
                    }
                    if (colRight) {
                        colRight.loadPerFloor += beam.Rright;
                        colRight.connectedBeams.push(beam.id);
                    }
                }
            }

            // Calculate total load (sum across floors, not multiply!)
            for (let col of state.columns) {
                // Each floor has same load pattern
                col.totalLoad = col.loadPerFloor * state.numFloors;
            }
        }

        // ========== v3.0: MEMBER SIZING (NSCP 2015) ==========

        /**
         * Size a column based on axial load (simplified - axial only, no moment)
         * Formula: Pu ≤ φPn = φ × 0.80 × [0.85 × f'c × (Ag - Ast) + fy × Ast]
         * Simplified: Ag_required = Pu / (φ × 0.80 × (0.85 × f'c × (1 - ρ) + fy × ρ))
         * v3.0: Supports rectangular columns (b × h)
         * @param {number} Pu_kN - Ultimate axial load in kN
         * @param {number} height_m - Column height in meters (for self-weight)
         * @returns {object} { b, h, Ast, selfWeight_kN, isOverride }
         */
        function sizeColumn(Pu_kN, height_m = 3.0) {
            const phi = 0.65;  // NSCP reduction factor for tied columns
            const rho = 0.01;  // 1% minimum steel ratio
            const fc = state.fc;  // MPa
            const fy = state.fy;  // MPa
            const Pu = Pu_kN * 1000;  // Convert kN to N

            let b, h;
            let isOverride = false;

            // v3.0: Check for user override (rectangular columns)
            if (state.defaultColumnB > 0) {
                b = state.defaultColumnB;
                h = state.defaultColumnH > 0 ? state.defaultColumnH : b;  // h=0 means square
                isOverride = true;
            } else {
                // Required gross area (mm²)
                const Ag_required = Pu / (phi * 0.80 * (0.85 * fc * (1 - rho) + fy * rho));

                // Size as square column, round up to nearest 50mm
                let side = Math.ceil(Math.sqrt(Ag_required) / 50) * 50;
                side = Math.max(side, 200);  // Minimum 200mm per NSCP
                b = side;
                h = side;
            }

            // Actual gross area and required steel
            const Ag_actual = b * h;
            const Ast = Math.ceil(rho * Ag_actual);

            // v3.0: Calculate column self-weight
            const volume_m3 = (b / 1000) * (h / 1000) * height_m;
            const selfWeight_kN = volume_m3 * state.concreteDensity;

            return { b, h, Ast, selfWeight_kN, isOverride };
        }

        /**
         * Size a beam based on span-to-depth ratio (NSCP Table 409.3.1.1)
         * v3.0: Respects user-provided dimensions when defaultBeamH > 0
         * @param {number} span_m - Beam span in meters
         * @param {boolean} isCantilever - Is this a cantilever beam?
         * @returns {object} { b: width in mm, h: depth in mm }
         */
        function sizeBeam(span_m, isCantilever = false) {
            let b, h;

            // v3.0: If user specified beam depth, use it
            if (state.defaultBeamH > 0) {
                h = state.defaultBeamH;
                b = state.defaultBeamB || 250;
            } else {
                // Auto-size using NSCP span-to-depth ratio
                const L = span_m * 1000;  // Convert to mm

                // Minimum depth per NSCP based on span
                // Simply supported: L/16, Cantilever: L/8
                const minDepthRatio = isCantilever ? 8 : 16;
                h = Math.ceil((L / minDepthRatio) / 50) * 50;  // Round to 50mm
                h = Math.max(h, 300);  // Minimum 300mm depth

                // Use user-provided width or calculate from depth
                b = state.defaultBeamB > 0
                    ? state.defaultBeamB
                    : Math.max(200, Math.ceil((h * 0.5) / 50) * 50);
            }

            return { b: b, h: h };
        }

        /**
         * Apply sizing to all columns and beams
         * v3.0: Also calculates self-weight dead load
         */
        function sizeMembers() {
            // Size all columns based on their total load
            let totalColumnSelfWeight = 0;
            for (let col of state.columns) {
                if (col.active === false) continue;
                const height = state.floors[0]?.height || 3.0;  // Use first floor height
                const sizing = sizeColumn(col.totalLoad, height);
                col.suggestedB = sizing.b;
                col.suggestedH = sizing.h;
                col.suggestedAst = sizing.Ast;
                col.selfWeight = sizing.selfWeight_kN;
                col.isOverride = sizing.isOverride;
                totalColumnSelfWeight += col.selfWeight;
            }
            state.totalColumnSelfWeight = totalColumnSelfWeight;

            // Size all beams based on their span
            let totalBeamSelfWeight = 0;
            for (let beam of state.beams) {
                const sizing = sizeBeam(beam.span, beam.isCantilever || false);
                beam.suggestedB = sizing.b;
                beam.suggestedH = sizing.h;

                // v3.0: Calculate beam self-weight
                // Volume = b × h × span, Weight = γc × Volume
                const bM = sizing.b / 1000;  // Convert mm to m
                const hM = sizing.h / 1000;  // Convert mm to m
                beam.selfWeight = state.concreteDensity * bM * hM * beam.span;  // kN total
                beam.selfWeightPerM = state.concreteDensity * bM * hM;  // kN/m
                totalBeamSelfWeight += beam.selfWeight;
            }

            // Store total self-weight for display
            state.totalBeamSelfWeight = totalBeamSelfWeight;
        }