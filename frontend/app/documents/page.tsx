"use client";

import { useRouter } from "next/navigation";

import { DocumentStatusPill, Tag } from "../components/Pill";
import { Page } from "../components/Shell";
import { EmptyState, Hint, Loading, TableWrap, tableStyles } from "../components/Ui";
import { documentTypeLabel, formatDateTime } from "../lib/format";
import { useAllDocumentIds, useDocumentsByIds, useOffersByIds } from "../lib/hooks";
import { forgetDocumentId } from "../lib/local-store";
import styles from "./DocumentsPage.module.css";

export default function DocumentsPage() {
  const router = useRouter();
  const documentIds = useAllDocumentIds();
  const documentQueries = useDocumentsByIds(documentIds);

  const documents = documentQueries.map((query) => query.data).filter((doc) => doc !== undefined);
  const loading = documentQueries.some((query) => query.isPending);

  // Ids whose fetch 404'd — the local index outlived the row on the server.
  const staleIds = documentIds.filter((_, index) => documentQueries[index]?.isError);

  const offerQueries = useOffersByIds([...new Set(documents.map((doc) => doc.offer_id))]);
  const offersById = new Map(
    offerQueries.map((query) => [query.data?.id, query.data] as const).filter(([id]) => id !== undefined),
  );

  const pending = documents.filter((doc) => doc.status === "pending_review").length;

  return (
    <Page
      title="Documents"
      subtitle={`${documents.length} draft${documents.length === 1 ? "" : "s"}, ${pending} awaiting approval`}
    >
      <Hint>
        The backend has no “list documents” endpoint — a document is only reachable at{" "}
        <code>GET /documents/{"{id}"}</code>. This page enumerates the drafts generated in this browser plus any
        attached to an application.
      </Hint>

      {staleIds.length > 0 ? (
        <div className={styles.staleRow}>
          {staleIds.length} remembered document{staleIds.length === 1 ? "" : "s"} could not be loaded.{" "}
          <button
            type="button"
            className="btn"
            onClick={() => staleIds.forEach((id) => forgetDocumentId(id))}
          >
            Forget them
          </button>
        </div>
      ) : null}

      {loading && documents.length === 0 ? (
        <Loading what="documents" />
      ) : documents.length === 0 ? (
        <TableWrap>
          <EmptyState title="No drafts yet">
            Open an offer and generate a tailored CV or cover letter — it will show up here for review.
          </EmptyState>
        </TableWrap>
      ) : (
        <TableWrap>
          <table className={tableStyles.table}>
            <thead>
              <tr>
                <th>Role</th>
                <th>Type</th>
                <th>Status</th>
                <th>Generated</th>
                <th>File</th>
              </tr>
            </thead>
            <tbody>
              {documents.map((doc) => {
                const offer = offersById.get(doc.offer_id);
                return (
                  <tr
                    key={doc.id}
                    className={tableStyles.rowClickable}
                    onClick={() => router.push(`/documents/${doc.id}`)}
                    tabIndex={0}
                    role="link"
                    onKeyDown={(event) => {
                      if (event.key === "Enter") router.push(`/documents/${doc.id}`);
                    }}
                  >
                    <td>
                      <div className={styles.roleCell}>
                        <span className={tableStyles.primaryCell}>{offer?.title ?? "…"}</span>
                        <span className={styles.company}>{offer?.company ?? doc.offer_id.slice(0, 8)}</span>
                      </div>
                    </td>
                    <td>
                      <Tag>{documentTypeLabel(doc.doc_type)}</Tag>
                    </td>
                    <td>
                      <DocumentStatusPill status={doc.status} />
                    </td>
                    <td className={tableStyles.numericCell}>{formatDateTime(doc.created_at)}</td>
                    <td className={tableStyles.numericCell}>{doc.file_path ? "rendered" : "—"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </TableWrap>
      )}
    </Page>
  );
}
