import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
    stages: [
        { duration: '30s', target: 10 },
        { duration: '30s', target: 25 },
        { duration: '30s', target: 50 },
        { duration: '30s', target: 100 },
        { duration: '15s', target: 0 },
    ],

    thresholds: {
        http_req_failed: ['rate<0.01'],
        http_req_duration: [
            'p(95)<1000',
            'p(99)<1500',
        ],
    },
};

export default function () {
    const response = http.get(
        'http://host.docker.internal:8003/correlations/paris/nord?limit=50'
    );

    check(response, {
        'status 200': (r) => r.status === 200,
        'response non vide': (r) => r.body.length > 2,
    });

    sleep(1);
}