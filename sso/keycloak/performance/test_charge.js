import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '15s', target: 1 },
    { duration: '15s', target: 5 },
    { duration: '15s', target: 10 },
    { duration: '15s', target: 20 },
    { duration: '15s', target: 0 },
  ],
};

export default function () {
  const response = http.get(
    'http://host.docker.internal:8080/realms/collector-poc/.well-known/openid-configuration'
  );

  check(response, {
    'HTTP 200': (r) => r.status === 200,
    'Temps inférieur à 1 seconde': (r) => r.timings.duration < 1000,
  });

  sleep(1);
}
