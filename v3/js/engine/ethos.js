// ========== RESIDENT ETHOS ENGINE ==========
        const ETHOS = {
            apiKey: localStorage.getItem('residentEthosApiKey'),
            history: [],
            isLoading: false,

            SYSTEM_PROMPT: `You are Resident Ethos, an AI structural engineering assistant in Tributary Pro v3.0.
Tributary Pro calculates column loads, beam reactions, and footing sizes per NSCP 2015 (Philippines).

You can access the current project state. Be concise, technical, use engineering terms.
Reference NSCP sections when applicable. Format numbers with units (kN, mm, m).`,

            // Get project state
            getState() {
                return {
                    grid: { xSpans: state.xSpans, ySpans: state.ySpans },
                    floors: state.floors.map(f => ({ id: f.id, height: f.height, load: f.load })),
                    columns: state.columns.filter(c => c.active !== false).length,
                    settings: { fc: state.fc, fy: state.fy, sbc: state.sbc }
                };
            },

            getColumnLoads() {
                return state.columns.filter(c => c.active !== false).map(c => ({
                    id: c.id, type: c.type,
                    load: c.totalLoad ? c.totalLoad.toFixed(1) + ' kN' : 'N/A',
                    size: c.suggestedB ? `${c.suggestedB}x${c.suggestedH} mm` : 'N/A'
                }));
            },

            // ========== ACTION FUNCTIONS ==========

            setXSpans(values) {
                if (!Array.isArray(values)) return { success: false, error: 'values must be an array' };
                state.xSpans = values.map(v => parseFloat(v));
                if (typeof renderSpans === 'function') renderSpans();
                if (typeof calculate === 'function') calculate();
                return { success: true, message: `✅ Set ${state.xSpans.length} X-spans: ${state.xSpans.join('m, ')}m` };
            },

            setYSpans(values) {
                if (!Array.isArray(values)) return { success: false, error: 'values must be an array' };
                state.ySpans = values.map(v => parseFloat(v));
                if (typeof renderSpans === 'function') renderSpans();
                if (typeof calculate === 'function') calculate();
                return { success: true, message: `✅ Set ${state.ySpans.length} Y-spans: ${state.ySpans.join('m, ')}m` };
            },

            setFloorCount(count) {
                const target = parseInt(count);
                if (target < 1 || target > 10) return { success: false, error: 'Floor count must be 1-10' };
                while (state.floors.length < target) { if (typeof addFloor === 'function') addFloor(); else break; }
                while (state.floors.length > target) { if (typeof removeFloor === 'function') removeFloor(); else break; }
                return { success: true, message: `✅ Set to ${state.floors.length} floors` };
            },

            runCalculation() {
                if (typeof calculate === 'function') {
                    calculate();
                    const maxLoad = state.columns.length > 0
                        ? Math.max(...state.columns.filter(c => c.active !== false).map(c => c.totalLoad || 0))
                        : 0;
                    return { success: true, message: `✅ Calculation complete!\n📊 Max column load: ${maxLoad.toFixed(1)} kN\n🏛️ Active columns: ${state.columns.filter(c => c.active !== false).length}` };
                }
                return { success: false, error: 'calculate function not available' };
            },

            exportProject(format) {
                const fmt = format.toUpperCase();
                if (fmt === 'STAAD' && typeof exportToSTAAD === 'function') {
                    exportToSTAAD();
                    return { success: true, message: '✅ Exported to STAAD format (download started)' };
                } else if (fmt === 'ETABS' && typeof exportToETABS === 'function') {
                    exportToETABS();
                    return { success: true, message: '✅ Exported to ETABS format (download started)' };
                }
                return { success: false, error: `Unknown format: ${format}. Use STAAD or ETABS.` };
            },

            setLiveLoad(value) {
                const ll = parseFloat(value);
                if (isNaN(ll) || ll < 0 || ll > 20) return { success: false, error: 'Live load must be 0-20 kPa' };
                state.LL = ll;
                const llInput = document.getElementById('LL');
                if (llInput) llInput.value = ll;
                if (typeof calculate === 'function') calculate();
                return { success: true, message: `✅ Live load set to ${ll} kPa` };
            },

            // ========== COMMAND PARSER ==========
            parseCommand(msg) {
                const lower = msg.toLowerCase();

                // Set X spans: "set x spans to 4, 5, 4" or "x spans 4m 5m 4m"
                let match = lower.match(/(?:set\s+)?x\s*spans?\s*(?:to\s+)?([\d.,\s]+)/);
                if (match) {
                    const values = match[1].split(/[\s,]+/).map(v => parseFloat(v.replace('m', ''))).filter(v => !isNaN(v) && v > 0);
                    if (values.length > 0) return this.setXSpans(values);
                }

                // Set Y spans
                match = lower.match(/(?:set\s+)?y\s*spans?\s*(?:to\s+)?([\d.,\s]+)/);
                if (match) {
                    const values = match[1].split(/[\s,]+/).map(v => parseFloat(v.replace('m', ''))).filter(v => !isNaN(v) && v > 0);
                    if (values.length > 0) return this.setYSpans(values);
                }

                // Set floor count: "set to 4 floors" or "4 floors" or "add 3 floors"
                match = lower.match(/(\d+)\s*(?:storeys?|floors?)/);
                if (match && (lower.includes('set') || lower.includes('make') || lower.includes('floors'))) {
                    return this.setFloorCount(parseInt(match[1]));
                }

                // Calculate: "calculate" or "run calculation"
                if (lower.includes('calculate') || lower.includes('run calc') || lower.includes('compute')) {
                    return this.runCalculation();
                }

                // Export: "export to staad" or "staad export"
                if (lower.includes('export') && lower.includes('staad')) {
                    return this.exportProject('STAAD');
                }
                if (lower.includes('export') && lower.includes('etabs')) {
                    return this.exportProject('ETABS');
                }

                // Set live load: "set live load to 2.4" or "LL 2.4 kpa"
                match = lower.match(/(?:set\s+)?(?:live\s*load|ll)\s*(?:to\s+)?([\d.]+)/);
                if (match) {
                    return this.setLiveLoad(parseFloat(match[1]));
                }

                return null; // No command matched
            },

            // Chat with Gemini
            async chat(message) {
                if (!this.apiKey) return { success: false, error: 'API key not set' };

                // v3.0: Check for action commands FIRST
                const cmdResult = this.parseCommand(message);
                if (cmdResult) {
                    this.history.push({ role: 'user', parts: [{ text: message }] });
                    this.history.push({ role: 'model', parts: [{ text: cmdResult.message || cmdResult.error }] });
                    return cmdResult;
                }

                this.history.push({ role: 'user', parts: [{ text: message }] });

                // Check for local queries
                const lower = message.toLowerCase();
                if (lower.includes('span') || lower.includes('grid')) {
                    const s = this.getState();
                    return {
                        success: true, message:
                            `📏 **Current Grid:**\n- X Spans: ${s.grid.xSpans.join(', ')} m\n- Y Spans: ${s.grid.ySpans.join(', ')} m\n- Total X: ${s.grid.xSpans.reduce((a, b) => a + b, 0).toFixed(1)} m\n- Total Y: ${s.grid.ySpans.reduce((a, b) => a + b, 0).toFixed(1)} m`
                    };
                }
                if (lower.includes('column') && lower.includes('load')) {
                    const cols = this.getColumnLoads().slice(0, 8);
                    return {
                        success: true, message:
                            `🏗️ **Column Loads (first 8):**\n${cols.map(c => `- ${c.id}: ${c.load} → ${c.size}`).join('\n')}`
                    };
                }
                if (lower.includes('floor') || lower.includes('storey')) {
                    const s = this.getState();
                    return {
                        success: true, message:
                            `🏢 **Floors:** ${s.floors.length}\n${s.floors.map(f => `- ${f.id}: H=${f.height}m, Load=${f.load} kN/m²`).join('\n')}`
                    };
                }

                try {
                    const response = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${this.apiKey}`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            system_instruction: { parts: [{ text: this.SYSTEM_PROMPT + '\n\nCurrent State: ' + JSON.stringify(this.getState()) }] },
                            contents: this.history
                        })
                    });

                    if (!response.ok) {
                        const err = await response.json();
                        throw new Error(err.error?.message || 'API error');
                    }

                    const data = await response.json();
                    const text = data.candidates?.[0]?.content?.parts?.[0]?.text || 'No response';

                    this.history.push({ role: 'model', parts: [{ text }] });
                    return { success: true, message: text };

                } catch (e) {
                    this.history.pop();
                    return { success: false, error: e.message };
                }
            }
        };

        // ========== UI LOGIC ==========
        document.addEventListener('DOMContentLoaded', () => {
            const fab = document.getElementById('ethosFab');
            const panel = document.getElementById('ethosPanel');
            const closeBtn = document.getElementById('ethosClose');
            const clearBtn = document.getElementById('ethosClear');
            const settingsBtn = document.getElementById('ethosSettings');
            const sendBtn = document.getElementById('ethosSend');
            const input = document.getElementById('ethosInput');
            const messages = document.getElementById('ethosMessages');
            const apiSetup = document.getElementById('ethosApiSetup');
            const inputArea = document.getElementById('ethosInputArea');
            const apiSaveBtn = document.getElementById('ethosApiKeySave');

            // Open/Close panel
            fab.onclick = () => { panel.classList.add('open'); fab.classList.add('hidden'); input.focus(); };
            closeBtn.onclick = () => { panel.classList.remove('open'); fab.classList.remove('hidden'); };

            // Clear chat
            clearBtn.onclick = () => {
                ETHOS.history = [];
                messages.innerHTML = '<div class="ethos-welcome"><p>👋 Chat cleared! How can I help?</p></div>';
            };

            // Settings
            settingsBtn.onclick = () => {
                apiSetup.style.display = 'block';
                inputArea.style.display = 'none';
            };

            // Save API key
            apiSaveBtn.onclick = () => {
                const key = document.getElementById('ethosApiKeyInput').value.trim();
                if (key) {
                    ETHOS.apiKey = key;
                    localStorage.setItem('residentEthosApiKey', key);
                    apiSetup.style.display = 'none';
                    inputArea.style.display = 'flex';
                    addMsg('assistant', '✅ API key saved! Ready to help.');
                }
            };

            // Check API key on load
            if (!ETHOS.apiKey) {
                apiSetup.style.display = 'block';
                inputArea.style.display = 'none';
            }

            // Send message
            const sendMessage = async () => {
                if (ETHOS.isLoading) return;
                const text = input.value.trim();
                if (!text) return;
                if (!ETHOS.apiKey) { settingsBtn.click(); return; }

                input.value = '';
                addMsg('user', text);

                ETHOS.isLoading = true;
                sendBtn.disabled = true;
                const loading = addMsg('loading', 'Thinking');

                const result = await ETHOS.chat(text);
                loading.remove();

                if (result.success) addMsg('assistant', result.message);
                else addMsg('error', '❌ ' + result.error);

                ETHOS.isLoading = false;
                sendBtn.disabled = false;
                input.focus();
            };

            sendBtn.onclick = sendMessage;
            input.onkeydown = (e) => { if (e.key === 'Enter') sendMessage(); };

            function addMsg(type, text) {
                const div = document.createElement('div');
                div.className = 'ethos-message ' + type;
                div.textContent = text;
                messages.appendChild(div);
                messages.scrollTop = messages.scrollHeight;
                return div;
            }

            console.log('🤖 Resident Ethos initialized');

            // v3.3: Hamburger Dropdown Logic
            window.toggleDropdown = function () {
                const dd = document.getElementById('settingsDropdown');
                if (dd) dd.classList.toggle('hidden');
            };

            // Close dropdown when clicking outside
            document.addEventListener('click', function (event) {
                const dd = document.getElementById('settingsDropdown');
                const btn = document.querySelector('.settings-gear');
                if (dd && !dd.classList.contains('hidden') && !dd.contains(event.target) && !btn.contains(event.target)) {
                    dd.classList.add('hidden');
                }
            });
        });