import { Trend } from 'k6/metrics';

// Document API latency, tracked separately from the aggregate http_req_duration
// so it can be thresholded on its own.
export const readDuration = new Trend('documents_read_duration', true);
