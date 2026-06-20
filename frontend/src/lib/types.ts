export type IngestResponse = {
  document_id: string;
  filename: string;
  pages: number;
  chunks: number;
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
