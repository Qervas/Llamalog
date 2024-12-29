import { writable } from "svelte/store";
import { config } from "./config";

export const serverConfig = writable({
  backendUrl: config.BACKEND_URL,
  llmServerUrl: config.LLM_SERVER_URL,
});

export const serverStatus = writable({
  healthy: false,
  modelServer: null,
  apiServer: null,
  lastCheck: null,
  error: null,
});

export const modelState = writable({
  available: [],
  current: null,
  loading: false,
  error: null,
});

export const modelSettings = writable({
  model: null,
  max_tokens: 2048,
  temperature: 0.7,
  top_p: 1.0,
  presence_penalty: 0,
  frequency_penalty: 0,
  stream: true,
  useWebSearch: false,
});

export const artifacts = writable({
  visible: false,
  currentArtifact: null,
  items: [],
});

export const currentTheme = writable("light");
