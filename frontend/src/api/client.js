import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// ============================================================================
// Parcels & Data Endpoints
// ============================================================================

export const getParcelsLightweight = async () => {
  const response = await apiClient.get('/parcels/lightweight');
  return response.data;
};

export const getParcelDetail = async (objectId) => {
  const response = await apiClient.get(`/parcels/${objectId}`);
  return response.data;
};

export const getBlocks = async () => {
  const response = await apiClient.get('/blocks');
  return response.data;
};

export const getBlockAnalysis = async (blockId) => {
  const response = await apiClient.get(`/analysis/block/${blockId}`);
  return response.data;
};

// ============================================================================
// Selection Endpoints
// ============================================================================

export const selectPolygon = async (coordinates) => {
  const response = await apiClient.post('/selection/polygon', { coordinates });
  return response.data;
};

export const selectBBox = async (minLat, maxLat, minLon, maxLon) => {
  const response = await apiClient.post('/selection/bbox', {
    min_lat: minLat,
    max_lat: maxLat,
    min_lon: minLon,
    max_lon: maxLon,
  });
  return response.data;
};

// ============================================================================
// Query Endpoints
// ============================================================================

export const queryCategory = async (category, selectedObjectIds) => {
  const response = await apiClient.post('/query/category', {
    category,
    selected_objectids: selectedObjectIds,
  });
  return response.data;
};

export const queryNaturalLanguage = async (question, selectionSummary) => {
  const response = await apiClient.post('/query/nl', {
    question,
    selection_summary: selectionSummary,
  });
  return response.data;
};

/**
 * Stream a natural language query answer via SSE.
 * @param {string} question
 * @param {object} selectionSummary
 * @param {function} onToken - Called with each text chunk as it arrives
 * @param {function} onDone - Called with { matching_parcel_ids } when complete
 * @returns {Promise<void>}
 */
export const streamNaturalLanguageQuery = async (question, selectionSummary, onToken, onDone) => {
  const response = await fetch(`${API_BASE_URL}/query/nl/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      question,
      selection_summary: selectionSummary,
    }),
  });

  if (!response.ok) {
    throw new Error(`Stream request failed: ${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop(); // keep incomplete line in buffer

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const payload = JSON.parse(line.slice(6));
          if (payload.type === 'token') {
            onToken(payload.content);
          } else if (payload.type === 'done') {
            onDone({ matching_parcel_ids: payload.matching_parcel_ids || [] });
          }
        } catch {
          // skip malformed lines
        }
      }
    }
  }
};

// ============================================================================
// Capacity Calculation Endpoints
// ============================================================================

export const calculateMosqueCapacity = async (objectId) => {
  const response = await apiClient.post('/calculate/mosque', { object_id: objectId });
  return response.data;
};

export const calculateCommercialCapacity = async (objectId, shopSizeM2) => {
  const response = await apiClient.post('/calculate/commercial', {
    object_id: objectId,
    shop_size_m2: shopSizeM2,
  });
  return response.data;
};

// ============================================================================
// Report Endpoints
// ============================================================================

export const generateTextReport = async (reportPayload) => {
  // reportPayload should be the full report request object:
  // { selection_summary, filtered_summary?, applied_filters?, capacity_calculations?,
  //   report_type?, report_title?, extra_context? }
  const response = await apiClient.post('/report/text', reportPayload);
  return response.data;
};

export const generatePdfReport = async (reportPayload) => {
  // Same full payload as generateTextReport
  const response = await apiClient.post('/report/pdf', reportPayload, { responseType: 'blob' });
  return response.data;
};

export const exportShapefile = async (selectedObjectIds) => {
  const response = await apiClient.post('/export/shapefile', {
    selected_objectids: selectedObjectIds,
  }, { responseType: 'blob' });
  return response.data;
};

/**
 * Export analysis results to File Geodatabase (.gdb) format.
 * 
 * Creates a complete GDB export containing:
 * - Selection polygon layer
 * - All selected parcels with full geometry and computed fields
 * - Query result layer (if category filter was applied)
 * - Capacity calculations layer (if calculations were performed)
 * - Analysis summary table
 * - LLM report sections table
 * - Domain lookup tables for Arabic labels
 * 
 * @param {object} exportPayload - Export request payload
 * @param {string[]} exportPayload.selected_objectids - List of parcel IDs to export
 * @param {number[][]} exportPayload.polygon_coordinates - [[lat, lon], ...] selection polygon
 * @param {object} exportPayload.selection_summary - Full selection summary
 * @param {string} exportPayload.query_category - Applied category filter
 * @param {string[]} exportPayload.query_parcel_ids - IDs matching the filter
 * @param {object[]} exportPayload.capacity_calculations - Capacity calculations performed
 * @param {string} exportPayload.report_text - Pre-generated report (optional)
 * @param {boolean} exportPayload.generate_report_if_missing - Generate report if not provided
 * @returns {Promise<Blob>} Zipped GDB export
 */
export const exportGDB = async (exportPayload) => {
  const response = await apiClient.post('/export/gdb', exportPayload, { responseType: 'blob' });
  return response.data;
};

// ============================================================================
// Legacy Endpoints (backward compatibility)
// ============================================================================

export const analyzeBBox = async (bbox) => {
  const response = await apiClient.post('/analyze/bbox', bbox);
  return response.data;
};

export const analyzePolygon = async (polygonData) => {
  const response = await apiClient.post('/analyze/polygon', polygonData);
  return response.data;
};

export default apiClient;
