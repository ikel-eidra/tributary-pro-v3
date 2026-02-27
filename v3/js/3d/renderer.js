// ========== v2.4: THREE.JS 3D VIEW ==========
        let scene3D, camera3D, renderer3D, controls3D;
        let meshes3D = [];
        let view3DInitialized = false;

        function init3D() {
            if (view3DInitialized) return;

            const container = document.getElementById('container3D');

            // Scene
            scene3D = new THREE.Scene();
            scene3D.background = new THREE.Color(0x0f1419);

            // Camera
            camera3D = new THREE.PerspectiveCamera(60, container.clientWidth / container.clientHeight, 0.1, 1000);
            camera3D.position.set(25, 30, 25);
            camera3D.lookAt(0, 5, 0);

            // Renderer
            renderer3D = new THREE.WebGLRenderer({ antialias: true });
            renderer3D.setSize(container.clientWidth, container.clientHeight);

            // v3.0 FIX: Set initial background color based on current theme
            const currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
            if (currentTheme === 'light') {
                renderer3D.setClearColor(0xf8fafc);
            } else if (currentTheme === 'blueprint') {
                renderer3D.setClearColor(0x0a1929);
            } else {
                renderer3D.setClearColor(0x0a0d10);
            }

            container.appendChild(renderer3D.domElement);

            // Orbit Controls - v3.0: Restored to default (LEFT = rotate, like v2.8)
            controls3D = new THREE.OrbitControls(camera3D, renderer3D.domElement);
            controls3D.enableDamping = true;
            controls3D.dampingFactor = 0.05;
            controls3D.target.set(0, 5, 0);

            // Lights
            scene3D.add(new THREE.AmbientLight(0xffffff, 0.5));
            const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
            dirLight.position.set(20, 30, 20);
            scene3D.add(dirLight);

            // Grid helper
            const grid = new THREE.GridHelper(50, 20, 0x00d4ff, 0x333333);
            scene3D.add(grid);

            // v3.0: Raycaster for 3D click detection
            const raycaster3D = new THREE.Raycaster();
            const mouse3D = new THREE.Vector2();

            // ========== v3.0: AutoCAD-Style Box Selection ==========
            // Create selection overlay canvas
            const selectionOverlay = document.createElement('canvas');
            selectionOverlay.id = 'selectionOverlay3D';
            selectionOverlay.style.cssText = 'position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:10;';
            container.appendChild(selectionOverlay);
            const selCtx = selectionOverlay.getContext('2d');

            // Box selection state
            let boxSelecting = false;
            let boxStart = { x: 0, y: 0 };
            let boxEnd = { x: 0, y: 0 };
            let isWindowSelection = true; // Left-to-right = window, Right-to-left = crossing

            // Resize overlay with container
            function resizeSelectionOverlay() {
                selectionOverlay.width = container.clientWidth;
                selectionOverlay.height = container.clientHeight;
            }
            resizeSelectionOverlay();
            window.addEventListener('resize', resizeSelectionOverlay);

            // Draw selection box
            function drawSelectionBox() {
                selCtx.clearRect(0, 0, selectionOverlay.width, selectionOverlay.height);
                if (!boxSelecting) return;

                const x = Math.min(boxStart.x, boxEnd.x);
                const y = Math.min(boxStart.y, boxEnd.y);
                const w = Math.abs(boxEnd.x - boxStart.x);
                const h = Math.abs(boxEnd.y - boxStart.y);

                if (w < 5 && h < 5) return; // Too small to draw

                // v3.0: AutoCAD-style colors
                // Window (left-to-right): Blue with dashed border
                // Crossing (right-to-left): Green with solid border
                if (isWindowSelection) {
                    selCtx.fillStyle = 'rgba(0, 120, 255, 0.15)';
                    selCtx.strokeStyle = '#0078ff';
                    selCtx.setLineDash([8, 4]);
                } else {
                    selCtx.fillStyle = 'rgba(0, 255, 100, 0.15)';
                    selCtx.strokeStyle = '#00ff64';
                    selCtx.setLineDash([]);
                }
                selCtx.lineWidth = 2;
                selCtx.fillRect(x, y, w, h);
                selCtx.strokeRect(x, y, w, h);

                // Label
                selCtx.font = 'bold 12px Inter, system-ui, sans-serif';
                selCtx.fillStyle = isWindowSelection ? '#0078ff' : '#00ff64';
                selCtx.fillText(isWindowSelection ? '⬜ WINDOW' : '🔲 CROSSING', x + 5, y - 5);
            }

            // Project 3D mesh to 2D screen coordinates
            function getMeshScreenBounds(mesh) {
                if (!mesh.geometry) return null;

                mesh.geometry.computeBoundingBox();
                const box = mesh.geometry.boundingBox;
                if (!box) return null;

                // Get 8 corners of bounding box
                const corners = [
                    new THREE.Vector3(box.min.x, box.min.y, box.min.z),
                    new THREE.Vector3(box.min.x, box.min.y, box.max.z),
                    new THREE.Vector3(box.min.x, box.max.y, box.min.z),
                    new THREE.Vector3(box.min.x, box.max.y, box.max.z),
                    new THREE.Vector3(box.max.x, box.min.y, box.min.z),
                    new THREE.Vector3(box.max.x, box.min.y, box.max.z),
                    new THREE.Vector3(box.max.x, box.max.y, box.min.z),
                    new THREE.Vector3(box.max.x, box.max.y, box.max.z),
                ];

                let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;

                mesh.updateMatrixWorld(true);
                for (const corner of corners) {
                    const worldPos = corner.clone().applyMatrix4(mesh.matrixWorld);
                    worldPos.project(camera3D);

                    const screenX = (worldPos.x * 0.5 + 0.5) * selectionOverlay.width;
                    const screenY = (-worldPos.y * 0.5 + 0.5) * selectionOverlay.height;

                    minX = Math.min(minX, screenX);
                    minY = Math.min(minY, screenY);
                    maxX = Math.max(maxX, screenX);
                    maxY = Math.max(maxY, screenY);
                }

                return { minX, minY, maxX, maxY };
            }

            // Check if mesh is inside selection box
            function isMeshInSelection(mesh, selBox, windowMode) {
                const meshBounds = getMeshScreenBounds(mesh);
                if (!meshBounds) return false;

                if (windowMode) {
                    // Window: mesh must be fully enclosed
                    return meshBounds.minX >= selBox.minX && meshBounds.maxX <= selBox.maxX &&
                        meshBounds.minY >= selBox.minY && meshBounds.maxY <= selBox.maxY;
                } else {
                    // Crossing: mesh just needs to intersect
                    return !(meshBounds.maxX < selBox.minX || meshBounds.minX > selBox.maxX ||
                        meshBounds.maxY < selBox.minY || meshBounds.minY > selBox.maxY);
                }
            }

            // Handle box selection completion
            function completeBoxSelection() {
                const selBox = {
                    minX: Math.min(boxStart.x, boxEnd.x),
                    minY: Math.min(boxStart.y, boxEnd.y),
                    maxX: Math.max(boxStart.x, boxEnd.x),
                    maxY: Math.max(boxStart.y, boxEnd.y)
                };

                // Only process if box is large enough
                if (selBox.maxX - selBox.minX < 10 || selBox.maxY - selBox.minY < 10) {
                    return;
                }

                // Find all selected meshes with valid userData.type
                const selectedItems = [];
                for (const mesh of meshes3D) {
                    if (mesh.userData && mesh.userData.type && isMeshInSelection(mesh, selBox, isWindowSelection)) {
                        selectedItems.push({
                            mesh: mesh,
                            type: mesh.userData.type,
                            id: mesh.userData.id,
                            floorId: mesh.userData.floorId
                        });
                    }
                }

                if (selectedItems.length === 0) {
                    console.log('v3.0: No items selected');
                    return;
                }

                // Group by type for display
                const columns = selectedItems.filter(i => i.type === 'column');
                const beams = selectedItems.filter(i => i.type === 'beam');
                const customBeams = selectedItems.filter(i => i.type === 'customBeam');

                // Build confirmation message
                let msg = `🗑️ Delete ${selectedItems.length} item(s)?\n\n`;
                if (columns.length > 0) {
                    msg += `📍 Columns (${columns.length}): ${columns.map(c => c.id).join(', ')}\n`;
                }
                if (beams.length > 0) {
                    msg += `📏 Beams (${beams.length}): ${beams.slice(0, 10).map(b => b.id).join(', ')}${beams.length > 10 ? '...' : ''}\n`;
                }
                if (customBeams.length > 0) {
                    msg += `🪜 Custom Beams (${customBeams.length}): ${customBeams.map(b => b.id).join(', ')}\n`;
                }

                if (confirm(msg)) {
                    // Delete columns
                    for (const item of columns) {
                        toggleColumn(item.id);
                        console.log(`v3.0: Column ${item.id} deleted via box selection`);
                    }

                    // Delete beams
                    for (const item of beams) {
                        const floor = state.floors.find(f => f.id === item.floorId);
                        if (floor) {
                            if (!floor.deletedBeams) floor.deletedBeams = [];
                            if (!floor.deletedBeams.includes(item.id)) {
                                floor.deletedBeams.push(item.id);
                            }
                        }
                    }

                    // Delete custom beams
                    for (const item of customBeams) {
                        const floor = state.floors.find(f => f.id === item.floorId);
                        if (floor && floor.customBeams) {
                            floor.customBeams = floor.customBeams.filter(b => b.id !== item.id);
                        }
                    }

                    // Refresh
                    calculate();
                    render3DFrame();
                    console.log(`v3.0: Deleted ${selectedItems.length} items via ${isWindowSelection ? 'window' : 'crossing'} selection`);
                }
            }

            // Mouse event handlers for box selection
            renderer3D.domElement.addEventListener('mousedown', (event) => {
                // Only left mouse button
                if (event.button !== 0) return;

                const rect = renderer3D.domElement.getBoundingClientRect();
                boxStart = {
                    x: event.clientX - rect.left,
                    y: event.clientY - rect.top
                };
                boxEnd = { ...boxStart };
                boxSelecting = true;

                // v3.0 FIX: Do NOT disable OrbitControls here - let orbit work by default
                // Only disable after significant drag in mousemove (see below)
                isWindowSelection = true;
            });

            renderer3D.domElement.addEventListener('mousemove', (event) => {
                if (!boxSelecting) return;

                const rect = renderer3D.domElement.getBoundingClientRect();
                boxEnd = {
                    x: event.clientX - rect.left,
                    y: event.clientY - rect.top
                };

                // AutoCAD-style: left-to-right = window, right-to-left = crossing
                isWindowSelection = boxEnd.x >= boxStart.x;

                // Disable orbit controls while box selecting (if box is large enough)
                if (Math.abs(boxEnd.x - boxStart.x) > 5 || Math.abs(boxEnd.y - boxStart.y) > 5) {
                    controls3D.enabled = false;
                }

                drawSelectionBox();
            });

            renderer3D.domElement.addEventListener('mouseup', (event) => {
                if (!boxSelecting) return;

                const wasBoxSelection = Math.abs(boxEnd.x - boxStart.x) > 10 || Math.abs(boxEnd.y - boxStart.y) > 10;

                boxSelecting = false;
                controls3D.enabled = true;
                selCtx.clearRect(0, 0, selectionOverlay.width, selectionOverlay.height);

                if (wasBoxSelection) {
                    completeBoxSelection();
                }
            });

            // v3.0: Double-click to delete individual 3D members
            renderer3D.domElement.addEventListener('dblclick', (event) => {
                const rect = renderer3D.domElement.getBoundingClientRect();

                // Calculate normalized device coordinates (-1 to +1)
                mouse3D.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
                mouse3D.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

                // Update raycaster
                raycaster3D.setFromCamera(mouse3D, camera3D);

                // Check intersections with all meshes
                const intersects = raycaster3D.intersectObjects(meshes3D, false);

                if (intersects.length === 0) {
                    console.log('v3.0: No object detected at click position');
                    return;
                }

                // v3.0 FIX: Find first intersected object with valid userData.type
                // Skip slabs and tributary surfaces that have empty userData
                const hit = intersects.find(i => i.object.userData && i.object.userData.type);

                if (!hit) {
                    console.log('v3.0: No structural member at click position (only slabs/surfaces)');
                    return;
                }

                const userData = hit.object.userData;

                console.log(`v3.0: Double-clicked ${userData.type}: ${userData.id}`);

                // Confirm and delete
                if (userData.type === 'column') {
                    if (confirm(`🗑️ Delete column ${userData.id}?`)) {
                        toggleColumn(userData.id);
                        calculate();
                        render3DFrame();
                        console.log(`v3.0: Column ${userData.id} deleted`);
                    }
                } else if (userData.type === 'beam') {
                    if (confirm(`🗑️ Delete beam ${userData.id}?`)) {
                        const floor = state.floors.find(f => f.id === userData.floorId);
                        if (floor) {
                            if (!floor.deletedBeams) floor.deletedBeams = [];
                            if (!floor.deletedBeams.includes(userData.id)) {
                                floor.deletedBeams.push(userData.id);
                            }
                            calculate();
                            render3DFrame();
                            console.log(`v3.0: Beam ${userData.id} deleted`);
                        }
                    }
                } else if (userData.type === 'customBeam') {
                    if (confirm(`🗑️ Delete custom beam ${userData.id}?`)) {
                        const floor = state.floors.find(f => f.id === userData.floorId);
                        if (floor && floor.customBeams) {
                            floor.customBeams = floor.customBeams.filter(b => b.id !== userData.id);
                            calculate();
                            render3DFrame();
                            console.log(`v3.0: Custom beam ${userData.id} deleted`);
                        }
                    }
                }
            });

            // ESC to cancel selection
            document.addEventListener('keydown', (event) => {
                if (event.key === 'Escape' && boxSelecting) {
                    boxSelecting = false;
                    controls3D.enabled = true;
                    selCtx.clearRect(0, 0, selectionOverlay.width, selectionOverlay.height);
                    console.log('v3.0: Box selection cancelled');
                }
            });

            view3DInitialized = true;
            animate3D();
        }

        function animate3D() {
            requestAnimationFrame(animate3D);
            if (controls3D) controls3D.update();
            if (renderer3D && scene3D && camera3D) {
                renderer3D.render(scene3D, camera3D);
            }
        }

        function render3DFrame() {
            if (!scene3D) return;

            // Clear previous meshes
            meshes3D.forEach(m => scene3D.remove(m));
            meshes3D = [];

            const colSize = 0.3;  // 300mm column
            const beamW = 0.25;   // 250mm beam width
            const beamH = 0.5;    // 500mm beam depth

            // Calculate grid bounds for centering
            const totalX = state.xSpans.reduce((a, b) => a + b, 0);
            const totalY = state.ySpans.reduce((a, b) => a + b, 0);
            const offsetX = -totalX / 2;
            const offsetZ = -totalY / 2;

            // Track cumulative height for proper floor stacking
            let cumulativeY = 0;

            // For each floor
            state.floors.forEach((floor, fi) => {
                const baseY = cumulativeY;  // Use cumulative height, not fi * height

                // COLUMNS - vertical boxes (skip inactive on THIS floor)
                for (let col of state.columns) {
                    // v3.0: Skip columns inactive on THIS floor (not global col.active)
                    if (!isColumnActiveOnFloor(col, floor.id)) continue;

                    // v3.0: Skip planted columns on floors BELOW their startFloor
                    if (col.startFloor && !isFloorAtOrAbove(floor.id, col.startFloor)) {
                        continue; // Don't render this column segment on floors below startFloor
                    }

                    // v3.0: Custom planted columns (placed on beams) - check isPlanted and startFloor
                    if (col.isPlanted && col.startFloor && !isFloorAtOrAbove(floor.id, col.startFloor)) {
                        continue; // Don't render beam-placed planted columns below their start floor
                    }

                    const geo = new THREE.BoxGeometry(colSize, floor.height, colSize);

                    // Column color by type - planted columns get purple color
                    let colColor = col.type === 'corner' ? 0xf59e0b :
                        col.type === 'edge' ? 0x00d4ff : 0x10b981;

                    // v3.0: Planted columns (beam-placed) get purple to distinguish
                    if (col.isPlanted) colColor = 0x8b5cf6;

                    const mat = new THREE.MeshStandardMaterial({ color: colColor });
                    const mesh = new THREE.Mesh(geo, mat);
                    mesh.position.set(col.x + offsetX, baseY + floor.height / 2, col.y + offsetZ);

                    // v3.0: Store data for click detection
                    mesh.userData = { type: 'column', id: col.id, floorId: floor.id, isPlanted: col.isPlanted };

                    scene3D.add(mesh);
                    meshes3D.push(mesh);
                }

                // Note: cumulativeY updated at end of forEach iteration

                // BEAMS - at top of each floor (skip if connected to inactive columns OR deleted on this floor)
                const floorDeletedBeams = floor.deletedBeams || [];  // v3.0: Per-floor deleted beams

                for (let beam of state.beams) {
                    // v3.0 FIX: Skip custom beams - they are drawn separately below
                    if (beam.isCustom) continue;

                    // v3.0: Skip beams deleted on THIS floor
                    if (floorDeletedBeams.includes(beam.id)) continue;

                    // v2.7: Skip beams connected to inactive columns
                    const startCol = state.columns.find(c => c.id === beam.startCol);
                    const endCol = state.columns.find(c => c.id === beam.endCol);
                    if ((startCol && startCol.active === false) || (endCol && endCol.active === false)) {
                        continue;
                    }


                    // v3.0: Get actual column sizes at beam ends
                    const startColSize = startCol ? (startCol.suggestedB || 300) / 1000 : 0.3;
                    const endColSize = endCol ? (endCol.suggestedB || 300) / 1000 : 0.3;

                    // v3.0 FIX: Subtract half column width from each end for non-overlapping BOQ
                    const rawLength = Math.sqrt(
                        Math.pow(beam.x2 - beam.x1, 2) +
                        Math.pow(beam.y2 - beam.y1, 2)
                    );
                    const clearLength = rawLength - (startColSize / 2) - (endColSize / 2);
                    const length = Math.max(0.1, clearLength);  // Ensure positive length

                    // Create beam geometry with correct length
                    const geo = beam.direction === 'X'
                        ? new THREE.BoxGeometry(length, beamH, beamW)
                        : new THREE.BoxGeometry(beamW, beamH, length);

                    // Beam color by direction
                    const mat = new THREE.MeshStandardMaterial({
                        color: beam.direction === 'X' ? 0x7c3aed : 0x10b981
                    });
                    const mesh = new THREE.Mesh(geo, mat);

                    // Position at midpoint
                    const mx = (beam.x1 + beam.x2) / 2 + offsetX;
                    const mz = (beam.y1 + beam.y2) / 2 + offsetZ;
                    mesh.position.set(mx, baseY + floor.height - beamH / 2, mz);

                    // v3.0: Store data for click detection
                    mesh.userData = { type: 'beam', id: beam.id, floorId: floor.id };

                    scene3D.add(mesh);
                    meshes3D.push(mesh);
                }

                // v3.0: CUSTOM BEAMS - orange intermediate framing beams
                const customBeams = floor.customBeams || [];
                for (let cb of customBeams) {
                    let length, cbX, cbZ;
                    // v3.0 FIX: dir='X' means beam runs horizontally (along X axis), constant Y
                    // dir='Y' means beam runs vertically (along Y axis), constant X
                    if (cb.dir === 'X') {
                        // Horizontal beam at Y = cb.pos, runs from cb.start to cb.end in X
                        length = cb.end - cb.start;
                        cbX = (cb.start + cb.end) / 2 + offsetX;
                        cbZ = cb.pos + offsetZ;
                    } else {
                        // Vertical beam at X = cb.pos, runs from cb.start to cb.end in Y
                        length = cb.end - cb.start;
                        cbX = cb.pos + offsetX;
                        cbZ = (cb.start + cb.end) / 2 + offsetZ;
                    }

                    // Geometry: X beams are wide in X, Y beams are wide in Z
                    const geo = cb.dir === 'X'
                        ? new THREE.BoxGeometry(length, beamH, beamW)
                        : new THREE.BoxGeometry(beamW, beamH, length);

                    const mat = new THREE.MeshStandardMaterial({
                        color: 0xf97316  // Orange for custom beams
                    });
                    const mesh = new THREE.Mesh(geo, mat);
                    mesh.position.set(cbX, baseY + floor.height - beamH / 2, cbZ);
                    mesh.userData = { type: 'customBeam', id: cb.id, floorId: floor.id };

                    scene3D.add(mesh);
                    meshes3D.push(mesh);
                }

                // SLABS - transparent horizontal planes (skip void slabs on THIS floor)
                const floorVoidSlabs = floor.voidSlabs || [];  // v3.0: Per-floor void slabs

                for (let slab of state.slabs) {
                    // v3.0: Skip void slabs on THIS floor (not slab.isVoid which is current floor only)
                    if (floorVoidSlabs.includes(slab.id)) continue;

                    const geo = new THREE.PlaneGeometry(slab.lx * 0.95, slab.ly * 0.95);
                    const mat = new THREE.MeshStandardMaterial({
                        color: slab.isTwoWay ? 0x00d4ff : 0x7c3aed,
                        transparent: true,
                        opacity: 0.4,

                        side: THREE.DoubleSide
                    });
                    const mesh = new THREE.Mesh(geo, mat);
                    mesh.rotation.x = -Math.PI / 2;
                    mesh.position.set(
                        slab.x1 + slab.lx / 2 + offsetX,
                        baseY + floor.height + 0.01,
                        slab.y1 + slab.ly / 2 + offsetZ
                    );
                    scene3D.add(mesh);
                    meshes3D.push(mesh);
                }

                // Update cumulative height for next floor
                cumulativeY += floor.height;
            });

            // v2.6: ELEVATED GF BEAMS - when gfSuspended is checked
            const elevationHeight = state.gfSuspended
                ? (parseFloat(document.getElementById('elevationHeight')?.value) || 1.2)
                : 0;

            if (state.gfSuspended && elevationHeight > 0) {
                for (let beam of state.beams) {
                    // v3.0 FIX: Skip custom beams - they belong to specific floors only
                    if (beam.isCustom) continue;

                    const length = Math.sqrt(
                        Math.pow(beam.x2 - beam.x1, 2) +
                        Math.pow(beam.y2 - beam.y1, 2)
                    );

                    const geo = beam.direction === 'X'
                        ? new THREE.BoxGeometry(length, beamH, beamW)
                        : new THREE.BoxGeometry(beamW, beamH, length);

                    const mat = new THREE.MeshStandardMaterial({
                        color: 0x22d3ee  // Cyan for elevated GF beams
                    });
                    const mesh = new THREE.Mesh(geo, mat);

                    const mx = (beam.x1 + beam.x2) / 2 + offsetX;
                    const mz = (beam.y1 + beam.y2) / 2 + offsetZ;
                    // Position at elevation height (below GF floor)
                    mesh.position.set(mx, elevationHeight - beamH / 2, mz);

                    scene3D.add(mesh);
                    meshes3D.push(mesh);
                }
            }

            // v2.6: FOOTINGS - all leveled at top (same top level, varying thickness)
            const footingDepth = state.footingDepth;
            const maxThick = Math.max(...state.columns.map(c => c.footingThick || 0.3));

            for (let col of state.columns) {
                // v2.7: Skip footings for inactive columns
                if (col.active === false) continue;

                // v3.0 FIX: Skip footings for planted columns (they sit on beams, not ground)
                if (col.startFloor || col.isPlanted) continue;

                const size = col.footingSize || 0.8;
                // Increase thickness for smaller footings so all tops are level
                const baseThick = col.footingThick || 0.3;
                const adjustedThick = maxThick;  // All same thickness for level top

                // Footing geometry
                const geo = new THREE.BoxGeometry(size, adjustedThick, size);
                const mat = new THREE.MeshStandardMaterial({
                    color: 0x8b5cf6,  // Purple for footings
                    transparent: true,
                    opacity: 0.8
                });
                const mesh = new THREE.Mesh(geo, mat);

                // Position below ground - all tops at same level
                const footingTopY = -footingDepth + adjustedThick;
                mesh.position.set(
                    col.x + offsetX,
                    footingTopY - adjustedThick / 2,
                    col.y + offsetZ
                );
                scene3D.add(mesh);
                meshes3D.push(mesh);

                // Footing pedestal (connecting column to footing)
                const pedestalGeo = new THREE.BoxGeometry(colSize * 1.2, footingDepth - adjustedThick, colSize * 1.2);
                const pedestalMat = new THREE.MeshStandardMaterial({ color: 0x666666 });
                const pedestal = new THREE.Mesh(pedestalGeo, pedestalMat);
                pedestal.position.set(
                    col.x + offsetX,
                    -(footingDepth - adjustedThick) / 2,
                    col.y + offsetZ
                );
                scene3D.add(pedestal);
                meshes3D.push(pedestal);
            }

            // v2.8: TIE BEAMS - using calculated sizing from longest span
            const tieBeamH = state.tieBeamH;  // Calculated: max(longestSpan/10, 0.3m)
            const tieBeamW = state.tieBeamW;  // Calculated: max(largestFooting, 0.25m)
            const tieBeamTopY = -footingDepth + maxThick + tieBeamH / 2;  // On top of footings

            for (let beam of state.beams) {
                // v3.0 FIX: Skip custom beams - they belong to specific floors only
                if (beam.isCustom) continue;
                // v3.0 FIX: Skip cantilever and edge beams - tie beams only connect main grid columns
                if (beam.isCantilever || beam.isEdgeBeam) continue;

                const length = Math.sqrt(
                    Math.pow(beam.x2 - beam.x1, 2) +
                    Math.pow(beam.y2 - beam.y1, 2)
                );

                const geo = beam.direction === 'X'
                    ? new THREE.BoxGeometry(length, tieBeamH, tieBeamW)
                    : new THREE.BoxGeometry(tieBeamW, tieBeamH, length);

                const mat = new THREE.MeshStandardMaterial({
                    color: 0x666666  // Gray for tie beams
                });
                const mesh = new THREE.Mesh(geo, mat);

                const mx = (beam.x1 + beam.x2) / 2 + offsetX;
                const mz = (beam.y1 + beam.y2) / 2 + offsetZ;
                mesh.position.set(mx, tieBeamTopY, mz);

                scene3D.add(mesh);
                meshes3D.push(mesh);
            }

            // Update camera target to center (including footings)
            const centerY = (state.floors.length * 3) / 2 - footingDepth / 2;
            controls3D.target.set(0, centerY, 0);
            camera3D.position.set(totalX * 1.5, centerY + 15, totalY * 1.5);
        }

        function setView(mode) {
            const canvas2D = document.getElementById('mainCanvas');
            const container3D = document.getElementById('container3D');
            const btn2D = document.getElementById('view2D');
            const btn3D = document.getElementById('view3D');

            if (mode === '2d') {
                canvas2D.style.display = 'block';
                container3D.classList.remove('active');
                btn2D.classList.add('active');
                btn3D.classList.remove('active');
            } else {
                canvas2D.style.display = 'none';
                container3D.classList.add('active');
                btn2D.classList.remove('active');
                btn3D.classList.add('active');

                if (!view3DInitialized) {
                    init3D();
                }
                render3DFrame();

                // Resize renderer
                const rect = container3D.getBoundingClientRect();
                if (renderer3D && rect.width > 0 && rect.height > 0) {
                    renderer3D.setSize(rect.width, rect.height);
                    camera3D.aspect = rect.width / rect.height;
                    camera3D.updateProjectionMatrix();
                }
            }
        }