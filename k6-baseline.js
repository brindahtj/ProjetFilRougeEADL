import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  vus: 10,
  duration: '30s',

  summaryTrendStats: ['avg', 'min', 'med', 'p(90)', 'p(95)', 'p(99)', 'max'],

  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<1000',
                        'p(99)<1500'],
  },
};

export default function () {
  const res = http.get(
    'http://host.docker.internal:8003/correlations/paris/nord?limit=50'
  );

  check(res, {
    'status 200': (r) => r.status === 200,
    'response non vide': (r) => r.body && r.body.length > 2,
  });

  sleep(1);
}
