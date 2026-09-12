import type { ApplicationStatus, DocumentStatus, OfferStatus } from "../lib/types";
import {
  applicationStatusTone,
  documentStatusTone,
  humanize,
  offerStatusTone,
  scoreTone,
  type Tone,
} from "../lib/format";
import styles from "./Pill.module.css";

function className(tone: Tone, variant: "score" | "status") {
  return `${styles.pill} ${styles[variant]} ${styles[tone]}`;
}

/** Monospace score chip, coloured by band: >=75 good, 45-74 warn, <45 bad. */
export function ScorePill({ score }: { score: number | null | undefined }) {
  return (
    <span className={className(scoreTone(score), "score")}>
      {score === null || score === undefined ? "—" : score}
    </span>
  );
}

export function OfferStatusPill({ status }: { status: OfferStatus }) {
  return <span className={className(offerStatusTone(status), "status")}>{humanize(status)}</span>;
}

export function DocumentStatusPill({ status }: { status: DocumentStatus }) {
  return <span className={className(documentStatusTone(status), "status")}>{humanize(status)}</span>;
}

export function ApplicationStatusPill({ status }: { status: ApplicationStatus }) {
  return <span className={className(applicationStatusTone(status), "status")}>{humanize(status)}</span>;
}

/** Plain tag used for skills, dealbreakers, sources. */
export function Tag({ children, tone = "neutral" }: { children: React.ReactNode; tone?: Tone }) {
  return <span className={className(tone, "status")}>{children}</span>;
}
