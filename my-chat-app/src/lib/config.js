export const config = {
  BACKEND_URL: import.meta.env.VITE_BACKEND_URL || "http://localhost:8000",
  LLM_SERVER_URL:
    import.meta.env.VITE_LLM_SERVER_URL || "http://localhost:8080",
  API_TIMEOUT: 30000, // 30 seconds
  HEALTH_CHECK_INTERVAL: 10000, // 10 seconds
  MODEL_CHECK_INTERVAL: 5000, // 5 seconds
};
