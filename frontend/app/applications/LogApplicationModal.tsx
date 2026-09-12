"use client";

import { useState } from "react";

import { Modal } from "../components/Ui";
import { documentTypeLabel } from "../lib/format";
import { useAllDocumentIds, useCreateApplication, useDocumentsByIds, useOffers } from "../lib/hooks";
import styles from "./ApplicationsPage.module.css";

/**
 * Records an application the user made themselves. Nothing here submits
 * anything — the backend only stores what happened.
 */
export function LogApplicationModal({ onClose }: { onClose: () => void }) {
  const { data: offers } = useOffers({ limit: 200 });
  const documentIds = useAllDocumentIds();
  const documentQueries = useDocumentsByIds(documentIds);
  const createApplication = useCreateApplication();

  const [offerId, setOfferId] = useState("");
  const [documentId, setDocumentId] = useState("");
  const [notes, setNotes] = useState("");

  // The backend rejects attaching an unapproved document (409).
  const approvedDocs = documentQueries
    .map((query) => query.data)
    .filter((doc) => doc !== undefined)
    .filter((doc) => doc.status === "approved");

  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    if (!offerId) return;
    createApplication.mutate(
      {
        offer_id: offerId,
        document_id: documentId || null,
        notes: notes.trim() || null,
      },
      { onSuccess: onClose },
    );
  };

  return (
    <Modal
      title="Log application"
      onClose={onClose}
      footer={
        <>
          <button type="button" className="btn" onClick={onClose}>
            Cancel
          </button>
          <button
            type="submit"
            form="log-application-form"
            className="btn btn-primary"
            disabled={!offerId || createApplication.isPending}
          >
            {createApplication.isPending ? "Saving…" : "Log it"}
          </button>
        </>
      }
    >
      <form id="log-application-form" onSubmit={submit} style={{ display: "grid", gap: 13 }}>
        <div className="field">
          <label className="label" htmlFor="application-offer">
            Offer
          </label>
          <select
            id="application-offer"
            className="select"
            value={offerId}
            onChange={(event) => setOfferId(event.target.value)}
            required
          >
            <option value="">Select an offer…</option>
            {(offers ?? []).map((offer) => (
              <option key={offer.id} value={offer.id}>
                {offer.title} — {offer.company}
              </option>
            ))}
          </select>
        </div>

        <div className="field">
          <label className="label" htmlFor="application-document">
            Attached document (optional)
          </label>
          <select
            id="application-document"
            className="select"
            value={documentId}
            onChange={(event) => setDocumentId(event.target.value)}
          >
            <option value="">None</option>
            {approvedDocs.map((doc) => (
              <option key={doc.id} value={doc.id}>
                {documentTypeLabel(doc.doc_type)} · {doc.id.slice(0, 8)}
              </option>
            ))}
          </select>
          <span className={styles.formNote}>Only approved documents can be attached.</span>
        </div>

        <div className="field">
          <label className="label" htmlFor="application-notes">
            Notes
          </label>
          <textarea
            id="application-notes"
            className="textarea"
            value={notes}
            onChange={(event) => setNotes(event.target.value)}
            placeholder="Applied through the company portal, referred by…"
          />
        </div>

        {createApplication.isError ? (
          <div className={styles.formError}>{(createApplication.error as Error).message}</div>
        ) : null}
      </form>
    </Modal>
  );
}
