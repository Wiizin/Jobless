"use client";

import { useEffect, useRef, useState } from "react";

import { Tag } from "../components/Pill";
import { Page } from "../components/Shell";
import { ErrorNote, Hint, Loading, Section, layoutStyles } from "../components/Ui";
import { formatDate } from "../lib/format";
import { useImportCv, useProfile, useSearchProfiles, useUpdateProfile } from "../lib/hooks";
import { useActiveProfileId } from "../lib/local-store";
import type { ProfileIn, ProfileOut } from "../lib/types";
import {
  AddCertificationModal,
  AddEducationModal,
  AddExperienceModal,
  AddSearchProfileModal,
  AddSkillModal,
} from "./AddItemModals";
import { ProfileSetup } from "./ProfileSetup";
import styles from "./ProfilePage.module.css";

type ModalKind = "experience" | "skill" | "education" | "certification" | "search-profile" | null;

function initials(fullName: string): string {
  const parts = fullName.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "—";
  return (parts[0][0] + (parts.length > 1 ? parts[parts.length - 1][0] : "")).toUpperCase();
}

export default function ProfilePage() {
  const { profileId, setProfileId, ready } = useActiveProfileId();
  const { data: profile, isPending, isError, error } = useProfile(profileId);
  const [modal, setModal] = useState<ModalKind>(null);

  if (!ready) {
    return (
      <Page title="Profile">
        <Loading what="profile" />
      </Page>
    );
  }

  if (!profileId) {
    return (
      <Page title="Profile" subtitle="Everything generation draws on lives here.">
        <div style={{ marginBottom: 16 }}>
          <Hint>
            No profile is selected in this browser yet. The API has no “list profiles” endpoint, so pick one of the
            three routes below — the id is then remembered locally.
          </Hint>
        </div>
        <ProfileSetup onReady={setProfileId} />
      </Page>
    );
  }

  if (isError) {
    return (
      <Page
        title="Profile"
        action={
          <button type="button" className="btn" onClick={() => setProfileId(null)}>
            Switch profile
          </button>
        }
      >
        <ErrorNote error={error} what="load this profile" />
        <div style={{ marginTop: 14 }}>
          <Hint>
            The remembered id <code>{profileId}</code> didn’t resolve. Switch profile to start over.
          </Hint>
        </div>
      </Page>
    );
  }

  if (isPending || !profile) {
    return (
      <Page title="Profile">
        <Loading what="profile" />
      </Page>
    );
  }

  return (
    <Page
      title="Profile"
      subtitle="The single source of truth generation is allowed to draw on."
      action={
        <button type="button" className="btn" onClick={() => setProfileId(null)}>
          Switch profile
        </button>
      }
    >
      <IdentitySection profile={profile} profileId={profileId} />

      <Section
        title={`Experience (${profile.experiences.length})`}
        action={
          <button type="button" className="btn" onClick={() => setModal("experience")}>
            ＋ Add
          </button>
        }
      >
        {profile.experiences.length === 0 ? (
          <p className={styles.emptyNote}>No experience recorded — generation has nothing to select from yet.</p>
        ) : (
          <div className={styles.itemList}>
            {profile.experiences.map((experience) => (
              <div key={experience.id} className={styles.item}>
                <div className={styles.itemTitle}>
                  {experience.title} · {experience.company}
                </div>
                <div className={styles.itemMeta}>
                  {formatDate(experience.start_date)} →{" "}
                  {experience.is_current ? "present" : formatDate(experience.end_date)}
                  {experience.location ? ` · ${experience.location}` : ""}
                </div>
                {experience.description ? <div className={styles.itemBody}>{experience.description}</div> : null}
                {experience.bullets && experience.bullets.length > 0 ? (
                  <ul className={styles.bullets}>
                    {experience.bullets.map((bullet, index) => (
                      <li key={index}>{bullet}</li>
                    ))}
                  </ul>
                ) : null}
              </div>
            ))}
          </div>
        )}
      </Section>

      <Section
        title={`Skills (${profile.skills.length})`}
        action={
          <button type="button" className="btn" onClick={() => setModal("skill")}>
            ＋ Add
          </button>
        }
      >
        {profile.skills.length === 0 ? (
          <p className={styles.emptyNote}>No skills recorded.</p>
        ) : (
          <div className={layoutStyles.tagRow}>
            {profile.skills.map((skill) => (
              <Tag key={skill.id} tone={skill.proficiency === "expert" ? "good" : "neutral"}>
                {skill.name}
                {skill.proficiency ? ` · ${skill.proficiency}` : ""}
              </Tag>
            ))}
          </div>
        )}
      </Section>

      <Section
        title={`Education (${profile.education.length})`}
        action={
          <button type="button" className="btn" onClick={() => setModal("education")}>
            ＋ Add
          </button>
        }
      >
        {profile.education.length === 0 ? (
          <p className={styles.emptyNote}>No education recorded.</p>
        ) : (
          <div className={styles.itemList}>
            {profile.education.map((education) => (
              <div key={education.id} className={styles.item}>
                <div className={styles.itemTitle}>
                  {education.degree ? `${education.degree} · ` : ""}
                  {education.institution}
                </div>
                <div className={styles.itemMeta}>
                  {education.field_of_study ? `${education.field_of_study} · ` : ""}
                  {formatDate(education.start_date)} → {formatDate(education.end_date)}
                </div>
                {education.description ? <div className={styles.itemBody}>{education.description}</div> : null}
              </div>
            ))}
          </div>
        )}
      </Section>

      <Section
        title={`Certifications (${profile.certifications.length})`}
        action={
          <button type="button" className="btn" onClick={() => setModal("certification")}>
            ＋ Add
          </button>
        }
      >
        {profile.certifications.length === 0 ? (
          <p className={styles.emptyNote}>No certifications recorded.</p>
        ) : (
          <div className={styles.itemList}>
            {profile.certifications.map((certification) => (
              <div key={certification.id} className={styles.item}>
                <div className={styles.itemTitle}>{certification.name}</div>
                <div className={styles.itemMeta}>
                  {certification.issuer ? `${certification.issuer} · ` : ""}
                  issued {formatDate(certification.issued_date)}
                  {certification.expiry_date ? ` · expires ${formatDate(certification.expiry_date)}` : ""}
                </div>
                {certification.credential_url ? (
                  <div className={styles.itemBody}>
                    <a href={certification.credential_url} target="_blank" rel="noopener noreferrer">
                      Credential ↗
                    </a>
                  </div>
                ) : null}
              </div>
            ))}
          </div>
        )}
      </Section>

      <SearchProfilesSection profileId={profileId} onAdd={() => setModal("search-profile")} />

      <ReimportSection profileId={profileId} />

      {modal === "experience" ? (
        <AddExperienceModal profileId={profileId} onClose={() => setModal(null)} />
      ) : null}
      {modal === "skill" ? <AddSkillModal profileId={profileId} onClose={() => setModal(null)} /> : null}
      {modal === "education" ? <AddEducationModal profileId={profileId} onClose={() => setModal(null)} /> : null}
      {modal === "certification" ? (
        <AddCertificationModal profileId={profileId} onClose={() => setModal(null)} />
      ) : null}
      {modal === "search-profile" ? (
        <AddSearchProfileModal profileId={profileId} onClose={() => setModal(null)} />
      ) : null}
    </Page>
  );
}

