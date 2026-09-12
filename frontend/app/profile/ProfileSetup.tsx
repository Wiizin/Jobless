"use client";

import { useRef, useState } from "react";

import { Section } from "../components/Ui";
import { useCreateProfile, useImportCv } from "../lib/hooks";
import type { ProfileIn } from "../lib/types";
import styles from "./ProfilePage.module.css";

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/**
 * First-run state.
 *
 * The backend has no "list profiles" endpoint — a profile is only reachable
 * at GET /profile/{id} — so the id has to come from creating one, importing a
 * CV, or being pasted in by hand.
 */
export function ProfileSetup({ onReady }: { onReady: (profileId: string) => void }) {
  return (
    <div className={styles.setupGrid}>
      <CreateProfileCard onReady={onReady} />
      <ImportCvCard onReady={onReady} />
      <ExistingIdCard onReady={onReady} />
    </div>
  );
}

function CreateProfileCard({ onReady }: { onReady: (profileId: string) => void }) {
  const createProfile = useCreateProfile();
  const [form, setForm] = useState<ProfileIn>({ full_name: "", email: "", location: "" });

  const set = (field: keyof ProfileIn) => (event: React.ChangeEvent<HTMLInputElement>) =>
    setForm((previous) => ({ ...previous, [field]: event.target.value }));

  return (
    <Section title="Start from scratch">
      <form
        className={styles.setupBody}
        onSubmit={(event) => {
          event.preventDefault();
          createProfile.mutate(form, { onSuccess: (profile) => onReady(profile.id) });
        }}
      >
        <p className={styles.setupLead}>Create an empty profile and fill in experience as you go.</p>
        <div className="field">
          <label className="label" htmlFor="new-name">
            Full name
          </label>
          <input id="new-name" className="input" value={form.full_name} onChange={set("full_name")} required />
        </div>
        <div className="field">
          <label className="label" htmlFor="new-email">
            Email
          </label>
          <input
            id="new-email"
            type="email"
            className="input"
            value={form.email}
            onChange={set("email")}
            required
          />
        </div>
        <div className="field">
          <label className="label" htmlFor="new-location">
            Location
          </label>
          <input id="new-location" className="input" value={form.location ?? ""} onChange={set("location")} />
        </div>
        <button type="submit" className="btn btn-primary" disabled={createProfile.isPending}>
          {createProfile.isPending ? "Creating…" : "Create profile"}
        </button>
        {createProfile.isError ? (
          <div className={styles.formError}>{(createProfile.error as Error).message}</div>
        ) : null}
      </form>
    </Section>
  );
}

function ImportCvCard({ onReady }: { onReady: (profileId: string) => void }) {
  const importCv = useImportCv();
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);

  return (
    <Section title="Import a CV">
      <div className={styles.setupBody}>
        <p className={styles.setupLead}>
          Upload a .pdf, .docx, .tex or .txt — the backend parses it into experiences, skills, education and
          certifications in one shot.
        </p>
        <div className={styles.uploadRow}>
          <input
            ref={inputRef}
            type="file"
            accept=".pdf,.docx,.tex,.txt"
            style={{ display: "none" }}
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
          />
          <button type="button" className="btn" onClick={() => inputRef.current?.click()}>
            Choose file
          </button>
          <span className={styles.formNote}>{file ? file.name : "No file chosen"}</span>
        </div>
        <button
          type="button"
          className="btn btn-primary"
          disabled={!file || importCv.isPending}
          onClick={() =>
            file && importCv.mutate({ file }, { onSuccess: (profile) => onReady(profile.id) })
          }
        >
          {importCv.isPending ? "Parsing…" : "Import CV"}
        </button>
        {importCv.isError ? <div className={styles.formError}>{(importCv.error as Error).message}</div> : null}
      </div>
    </Section>
  );
}

function ExistingIdCard({ onReady }: { onReady: (profileId: string) => void }) {
  const [value, setValue] = useState("");
  const valid = UUID_RE.test(value.trim());

  return (
    <Section title="Use an existing profile">
      <form
        className={styles.setupBody}
        onSubmit={(event) => {
          event.preventDefault();
          if (valid) onReady(value.trim());
        }}
      >
        <p className={styles.setupLead}>
          Already created a profile (another browser, or via the API)? Paste its UUID to point this browser at it.
        </p>
        <div className="field">
          <label className="label" htmlFor="existing-id">
            Profile ID
          </label>
          <input
            id="existing-id"
            className="input"
            value={value}
            onChange={(event) => setValue(event.target.value)}
            placeholder="00000000-0000-0000-0000-000000000000"
          />
        </div>
        <button type="submit" className="btn" disabled={!valid}>
          Use this profile
        </button>
      </form>
    </Section>
  );
}
