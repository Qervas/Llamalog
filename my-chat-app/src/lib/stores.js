import { writable } from "svelte/store";

export const modelSettings = writable({
  model: "llama-3.2-3b-instruct",
  max_tokens: 2048,
  temperature: 0.7,
  top_p: 1.0,
  presence_penalty: 0,
  frequency_penalty: 0,
  stream: true,
});
