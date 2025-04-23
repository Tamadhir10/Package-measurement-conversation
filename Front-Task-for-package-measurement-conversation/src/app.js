const input = document.getElementById('inputString');
const convertBtn = document.getElementById('convertBtn');
const historyBtn = document.getElementById('historyBtn');
const clearBtn = document.getElementById('clearBtn');
const resultDiv = document.getElementById('result');
const errorDiv = document.getElementById('error');

function showResult(content) {
    resultDiv.textContent = content;
    errorDiv.textContent = '';
}
function showError(msg) {
    errorDiv.textContent = msg;
    resultDiv.textContent = '';
}
function clearAll() {
    resultDiv.textContent = '';
    errorDiv.textContent = '';
    input.value = '';
}

convertBtn.onclick = async () => {
    const value = input.value.trim();
    if (!value) {
        showError('Please enter a measurement string.');
        return;
    }
    showResult('Converting...');
    try {
        const resp = await fetch(`http://localhost:8000/convert-measurements/?input=${encodeURIComponent(value)}`);
        if (!resp.ok) {
            const data = await resp.json();
            throw new Error(data.detail || 'Conversion failed.');
        }
        const data = await resp.json();
        showResult('Result: ' + JSON.stringify(data));
    } catch (err) {
        showError('Error: ' + (err.message || 'Server unavailable.'));
    }
};

historyBtn.onclick = async () => {
    showResult('Loading history...');
    try {
        const resp = await fetch('http://localhost:8000/measurement-history/');
        if (!resp.ok) throw new Error('Could not fetch history.');
        const data = await resp.json();
        if (!data.length) {
            showResult('No history found.');
        } else {
            let html = 'History:<br><ul style="padding-left:1.2em;">';
            data.forEach(item => {
                html += `<li><b>Input:</b> ${item.input} <b>Output:</b> ${JSON.stringify(item.output)}</li>`;
            });
            html += '</ul>';
            resultDiv.innerHTML = html;
            errorDiv.textContent = '';
        }
    } catch (err) {
        showError('Error: ' + (err.message || 'Server unavailable.'));
    }
};

clearBtn.onclick = clearAll;