/** Editable identity block. PUT replaces every ProfileIn field, so the form
 *  always submits the complete set. */
function IdentitySection({ profile, profileId }: { profile: ProfileOut; profileId: string }) {
  const updateProfile = useUpdateProfile(profileId);
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState<ProfileIn>(toForm(profile));

  useEffect(() => {
    if (!editing) setForm(toForm(profile));
  }, [profile, editing]);

  const set = (field: keyof ProfileIn) => (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
    setForm((previous) => ({ ...previous, [field]: event.target.value }));

  if (!editing) {
    return (
      <Section
        action={
          <button type="button" className="btn" onClick={() => setEditing(true)}>
            Edit
          </button>
        }
      >
        <div className={styles.identity}>
          <span className={styles.avatar}>{initials(profile.full_name)}</span>
          <span className={styles.identityText}>
            <span className={styles.identityName}>{profile.full_name}</span>
            <span className={styles.identityMeta} style={{ display: "block" }}>
              {profile.email}
              {profile.phone ? ` · ${profile.phone}` : ""}
              {profile.location ? ` · ${profile.location}` : ""}
            </span>
          </span>
          <span className={styles.profileId}>{profileId}</span>
        </div>
        {profile.summary ? <p className={layoutStyles.prose}>{profile.summary}</p> : null}
        {Object.keys(profile.links ?? {}).length > 0 ? (
          <div className={layoutStyles.tagRow} style={{ marginTop: 10 }}>
            {Object.entries(profile.links ?? {}).map(([key, value]) => (
              <a key={key} href={value} target="_blank" rel="noopener noreferrer">
                <Tag tone="accent">{key} ↗</Tag>
              </a>
            ))}
          </div>
        ) : null}
      </Section>
    );
  }

  return (
    <Section title="Edit profile">
      <form
        style={{ display: "grid", gap: 13 }}
        onSubmit={(event) => {
          event.preventDefault();
          updateProfile.mutate(form, { onSuccess: () => setEditing(false) });
        }}
      >
        <div className={styles.grid2}>
          <div className="field">
            <label className="label" htmlFor="p-name">
              Full name
            </label>
            <input id="p-name" className="input" value={form.full_name} onChange={set("full_name")} required />
          </div>
          <div className="field">
            <label className="label" htmlFor="p-email">
              Email
            </label>
            <input id="p-email" type="email" className="input" value={form.email} onChange={set("email")} required />
          </div>
        </div>
        <div className={styles.grid2}>
          <div className="field">
            <label className="label" htmlFor="p-phone">
              Phone
            </label>
            <input id="p-phone" className="input" value={form.phone ?? ""} onChange={set("phone")} />
          </div>
          <div className="field">
            <label className="label" htmlFor="p-location">
              Location
            </label>
            <input id="p-location" className="input" value={form.location ?? ""} onChange={set("location")} />
          </div>
        </div>
        <div className="field">
          <label className="label" htmlFor="p-summary">
            Summary
          </label>
          <textarea id="p-summary" className="textarea" value={form.summary ?? ""} onChange={set("summary")} />
        </div>
        <div className={styles.actionRow}>
          <button type="submit" className="btn btn-primary" disabled={updateProfile.isPending}>
            {updateProfile.isPending ? "Saving…" : "Save profile"}
          </button>
          <button type="button" className="btn" onClick={() => setEditing(false)}>
            Cancel
          </button>
        </div>
        {updateProfile.isError ? (
          <div className={styles.formError}>{(updateProfile.error as Error).message}</div>
        ) : null}
      </form>
    </Section>
  );
}

function toForm(profile: ProfileOut): ProfileIn {
  return {
    full_name: profile.full_name,
    email: profile.email,
    phone: profile.phone ?? null,
    location: profile.location ?? null,
    summary: profile.summary ?? null,
    links: profile.links ?? {},
  };
}

function SearchProfilesSection({ profileId, onAdd }: { profileId: string; onAdd: () => void }) {
  const { data: searchProfiles, isPending } = useSearchProfiles(profileId);

  return (
    <Section
      title={`Search profiles (${searchProfiles?.length ?? 0})`}
      action={
        <button type="button" className="btn" onClick={onAdd}>
          ＋ Add
        </button>
      }
    >
      {isPending ? (
        <Loading what="search profiles" />
      ) : !searchProfiles || searchProfiles.length === 0 ? (
        <p className={styles.emptyNote}>
          None yet — these drive what the scheduled collector looks for.
        </p>
      ) : (
        <div className={styles.itemList}>
          {searchProfiles.map((searchProfile) => (
            <div key={searchProfile.id} className={styles.item}>
              <div className={styles.itemTitle}>
                {searchProfile.name}{" "}
                <Tag tone={searchProfile.is_active ? "good" : "neutral"}>
                  {searchProfile.is_active ? "active" : "paused"}
                </Tag>
              </div>
              <div className={styles.itemMeta}>min score {searchProfile.min_score_threshold}</div>
              <div className={layoutStyles.tagRow} style={{ marginTop: 8 }}>
                {(searchProfile.keywords ?? []).map((keyword) => (
                  <Tag key={`k-${keyword}`} tone="accent">
                    {keyword}
                  </Tag>
                ))}
                {(searchProfile.locations ?? []).map((location) => (
                  <Tag key={`l-${location}`}>{location}</Tag>
                ))}
                {(searchProfile.contract_types ?? []).map((contractType) => (
                  <Tag key={`c-${contractType}`}>{contractType}</Tag>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </Section>
  );
}

/** Re-syncing from a CV *replaces* the profile's items wholesale. */
function ReimportSection({ profileId }: { profileId: string }) {
  const importCv = useImportCv();
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [confirming, setConfirming] = useState(false);

  return (
    <Section title="Re-sync from a CV">
      <p className={styles.emptyNote} style={{ marginTop: 0 }}>
        Uploading here <strong>replaces</strong> this profile’s experiences, skills, education and certifications
        with whatever the CV contains. Existing items are not merged.
      </p>
      <div className={styles.uploadRow} style={{ marginTop: 12 }}>
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.docx,.tex,.txt"
          style={{ display: "none" }}
          onChange={(event) => {
            setFile(event.target.files?.[0] ?? null);
            setConfirming(false);
          }}
        />
        <button type="button" className="btn" onClick={() => inputRef.current?.click()}>
          Choose file
        </button>
        <span className={styles.formNote}>{file ? file.name : "No file chosen"}</span>
        {file && !confirming ? (
          <button type="button" className="btn" onClick={() => setConfirming(true)}>
            Re-sync…
          </button>
        ) : null}
        {file && confirming ? (
          <>
            <button
              type="button"
              className="btn btn-primary"
              disabled={importCv.isPending}
              onClick={() =>
                importCv.mutate(
                  { file, profileId },
                  {
                    onSuccess: () => {
                      setFile(null);
                      setConfirming(false);
                    },
                  },
                )
              }
            >
              {importCv.isPending ? "Parsing…" : "Yes, replace everything"}
            </button>
            <button type="button" className="btn" onClick={() => setConfirming(false)}>
              Cancel
            </button>
          </>
        ) : null}
      </div>
      {importCv.isError ? (
        <div className={styles.formError} style={{ marginTop: 10 }}>
          {(importCv.error as Error).message}
        </div>
      ) : null}
    </Section>
  );
}
