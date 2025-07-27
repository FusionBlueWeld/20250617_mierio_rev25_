const UIHandlers = {
    initTabSwitching: () => {
        window.openTab = (evt, tabName) => {
            const tabContents = document.getElementsByClassName('tab-content');
            for (let i = 0; i < tabContents.length; i++) {
                tabContents[i].style.display = 'none';
            }
            const tabButtons = document.getElementsByClassName('tab-button');
            for (let i = 0; i < tabButtons.length; i++) {
                tabButtons[i].classList.remove('active');
            }
            document.getElementById(tabName).style.display = 'block';
            evt.currentTarget.classList.add('active');
            if (tabName === 'view-tab') {
                if (window.updatePlot) window.updatePlot();
            } else if (tabName === 'model-tab') {
                if (window.populateFunctionTable) window.populateFunctionTable();
                if (window.populateFittingTable) window.populateFittingTable();
            }
        };
        document.querySelector('.tab-button.active').click();
    },

    setupAssetFolderInput: (inputId, displayNameId, onUploadSuccess, onClear) => {
        const folderInput = document.getElementById(inputId);
        const displayName = document.getElementById(displayNameId);

        folderInput.addEventListener('change', async (event) => {
            const files = event.target.files;
            if (files.length > 0) {
                const folderName = files[0].webkitRelativePath.split('/')[0];
                displayName.value = folderName;

                let featureFile = null;
                let targetFile = null;
                for (const file of files) {
                    if (file.name.toLowerCase() === 'feature.csv') featureFile = file;
                    if (file.name.toLowerCase() === 'target.csv') targetFile = file;
                }

                if (featureFile && targetFile) {
                    const formData = new FormData();
                    formData.append('files[]', featureFile, featureFile.name);
                    formData.append('files[]', targetFile, targetFile.name);
                    const result = await APIService.uploadAssetFolder(formData);
                    
                    if (result.error) {
                        alert(`フォルダのアップロードに失敗しました: ${result.error}`);
                        displayName.value = '';
                        onClear();
                    } else {
                        onUploadSuccess(result.headers.feature, result.headers.target);
                    }
                } else {
                    alert('選択したフォルダに Feature.csv と Target.csv が見つかりません。');
                    displayName.value = '';
                    onClear();
                }
            } else {
                displayName.value = '';
                onClear();
            }
            UIHandlers.updateModelFileButtonState();
        });
    },

    setupFileInput: (fileInputId, fileNameDisplayId, fileType, onFileUploadSuccess, onFileClear) => {
        const fileInput = document.getElementById(fileInputId);
        const fileNameDisplay = document.getElementById(fileNameDisplayId);
        fileInput.addEventListener('change', async (event) => {
            if (event.target.files.length > 0) {
                const file = event.target.files[0];
                fileNameDisplay.value = file.name;
                const result = await APIService.uploadCSV(file, fileType);
                if (result.error) {
                    alert(`ファイルのアップロードに失敗しました: ${result.error}`);
                    fileNameDisplay.value = '';
                    if(onFileClear) onFileClear(fileType);
                } else {
                    if(onFileUploadSuccess) onFileUploadSuccess(fileType, result.headers || result);
                }
            } else {
                fileNameDisplay.value = '';
                if(onFileClear) onFileClear(fileType);
            }
            UIHandlers.updateModelFileButtonState();
        });
    },

    initLedButtons: () => {
        const ledButtons = document.querySelectorAll('.led-button');
        ledButtons.forEach(button => {
            button.addEventListener('click', () => {
                const ledIndicator = button.querySelector('.led-indicator');
                ledIndicator.classList.toggle('active');
            });
        });
    },

    updateProgressBar: (progress, text) => {
        const progressBarContainer = document.getElementById('learning-progress-bar-container');
        const progressBar = document.getElementById('learning-progress-bar');
        const progressText = document.getElementById('learning-progress-text');

        progressBarContainer.style.display = 'block';
        progressBar.style.width = `${progress}%`;
        progressText.textContent = text;

        if (progress >= 100) {
            setTimeout(() => {
                progressBarContainer.style.display = 'none';
                progressText.textContent = '';
            }, 2000);
        }
    },
    
    // ▼▼▼ここから修正▼▼▼
    updateViewActionButtons: () => {
        const finetuneButton = document.getElementById('finetune-button');
        const thresholdButton = document.getElementById('threshold-button');
        const thresholdValueInput = document.getElementById('threshold-value');
        const overlapToggle = document.getElementById('overlap-toggle');
        
        const isModelLoaded = ModelTab.getModelConfigLoaded();
        const areParamsSelected = ViewTab.areAxisParamsSelected();

        // オーバーラップスイッチの有効化/無効化
        const canEnableOverlap = isModelLoaded && areParamsSelected;
        overlapToggle.disabled = !canEnableOverlap;
        if (!canEnableOverlap && overlapToggle.checked) {
            overlapToggle.checked = false;
            // スイッチが強制的にOFFになった場合、関連する描画も消す
            ViewTab.removeOverlapContour();
        }

        const isOverlapOn = overlapToggle.checked;

        // FINETUNEボタンの有効化/無効化 (オーバーラップ表示中のみ)
        finetuneButton.disabled = !isOverlapOn;

        // Threshold関連ボタンの有効化/無効化 (オーバーラップ表示中のみ)
        thresholdButton.disabled = !isOverlapOn;
        thresholdValueInput.disabled = !isOverlapOn;
        if (!isOverlapOn) {
            thresholdButton.classList.remove('active');
        }
    },
    // ▲▲▲ここまで修正▲▲▲

    updateModelFileButtonState: () => {
        const assetFolderName = document.getElementById('asset-folder-name').value;
        const modelFileButton = document.getElementById('model-file-button');
        if (assetFolderName) {
            modelFileButton.disabled = false;
            modelFileButton.style.backgroundColor = '#28a745';
            modelFileButton.style.cursor = 'pointer';
        } else {
            modelFileButton.disabled = true;
            modelFileButton.style.backgroundColor = '#6c757d';
            modelFileButton.style.cursor = 'not-allowed';
        }
    }
};