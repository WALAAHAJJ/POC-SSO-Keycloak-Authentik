import http from "k6/http";
import { check } from "k6";

// Paramètres transmis depuis Git Bash
const BASE_URL = __ENV.BASE_URL;
const API_PATH = __ENV.API_PATH || "/api/products";
const RATE = Number(__ENV.RATE || 100);
const DURATION = __ENV.DURATION || "60s";

export const options = {
  discardResponseBodies: true,

  scenarios: {
    benchmark: {
      executor: "constant-arrival-rate",
      rate: RATE,
      timeUnit: "1s",
      duration: DURATION,
      preAllocatedVUs: 50,
      maxVUs: 200,
    },
  },

  summaryTrendStats: ["avg", "min", "med", "max", "p(90)", "p(95)", "p(99)"],
};

export default function () {
  const response = http.get(`${BASE_URL}${API_PATH}`);

  check(response, {
    "HTTP 200": (r) => r.status === 200,
  });
}
