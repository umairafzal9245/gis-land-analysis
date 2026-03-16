import React, { useState } from 'react';
import MapView from './components/MapView';
import AnalysisPanel from './components/AnalysisPanel';
import ReportViewer from './components/ReportViewer';
import { analyzeBBox, analyzePolygon, generateReport } from './api/client';
import './App.css';

export default function App() {
  const [activeTab, setActiveTab] = useState('map');
  const [analysisData, setAnalysisData] = useState(null);
  const [selectedBlockId, setSelectedBlockId] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);

  const handleAreaSelect = async (payload) => {
    try {
      const data = await analyzeBBox(payload);
      setAnalysisData(data);
      setActiveTab('analysis');
    } catch (e) {
      console.error(e);
    }
  };

  const handlePolygonSelect = async (payload) => {
    try {
      const data = await analyzePolygon(payload);
      setAnalysisData(data);
      setActiveTab('analysis');
    } catch (e) {
      console.error(e);
    }
  };

  const handleGenerateReport = async (stats) => {
    setIsGenerating(true);
    try {
      const result = await generateReport(stats);
      if (result && result.report_text) {
         setSelectedBlockId(result.report_text);
         setActiveTab('report');
      }
    } catch (e) {
      console.error(e);
    } finally {
      setIsGenerating(false);
    }
  }

  const handleBlockReportClick = (blockId) => {
    setSelectedBlockId(blockId);
    setActiveTab('report');
  };

  return (
    <div className="app-container" style={{ display: 'flex', flexDirection: 'column', height: '100vh', fontFamily: 'sans-serif' }}>
      <header style={{ display: 'flex', gap: '20px', padding: '15px 20px', backgroundColor: '#2c3e50', color: 'white' }}>
        <h1 style={{ margin: 0, fontSize: '1.2rem', marginRight: '40px' }}>Land Analysis Platform</h1>
        <button style={tabStyle(activeTab === 'map')} onClick={() => setActiveTab('map')}>Map</button>
        <button style={tabStyle(activeTab === 'analysis')} onClick={() => setActiveTab('analysis')}>Analysis</button>
        <button style={tabStyle(activeTab === 'report')} onClick={() => setActiveTab('report')}>Report</button>
      </header>

      <main style={{ flex: 1, overflow: 'hidden', display: 'flex' }}>
        <div style={{ display: activeTab === 'map' ? 'flex' : 'none', flex: 1, height: '100%' }}>
          <MapView 
            onAreaSelect={handleAreaSelect} 
            onPolygonSelect={handlePolygonSelect} 
          />
        </div>
        <div style={{ display: activeTab === 'analysis' ? 'block' : 'none', flex: 1, height: '100%', overflow: 'auto' }}>
          <AnalysisPanel 
            results={analysisData} 
            onGenerateReport={handleGenerateReport}
            isGenerating={isGenerating}
          />
        </div>
        <div style={{ display: activeTab === 'report' ? 'block' : 'none', flex: 1, height: '100%', overflow: 'auto' }}>
          {selectedBlockId && selectedBlockId.length > 50 ? (
            <div style={{ padding: '30px', whiteSpace: 'pre-wrap' }}>{selectedBlockId}</div>
          ) : (
            <ReportViewer blockId={selectedBlockId} />
          )}
        </div>
      </main>
    </div>
  );
}

const tabStyle = (isActive) => ({
  background: isActive ? '#34495e' : 'transparent',
  border: 'none',
  color: isActive ? '#fff' : '#bdc3c7',
  padding: '8px 16px',
  cursor: 'pointer',
  borderRadius: '4px',
  fontWeight: isActive ? 'bold' : 'normal',
});
