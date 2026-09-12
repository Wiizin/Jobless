"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { DocumentStatusPill, Tag } from "../../components/Pill";
import { Page } from "../../components/Shell";
import { ErrorNote, Hint, Loading, Section, layoutStyles } from "../../components/Ui";
import { documentTypeLabel, formatDateTime } from "../../lib/format";
import {
  useApproveDocument,
  useDocument,
  useDownloadDocument,
  useEditDocument,
  useOffer,
} from "../../lib/hooks";
import type { CoverLetterSections, DocumentEditRequest, DocumentOut } from "../../lib/types";
import styles from "./DocumentReview.module.css";

/** Local, editable mirror of the parts of a document a human can change. */
interface Draft {
  bullets: string[];
  intro: string;
  bodyParagraphs: string[];
  closing: string;
  qaAnswers: [question: string, answer: string][];
}

function toDraft(document: DocumentOut): Draft {
  const sections = document.cover_letter_sections ?? {};
  return {
    bullets: [...document.bullets],
    intro: sections.intro ?? "",
    bodyParagraphs: [...(sections.body_paragraphs ?? [])],
    closing: sections.closing ?? "",
    qaAnswers: Object.entries(document.qa_answers ?? {}),
  };
}

export default function DocumentReviewPage() {
  const params = useParams<{ id: string }>();
  const documentId = params.id;

  const { data: document, isPending, isError, error } = useDocument(documentId);
  const { data: offer } = useOffer(document?.offer_id ?? null);
  const edit = useEditDocument(documentId);
  const approve = useApproveDocument(documentId);
  const download = useDownloadDocument(documentId);

  const [draft, setDraft] = useState<Draft | null>(null);

  // Seed the editor from the server copy, and re-seed whenever the server copy
  // changes underneath (e.g. after a save or an approval).
  useEffect(() => {
    if (document) setDraft(toDraft(document));
  }, [document]);

  const approved = document?.status === "approved";

  /** Does this document carry cover-letter content worth editing? */
  const hasCoverLetter = useMemo(() => {
    if (!document) return false;
    if (document.doc_type === "cover_letter") return true;
    const sections = document.cover_letter_sections ?? {};
    return Boolean(sections.intro || sections.closing || sections.body_paragraphs?.length);
  }, [document]);

  const dirty = useMemo(() => {
    if (!document || !draft) return false;
    return JSON.stringify(draft) !== JSON.stringify(toDraft(document));
  }, [document, draft]);

  if (isError) {
    return (
      <Page title="Document" action={<BackLink />}>
        <ErrorNote error={error} what="load this document" />
      </Page>
    );
  }

  if (isPending || !document || !draft) {
    return (
      <Page title="Document" action={<BackLink />}>
        <Loading what="document" />
      </Page>
    );
  }

  const update = (patch: Partial<Draft>) => setDraft((previous) => (previous ? { ...previous, ...patch } : previous));

  const save = () => {
    const payload: DocumentEditRequest = { bullets: draft.bullets.map((b) => b.trim()).filter(Boolean) };

    // The backend validates cover_letter_sections as a complete
    // CoverLetterSections, so only send it when this document actually has one.
    if (hasCoverLetter) {
      const sections: CoverLetterSections = {
        intro: draft.intro,
        body_paragraphs: draft.bodyParagraphs.map((p) => p.trim()).filter(Boolean),
        closing: draft.closing,
      };
      payload.cover_letter_sections = sections;
    }

    if (draft.qaAnswers.length > 0) {
      payload.qa_answers = Object.fromEntries(draft.qaAnswers.filter(([question]) => question.trim() !== ""));
    }

    edit.mutate(payload);
  };

  const canDownload = approved && Boolean(document.file_path);

  return (
    <Page
      title={`${documentTypeLabel(document.doc_type)} draft`}
      subtitle={offer ? `${offer.title} · ${offer.company}` : "Review every line before approving."}
      action={<BackLink />}
    >
      <Section>
        <div className={styles.headline}>
          <div className={styles.headlineMain}>
            <h2 className={styles.docTitle}>
              {offer ? offer.title : documentTypeLabel(document.doc_type)}
            </h2>
            <div className={styles.docMeta}>
              {offer ? `${offer.company} · ` : ""}Generated {formatDateTime(document.created_at)}
            </div>
          </div>
          <div className={styles.headlineSide}>
            <Tag tone="neutral">{documentTypeLabel(document.doc_type)}</Tag>
            <DocumentStatusPill status={document.status} />
          </div>
        </div>

        <div className={styles.actions}>
          <button type="button" className="btn" onClick={save} disabled={approved || !dirty || edit.isPending}>
            {edit.isPending ? "Saving…" : "Save edits"}
          </button>
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => approve.mutate()}
            disabled={approved || approve.isPending || dirty}
          >
            {approved ? "Approved" : approve.isPending ? "Rendering…" : "Approve & render .docx"}
          </button>
          {canDownload ? (
            <button
              type="button"
              className="btn"
              onClick={() => download.mutate()}
              disabled={download.isPending}
            >
              {download.isPending ? "Preparing…" : "⭳ Download"}
            </button>
          ) : null}
          {offer ? (
            <Link href={`/offers/${offer.id}`} className="btn">
              View offer
            </Link>
          ) : null}
          {dirty ? (
            <span className={styles.dirty}>Unsaved edits</span>
          ) : approved ? (
            <span className={styles.saved}>Approved documents are immutable.</span>
          ) : (
            <span className={styles.saved}>Edits are saved only when you click Save.</span>
          )}
        </div>

        {approved && !document.file_path ? (
          <div className={styles.errorRow}>
            <Hint>
              Approved — but {documentTypeLabel(document.doc_type)} content has no standalone file, so there’s
              nothing to download. Review it in-app.
            </Hint>
          </div>
        ) : null}
        {edit.isError ? (
          <div className={styles.errorRow}>
            <ErrorNote error={edit.error} what="save your edits" />
          </div>
        ) : null}
        {approve.isError ? (
          <div className={styles.errorRow}>
            <ErrorNote error={approve.error} what="approve this document" />
          </div>
        ) : null}
        {download.isError ? (
          <div className={styles.errorRow}>
            <ErrorNote error={download.error} what="download this document" />
          </div>
        ) : null}
      </Section>

      <Section
        title="CV bullets"
        action={
          !approved ? (
            <button
              type="button"
              className="btn"
              onClick={() => update({ bullets: [...draft.bullets, ""] })}
            >
              ＋ Add bullet
            </button>
          ) : null
        }
      >
        {draft.bullets.length === 0 ? (
          <p className={styles.emptyNote}>No bullets on this document.</p>
        ) : (
          <div className={styles.itemList}>
            {draft.bullets.map((bullet, index) => (
              <div key={index} className={styles.item}>
                <span className={styles.itemIndex}>{index + 1}</span>
                <textarea
                  className="textarea"
                  style={{ minHeight: 58 }}
                  value={bullet}
                  disabled={approved}
                  aria-label={`Bullet ${index + 1}`}
                  onChange={(event) => {
                    const next = [...draft.bullets];
                    next[index] = event.target.value;
                    update({ bullets: next });
                  }}
                />
                <button
                  type="button"
                  className={styles.iconBtn}
                  disabled={approved}
                  aria-label={`Remove bullet ${index + 1}`}
                  onClick={() => update({ bullets: draft.bullets.filter((_, i) => i !== index) })}
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        )}
      </Section>

      {hasCoverLetter ? (
        <Section
          title="Cover letter"
          action={
            !approved ? (
              <button
                type="button"
                className="btn"
                onClick={() => update({ bodyParagraphs: [...draft.bodyParagraphs, ""] })}
              >
                ＋ Add paragraph
              </button>
            ) : null
          }
        >
          <div className="field" style={{ marginBottom: 14 }}>
            <label className="label" htmlFor="cl-intro">
              Intro
            </label>
            <textarea
              id="cl-intro"
              className="textarea"
              value={draft.intro}
              disabled={approved}
              onChange={(event) => update({ intro: event.target.value })}
            />
          </div>

          <div className="label" style={{ marginBottom: 6 }}>
            Body paragraphs
          </div>
          {draft.bodyParagraphs.length === 0 ? (
            <p className={styles.emptyNote}>No body paragraphs yet.</p>
          ) : (
            <div className={styles.itemList}>
              {draft.bodyParagraphs.map((paragraph, index) => (
                <div key={index} className={styles.item}>
                  <span className={styles.itemIndex}>{index + 1}</span>
                  <textarea
                    className="textarea"
                    style={{ minHeight: 96 }}
                    value={paragraph}
                    disabled={approved}
                    aria-label={`Body paragraph ${index + 1}`}
                    onChange={(event) => {
                      const next = [...draft.bodyParagraphs];
                      next[index] = event.target.value;
                      update({ bodyParagraphs: next });
                    }}
                  />
                  <button
                    type="button"
                    className={styles.iconBtn}
                    disabled={approved}
                    aria-label={`Remove body paragraph ${index + 1}`}
                    onClick={() =>
                      update({ bodyParagraphs: draft.bodyParagraphs.filter((_, i) => i !== index) })
                    }
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
          )}

          <div className="field" style={{ marginTop: 14 }}>
            <label className="label" htmlFor="cl-closing">
              Closing
            </label>
            <textarea
              id="cl-closing"
              className="textarea"
              value={draft.closing}
              disabled={approved}
              onChange={(event) => update({ closing: event.target.value })}
            />
          </div>
        </Section>
      ) : null}

      {draft.qaAnswers.length > 0 ? (
        <Section title="Application questions">
          {draft.qaAnswers.map(([question, answer], index) => (
            <div key={question} className={styles.qaItem}>
              <div className={styles.qaQuestion}>{question}</div>
              <textarea
                className="textarea"
                value={answer}
                disabled={approved}
                aria-label={question}
                onChange={(event) => {
                  const next = [...draft.qaAnswers];
                  next[index] = [question, event.target.value];
                  update({ qaAnswers: next });
                }}
              />
            </div>
          ))}
        </Section>
      ) : null}

      {document.selected_experiences.length > 0 ? (
        <Section title="Experiences drawn on">
          <div className={layoutStyles.tagRow}>
            {document.selected_experiences.map((experienceId) => (
              <Tag key={experienceId}>{experienceId.slice(0, 8)}</Tag>
            ))}
          </div>
        </Section>
      ) : null}
    </Page>
  );
}

function BackLink() {
  return (
    <Link href="/documents" className="btn">
      ← All documents
    </Link>
  );
}
