import React, { useState, useEffect } from 'react';
import { generateTextReport, generatePdfReport } from '../api/client';

export default function ReportViewer({ blockId }) {
  const [reportText, setReportText] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    // Automatically pre-fill and maybe even trigger generate if we wanted, 
    // but requirement says "Generate Report button calls /report/text"
    if (blockId) {
      setReportText('');
      setError(null);
    }
  }, [blockId]);

  const handleGenerateReport = async () => {
    if (!blockId) return;
    setLoading(true);
    setError(null);
    try {
      const response = await generateTextReport(blockId);
      // Handle various response struct shapes from different dynamic backends
      const text = response.data.report || response.data.text || response.data;
      setReportText(typeof text === 'object' ? JSON.stringify(text, null, 2) : text);
    } catch (err) {
      setError(err.response?.data?.error || err.message || 'Error generating report');
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadPdf = async () => {
    if (!blockId) return;
    try {
      const response = await generatePdfReport(blockId);
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `block_${blockId}_report.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err) {
      console.error('Failed to download PDF', err);
      setError('Failed to download PDF');
    }
  };

  return (
    <div style={{ padding: '30px', maxWidth: '800px', margin: '0 auto', fontFamily: 'sans-serif' }}>
      <h2 style={{ color: '#2c3e50', borderBottom: '2px solid #ecf0f1', paddingBottom: '10px' }}>
        Block Report Generator
      </h2>
      
      <div style={{ marginBottom: '20px', padding: '15px', background: '#f8f9fa', borderRadius: '6px' }}>
        <label style={{ marginRight: '10px', fontWeight: 'bold' }}>Target Block ID:</label>
        <input 
          type="text" 
          value={blockId || ''} 
          readOnly 
          placeholder="Select a block from the Analysis Panel" 
          style={{ padding: '8px', width: '250px', border: '1px solid #bdc3c7', borderRadius: '4px' }}
        />
        <div style={{ marginTop: '15px', display: 'flex', gap: '10px' }}>
          <button 
            onClick={handleGenerateReport} 
            disabled={!blockId || loading}
            style={btnStyle(loading || !blockId ? '#95a5a6' : '#3498db')}
          >
            {loading ? 'Generating...' : 'Generate Text Report'}
          </button>
          <button 
            onClick={handleDownloadPdf} 
            disabled={!blockId}
            style={btnStyle(!blockId ? '#95a5a6' : '#e74c3c')}
          >
            Download PDF Report
          </button>
        </div>
        {error && <div style={{ color: '#c0392b', marginTop: '10px', fontWeight: 'bold' }}>{error}</div>}
      </div>

      {reportText && (
        <div style={{ 
          border: '1px solid #bdc3c7', 
          padding: '25px', 
          backgroundColor: '#fff',
          borderRadius: '8px',
          boxShadow: '0 2px 10px rgba(0,0,0,0.05)',
          whiteSpace: 'pre-wrap',
          lineHeight: '1.6',
          color: '#34495e'
        }}>
          {reportText}
        </div>
      )}
    </div>
  );
}

const btnStyle = (bg) => ({
  backgroundColor: bg,
  color: 'white',
  padding: '10px 20px',
  border: 'none',
  borderRadius: '4px',
  cursor: bg === '#95a5a6' ? 'not-allowed' : 'pointer',
  fontWeight: 'bold',
  transition: 'background 0.2s'
});
