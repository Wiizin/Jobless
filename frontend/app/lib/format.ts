import type { ApplicationStatus, DocumentStatus, DocumentType, OfferStatus } from "./types";

/** The three colour bands score pills and stat tiles share. */
export type Tone = "good" | "warn" | "bad" | "accent" | "neutral";

export function scoreTone(score: number | null | undefined): Tone {
  if (score === null || score === undefined) return "neutral";
  if (score >= 75) return "good";
  if (score >= 45) return "warn";
  return "bad";
}

/** Offer status → tone. `new`/`scored` are "in the queue"; dismissed is done with. */
export function offerStatusTone(status: OfferStatus): Tone {
  switch (status) {
    case "new":
    case "scored":
      return "accent";
    case "reviewed":
      return "good";
    case "dismissed":
      return "neutral";
  }
}

export function documentStatusTone(status: DocumentStatus): Tone {
  return status === "approved" ? "good" : "warn";
}

export function applicationStatusTone(status: ApplicationStatus): Tone {
  switch (status) {
    case "offer_received":
      return "good";
    case "applied":
    case "interviewing":
      return "accent";
    case "not_applied":
      return "warn";
    case "rejected":
      return "bad";
    case "withdrawn":
      return "neutral";
  }
}

/** `pending_review` → `Pending review`. Used for every enum label. */
export function humanize(value: string): string {
  const spaced = value.replace(/_/g, " ");
  return spaced.charAt(0).toUpperCase() + spaced.slice(1);
}

const DOC_TYPE_LABELS: Record<DocumentType, string> = {
  cv: "CV",
  cover_letter: "Cover letter",
  qa: "Q&A",
};

export function documentTypeLabel(docType: DocumentType): string {
  return DOC_TYPE_LABELS[docType] ?? humanize(docType);
}

/** ISO date/datetime → `12 Sep 2026`. Returns `—` for null/unparseable. */
export function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return `${formatDate(value)}, ${date.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" })}`;
}

/** True when the timestamp falls on today's local date. */
export function isToday(value: string | null | undefined): boolean {
  if (!value) return false;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return false;
  const now = new Date();
  return (
    date.getFullYear() === now.getFullYear() &&
    date.getMonth() === now.getMonth() &&
    date.getDate() === now.getDate()
  );
}
