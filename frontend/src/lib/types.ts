export type IngestResponse = {
  document_id: string;
  filename: string;
  pages: number;
  chunks: number;
};

// Yeni: async ingestion (Celery) yaniti
export type JobAccepted = {
  job_id: string;
  document_id: string;
  filename: string;
  status_url: string;
};

// Job polling sonucu
export type JobStatus = {
  job_id: string;
  state: "PENDING" | "STARTED" | "PROGRESS" | "SUCCESS" | "FAILURE";
  stage: string | null;
  percent: number | null;
  result: IngestResponse | null;
  error: string | null;
};

export type SearchHit = {
  text: string;
  page_number: number | null;
  document_id: string;
  score: number;
};

export type SearchResponse = {
  query: string;
  hits: SearchHit[];
};

export type ChatSource = {
  text: string;
  page_number: number | null;
  document_id: string;
  score: number;
};

export type ChatResponse = {
  answer: string;
  sources: ChatSource[];
};
