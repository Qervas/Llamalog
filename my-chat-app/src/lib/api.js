import { get } from "svelte/store";
import { serverConfig } from "./stores";
import { config } from "./config";

class APIClient {
  constructor() {
    this.config = get(serverConfig);
  }

  async fetch(endpoint, options = {}) {
    const url = `${this.config.backendUrl}${endpoint}`;
    const defaultOptions = {
      headers: {
        "Content-Type": "application/json",
      },
      timeout: config.API_TIMEOUT,
    };

    try {
      const response = await fetch(url, { ...defaultOptions, ...options });
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return response;
    } catch (error) {
      console.error(`API call failed: ${endpoint}`, error);
      throw error;
    }
  }

  async getModels() {
    const response = await this.fetch("/models");
    return response.json();
  }

  async loadModel(modelId) {
    const response = await this.fetch(`/models/${modelId}/load`, {
      method: "POST",
    });
    return response.json();
  }

  async stopModel() {
    const response = await this.fetch("/models/stop", {
      method: "POST",
    });
    return response.json();
  }

  async checkHealth() {
    const response = await this.fetch("/health");
    return response.json();
  }
}

export const api = new APIClient();
