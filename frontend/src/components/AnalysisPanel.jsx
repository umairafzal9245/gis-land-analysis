import React, { useState } from 'react';
import { Card, CardContent } from './ui/card';

const AnalysisPanel = ({ results, onGenerateReport, isGenerating }) => {
  const [shopSize, setShopSize] = useState(120);
  const [mosqueSpace, setMosqueSpace] = useState(8);

  // This will lift state when you change inputs to re-trigger calculations or 
  // you can let the user re-trigger analyzing manually.
  // For now we just display the results given by the backend

  if (!results) {
    return (
      <div className="p-4 bg-gray-50 border rounded text-center text-gray-500">
        Draw a box or polygon to run analysis.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardContent className="p-4 space-y-4">
          <h2 className="text-xl font-bold border-b pb-2">Analysis Summary</h2>
          
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-blue-50 p-3 rounded">
              <div className="text-sm text-blue-800">Total Parcels</div>
              <div className="text-2xl font-bold">{results.total_parcels?.toLocaleString()}</div>
            </div>
            <div className="bg-green-50 p-3 rounded">
              <div className="text-sm text-green-800">Total Area</div>
              <div className="text-2xl font-bold">
                {(results.total_area_m2 / 10000).toFixed(2)} ha
              </div>
            </div>
          </div>
          
          <div className="border-t pt-4 mt-4">
               <h3 className="font-semibold mb-2 text-indigo-800">Development Status</h3>
               <div className="flex gap-4">
                   <div className="flex-1 bg-yellow-50 p-2 text-center rounded">
                       <div className="text-xs text-yellow-700">Vacant</div>
                       <div className="font-bold">{results.vacant_count}</div>
                   </div>
                   <div className="flex-1 bg-teal-50 p-2 text-center rounded">
                       <div className="text-xs text-teal-700">Developed</div>
                       <div className="font-bold">{results.developed_count}</div>
                   </div>
               </div>
          </div>

          <div className="space-y-3 border-t pt-4">
            <h3 className="font-semibold">Subtype Classifications</h3>
            <div className="max-h-40 overflow-y-auto pr-2 gap-2 text-sm">
                {results.subtypes_counts && Object.entries(results.subtypes_counts).map(([subtype, count]) => (
                  <div key={subtype} className="flex justify-between border-b pb-1">
                    <span className="text-gray-700">{subtype}</span>
                    <span className="font-medium bg-gray-100 px-2 rounded">{count}</span>
                  </div>
                ))}
            </div>
          </div>

          <div className="space-y-4 border-t pt-4">
            <h3 className="font-semibold text-purple-800">Capacity & Usage Estimates</h3>
            
            <div className="bg-gray-50 p-3 rounded-lg border">
                <div className="flex justify-between items-center mb-2">
                    <div className="text-sm font-medium">Mosque Capacity</div>
                    <div className="text-lg font-bold text-blue-600">{results.total_mosque_capacity?.toLocaleString()} <span className="text-xs text-gray-500 font-normal">people</span></div>
                </div>
                <div className="text-xs text-gray-500">Based on {results.mosque_space_m2} m² per person (adjustable in Map tools)</div>
            </div>

            <div className="bg-gray-50 p-3 rounded-lg border">
                <div className="flex justify-between items-center mb-2">
                    <div className="text-sm font-medium">Commercial Usage</div>
                    <div className="text-lg font-bold text-green-600">{results.total_shops?.toLocaleString()} <span className="text-xs text-gray-500 font-normal">shops</span></div>
                </div>
                <div className="text-xs text-gray-500">Based on {results.shop_size_m2} m² per shop (adjustable in Map tools)</div>
            </div>
          </div>

          <div className="pt-4 mt-4 border-t">
            <button
              onClick={() => onGenerateReport(results)}
              disabled={isGenerating || results.total_parcels === 0}
              className={`w-full py-2 px-4 rounded font-medium text-white ${
                isGenerating ? 'bg-gray-400 cursor-not-allowed' : 'bg-indigo-600 hover:bg-indigo-700'
              }`}
            >
              {isGenerating ? 'Generating AI Report...' : 'Generate AI Report'}
            </button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default AnalysisPanel;
