"use client";

import { useState } from "react";

import { useAddManualOffer } from "../lib/hooks";
import type { ManualOfferIn } from "../lib/types";
import { Hint, Modal, layoutStyles } from "../components/Ui";
import styles from "./OffersPage.module.css";

const EMPTY: ManualOfferIn = {
  title: "",
  company: "",
  location: "",
  contract_type: "",
  description: "",
  url: "",
};

/**
 * Hand-pasted posting entry. The backend stores this exactly like an
 * API-sourced offer (status=new) — nothing is submitted anywhere.
 */
export function AddPostingModal({
  profileId,
  onClose,
  onCreated,
}: {
  profileId: string | null;
  onClose: () => void;
  onCreated: (offerId: string) => void;
}) {
  const [form, setForm] = useState<ManualOfferIn>(EMPTY);
  const addOffer = useAddManualOffer(profileId);

  const set = (field: keyof ManualOfferIn) => (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
    setForm((previous) => ({ ...previous, [field]: event.target.value }));

  const complete =
    form.title.trim() !== "" &&
    form.company.trim() !== "" &&
    form.description.trim() !== "" &&
    form.url.trim() !== "";

  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    if (!complete) return;
    addOffer.mutate(form, { onSuccess: (offer) => onCreated(offer.id) });
  };

  return (
    <Modal
      title="Add posting"
      onClose={onClose}
      footer={
        <>
          <button type="button" className="btn" onClick={onClose}>
            Cancel
          </button>
          <button
            type="submit"
            form="add-posting-form"
            className="btn btn-primary"
            disabled={!complete || addOffer.isPending}
          >
            {addOffer.isPending ? "Saving…" : "Save posting"}
          </button>
        </>
      }
    >
      <form id="add-posting-form" onSubmit={submit} style={{ display: "grid", gap: 13 }}>
        {!profileId ? (
          <Hint>
            No profile is selected, so this posting will be stored <strong>unscored</strong> — and the offers list
            only shows scored postings, so it won’t appear there yet. Set up a profile first to have it scored on
            save.
          </Hint>
        ) : null}

        <div className={layoutStyles.formRow}>
          <div className="field">
            <label className="label" htmlFor="posting-title">
              Role title
            </label>
            <input
              id="posting-title"
              className="input"
              value={form.title}
              onChange={set("title")}
              placeholder="Backend Engineering Intern"
              required
            />
          </div>
          <div className="field">
            <label className="label" htmlFor="posting-company">
              Company
            </label>
            <input
              id="posting-company"
              className="input"
              value={form.company}
              onChange={set("company")}
              placeholder="Acme"
              required
            />
          </div>
        </div>

        <div className={layoutStyles.formRow}>
          <div className="field">
            <label className="label" htmlFor="posting-location">
              Location
            </label>
            <input
              id="posting-location"
              className="input"
              value={form.location}
              onChange={set("location")}
              placeholder="Remote — EU"
            />
          </div>
          <div className="field">
            <label className="label" htmlFor="posting-contract">
              Contract type
            </label>
            <input
              id="posting-contract"
              className="input"
              value={form.contract_type}
              onChange={set("contract_type")}
              placeholder="internship"
            />
          </div>
        </div>

        <div className="field">
          <label className="label" htmlFor="posting-url">
            URL
          </label>
          <input
            id="posting-url"
            className="input"
            value={form.url}
            onChange={set("url")}
            placeholder="https://…"
            required
          />
          <span className={styles.formNote}>
            Also used as the dedup key — re-adding the same URL is rejected as a duplicate.
          </span>
        </div>

        <div className="field">
          <label className="label" htmlFor="posting-description">
            Posting text
          </label>
          <textarea
            id="posting-description"
            className="textarea"
            style={{ minHeight: 150 }}
            value={form.description}
            onChange={set("description")}
            placeholder="Paste the full job description…"
            required
          />
        </div>

        {addOffer.isError ? <div className={styles.formError}>{(addOffer.error as Error).message}</div> : null}
      </form>
    </Modal>
  );
}
