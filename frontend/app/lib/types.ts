/**
 * Hand-written mirrors of the backend's Pydantic schemas.
 *
 * Each type below names the schema it tracks so drift is easy to spot; the
 * backend has no OpenAPI client-generation step wired up, so these are
 * maintained by hand against app/schemas/*.py and app/db/models.py.
 */

// --- enums (app/db/models.py) ---------------------------------------------

/** models.py::OfferStatus */
export type OfferStatus = "new" | "scored" | "reviewed" | "dismissed";
export const OFFER_STATUSES: OfferStatus[] = ["new", "scored", "reviewed", "dismissed"];

/** models.py::DocumentType */
export type DocumentType = "cv" | "cover_letter" | "qa";
export const DOCUMENT_TYPES: DocumentType[] = ["cv", "cover_letter", "qa"];

/** models.py::DocumentStatus */
export type DocumentStatus = "pending_review" | "approved";

/** models.py::ApplicationStatus */
export type ApplicationStatus =
  | "not_applied"
  | "applied"
  | "interviewing"
  | "rejected"
  | "offer_received"
  | "withdrawn";
export const APPLICATION_STATUSES: ApplicationStatus[] = [
  "not_applied",
  "applied",
  "interviewing",
  "rejected",
  "offer_received",
  "withdrawn",
];

// --- profile (app/schemas/profile.py) -------------------------------------

/** schemas/profile.py::ExperienceIn */
export interface ExperienceIn {
  title: string;
  company: string;
  location?: string | null;
  start_date?: string | null; // date
  end_date?: string | null; // date
  is_current?: boolean;
  description?: string | null;
  bullets?: string[];
}
/** schemas/profile.py::ExperienceOut */
export interface ExperienceOut extends ExperienceIn {
  id: string;
}

/** schemas/profile.py::SkillIn */
export interface SkillIn {
  name: string;
  category?: string | null;
  proficiency?: string | null;
}
/** schemas/profile.py::SkillOut */
export interface SkillOut extends SkillIn {
  id: string;
}

/** schemas/profile.py::EducationIn */
export interface EducationIn {
  institution: string;
  degree?: string | null;
  field_of_study?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  description?: string | null;
}
/** schemas/profile.py::EducationOut */
export interface EducationOut extends EducationIn {
  id: string;
}

/** schemas/profile.py::CertificationIn */
export interface CertificationIn {
  name: string;
  issuer?: string | null;
  issued_date?: string | null;
  expiry_date?: string | null;
  credential_url?: string | null;
}
/** schemas/profile.py::CertificationOut */
export interface CertificationOut extends CertificationIn {
  id: string;
}

/** schemas/profile.py::ProfileIn */
export interface ProfileIn {
  full_name: string;
  email: string;
  phone?: string | null;
  location?: string | null;
  summary?: string | null;
  links?: Record<string, string>;
}

/** schemas/profile.py::ProfileOut */
export interface ProfileOut extends ProfileIn {
  id: string;
  experiences: ExperienceOut[];
  skills: SkillOut[];
  education: EducationOut[];
  certifications: CertificationOut[];
}

/** schemas/profile.py::SearchProfileIn */
export interface SearchProfileIn {
  name?: string;
  keywords?: string[];
  locations?: string[];
  contract_types?: string[];
  target_companies?: string[];
  min_score_threshold?: number;
  is_active?: boolean;
}

/** schemas/profile.py::SearchProfileOut */
export interface SearchProfileOut extends SearchProfileIn {
  id: string;
  profile_id: string;
}

// --- offers (app/schemas/offer.py) ----------------------------------------

/** schemas/offer.py::ManualOfferIn */
export interface ManualOfferIn {
  title: string;
  company: string;
  location: string;
  contract_type: string;
  description: string;
  url: string;
  posted_date?: string | null; // datetime
}

/** schemas/offer.py::OfferOut */
export interface OfferOut {
  id: string;
  source: string;
  external_id: string;
  title: string;
  company: string;
  location: string | null;
  contract_type: string | null;
  description: string;
  url: string;
  posted_date: string | null;
  match_score: number | null;
  match_reasoning: string | null;
  missing_skills: string[];
  dealbreakers: string[];
  status: OfferStatus;
  created_at: string;
}

/** schemas/offer.py::OfferDetail — currently identical to OfferOut. */
export type OfferDetail = OfferOut;

/** Query params accepted by GET /offers. */
export interface ListOffersParams {
  min_score?: number;
  status?: OfferStatus;
  limit?: number;
  offset?: number;
}

// --- documents (app/schemas/document.py) ----------------------------------

/** schemas/document.py::CoverLetterSections */
export interface CoverLetterSections {
  intro: string;
  body_paragraphs: string[];
  closing: string;
}

/** schemas/document.py::GenerateDocumentRequest */
export interface GenerateDocumentRequest {
  offer_id: string;
  doc_type: DocumentType;
}

/** schemas/document.py::DocumentEditRequest */
export interface DocumentEditRequest {
  selected_experiences?: string[] | null;
  bullets?: string[] | null;
  cover_letter_sections?: CoverLetterSections | null;
  qa_answers?: Record<string, string> | null;
}

/**
 * schemas/document.py::DocumentOut
 *
 * `cover_letter_sections` is a bare `dict` on the backend and is written as
 * `{}` for cv/qa documents, so it is only partially shaped here.
 */
export interface DocumentOut {
  id: string;
  offer_id: string;
  profile_id: string;
  doc_type: DocumentType;
  selected_experiences: string[];
  bullets: string[];
  cover_letter_sections: Partial<CoverLetterSections>;
  qa_answers: Record<string, string>;
  file_path: string | null;
  status: DocumentStatus;
  created_at: string;
}

// --- applications (app/routers/applications.py) ---------------------------

/** routers/applications.py::ApplicationCreate */
export interface ApplicationCreate {
  offer_id: string;
  document_id?: string | null;
  notes?: string | null;
}

/** routers/applications.py::ApplicationStatusUpdate */
export interface ApplicationStatusUpdate {
  status: ApplicationStatus;
  notes?: string | null;
}

/** routers/applications.py::ApplicationOut */
export interface ApplicationOut {
  id: string;
  offer_id: string;
  document_id: string | null;
  status: ApplicationStatus;
  applied_at: string | null;
  notes: string | null;
  created_at: string;
}
