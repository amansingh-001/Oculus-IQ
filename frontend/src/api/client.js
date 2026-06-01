import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || 'http://localhost:8000/api/v1',
  timeout: 30000,
});

export const QUERY_KEYS = {
  shipments: ['shipments'],
  stats: ['shipments', 'stats'],
  disruptions: ['disruptions'],
  alerts: ['alerts'],
  weatherRisks: ['weather', 'risks'],
  feeds: ['health', 'feeds'],
  timeline: ['shipments', 'timeline'],
  financial: ['shipments', 'financial'],
  portNetwork: ['routes', 'network'],
  chokepoints: ['routes', 'chokepoints'],
  portCongestion: ['ports', 'congestion'],
  scenarios: ['simulation', 'scenarios'],
  simulationHistory: ['simulation', 'history'],
  anomalies: ['intelligence', 'anomalies'],
  cascadeGraph: ['intelligence', 'cascade-graph'],
  latestScan: ['intelligence', 'scan', 'latest'],
  externalRisks: ['intelligence', 'external-risks'],
  suppliers: ['suppliers'],
  agentStatus: ['agent', 'status'],
  clients: ['clients'],
  slaOverview: ['clients', 'sla-overview'],
  tariffFleet: ['tariff', 'fleet-exposure'],
  carbonFleet: ['carbon', 'fleet-summary'],
};

const clean = (params = {}) => Object.fromEntries(Object.entries(params).filter(([, value]) => value !== undefined && value !== null && value !== ''));

// Shipments
export const getShipments = async (filters = {}) => {
  const { data } = await api.get('/shipments', { params: clean(filters) });
  return data;
};

export const getShipmentStats = async () => {
  const { data } = await api.get('/shipments/stats');
  return data;
};

export const getShipmentById = async (id) => {
  const { data } = await api.get(`/shipments/${id}`);
  return data;
};

export const updateShipment = async (id, payload) => {
  const { data } = await api.patch(`/shipments/${id}`, payload);
  return data;
};

export const createShipment = async (payload) => {
  const { data } = await api.post('/shipments', payload);
  return data;
};

export const getShipmentTimeline = async () => {
  const { data } = await api.get('/shipments/timeline');
  return data;
};

export const getFinancialSummary = async () => {
  const { data } = await api.get('/shipments/financial-summary');
  return data;
};

export const getShipmentLandedCost = async (id) => {
  const { data } = await api.get(`/shipments/${id}/landed-cost`);
  return data;
};

// Disruptions
export const getDisruptions = async () => {
  const { data } = await api.get('/disruptions');
  return data;
};

export const simulateDisruption = async (payload = {}) => {
  const { data } = await api.post('/disruptions/simulate', payload);
  return data;
};

// Weather
export const getWeatherRisks = async () => {
  const { data } = await api.get('/weather/risks');
  return data;
};

// Health
export const getFeedHealth = async () => {
  const { data } = await api.get('/health/feeds');
  return data;
};

// Routes
export const getRouteAlternatives = async (shipmentId) => {
  const { data } = await api.get(`/routes/${shipmentId}/alternatives`);
  return data;
};

export const getRouteNetwork = async () => {
  const { data } = await api.get('/routes/network');
  return data;
};

export const getChokepoints = async () => {
  const { data } = await api.get('/routes/chokepoints');
  return data;
};

export const optimizeRoute = async (originPortId, destPortId, optimizeFor = 'balanced') => {
  const { data } = await api.post('/routes/optimize', {
    origin_port_id: originPortId,
    dest_port_id: destPortId,
    optimize_for: optimizeFor,
  });
  return data;
};

// Alerts
export const getAlerts = async (filters = {}) => {
  const { data } = await api.get('/alerts', { params: clean(filters) });
  return data;
};

export const acknowledgeAlert = async (id) => {
  const { data } = await api.post(`/alerts/${id}/acknowledge`);
  return data;
};

export const getAlertDraft = async (id) => {
  const { data } = await api.get(`/alerts/${id}/draft`);
  return data;
};

// Copilot
export const sendCopilotMessage = async (message, conversationHistory = []) => {
  const { data } = await api.post('/copilot/chat', {
    message,
    conversation_history: conversationHistory,
  });
  return data;
};

// Simulation
export const getSimulationScenarios = async () => {
  const { data } = await api.get('/simulation/scenarios');
  return data;
};

export const runSimulation = async (scenarioKey, durationHours, target = {}) => {
  const { data } = await api.post('/simulation/run', {
    scenario_key: scenarioKey,
    duration_hours: durationHours,
    ...target,
  });
  return data;
};

export const getSimulationHistory = async () => {
  const { data } = await api.get('/simulation/history');
  return data;
};

// Intelligence
export const getAnomalies = async () => {
  const { data } = await api.get('/intelligence/anomalies');
  return data;
};

export const getCascadeGraph = async () => {
  const { data } = await api.get('/intelligence/cascade-graph');
  return data;
};

export const getCascadeAnalysis = async () => {
  const { data } = await api.get('/intelligence/cascade');
  return data;
};

export const runIntelligenceScan = async () => {
  const { data } = await api.post('/intelligence/scan');
  return data;
};

export const getLatestIntelligenceScan = async () => {
  const { data } = await api.get('/intelligence/scans/latest');
  return data;
};

export const getExternalRisks = async () => {
  const { data } = await api.get('/intelligence/external-risks');
  return data;
};

// Ports
export const getPortCongestion = async () => {
  const { data } = await api.get('/ports/congestion');
  return data;
};

export const createPort = async (payload) => {
  const { data } = await api.post('/ports', payload);
  return data;
};

// Suppliers
export const getSuppliers = async () => {
  const { data } = await api.get('/suppliers');
  return data;
};

export const getSupplierScorecard = async (id) => {
  const { data } = await api.get(`/suppliers/${id}/scorecard`);
  return data;
};

// Clients
export const getClients = async () => {
  const { data } = await api.get('/clients');
  return data;
};

export const createClient = async (payload) => {
  const { data } = await api.post('/clients', payload);
  return data;
};

export const createRoute = async (payload) => {
  const { data } = await api.post('/routes', payload);
  return data;
};

export const getClientShipments = async (id) => {
  const { data } = await api.get(`/clients/${id}/shipments`);
  return data;
};

export const getClientSlaOverview = async () => {
  const { data } = await api.get('/clients/sla-overview');
  return data;
};

export const getClientWeeklyReport = async (id) => {
  const { data } = await api.get(`/clients/${id}/weekly-report`);
  return data;
};

export const getClientWhatsappAlert = async (id) => {
  const { data } = await api.get(`/clients/${id}/whatsapp-alert`);
  return data;
};

// Tariff and carbon
export const getFleetTariffExposure = async () => {
  const { data } = await api.get('/tariff/fleet-exposure');
  return data;
};

export const getFleetCarbonSummary = async () => {
  const { data } = await api.get('/carbon/fleet-summary');
  return data;
};

// Documents / CSV import
export const importShipmentsCsv = async (csvText, upsert = true) => {
  const { data } = await api.post('/documents/import-csv', { csv_text: csvText, upsert });
  return data;
};

export const getCsvTemplate = async () => {
  const { data } = await api.get('/documents/template');
  return data;
};

// Agent
export const getAgentStatus = async () => {
  const { data } = await api.get('/agent/status');
  return data;
};

export const toggleAgent = async () => {
  const { data } = await api.post('/agent/toggle');
  return data;
};

export default api;
