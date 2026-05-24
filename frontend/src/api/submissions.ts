import api from './client';

export interface LatestSubmission {
  id: number;
  student_id: number;
  assignment_id: number;
  code: string;
  file_path?: string | null;
  submitted_at: string;
}

export async function getLatestSubmission(assignmentId: number) {
  return api.get<LatestSubmission>(`/submissions/${assignmentId}/latest`);
}

export async function submitAssignmentFile(assignmentId: number, file: File) {
  const formData = new FormData();
  formData.append('file', file);
  return api.post<LatestSubmission>(`/submissions/${assignmentId}`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
}
