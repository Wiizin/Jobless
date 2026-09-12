"use client";

import { useState } from "react";

import { Modal, layoutStyles } from "../components/Ui";
import {
  useAddCertification,
  useAddEducation,
  useAddExperience,
  useAddSkill,
  useCreateSearchProfile,
} from "../lib/hooks";
import styles from "./ProfilePage.module.css";

/** Splits a comma-separated input into a trimmed, non-empty list. */
function splitList(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function ModalShell({
  title,
  onClose,
  onSubmit,
  pending,
  error,
  children,
}: {
  title: string;
  onClose: () => void;
  onSubmit: () => void;
  pending: boolean;
  error: unknown;
  children: React.ReactNode;
}) {
  return (
    <Modal
      title={title}
      onClose={onClose}
      footer={
        <>
          <button type="button" className="btn" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" form="add-item-form" className="btn btn-primary" disabled={pending}>
            {pending ? "Saving…" : "Save"}
          </button>
        </>
      }
    >
      <form
        id="add-item-form"
        style={{ display: "grid", gap: 13 }}
        onSubmit={(event) => {
          event.preventDefault();
          onSubmit();
        }}
      >
        {children}
        {error ? <div className={styles.formError}>{(error as Error).message}</div> : null}
      </form>
    </Modal>
  );
}

export function AddExperienceModal({
  profileId,
  onClose,
}: {
  profileId: string;
  onClose: () => void;
}) {
  const addExperience = useAddExperience(profileId);
  const [title, setTitle] = useState("");
  const [company, setCompany] = useState("");
  const [location, setLocation] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [isCurrent, setIsCurrent] = useState(false);
  const [description, setDescription] = useState("");
  const [bullets, setBullets] = useState("");

  return (
    <ModalShell
      title="Add experience"
      onClose={onClose}
      pending={addExperience.isPending}
      error={addExperience.isError ? addExperience.error : null}
      onSubmit={() =>
        addExperience.mutate(
          {
            title,
            company,
            location: location || null,
            start_date: startDate || null,
            end_date: isCurrent ? null : endDate || null,
            is_current: isCurrent,
            description: description || null,
            // One bullet per line — these are the raw achievements generation
            // draws on, so they are never invented on top of.
            bullets: bullets.split("\n").map((b) => b.trim()).filter(Boolean),
          },
          { onSuccess: onClose },
        )
      }
    >
      <div className={layoutStyles.formRow}>
        <div className="field">
          <label className="label" htmlFor="exp-title">
            Title
          </label>
          <input id="exp-title" className="input" value={title} onChange={(e) => setTitle(e.target.value)} required />
        </div>
        <div className="field">
          <label className="label" htmlFor="exp-company">
            Company
          </label>
          <input
            id="exp-company"
            className="input"
            value={company}
            onChange={(e) => setCompany(e.target.value)}
            required
          />
        </div>
      </div>
      <div className="field">
        <label className="label" htmlFor="exp-location">
          Location
        </label>
        <input id="exp-location" className="input" value={location} onChange={(e) => setLocation(e.target.value)} />
      </div>
      <div className={layoutStyles.formRow}>
        <div className="field">
          <label className="label" htmlFor="exp-start">
            Start date
          </label>
          <input
            id="exp-start"
            type="date"
            className="input"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
          />
        </div>
        <div className="field">
          <label className="label" htmlFor="exp-end">
            End date
          </label>
          <input
            id="exp-end"
            type="date"
            className="input"
            value={endDate}
            disabled={isCurrent}
            onChange={(e) => setEndDate(e.target.value)}
          />
        </div>
      </div>
      <label className={styles.formNote} style={{ display: "flex", gap: 8, alignItems: "center" }}>
        <input type="checkbox" checked={isCurrent} onChange={(e) => setIsCurrent(e.target.checked)} />
        This is my current role
      </label>
      <div className="field">
        <label className="label" htmlFor="exp-description">
          Description
        </label>
        <textarea
          id="exp-description"
          className="textarea"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
      </div>
      <div className="field">
        <label className="label" htmlFor="exp-bullets">
          Achievement bullets
        </label>
        <textarea
          id="exp-bullets"
          className="textarea"
          value={bullets}
          onChange={(e) => setBullets(e.target.value)}
          placeholder="One per line"
        />
        <span className={styles.formNote}>One per line. Generation only rephrases these — it never invents new ones.</span>
      </div>
    </ModalShell>
  );
}

export function AddSkillModal({ profileId, onClose }: { profileId: string; onClose: () => void }) {
  const addSkill = useAddSkill(profileId);
  const [name, setName] = useState("");
  const [category, setCategory] = useState("");
  const [proficiency, setProficiency] = useState("");

  return (
    <ModalShell
      title="Add skill"
      onClose={onClose}
      pending={addSkill.isPending}
      error={addSkill.isError ? addSkill.error : null}
      onSubmit={() =>
        addSkill.mutate(
          { name, category: category || null, proficiency: proficiency || null },
          { onSuccess: onClose },
        )
      }
    >
      <div className="field">
        <label className="label" htmlFor="skill-name">
          Skill
        </label>
        <input id="skill-name" className="input" value={name} onChange={(e) => setName(e.target.value)} required />
      </div>
      <div className={layoutStyles.formRow}>
        <div className="field">
          <label className="label" htmlFor="skill-category">
            Category
          </label>
          <input
            id="skill-category"
            className="input"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            placeholder="language / framework / tool"
          />
        </div>
        <div className="field">
          <label className="label" htmlFor="skill-proficiency">
            Proficiency
          </label>
          <select
            id="skill-proficiency"
            className="select"
            value={proficiency}
            onChange={(e) => setProficiency(e.target.value)}
          >
            <option value="">—</option>
            <option value="beginner">Beginner</option>
            <option value="intermediate">Intermediate</option>
            <option value="expert">Expert</option>
          </select>
        </div>
      </div>
    </ModalShell>
  );
}

export function AddEducationModal({ profileId, onClose }: { profileId: string; onClose: () => void }) {
  const addEducation = useAddEducation(profileId);
  const [institution, setInstitution] = useState("");
  const [degree, setDegree] = useState("");
  const [fieldOfStudy, setFieldOfStudy] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [description, setDescription] = useState("");

  return (
    <ModalShell
      title="Add education"
      onClose={onClose}
      pending={addEducation.isPending}
      error={addEducation.isError ? addEducation.error : null}
      onSubmit={() =>
        addEducation.mutate(
          {
            institution,
            degree: degree || null,
            field_of_study: fieldOfStudy || null,
            start_date: startDate || null,
            end_date: endDate || null,
            description: description || null,
          },
          { onSuccess: onClose },
        )
      }
    >
      <div className="field">
        <label className="label" htmlFor="edu-institution">
          Institution
        </label>
        <input
          id="edu-institution"
          className="input"
          value={institution}
          onChange={(e) => setInstitution(e.target.value)}
          required
        />
      </div>
      <div className={layoutStyles.formRow}>
        <div className="field">
          <label className="label" htmlFor="edu-degree">
            Degree
          </label>
          <input id="edu-degree" className="input" value={degree} onChange={(e) => setDegree(e.target.value)} />
        </div>
        <div className="field">
          <label className="label" htmlFor="edu-field">
            Field of study
          </label>
          <input
            id="edu-field"
            className="input"
            value={fieldOfStudy}
            onChange={(e) => setFieldOfStudy(e.target.value)}
          />
        </div>
      </div>
      <div className={layoutStyles.formRow}>
        <div className="field">
          <label className="label" htmlFor="edu-start">
            Start date
          </label>
          <input
            id="edu-start"
            type="date"
            className="input"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
          />
        </div>
        <div className="field">
          <label className="label" htmlFor="edu-end">
            End date
          </label>
          <input
            id="edu-end"
            type="date"
            className="input"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
          />
        </div>
      </div>
      <div className="field">
        <label className="label" htmlFor="edu-description">
          Description
        </label>
        <textarea
          id="edu-description"
          className="textarea"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
      </div>
    </ModalShell>
  );
}

export function AddCertificationModal({ profileId, onClose }: { profileId: string; onClose: () => void }) {
  const addCertification = useAddCertification(profileId);
  const [name, setName] = useState("");
  const [issuer, setIssuer] = useState("");
  const [issuedDate, setIssuedDate] = useState("");
  const [expiryDate, setExpiryDate] = useState("");
  const [credentialUrl, setCredentialUrl] = useState("");

  return (
    <ModalShell
      title="Add certification"
      onClose={onClose}
      pending={addCertification.isPending}
      error={addCertification.isError ? addCertification.error : null}
      onSubmit={() =>
        addCertification.mutate(
          {
            name,
            issuer: issuer || null,
            issued_date: issuedDate || null,
            expiry_date: expiryDate || null,
            credential_url: credentialUrl || null,
          },
          { onSuccess: onClose },
        )
      }
    >
      <div className={layoutStyles.formRow}>
        <div className="field">
          <label className="label" htmlFor="cert-name">
            Name
          </label>
          <input id="cert-name" className="input" value={name} onChange={(e) => setName(e.target.value)} required />
        </div>
        <div className="field">
          <label className="label" htmlFor="cert-issuer">
            Issuer
          </label>
          <input id="cert-issuer" className="input" value={issuer} onChange={(e) => setIssuer(e.target.value)} />
        </div>
      </div>
      <div className={layoutStyles.formRow}>
        <div className="field">
          <label className="label" htmlFor="cert-issued">
            Issued
          </label>
          <input
            id="cert-issued"
            type="date"
            className="input"
            value={issuedDate}
            onChange={(e) => setIssuedDate(e.target.value)}
          />
        </div>
        <div className="field">
          <label className="label" htmlFor="cert-expiry">
            Expires
          </label>
          <input
            id="cert-expiry"
            type="date"
            className="input"
            value={expiryDate}
            onChange={(e) => setExpiryDate(e.target.value)}
          />
        </div>
      </div>
      <div className="field">
        <label className="label" htmlFor="cert-url">
          Credential URL
        </label>
        <input
          id="cert-url"
          className="input"
          value={credentialUrl}
          onChange={(e) => setCredentialUrl(e.target.value)}
        />
      </div>
    </ModalShell>
  );
}

export function AddSearchProfileModal({ profileId, onClose }: { profileId: string; onClose: () => void }) {
  const createSearchProfile = useCreateSearchProfile(profileId);
  const [name, setName] = useState("default");
  const [keywords, setKeywords] = useState("");
  const [locations, setLocations] = useState("");
  const [contractTypes, setContractTypes] = useState("");
  const [targetCompanies, setTargetCompanies] = useState("");
  const [minScore, setMinScore] = useState(50);
  const [isActive, setIsActive] = useState(true);

  return (
    <ModalShell
      title="Add search profile"
      onClose={onClose}
      pending={createSearchProfile.isPending}
      error={createSearchProfile.isError ? createSearchProfile.error : null}
      onSubmit={() =>
        createSearchProfile.mutate(
          {
            name,
            keywords: splitList(keywords),
            locations: splitList(locations),
            contract_types: splitList(contractTypes),
            target_companies: splitList(targetCompanies),
            min_score_threshold: minScore,
            is_active: isActive,
          },
          { onSuccess: onClose },
        )
      }
    >
      <div className="field">
        <label className="label" htmlFor="sp-name">
          Name
        </label>
        <input id="sp-name" className="input" value={name} onChange={(e) => setName(e.target.value)} required />
      </div>
      <div className="field">
        <label className="label" htmlFor="sp-keywords">
          Keywords
        </label>
        <input
          id="sp-keywords"
          className="input"
          value={keywords}
          onChange={(e) => setKeywords(e.target.value)}
          placeholder="python, backend, distributed systems"
        />
        <span className={styles.formNote}>Comma-separated.</span>
      </div>
      <div className={layoutStyles.formRow}>
        <div className="field">
          <label className="label" htmlFor="sp-locations">
            Locations
          </label>
          <input
            id="sp-locations"
            className="input"
            value={locations}
            onChange={(e) => setLocations(e.target.value)}
            placeholder="Remote, Berlin"
          />
        </div>
        <div className="field">
          <label className="label" htmlFor="sp-contracts">
            Contract types
          </label>
          <input
            id="sp-contracts"
            className="input"
            value={contractTypes}
            onChange={(e) => setContractTypes(e.target.value)}
            placeholder="internship, full-time"
          />
        </div>
      </div>
      <div className="field">
        <label className="label" htmlFor="sp-companies">
          Target companies
        </label>
        <input
          id="sp-companies"
          className="input"
          value={targetCompanies}
          onChange={(e) => setTargetCompanies(e.target.value)}
        />
      </div>
      <div className={layoutStyles.formRow}>
        <div className="field">
          <label className="label" htmlFor="sp-score">
            Minimum score
          </label>
          <input
            id="sp-score"
            type="number"
            min={0}
            max={100}
            className="input"
            value={minScore}
            onChange={(e) => setMinScore(Number(e.target.value))}
          />
        </div>
        <label className={styles.formNote} style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <input type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} />
          Active
        </label>
      </div>
    </ModalShell>
  );
}
