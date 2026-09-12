"use client";

import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

import { OfferStatusPill, ScorePill } from "../components/Pill";
import {
  Chip,
  ChipRow,
  EmptyState,
  ErrorNote,
  Loading,
  StatTile,
  StatTiles,
  TableWrap,
  tableStyles,
} from "../components/Ui";
import { Page } from "../components/Shell";
import { formatDate, isToday, scoreTone } from "../lib/format";
import { useAllDocumentIds, useDocumentsByIds, useOffers } from "../lib/hooks";
import { useActiveProfileId } from "../lib/local-store";
import type { ListOffersParams } from "../lib/types";
import { AddPostingModal } from "./AddPostingModal";
import styles from "./OffersPage.module.css";

type StatusFilter = "all" | "open" | "dismissed";

export default function OffersDashboard() {
  const router = useRouter();
  const { profileId } = useActiveProfileId();

  const [statusFilter, setStatusFilter] = useState<StatusFilter>("open");
  const [highScoreOnly, setHighScoreOnly] = useState(false);
  const [addOpen, setAddOpen] = useState(false);

  // "Open" has no single status value on the backend (new/scored/reviewed are
  // all open), so only "dismissed" maps to a query param; "open" is filtered
  // out of the response below.
  const params: ListOffersParams = useMemo(
    () => ({
      limit: 200,
      ...(highScoreOnly ? { min_score: 80 } : {}),
      ...(statusFilter === "dismissed" ? { status: "dismissed" as const } : {}),
    }),
    [highScoreOnly, statusFilter],
  );

  const { data, isPending, isError, error } = useOffers(params);

  const offers = useMemo(() => {
    if (!data) return [];
    return statusFilter === "open" ? data.filter((offer) => offer.status !== "dismissed") : data;
  }, [data, statusFilter]);

  // Stat tiles are computed from the fetched list — no extra endpoint.
  const stats = useMemo(() => {
    const scores = offers.map((offer) => offer.match_score).filter((s): s is number => s !== null);
    return {
      newToday: offers.filter((offer) => isToday(offer.created_at)).length,
      avgScore: scores.length ? Math.round(scores.reduce((a, b) => a + b, 0) / scores.length) : null,
      strong: offers.filter((offer) => (offer.match_score ?? 0) >= 80).length,
    };
  }, [offers]);

  const documentIds = useAllDocumentIds();
  const documentQueries = useDocumentsByIds(documentIds);
  const draftsPending = documentQueries.filter((query) => query.data?.status === "pending_review").length;

  return (
    <Page
      title="Offers"
      subtitle="Scored postings awaiting your review. Nothing is generated or sent without you."
      action={
        <button type="button" className="btn btn-primary" onClick={() => setAddOpen(true)}>
          ＋ Add posting
        </button>
      }
    >
      <StatTiles>
        <StatTile label="New today" value={stats.newToday} tone="accent" hint="Collected in the last day" />
        <StatTile
          label="Average score"
          value={stats.avgScore ?? "—"}
          tone={scoreTone(stats.avgScore)}
          hint={`Across ${offers.length} shown`}
        />
        <StatTile label="Score ≥ 80" value={stats.strong} tone="good" hint="Strong matches" />
        <StatTile
          label="Drafts pending"
          value={draftsPending}
          tone={draftsPending > 0 ? "warn" : "neutral"}
          hint="Generated, not yet approved"
        />
      </StatTiles>

      <ChipRow>
        <Chip active={statusFilter === "all"} onClick={() => setStatusFilter("all")}>
          All
        </Chip>
        <Chip active={statusFilter === "open"} onClick={() => setStatusFilter("open")}>
          Open
        </Chip>
        <Chip active={statusFilter === "dismissed"} onClick={() => setStatusFilter("dismissed")}>
          Dismissed
        </Chip>
        <span className={styles.chipDivider} aria-hidden="true" />
        <Chip active={highScoreOnly} onClick={() => setHighScoreOnly((value) => !value)}>
          Score ≥ 80
        </Chip>
      </ChipRow>

      {isError ? (
        <ErrorNote error={error} what="load offers" />
      ) : isPending ? (
        <Loading what="offers" />
      ) : offers.length === 0 ? (
        <TableWrap>
          <EmptyState title="No offers here yet">
            The backend only lists postings that have already been scored. Add one by hand, or let the collector
            run.
          </EmptyState>
        </TableWrap>
      ) : (
        <TableWrap>
          <table className={tableStyles.table}>
            <thead>
              <tr>
                <th>Role</th>
                <th>Score</th>
                <th>Source</th>
                <th>Posted</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {offers.map((offer) => (
                <tr
                  key={offer.id}
                  className={tableStyles.rowClickable}
                  onClick={() => router.push(`/offers/${offer.id}`)}
                  tabIndex={0}
                  role="link"
                  onKeyDown={(event) => {
                    if (event.key === "Enter") router.push(`/offers/${offer.id}`);
                  }}
                >
                  <td>
                    <div className={styles.roleCell}>
                      <span className={tableStyles.primaryCell}>{offer.title}</span>
                      <span className={styles.company}>
                        {offer.company}
                        {offer.location ? ` · ${offer.location}` : ""}
                      </span>
                    </div>
                  </td>
                  <td>
                    <ScorePill score={offer.match_score} />
                  </td>
                  <td className={styles.sourceCell}>{offer.source}</td>
                  <td className={tableStyles.numericCell}>{formatDate(offer.posted_date)}</td>
                  <td>
                    <OfferStatusPill status={offer.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableWrap>
      )}

      {addOpen ? (
        <AddPostingModal
          profileId={profileId}
          onClose={() => setAddOpen(false)}
          onCreated={(offerId) => {
            setAddOpen(false);
            router.push(`/offers/${offerId}`);
          }}
        />
      ) : null}
    </Page>
  );
}
