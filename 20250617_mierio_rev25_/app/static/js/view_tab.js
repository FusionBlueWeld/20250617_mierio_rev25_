let featureHeaders = [];
let targetHeaders = [];
let currentFeatureSelections = {};
let currentTargetSelection = '';
let plotlyGraphContainer;

const CONTOUR_TRACE_UID = 'overlap-contour-trace';

const ViewTab = {
    init: () => {
        plotlyGraphContainer = document.getElementById('graph-container');

        if (!plotlyGraphContainer.dataset.plotlyInitialized || plotlyGraphContainer.dataset.plotlyInitialized === 'false') {
            Plotly.newPlot(plotlyGraphContainer, [], {
                margin: { t: 50, b: 50, l: 50, r: 50 },
                xaxis: { title: 'X-axis' },
                yaxis: { title: 'Y-axis' },
                hovermode: 'closest',
                title: 'グラフ表示エリア'
            });
            plotlyGraphContainer.dataset.plotlyInitialized = 'true';
        }

        document.getElementById('overlap-toggle').addEventListener('change', (event) => {
            if (event.target.checked) {
                ViewTab.drawOverlapContour();
            } else {
                ViewTab.removeOverlapContour();
            }
            UIHandlers.updateViewActionButtons();
        });

        document.getElementById('threshold-button').addEventListener('click', () => {
            document.getElementById('threshold-button').classList.toggle('active');
        });

        // ▼▼▼ここから修正▼▼▼
        document.getElementById('finetune-button').addEventListener('click', async () => {
            const button = document.getElementById('finetune-button');
            
            // ベースとなるモデルファイル名を取得
            const baseModelFilename = window.currentLoadedModelFile;
            if (!baseModelFilename) {
                alert('ベースとなるモデルがロードされていません。');
                return;
            }

            button.disabled = true;
            UIHandlers.updateProgressBar(0, 'Finetuning...');

            try {
                const payload = {
                    baseModelFilename: baseModelFilename
                };

                const result = await APIService.finetuneGrid(payload);

                if (result.error) {
                    throw new Error(result.error);
                }

                alert(`${result.message}\n新しいモデル名: ${result.new_model_name}`);
                UIHandlers.updateProgressBar(100, 'Finetuning complete!');

            } catch (error) {
                alert(`ファインチューニングに失敗しました: ${error.message}`);
                UIHandlers.updateProgressBar(100, 'Finetuning failed.');
            } finally {
                // ボタンの状態は updateViewActionButtons に任せる
                UIHandlers.updateViewActionButtons();
            }
        });
        // ▲▲▲ここまで修正▲▲▲
    },

    drawOverlapContour: async () => {
        ViewTab.removeOverlapContour();

        try {
            const result = await APIService.getOverlapData();
            if (result.error) { throw new Error(result.error); }
            if (!result.data) { return; }

            const gridData = result.data;
            
            const contourTrace = {
                x: gridData.X,
                y: gridData.Y,
                z: gridData.Z,
                type: 'contour',
                colorscale: 'jet',
                showscale: false,
                connectgaps: true,
                contours_coloring: 'fill',
                line_smoothing: 0.85,
                opacity: 0.5,
                name: 'Overlap Contour',
                uid: CONTOUR_TRACE_UID
            };

            Plotly.addTraces(plotlyGraphContainer, contourTrace);

        } catch (error) {
            alert(`オーバーラップ表示に失敗しました: ${error.message}`);
            document.getElementById('overlap-toggle').checked = false;
            UIHandlers.updateViewActionButtons();
        }
    },

    removeOverlapContour: () => {
        const traces = plotlyGraphContainer.data;
        let contourIndex = -1;
        for (let i = 0; i < traces.length; i++) {
            if (traces[i].uid === CONTOUR_TRACE_UID) {
                contourIndex = i;
                break;
            }
        }
        if (contourIndex > -1) {
            Plotly.deleteTraces(plotlyGraphContainer, contourIndex);
        }
    },

    populateFeatureParameters: (headers) => {
        featureHeaders = headers;
        const container = document.getElementById('feature-params-container');
        container.innerHTML = '';

        featureHeaders.forEach((header, index) => {
            if (header.toLowerCase() !== 'main_id') {
                const row = document.createElement('div');
                row.classList.add('param-row');
                row.dataset.paramName = header;

                const dropdown = document.createElement('select');
                dropdown.classList.add('param-dropdown', 'feature-param-dropdown');
                dropdown.innerHTML = `
                    <option value="Constant">Constant</option>
                    <option value="X_axis">X_axis</option>
                    <option value="Y_axis">Y_axis</option>
                `;

                const constantInput = document.createElement('input');
                constantInput.type = 'number';
                constantInput.step = 'any';
                constantInput.classList.add('constant-value-input');
                constantInput.placeholder = 'Value (if Constant)';
                constantInput.style.display = 'block';

                if (currentFeatureSelections[header]) {
                    dropdown.value = currentFeatureSelections[header].type;
                    if (currentFeatureSelections[header].type === 'Constant') {
                        if (currentFeatureSelections[header].value !== undefined) {
                            constantInput.value = currentFeatureSelections[header].value;
                        }
                        constantInput.disabled = false;
                    } else {
                        constantInput.disabled = true;
                    }
                } else {
                    currentFeatureSelections[header] = { type: 'Constant', value: '0' };
                    constantInput.value = '0';
                }

                const updateAll = () => {
                    ViewTab.updatePlot();
                    UIHandlers.updateViewActionButtons();
                };

                dropdown.addEventListener('change', (event) => {
                    const selectedType = event.target.value;
                    constantInput.disabled = (selectedType !== 'Constant');
                    ViewTab.handleAxisSelection(header, selectedType);
                    currentFeatureSelections[header].type = selectedType;
                    currentFeatureSelections[header].value = (selectedType === 'Constant') ? constantInput.value : '';
                    updateAll();
                });

                constantInput.addEventListener('input', (event) => {
                    currentFeatureSelections[header].value = event.target.value;
                    updateAll();
                });

                row.appendChild(document.createTextNode(`${index + 1} "${header}" `));
                row.appendChild(dropdown);
                row.appendChild(constantInput);
                container.appendChild(row);
            }
        });
        ViewTab.updatePlot();
        UIHandlers.updateViewActionButtons();
    },

    handleAxisSelection: (changedParamName, selectedType) => {
        if (selectedType === 'X_axis' || selectedType === 'Y_axis') {
            document.querySelectorAll('.feature-param-dropdown').forEach(dropdown => {
                const paramName = dropdown.closest('.param-row').dataset.paramName;
                if (paramName !== changedParamName && dropdown.value === selectedType) {
                    dropdown.value = 'Constant';
                    const constantInput = dropdown.closest('.param-row').querySelector('.constant-value-input');
                    if (constantInput) {
                        constantInput.disabled = false;
                    }
                    currentFeatureSelections[paramName].type = 'Constant';
                    currentFeatureSelections[paramName].value = constantInput ? constantInput.value : '';
                }
            });
        }
    },

    populateTargetParameters: (headers) => {
        targetHeaders = headers;
        const container = document.getElementById('target-params-container');
        container.innerHTML = '';

        const row = document.createElement('div');
        row.classList.add('param-row');
        const select = document.createElement('select');
        select.id = 'target-param-dropdown';
        select.classList.add('param-dropdown');
        select.innerHTML = '<option value="">-- Targetを選択 --</option>';

        targetHeaders.forEach(header => {
            if (header.toLowerCase() !== 'main_id') {
                const option = document.createElement('option');
                option.value = header;
                option.textContent = header;
                select.appendChild(option);
            }
        });

        if (currentTargetSelection) {
            select.value = currentTargetSelection;
        }

        select.addEventListener('change', (event) => {
            currentTargetSelection = event.target.value;
            ViewTab.updatePlot();
            UIHandlers.updateViewActionButtons();
        });

        row.appendChild(select);
        container.appendChild(row);
        ViewTab.updatePlot();
        UIHandlers.updateViewActionButtons();
    },

    updatePlot: async () => {
        UIHandlers.updateViewActionButtons();

        if (!ViewTab.areAxisParamsSelected()) {
            plotlyGraphContainer.style.display = 'flex';
            Plotly.react(plotlyGraphContainer, [], { title: 'X軸、Y軸、およびターゲットを選択してください。' });
            return;
        }
        
        const payload = {
            featureParams: Object.keys(currentFeatureSelections).map(key => ({
                name: key,
                type: currentFeatureSelections[key].type,
                value: currentFeatureSelections[key].value
            })),
            targetParam: currentTargetSelection
        };

        try {
            const result = await APIService.getPlotData(payload);
            if (result.error) { throw new Error(result.error); }
            
            const graphData = JSON.parse(result.graph_json);
            const graphLayout = JSON.parse(result.layout_json);
            
            Plotly.react(plotlyGraphContainer, graphData, graphLayout);
            
            if (document.getElementById('overlap-toggle').checked) {
                ViewTab.drawOverlapContour();
            }

        } catch (error) {
            Plotly.react(plotlyGraphContainer, [], { title: `グラフ表示エラー: ${error.message}` });
        }
    },

    updatePlotDisplayState: () => {
        if (featureHeaders.length > 0 && targetHeaders.length > 0) {
            plotlyGraphContainer.style.display = 'flex';
        } else {
            Plotly.purge(plotlyGraphContainer);
            plotlyGraphContainer.style.display = 'none';
        }
    },

    areAxisParamsSelected: () => {
        const selectedX = Object.values(currentFeatureSelections).some(s => s.type === 'X_axis');
        const selectedY = Object.values(currentFeatureSelections).some(s => s.type === 'Y_axis');
        const selectedTarget = currentTargetSelection && currentTargetSelection !== '';
        return selectedX && selectedY && selectedTarget;
    },

    setFeatureHeaders: (headers) => { featureHeaders = headers; },
    setTargetHeaders: (headers) => { targetHeaders = headers; },
    setCurrentFeatureSelections: (selections) => { currentFeatureSelections = selections; },
    setCurrentTargetSelection: (selection) => { currentTargetSelection = selection; },
    getFeatureHeaders: () => featureHeaders,
    getTargetHeaders: () => targetHeaders,
};

window.ViewTab = ViewTab;