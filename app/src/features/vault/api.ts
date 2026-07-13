import { requestJson } from '../../api/client';
import type { VaultNode, VaultNoteResponse, VaultTreeResponse } from '../../api/client';

export async function fetchVaultTree(): Promise<VaultNode[]> {
  const response = await requestJson<VaultTreeResponse>('/api/vault/tree');
  return response.nodes;
}

export async function fetchVaultNote(path: string): Promise<string> {
  const response = await requestJson<VaultNoteResponse>(
    `/api/vault/note?path=${encodeURIComponent(path)}`,
  );
  return response.content;
}
