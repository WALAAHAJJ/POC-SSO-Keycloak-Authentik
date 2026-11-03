import http from "k6/http";
import { check } from "k6";

export const options = {
  scenarios: {
    catalogue: {
      executor: "constant-arrival-rate",
      rate: 20,
      timeUnit: "1s",
      duration: "30s",
      preAllocatedVUs: 20,
      maxVUs: 100,
    },
  },
  summaryTrendStats: ["avg", "min", "med", "max", "p(90)", "p(95)", "p(99)"],
};

const BASE_URL = __ENV.BASE_URL || "http://localhost:8001";

export default function () {
  const response = http.get(`${BASE_URL}/products`);

  check(response, {
    "Statut HTTP 200": (r) => r.status === 200,
  });
}
