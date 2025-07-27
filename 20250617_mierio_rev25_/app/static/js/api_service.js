const _handleErrorResponse = async (response) => {
    try {
        const errorData = await response.json();
        return new Error(errorData.error || `サーバーエラーが発生しました (ステータス: ${response.status})`);
    } catch (e) {
        const errorText = await response.text();
        console.error("Received non-JSON error response:", errorText);
        return new Error(`サーバーとの通信に失敗しました。レスポンスが不正です (ステータス: ${response.status})`);
    }
};

const APIService = {
    uploadAssetFolder: async (formData) => {
        try {
            const response = await fetch('/upload_asset_folder', {
                method: 'POST',
                body: formData,
            });

            const responseBody = await response.text();
            if (!response.ok) {
                try {
                    const errorJson = JSON.parse(responseBody);
                    throw new Error(errorJson.error || `サーバーがステータス ${response.status} を返しました`);
                } catch (e) {
                    console.error("サーバーからの予期せぬレスポンス:", responseBody);
                    throw new Error(`サーバーエラー (ステータス ${response.status})。詳細はサーバー側のログを確認してください。`);
                }
            }
            return JSON.parse(responseBody);
        } catch (error) {
            console.error('Assetフォルダのアップロードに失敗:', error);
            return { error: error.message };
        }
    },

    uploadCSV: async (file, fileType) => {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('file_type', fileType);

        const response = await fetch('/upload_csv', {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) throw await _handleErrorResponse(response);
        return response.json();
    },

    getPlotData: async (payload) => {
        const response = await fetch('/get_plot_data', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });

        if (!response.ok) throw await _handleErrorResponse(response);
        return response.json();
    },

    // ▼▼▼ここから修正▼▼▼
    finetuneGrid: async (payload) => {
        const response = await fetch('/finetune_grid', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });

        if (!response.ok) throw await _handleErrorResponse(response);
        return response.json();
    },
    // ▲▲▲ここまで修正▲▲▲

    getCalculatedContour: async (payload) => {
        const response = await fetch('/get_calculated_contour', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });

        if (!response.ok) throw await _handleErrorResponse(response);
        return response.json();
    },

    getOverlapData: async () => {
        const response = await fetch('/get_overlap_data', {
            method: 'GET',
            headers: { 'Content-Type': 'application/json' },
        });

        if (!response.ok) throw await _handleErrorResponse(response);
        return response.json();
    },

    getModelTableHeaders: async () => {
        const response = await fetch('/get_model_table_headers');
        if (!response.ok) throw await _handleErrorResponse(response);
        return response.json();
    },

    saveModelConfig: async (payload) => {
        const response = await fetch('/model/save_model_config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });

        if (!response.ok) throw await _handleErrorResponse(response);
        return response.json();
    },

    loadModelConfig: async (filename) => {
        const response = await fetch('/model/load_model_config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filename: filename }),
        });

        if (!response.ok) throw await _handleErrorResponse(response);
        return response.json();
    },

    runCalculationDemo: async () => {
        const response = await fetch('/model/run_calculation_demo', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
        });

        if (!response.ok) throw await _handleErrorResponse(response);
        return response.json();
    }
};