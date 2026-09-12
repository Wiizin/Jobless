"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";

import { OfferStatusPill, ScorePill, Tag } from "../../components/Pill";
import { Page } from "../../components/Shell";
import { ErrorNote, Hint, Loading, Section, layoutStyles } from "../../components/Ui";
import { formatDate, formatDateTime } from "../../lib/format";
import { useDismissOffer, useGenerateDocument, useOffer } from "../../lib/hooks";
import { useActiveProfileId } from "../../lib/local-store";
import type { DocumentType } from "../../lib/types";
import styles from "./OfferDetail.module.css";

export default function OfferDetailPage() {
  const params = useParams<{ id: string }>();
  const offerId = params.id;
  const router = useRouter();
  const { profileId, ready } = useActiveProfileId();

  const { data: offer, isPending, isError, error } = useOffer(offerId);
  const generate = useGenerateDocument(profileId);
  const dismiss = useDismissOffer();

  const runGenerate = (docType: DocumentType) => {
    if (!profileId) return;
    generate.mutate(
      { offer_id: offerId, doc_type: docType },
      { onSuccess: (document) => router.push(`/documents/${document.id}`) },
    );
  };

  if (isError) {
    return (
      <Page title="Offer" action={<BackLink />}>
        <ErrorNote error={error} what="load this offer" />
      </Page>
    );
  }

  if (isPending || !offer) {
    return (
      <Page title="Offer" action={<BackLink />}>
        <Loading what="offer" />
      </Page>
    );
  }

  return (
    <Page
      title={offer.title}
      subtitle={`${offer.company}${offer.location ? ` · ${offer.location}` : ""}`}
      action={<BackLink />}
    >
      <Section>
        <div className={styles.headline}>
          <div className={styles.headlineMain}>
            <h2 className={styles.role}>{offer.title}</h2>
            <div className={styles.company}>
              {offer.company}
              {offer.location ? ` · ${offer.location}` : ""}
              {offer.contract_type ? ` · ${offer.contract_type}` : ""}
            </div>
          </div>
          <div className={styles.headlineSide}>
            <ScorePill score={offer.match_score} />
            <OfferStatusPill status={offer.status} />
          </div>
        </div>

        <div className={styles.actions}>
          <button
            type="button"
            className="btn btn-primary"
            disabled={!profileId || generate.isPending}
            onClick={() => runGenerate("cv")}
          >
            {generate.isPending && generate.variables?.doc_type === "cv"
              ? "Generating…"
              : "Generate tailored CV →"}
          </button>
          <button
            type="button"
            className="btn"
            disabled={!profileId || generate.isPending}
            onClick={() => runGenerate("cover_letter")}
          >
            {generate.isPending && generate.variables?.doc_type === "cover_letter"
              ? "Generating…"
              : "Generate cover letter"}
          </button>
          <a className="btn" href={offer.url} target="_blank" rel="noopener noreferrer">
            Open posting ↗
          </a>
          <button
            type="button"
            className="btn"
            disabled={offer.status === "dismissed" || dismiss.isPending}
            onClick={() => dismiss.mutate(offerId)}
          >
            {offer.status === "dismissed" ? "Dismissed" : dismiss.isPending ? "Dismissing…" : "Dismiss"}
          </button>
        </div>

        {ready && !profileId ? (
          <div className={styles.errorRow}>
            <Hint>
              Generation needs a profile — the backend takes <code>profile_id</code> on the generate call.{" "}
              <Link href="/profile">Set one up →</Link>
            </Hint>
          </div>
        ) : null}

        {generate.isError ? (
          <div className={styles.errorRow}>
            <ErrorNote error={generate.error} what="generate a document" />
          </div>
        ) : null}
        {dismiss.isError ? (
          <div className={styles.errorRow}>
            <ErrorNote error={dismiss.error} what="dismiss this offer" />
          </div>
        ) : null}

        <div className={styles.meta} style={{ marginTop: 16 }}>
          <div>
            <div className={styles.metaLabel}>Source</div>
            <div className={styles.metaValue}>{offer.source}</div>
          </div>
          <div>
            <div className={styles.metaLabel}>Posted</div>
            <div className={styles.metaValue}>{formatDate(offer.posted_date)}</div>
          </div>
          <div>
            <div className={styles.metaLabel}>Collected</div>
            <div className={styles.metaValue}>{formatDateTime(offer.created_at)}</div>
          </div>
          <div>
            <div className={styles.metaLabel}>External ID</div>
            <div className={styles.metaValue}>{offer.external_id || "—"}</div>
          </div>
        </div>
      </Section>

      <div className={styles.columns}>
        <Section title="Full posting">
          <div className={layoutStyles.posting}>{offer.description}</div>
        </Section>

        <div>
          <Section title="Why this scored the way it did">
            {offer.match_reasoning ? (
              <p className={layoutStyles.prose}>{offer.match_reasoning}</p>
            ) : (
              <p className={styles.emptyNote}>No reasoning recorded — this offer hasn’t been scored yet.</p>
            )}
          </Section>

          <Section title="Missing skills">
            {offer.missing_skills.length > 0 ? (
              <div className={layoutStyles.tagRow}>
                {offer.missing_skills.map((skill) => (
                  <Tag key={skill} tone="warn">
                    {skill}
                  </Tag>
                ))}
              </div>
            ) : (
              <p className={styles.emptyNote}>
                Nothing flagged — the posting’s requirements are all covered by your profile.
              </p>
            )}
          </Section>

          <Section title="Dealbreakers">
            {offer.dealbreakers.length > 0 ? (
              <div className={layoutStyles.tagRow}>
                {offer.dealbreakers.map((item) => (
                  <Tag key={item} tone="bad">
                    {item}
                  </Tag>
                ))}
              </div>
            ) : (
              <p className={styles.emptyNote}>No dealbreakers found.</p>
            )}
          </Section>
        </div>
      </div>
    </Page>
  );
}

function BackLink() {
  return (
    <Link href="/offers" className="btn">
      ← All offers
    </Link>
  );
}
