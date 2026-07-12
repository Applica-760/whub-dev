import { requestJson } from '../../api/client';
import type { paths } from '../../api/generated/schema';

export type ResourceStatusResponse =
  paths['/api/resources/status']['get']['responses'][200]['content']['application/json'];
export type ResourceStatusItem = ResourceStatusResponse['resources'][number];

export async function listResourceStatus(): Promise<ResourceStatusResponse> {
  return requestJson<ResourceStatusResponse>('/api/resources/status');
}
