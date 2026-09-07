import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
    vus: 145,
    duration: '30s',

    thresholds: {
        http_req_duration: [
            'p(95)<1000',
            'p(99)<1500',
        ],
        http_req_failed: ['rate<0.01'],
    },
};

export default function () {
    const response = http.get(
        'http://host.docker.internal:8003/correlations/paris/nord?limit=50'
    );

    check(response, {
        'status 200': (r) => r.status === 200,
        'response non vide': (r) => r.body && r.body.length > 2,
    });

    sleep(1);
}
