/** DRF PageNumberPagination envelope (?page=, ?page_size=). */
export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

/** DRF serializes DecimalField as a string ("99.99") to avoid float rounding — keep it a string. */
export type Money = string;
