"use client";

import Link from "next/link";
import { useState } from "react";

import { ApplicationStatusPill } from "../components/Pill";
import { Page } from "../components/Shell";
import { EmptyState, ErrorNote, Loading, Modal, TableWrap, tableStyles } from "../components/Ui";
import { formatDate, formatDateTime, humanize } from "../lib/format";
import { useApplications, useOffersByIds, useUpdateApplicationStatus } from "../lib/hooks";
import { APPLICATION_STATUSES, type ApplicationOut, type ApplicationStatus } from "../lib/types";
import { LogApplicationModal } from "./LogApplicationModal";
import styles from "./ApplicationsPage.module.css";

export default function ApplicationsPage() {
  const { data: applications, isPending, isError, error } = useApplications();
  const updateStatus = useUpdateApplicationStatus();

  const [logOpen, setLogOpen] = useState(false);
  const [editingNotes, setEditingNotes] = useState<ApplicationOut | null>(null);

  // ApplicationOut carries only offer_id, so role/company is joined here.
  const offerIds = [...new Set((applications ?? []).map((application) => application.offer_id))];
  const offerQueries = useOffersByIds(offerIds);
  const offersById = new Map(
    offerQueries.map((query) => [query.data?.id, query.data] as const).filter(([id]) => id !== undefined),
  );

  const active = (applications ?? []).filter((application) =>
    ["applied", "interviewing"].includes(application.status),
  ).length;

  return (
    <Page
      title="Applications"
      subtitle={
        applications
          ? `${applications.length} tracked · ${active} in flight`
          : "Manually tracked — nothing is submitted for you."
      }
      action={
        <button type="button" className="btn btn-primary" onClick={() => setLogOpen(true)}>
          ＋ Log application
        </button>
      }
    >
      {isError ? (
        <ErrorNote error={error} what="load applications" />
      ) : isPending ? (
        <Loading what="applications" />
      ) : applications.length === 0 ? (
        <TableWrap>
          <EmptyState title="Nothing tracked yet">
            Once you’ve applied somewhere, log it here to keep the status trail in one place.
          </EmptyState>
        </TableWrap>
      ) : (
        <TableWrap>
          <table className={tableStyles.table}>
            <thead>
              <tr>
                <th>Role</th>
                <th>Status</th>
                <th>Applied</th>
                <th>Notes</th>
                <th>Document</th>
              </tr>
            </thead>
            <tbody>
              {applications.map((application) => {
                const offer = offersById.get(application.offer_id);
                const saving = updateStatus.isPending && updateStatus.variables?.id === application.id;
                return (
                  <tr key={application.id}>
                    <td>
                      <div className={styles.roleCell}>
                        {offer ? (
                          <Link href={`/offers/${offer.id}`} className={tableStyles.primaryCell}>
                            {offer.title}
                          </Link>
                        ) : (
                          <span className={tableStyles.primaryCell}>…</span>
                        )}
                        <span className={styles.company}>
                          {offer?.company ?? application.offer_id.slice(0, 8)}
                        </span>
                      </div>
                    </td>
                    <td>
                      <select
                        className={styles.statusSelect}
                        value={application.status}
                        disabled={saving}
                        aria-label={`Status for ${offer?.title ?? "application"}`}
                        onChange={(event) =>
                          updateStatus.mutate({
                            id: application.id,
                            payload: { status: event.target.value as ApplicationStatus },
                          })
                        }
                      >
                        {APPLICATION_STATUSES.map((status) => (
                          <option key={status} value={status}>
                            {humanize(status)}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className={tableStyles.numericCell}>{formatDate(application.applied_at)}</td>
                    <td className={styles.notesCell}>
                      <button
                        type="button"
                        className={styles.notesButton}
                        onClick={() => setEditingNotes(application)}
                      >
                        {application.notes || "Add notes…"}
                      </button>
                    </td>
                    <td className={tableStyles.numericCell}>
                      {application.document_id ? (
                        <Link href={`/documents/${application.document_id}`}>
                          {application.document_id.slice(0, 8)}
                        </Link>
                      ) : (
                        "—"
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </TableWrap>
      )}

      {updateStatus.isError ? (
        <div style={{ marginTop: 14 }}>
          <ErrorNote error={updateStatus.error} what="update that application" />
        </div>
      ) : null}

      {logOpen ? <LogApplicationModal onClose={() => setLogOpen(false)} /> : null}
      {editingNotes ? (
        <NotesModal application={editingNotes} onClose={() => setEditingNotes(null)} />
      ) : null}
    </Page>
  );
}

/**
 * Notes-only edit. PATCH /applications/{id} requires `status`, so the row's
 * current status is sent back unchanged alongside the new notes.
 */
function NotesModal({ application, onClose }: { application: ApplicationOut; onClose: () => void }) {
  const [notes, setNotes] = useState(application.notes ?? "");
  const updateStatus = useUpdateApplicationStatus();

  return (
    <Modal
      title="Application notes"
      onClose={onClose}
      footer={
        <>
          <button type="button" className="btn" onClick={onClose}>
            Cancel
          </button>
          <button
            type="button"
            className="btn btn-primary"
            disabled={updateStatus.isPending}
            onClick={() =>
              updateStatus.mutate(
                { id: application.id, payload: { status: application.status, notes } },
                { onSuccess: onClose },
              )
            }
          >
            {updateStatus.isPending ? "Saving…" : "Save notes"}
          </button>
        </>
      }
    >
      <div className="field">
        <label className="label" htmlFor="notes-field">
          Notes
        </label>
        <textarea
          id="notes-field"
          className="textarea"
          style={{ minHeight: 140 }}
          value={notes}
          onChange={(event) => setNotes(event.target.value)}
        />
      </div>
      <div className={styles.formNote}>
        <ApplicationStatusPill status={application.status} /> · logged {formatDateTime(application.created_at)}
      </div>
      {updateStatus.isError ? (
        <div className={styles.formError}>{(updateStatus.error as Error).message}</div>
      ) : null}
    </Modal>
  );
}
