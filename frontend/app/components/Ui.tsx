"use client";

import { useEffect, type ReactNode } from "react";

import type { Tone } from "../lib/format";
import styles from "./Ui.module.css";

const TONE_CLASS: Record<Tone, string> = {
  good: styles.toneGood,
  warn: styles.toneWarn,
  bad: styles.toneBad,
  accent: styles.toneAccent,
  neutral: styles.toneNeutral,
};

// --- async / empty states -------------------------------------------------

export function Spinner() {
  return <span className={styles.spinner} role="status" aria-label="Loading" />;
}

export function Loading({ what = "…" }: { what?: string }) {
  return (
    <div className={styles.note}>
      <Spinner /> <span style={{ marginLeft: 8 }}>Loading {what}</span>
    </div>
  );
}

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className={styles.note}>
      <div className={styles.noteTitle}>{title}</div>
      {children}
    </div>
  );
}

export function ErrorNote({ error, what }: { error: unknown; what: string }) {
  const message = error instanceof Error ? error.message : String(error);
  return (
    <div className={styles.error} role="alert">
      <div className={styles.errorTitle}>Couldn’t {what}</div>
      {message}
    </div>
  );
}

export function Hint({ children }: { children: ReactNode }) {
  return <div className={styles.hint}>{children}</div>;
}

// --- stat tiles -----------------------------------------------------------

export function StatTiles({ children }: { children: ReactNode }) {
  return <div className={styles.tiles}>{children}</div>;
}

export function StatTile({
  label,
  value,
  hint,
  tone = "neutral",
}: {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  tone?: Tone;
}) {
  return (
    <div className={styles.tile}>
      <div className={styles.tileLabel}>{label}</div>
      <div className={`${styles.tileValue} ${TONE_CLASS[tone]}`}>{value}</div>
      {hint ? <div className={styles.tileHint}>{hint}</div> : null}
    </div>
  );
}

// --- filter chips ---------------------------------------------------------

export function ChipRow({ children }: { children: ReactNode }) {
  return <div className={styles.chips}>{children}</div>;
}

export function Chip({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      className={`${styles.chip} ${active ? styles.chipActive : ""}`}
      aria-pressed={active}
      onClick={onClick}
    >
      {children}
    </button>
  );
}

// --- table ----------------------------------------------------------------

export function TableWrap({ children }: { children: ReactNode }) {
  return <div className={styles.tableWrap}>{children}</div>;
}

export const tableStyles = {
  table: styles.table,
  rowClickable: styles.rowClickable,
  primaryCell: styles.primaryCell,
  secondaryCell: styles.secondaryCell,
  numericCell: styles.numericCell,
};

// --- section --------------------------------------------------------------

export function Section({
  title,
  action,
  children,
}: {
  title?: string;
  action?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className={styles.section}>
      {title || action ? (
        <div className={styles.sectionHead}>
          {title ? <h2 className={styles.sectionTitle}>{title}</h2> : <span />}
          {action}
        </div>
      ) : null}
      {children}
    </section>
  );
}

export const layoutStyles = {
  tagRow: styles.tagRow,
  prose: styles.prose,
  posting: styles.posting,
  formRow: styles.formRow,
};

// --- modal ----------------------------------------------------------------

export function Modal({
  title,
  onClose,
  footer,
  children,
}: {
  title: string;
  onClose: () => void;
  footer?: ReactNode;
  children: ReactNode;
}) {
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div
      className={styles.backdrop}
      role="dialog"
      aria-modal="true"
      aria-label={title}
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div className={styles.modal}>
        <div className={styles.modalHead}>
          <h2 className={styles.modalTitle}>{title}</h2>
          <button type="button" className={styles.modalClose} onClick={onClose} aria-label="Close">
            ×
          </button>
        </div>
        <div className={styles.modalBody}>{children}</div>
        {footer ? <div className={styles.modalFoot}>{footer}</div> : null}
      </div>
    </div>
  );
}
