const API_BASE = 'http://localhost:8000';
let currentAnalysisResults = null;

// 파일 업로드 함수
async function uploadFile() {
    const fileInput = document.getElementById('csvFile');
    const file = fileInput.files[0];
    
    if (!file) {
        showResult('⚠️ 파일을 선택해주세요.', 'warning');
        return;
    }
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        updateStatus('📤 파일 업로드 중...');
        
        const response = await fetch(`${API_BASE}/api/upload`, {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showResult(`✅ 업로드 성공!\n파일명: ${file.name}\n크기: ${(file.size/1024).toFixed(1)} KB\n\n${JSON.stringify(result, null, 2)}`, 'success');
            updateStatus('✅ 파일 업로드 완료');
        } else {
            showResult(`❌ 업로드 실패: ${result.detail || '알 수 없는 오류'}`, 'error');
            updateStatus('❌ 파일 업로드 실패');
        }
    } catch (error) {
        showResult(`❌ 네트워크 오류: ${error.message}`, 'error');
        updateStatus('❌ 연결 오류');
    }
}

// 데이터 분석 함수
async function analyzeData() {
    const fileInput = document.getElementById('csvFile');
    const file = fileInput.files[0];
    
    if (!file) {
        showResult('⚠️ 분석할 파일을 먼저 선택해주세요.', 'warning');
        return;
    }
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        updateStatus('🔬 데이터 분석 중...');
        
        const response = await fetch(`${API_BASE}/api/analyze`, {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (response.ok) {
            currentAnalysisResults = result.results;
            displayAnalysisResults(result.results);
            updateStatus('✅ 데이터 분석 완료');
        } else {
            showResult(`❌ 분석 실패: ${result.detail || '알 수 없는 오류'}`, 'error');
            updateStatus('❌ 분석 실패');
        }
    } catch (error) {
        showResult(`❌ 분석 오류: ${error.message}`, 'error');
        updateStatus('❌ 분석 오류');
    }
}

// 시각화 생성 함수
async function createVisualization() {
    if (!currentAnalysisResults) {
        showResult('⚠️ 먼저 데이터 분석을 수행해주세요.', 'warning');
        return;
    }
    
    try {
        updateStatus('📊 시각화 생성 중...');
        
        // 시각화 컨테이너 표시
        document.getElementById('visualizationContainer').style.display = 'block';
        
        // 상세한 시각화 HTML 생성
        const results = currentAnalysisResults.results || currentAnalysisResults;
        const stats = results.statistics;
        const validCount = stats.valid_compounds || 0;
        const outlierCount = stats.outliers || 0;
        const totalCount = stats.total_compounds || 0;
        const successRate = stats.success_rate || 0;
        
        // 고도화된 시각화 HTML
        const visualizationHtml = `
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 25px; border-radius: 15px; margin: 15px 0; color: white;">
                <h3 style="margin-top: 0; text-align: center;">🏆 Ganglioside 분석 대시보드</h3>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 15px; margin: 25px 0;">
                    <div style="background: rgba(255,255,255,0.15); padding: 20px; border-radius: 12px; text-align: center;">
                        <h2 style="margin: 0; font-size: 2.5em;">${totalCount}</h2>
                        <p style="margin: 8px 0;">총 화합물</p>
                    </div>
                    <div style="background: rgba(46, 204, 113, 0.2); padding: 20px; border-radius: 12px; text-align: center;">
                        <h2 style="margin: 0; font-size: 2.5em; color: #2ecc71;">${validCount}</h2>
                        <p style="margin: 8px 0;">유효 화합물</p>
                    </div>
                    <div style="background: rgba(231, 76, 60, 0.2); padding: 20px; border-radius: 12px; text-align: center;">
                        <h2 style="margin: 0; font-size: 2.5em; color: #e74c3c;">${outlierCount}</h2>
                        <p style="margin: 8px 0;">이상치</p>
                    </div>
                    <div style="background: rgba(243, 156, 18, 0.2); padding: 20px; border-radius: 12px; text-align: center;">
                        <h2 style="margin: 0; font-size: 2.5em; color: #f39c12;">${successRate.toFixed(1)}%</h2>
                        <p style="margin: 8px 0;">성공률</p>
                    </div>
                </div>
                <div style="text-align: center; margin-top: 20px;">
                    <p style="font-size: 1.2em;">🎯 분석 상태: ${results.status || 'Enhanced Analysis'}</p>
                    <p style="font-size: 1.1em;">📊 목표 달성: ${results.target_achievement || 'N/A'}</p>
                </div>
            </div>
        `;
        
        document.getElementById('visualizations').innerHTML = visualizationHtml;
        
        showResult('📊 시각화가 성공적으로 생성되었습니다!', 'success');
        updateStatus('✅ 시각화 완료');
        
        // 시각화 영역으로 스크롤
        document.getElementById('visualizationContainer').scrollIntoView({ behavior: 'smooth' });
        
    } catch (error) {
        showResult(`❌ 시각화 오류: ${error.message}`, 'error');
        updateStatus('❌ 시각화 실패');
    }
}

// 샘플 데이터 테스트
async function testSampleData() {
    try {
        updateStatus('🧪 샘플 데이터 테스트 중...');
        
        const sampleCSV = `Name,RT,Volume,Log P,Anchor
GD1a(36:1;O2),9.572,1000000,1.53,T
GM1a(36:1;O2),10.452,500000,4.00,F
GM3(36:1;O2),10.606,2000000,7.74,F
GD3(36:1;O2),10.126,800000,5.27,T
GT1b(36:1;O2),8.701,1200000,-0.94,T
GQ1c(36:1;O2),8.101,600000,-3.41,T
GP1(36:1;O2),7.851,300000,-5.88,F`;
        
        const blob = new Blob([sampleCSV], { type: 'text/csv' });
        const formData = new FormData();
        formData.append('file', blob, 'sample_data.csv');
        
        const response = await fetch(`${API_BASE}/api/analyze`, {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (response.ok) {
            currentAnalysisResults = result.results;
            displayAnalysisResults(result.results);
            updateStatus('✅ 샘플 데이터 테스트 완료');
        } else {
            showResult(`❌ 샘플 테스트 실패: ${result.detail || '알 수 없는 오류'}`, 'error');
            updateStatus('❌ 샘플 테스트 실패');
        }
    } catch (error) {
        showResult(`❌ 샘플 테스트 오류: ${error.message}`, 'error');
        updateStatus('❌ 샘플 테스트 오류');
    }
}

// 결과 다운로드
async function downloadResults() {
    if (!currentAnalysisResults) {
        showResult('⚠️ 다운로드할 분석 결과가 없습니다.', 'warning');
        return;
    }
    
    try {
        const csvContent = generateCSVFromResults(currentAnalysisResults);
        const blob = new Blob([csvContent], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `ganglioside_analysis_results_${new Date().toISOString().slice(0,19).replace(/:/g, '-')}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        
        showResult('💾 분석 결과가 성공적으로 다운로드되었습니다!', 'success');
        updateStatus('✅ 다운로드 완료');
    } catch (error) {
        showResult(`❌ 다운로드 오류: ${error.message}`, 'error');
    }
}

// 분석 결과 표시 함수
function displayAnalysisResults(results) {
    const stats = results.statistics;
    const summary = `🔬 분석 완료!

=== 분석 요약 ===
총 화합물 수: ${stats.total_compounds || 'N/A'}
유효 화합물: ${stats.valid_compounds || 'N/A'}
이상치: ${stats.outliers || 'N/A'}
성공률: ${(stats.success_rate || 0).toFixed(1)}%

=== 규칙별 분석 ===
규칙1 (회귀분석): ${stats.rule_breakdown?.rule1_regression || 0}개 유효
규칙4 (O-아세틸화): ${stats.rule_breakdown?.rule4_oacetylation || 0}개 유효
규칙5 (RT 필터링): ${stats.rule_breakdown?.rule5_rt_filtering || 0}개 유효

분석 상태: ${results.status || 'Unknown'}
목표 달성도: ${results.target_achievement || 'N/A'}`;

    showResult(summary, 'success');
}

// CSV 생성 함수
function generateCSVFromResults(results) {
    let csv = 'Name,RT,Volume,Log P,Anchor,Status,Classification\n';
    
    if (results.valid_compounds) {
        results.valid_compounds.forEach(compound => {
            csv += `"${compound.Name}",${compound.RT},${compound.Volume},${compound['Log P']},${compound.Anchor},Valid,True Positive\n`;
        });
    }
    
    if (results.outliers) {
        results.outliers.forEach(outlier => {
            csv += `"${outlier.Name}",${outlier.RT},${outlier.Volume},${outlier['Log P']},${outlier.Anchor},Outlier,"${outlier.outlier_reason || 'Unknown'}"\n`;
        });
    }
    
    return csv;
}

// UI 헬퍼 함수들
function showResult(message, type) {
    const resultDiv = document.getElementById('result');
    resultDiv.className = `result ${type}`;
    resultDiv.textContent = message;
}

function updateStatus(message) {
    document.getElementById('statusBar').textContent = message;
}

// API 연결 확인
async function checkAPIStatus() {
    try {
        updateStatus('🔄 API 연결 확인 중...');
        const response = await fetch(`${API_BASE}/`);
        const result = await response.json();
        updateStatus(`✅ ${result.message || 'API 연결 성공'}`);
        showResult(`✅ 시스템 준비 완료!\n\nAPI 상태: 정상\n서버: ${API_BASE}\n연결 시간: ${new Date().toLocaleString()}\n\n이제 CSV 파일을 업로드하여 분석을 시작할 수 있습니다.`, 'success');
    } catch (error) {
        updateStatus('❌ API 연결 실패');
        showResult(`❌ API 연결 실패\n\n오류: ${error.message}\n서버: ${API_BASE}\n\n서버가 실행 중인지 확인해주세요.`, 'error');
    }
}

// 페이지 로드 시 초기화
window.onload = function() {
    updateStatus('🚀 시스템 초기화 중...');
    setTimeout(checkAPIStatus, 1000);
};
