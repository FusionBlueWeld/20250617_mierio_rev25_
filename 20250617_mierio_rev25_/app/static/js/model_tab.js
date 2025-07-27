let modelFittingSelections = {};
let modelFunctions = [];

const initialDefaultFunctions = [
    { name: "Exp_Decay", equation: "A * exp(-x / tau) + C", parameters: "A=1.0, tau=100.0, C=0.5" },
    { name: "Gaussian", equation: "Amp * exp(-(x - mu)**2 / (2 * sigma**2))", parameters: "Amp=1.0, mu=0.0, sigma=1.0" },
    { name: "Power_Law", equation: "alpha * x**beta", parameters: "alpha=1.0, beta=0.7" },
    { name: "Linear", equation: "m * x + b", parameters: "m=0.1, b=0.0" },
    { name: "Polynomial_2nd", equation: "a * x**2 + b * x + c", parameters: "a=0.01, b=0.1, c=0.0" },
    { name: "Log_Growth", equation: "K / (1 + exp(-r * (x - x0)))", parameters: "K=1.0, r=0.1, x0=0.0" }
];

const ModelTab = {
    init: () => {
        modelFunctions = [...initialDefaultFunctions];
        ModelTab.populateFunctionTable();

        const fittingMethodToggle = document.getElementById('fitting-method-toggle');
        const fittingMethodLabel = document.getElementById('fitting-method-label');
        fittingMethodToggle.addEventListener('change', () => {
            fittingMethodLabel.textContent = fittingMethodToggle.checked ? '線形結合' : '乗積';
        });

        document.getElementById('model-apply-button').addEventListener('click', async () => {
            const modelDisplayName = document.getElementById('model-display-name');
            const modelName = modelDisplayName.value.trim();

            for (const func of modelFunctions) {
                if (!func.name.match(/^[a-zA-Z0-9_]+$/)) {
                    alert(`関数名 "${func.name}" は英数字とアンダースコアのみ使用できます。`);
                    return;
                }
                if (!func.equation.trim()) {
                    alert(`関数 "${func.name}" の式は空にできません。`);
                    return;
                }
                if (func.parameters.trim()) {
                    const params = func.parameters.split(',').map(p => p.trim());
                    for (const param of params) {
                        if (!param.includes('=') || param.split('=').length !== 2) {
                            alert(`関数 "${func.name}" のパラメータ "${param}" の形式が無効です。「name=value」の形式で記述してください。`);
                            return;
                        }
                        const [paramName, paramValue] = param.split('=');
                        if (!paramName.match(/^[a-zA-Z_]+[a-zA-Z0-9_]*$/)) {
                            alert(`関数 "${func.name}" のパラメータ名 "${paramName}" は有効な変数名ではありません（英数字とアンダースコア、数字は先頭以外）。`);
                            return;
                        }
                        if (isNaN(parseFloat(paramValue))) {
                            alert(`関数 "${func.name}" のパラメータ "${paramName}" の値は数値である必要があります。`);
                            return;
                        }
                    }
                }
            }

            const fittingConfigToSend = {};
            const targetHeaders = window.ViewTab.getTargetHeaders();
            const featureHeaders = window.ViewTab.getFeatureHeaders();

            for (const featureHeader of featureHeaders) {
                if (featureHeader.toLowerCase() === 'main_id') continue;
                fittingConfigToSend[featureHeader] = {};
                for (const targetHeader of targetHeaders) {
                    if (targetHeader.toLowerCase() === 'main_id') continue;
                    const dropdown = document.querySelector(`#fitting-table tbody tr[data-feature-header="${featureHeader}"] td:nth-child(${targetHeaders.indexOf(targetHeader) + 2}) .fitting-dropdown`);
                    if (dropdown) {
                        fittingConfigToSend[featureHeader][targetHeader] = dropdown.value;
                    }
                }
            }

            const fittingMethod = fittingMethodToggle.checked ? '線形結合' : '乗積';

            const payload = {
                modelName: modelName,
                fittingConfig: fittingConfigToSend,
                fittingMethod: fittingMethod,
                functions: modelFunctions
            };

            try {
                const result = await APIService.saveModelConfig(payload);

                if (result.error) {
                    alert(`設定の保存に失敗しました: ${result.error}`);
                    ModelTab.setModelConfigLoaded(false);
                } else {
                    alert(`設定が保存されました: ${result.message}`);
                    console.log(result.filepath);
                    ModelTab.setModelConfigLoaded(true);
                    UIHandlers.updateViewActionButtons(document.getElementById('overlap-toggle').checked, ModelTab.getModelConfigLoaded());
                    window.ViewTab.updatePlot();
                }
            } catch (error) {
                console.error('Error saving model config:', error);
                alert(`設定保存中にエラーが発生しました: ${error.message}`);
                ModelTab.setModelConfigLoaded(false);
            }
        });

        document.getElementById('add-function-row').addEventListener('click', () => {
            modelFunctions.push({ name: "", equation: "", parameters: "" });
            ModelTab.populateFunctionTable();
        });

        document.getElementById('delete-function-row').addEventListener('click', () => {
            if (modelFunctions.length > 0) {
                modelFunctions.pop();
                ModelTab.populateFunctionTable();
            }
        });

        const modelFileSelect = document.getElementById('model-file-select');
        if (modelFileSelect) {
            modelFileSelect.addEventListener('change', async (event) => {
                const selectedModelName = event.target.value;
                if (selectedModelName) {
                    await ModelTab.loadModelByName(selectedModelName);
                } else {
                    ModelTab.resetModelSettings();
                }
            });
        }

        const deleteModelButton = document.getElementById('delete-model-button');
        if (deleteModelButton) {
            deleteModelButton.addEventListener('click', async () => {
                const modelName = document.getElementById('model-file-select').value;
                if (modelName && confirm(`モデル "${modelName}" を本当に削除しますか？`)) {
                    await ModelTab.deleteModelByName(modelName);
                }
            });
        }
    },

    loadModelByName: async (modelName) => {
        try {
            const result = await APIService.loadModelConfig(modelName);

            if (result.error) {
                alert(`モデルのロードに失敗しました: ${result.error}`);
                ModelTab.setModelConfigLoaded(false);
                ModelTab.resetModelSettings();
            } else {
                alert(`モデル "${modelName}" がロードされました。`);
                document.getElementById('model-display-name').value = result.model_name || modelName;
                document.getElementById('fitting-method-toggle').checked = result.fittingMethod === '線形結合';
                document.getElementById('fitting-method-label').textContent = result.fittingMethod === '線形結合' ? '線形結合' : '乗積';
                modelFunctions = result.functions || [...initialDefaultFunctions];
                modelFittingSelections = result.fittingConfig || {};
                
                window.currentLoadedModelFile = modelName;

                ModelTab.populateFunctionTable();
                ModelTab.populateFittingTable(); 

                ModelTab.setModelConfigLoaded(true);
                UIHandlers.updateViewActionButtons(document.getElementById('overlap-toggle').checked, ModelTab.getModelConfigLoaded());
                window.ViewTab.updatePlot();
            }
        } catch (error) {
            console.error('Error loading model:', error);
            alert(`モデルロード中にエラーが発生しました: ${error.message}`);
            ModelTab.setModelConfigLoaded(false);
            ModelTab.resetModelSettings();
        }
    },

    deleteModelByName: async (modelName) => {
        try {
            const result = await APIService.deleteModelConfig(modelName);

            if (result.error) {
                alert(`モデルの削除に失敗しました: ${result.error}`);
            } else {
                alert(`モデル "${modelName}" が削除されました。`);
                document.getElementById('model-file-select').value = '';
                ModelTab.resetModelSettings();
                document.getElementById('overlap-toggle').checked = false; 
                UIHandlers.updateViewActionButtons(false, false);
            }
        } catch (error) {
            console.error('Error deleting model:', error);
            alert(`モデル削除中にエラーが発生しました: ${error.message}`);
        }
    },

    populateFittingTable: async () => {
        const fittingTableBody = document.querySelector('#fitting-table tbody');
        const modelApplyButton = document.getElementById('model-apply-button');

        const featureHeaders = window.ViewTab.getFeatureHeaders();
        const targetHeaders = window.ViewTab.getTargetHeaders();

        if (featureHeaders.length === 0 || targetHeaders.length === 0) {
            fittingTableBody.innerHTML = '<tr><td colspan="100%">CSVファイルがロードされていません。FeatureとTargetファイルをアップロードしてください。</td></tr>';
            modelApplyButton.disabled = true;
            ModelTab.setModelConfigLoaded(false); 
            return;
        }
        
        modelApplyButton.disabled = false;

        const fittingTableHeaderRow = document.querySelector('#fitting-table thead tr');
        fittingTableHeaderRow.innerHTML = '<th>Feature / Target</th>';
        targetHeaders.forEach(tHeader => {
            if (tHeader.toLowerCase() !== 'main_id') {
                fittingTableHeaderRow.innerHTML += `<th>${tHeader}</th>`;
            }
        });

        fittingTableBody.innerHTML = '';

        const availableFunctions = modelFunctions.map(func => func.name).filter(name => name);
        console.log("Available Functions for Fitting Table:", availableFunctions);

        featureHeaders.forEach(fHeader => {
            if (fHeader.toLowerCase() !== 'main_id') {
                const row = document.createElement('tr');
                row.dataset.featureHeader = fHeader;
                row.innerHTML = `<td>${fHeader}</td>`;

                targetHeaders.forEach(tHeader => {
                    if (tHeader.toLowerCase() !== 'main_id') {
                        const cell = document.createElement('td');
                        const select = document.createElement('select');
                        select.classList.add('fitting-dropdown');
                        select.innerHTML = '<option value="">--関数を選択--</option>';

                        availableFunctions.forEach(funcName => {
                            const option = document.createElement('option');
                            option.value = funcName;
                            option.textContent = funcName;
                            select.appendChild(option);
                        });

                        if (modelFittingSelections[fHeader] && modelFittingSelections[fHeader][tHeader]) {
                            const optionExists = Array.from(select.options).some(option => option.value === modelFittingSelections[fHeader][tHeader]);
                            if (optionExists) {
                                select.value = modelFittingSelections[fHeader][tHeader];
                            } else {
                                select.value = '';
                            }
                        }

                        select.addEventListener('change', (event) => {
                            if (!modelFittingSelections[fHeader]) {
                                modelFittingSelections[fHeader] = {};
                            }
                            modelFittingSelections[fHeader][tHeader] = event.target.value;
                            console.log('Model Fitting Selection Updated:', modelFittingSelections);
                        });

                        cell.appendChild(select);
                        row.appendChild(cell);
                    }
                });
                fittingTableBody.appendChild(row);
            }
        });
    },

    populateFunctionTable: () => {
        const functionTableBody = document.getElementById('function-table-body');
        functionTableBody.innerHTML = '';

        modelFunctions.forEach((func, index) => {
            const newRow = document.createElement('tr');
            newRow.classList.add('function-row');
            newRow.dataset.functionIndex = index;
            newRow.innerHTML = `
                <td></td>
                <td><input type="text" class="function-name" placeholder="関数名 (英数字と_)" value="${func.name || ''}"></td>
                <td><input type="text" class="function-equation" placeholder="例: A * exp(-x/tau) + C" value="${func.equation || ''}"></td>
                <td><input type="text" class="function-parameters" placeholder="例: A=1.0, tau=100.0, C=0.5" value="${func.parameters || ''}"></td>
            `;
            functionTableBody.appendChild(newRow);
        });
        ModelTab.updateRowNumbers();

        document.querySelectorAll('#function-table-body .function-row input').forEach(input => {
            input.addEventListener('input', (event) => {
                const row = event.target.closest('.function-row');
                const index = parseInt(row.dataset.functionIndex);
                const func = modelFunctions[index];

                if (!func) return;

                if (event.target.classList.contains('function-name')) {
                    func.name = event.target.value.trim();
                    ModelTab.populateFittingTable();
                } else if (event.target.classList.contains('function-equation')) {
                    func.equation = event.target.value.trim();
                } else if (event.target.classList.contains('function-parameters')) {
                    func.parameters = event.target.value.trim();
                }
                console.log("modelFunctions Updated:", modelFunctions);
            });
        });
        ModelTab.populateFittingTable();
    },

    updateRowNumbers: () => {
        const functionTableBody = document.getElementById('function-table-body');
        const rows = functionTableBody.querySelectorAll('.function-row');
        rows.forEach((row, index) => {
            row.querySelector('td:first-child').textContent = index + 1;
        });
    },

    resetModelSettings: () => {
        modelFittingSelections = {};
        modelFunctions = [...initialDefaultFunctions];
        ModelTab.setModelConfigLoaded(false);
        window.currentLoadedModelFile = null;
        document.getElementById('fitting-method-toggle').checked = true;
        document.getElementById('fitting-method-label').textContent = '線形結合';
        document.getElementById('model-display-name').value = '';
        ModelTab.populateFunctionTable();
        ModelTab.populateFittingTable();
        UIHandlers.updateViewActionButtons(document.getElementById('overlap-toggle').checked, ModelTab.getModelConfigLoaded());
        window.ViewTab.updatePlot();
        document.getElementById('overlap-toggle').checked = false;
    },

    setModelFittingSelections: (selections) => { modelFittingSelections = selections; },
    getModelFittingSelections: () => modelFittingSelections,
    setModelFunctions: (functions) => { modelFunctions = functions; },
    getModelFunctions: () => modelFunctions,
    _modelConfigLoadedInternal: false,
    setModelConfigLoaded: (isLoaded) => {
        ModelTab._modelConfigLoadedInternal = isLoaded;
        window.modelConfigLoaded = isLoaded; 
        console.log("modelConfigLoaded set to:", isLoaded);
    },
    getModelConfigLoaded: () => ModelTab._modelConfigLoadedInternal
};

window.ModelTab = ModelTab;
window.modelFittingSelections = modelFittingSelections;
window.modelFunctions = modelFunctions;
window.modelConfigLoaded = ModelTab.getModelConfigLoaded();

window.populateFunctionTable = ModelTab.populateFunctionTable;
window.populateFittingTable = ModelTab.populateFittingTable;
