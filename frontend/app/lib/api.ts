/**
 * Typed fetch wrapper over the jobless FastAPI backend.
 *
 * One function per endpoint, hand-typed against app/schemas/*.py. Endpoint
 * signatures here follow the backend exactly, including the two places where
 * it takes `profile_id` as a *query* parameter rather than in the body
 * (POST /documents/generate, POST /offers/manual).
 */
import type {
  ApplicationCreate,
  ApplicationOut,
  ApplicationStatusUpdate,
  CertificationIn,
  DocumentEditRequest,
  DocumentOut,
  EducationIn,
  ExperienceIn,
  GenerateDocumentRequest,
  ListOffersParams,
  ManualOfferIn,
  OfferDetail,
  OfferOut,
  ProfileIn,
  ProfileOut,
  SearchProfileIn,
  SearchProfileOut,
  SkillIn,
} from "./types";

export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const SESSION_TOKEN = process.env.NEXT_PUBLIC_SESSION_TOKEN;

/** A non-2xx response, carrying the backend's `detail` message when it sent one. */
export class ApiError extends Error {
  readonly status: number;
  readonly detail: unknown;

  constructor(status: number, detail: unknown, fallback: string) {
    super(typeof detail === "string" && detail ? detail : fallback);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

function authHeaders(): Record<string, string> {
  // verify_session_token no-ops while the backend's SESSION_SECRET is at its
  // insecure default, so this header is optional in local dev.
  return SESSION_TOKEN ? { "x-session-token": SESSION_TOKEN } : {};
}

function buildUrl(path: string, params?: Record<string, unknown>): string {
  const url = new URL(path, API_URL);
  for (const [key, value] of Object.entries(params ?? {})) {
    if (value !== undefined && value !== null && value !== "") {
      url.searchParams.set(key, String(value));
    }
  }
  return url.toString();
}

/**
 * FastAPI sends validation errors as `{detail: [{loc, msg, ...}]}`; flatten
 * those into one readable line so a form can surface them.
 */
function flattenDetail(detail: unknown): unknown {
  if (!Array.isArray(detail)) return detail;
  return detail
    .map((item) => {
      if (item && typeof item === "object" && "msg" in item) {
        const { loc, msg } = item as { loc?: unknown[]; msg?: string };
        const field = Array.isArray(loc) ? loc.filter((p) => p !== "body").join(".") : "";
        return field ? `${field}: ${msg}` : String(msg);
      }
      return String(item);
    })
    .join("; ");
}

async function toApiError(res: Response): Promise<ApiError> {
  let detail: unknown;
  try {
    const body = await res.json();
    detail = flattenDetail(body?.detail ?? body);
  } catch {
    detail = undefined;
  }
  return new ApiError(res.status, detail, `${res.status} ${res.statusText}`);
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  params?: Record<string, unknown>;
  /** Send `body` as-is (used for multipart uploads) instead of JSON-encoding it. */
  raw?: boolean;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, params, raw = false } = options;

  const headers: Record<string, string> = { ...authHeaders() };
  // Let the browser set Content-Type (with its multipart boundary) for FormData.
  if (body !== undefined && !raw) headers["Content-Type"] = "application/json";

  const res = await fetch(buildUrl(path, params), {
    method,
    headers,
    body: body === undefined ? undefined : raw ? (body as BodyInit) : JSON.stringify(body),
  });

  if (!res.ok) throw await toApiError(res);
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

async function requestBlob(path: string): Promise<{ blob: Blob; filename: string | null }> {
  const res = await fetch(buildUrl(path), { headers: authHeaders() });
  if (!res.ok) throw await toApiError(res);

  // FileResponse sets `content-disposition: attachment; filename="..."`.
  const disposition = res.headers.get("content-disposition") ?? "";
  const match = /filename\*?=(?:UTF-8'')?"?([^";]+)"?/i.exec(disposition);
  const filename = match ? decodeURIComponent(match[1]) : null;

  return { blob: await res.blob(), filename };
}

// --- health ---------------------------------------------------------------

export function getHealth(): Promise<{ status: string }> {
  return request("/health");
}

// --- profile --------------------------------------------------------------

export function createProfile(payload: ProfileIn): Promise<ProfileOut> {
  return request("/profile", { method: "POST", body: payload });
}

export function getProfile(profileId: string): Promise<ProfileOut> {
  return request(`/profile/${profileId}`);
}

/** PUT, not PATCH — the backend replaces every ProfileIn field. */
export function updateProfile(profileId: string, payload: ProfileIn): Promise<ProfileOut> {
  return request(`/profile/${profileId}`, { method: "PUT", body: payload });
}

export function addExperience(profileId: string, payload: ExperienceIn): Promise<ProfileOut> {
  return request(`/profile/${profileId}/experiences`, { method: "POST", body: payload });
}

export function addSkill(profileId: string, payload: SkillIn): Promise<ProfileOut> {
  return request(`/profile/${profileId}/skills`, { method: "POST", body: payload });
}

export function addEducation(profileId: string, payload: EducationIn): Promise<ProfileOut> {
  return request(`/profile/${profileId}/education`, { method: "POST", body: payload });
}

export function addCertification(profileId: string, payload: CertificationIn): Promise<ProfileOut> {
  return request(`/profile/${profileId}/certifications`, { method: "POST", body: payload });
}

export function createSearchProfile(profileId: string, payload: SearchProfileIn): Promise<SearchProfileOut> {
  return request(`/profile/${profileId}/search-profile`, { method: "POST", body: payload });
}

export function listSearchProfiles(profileId: string): Promise<SearchProfileOut[]> {
  return request(`/profile/${profileId}/search-profile`);
}

/**
 * POST /profile/import-cv — multipart upload.
 *
 * With `profileId`, the CV *replaces* that profile's experiences/skills/
 * education/certifications wholesale; without it, a new profile is created.
 */
export function importCv(file: File, profileId?: string): Promise<ProfileOut> {
  const form = new FormData();
  form.append("file", file);
  return request("/profile/import-cv", {
    method: "POST",
    body: form,
    raw: true,
    params: profileId ? { profile_id: profileId } : undefined,
  });
}

// --- offers ---------------------------------------------------------------

/**
 * GET /offers. Note the backend only returns offers that have already been
 * scored (`match_score IS NOT NULL`), so unscored postings never appear here.
 */
export function listOffers(params: ListOffersParams = {}): Promise<OfferOut[]> {
  return request("/offers", { params: params as Record<string, unknown> });
}

export function getOffer(offerId: string): Promise<OfferDetail> {
  return request(`/offers/${offerId}`);
}

/** Passing `profileId` makes the backend score the posting immediately. */
export function addManualOffer(payload: ManualOfferIn, profileId?: string): Promise<OfferDetail> {
  return request("/offers/manual", {
    method: "POST",
    body: payload,
    params: profileId ? { profile_id: profileId } : undefined,
  });
}

export function dismissOffer(offerId: string): Promise<OfferDetail> {
  return request(`/offers/${offerId}/dismiss`, { method: "POST" });
}

// --- documents ------------------------------------------------------------

/** `profile_id` is a required *query* parameter on this endpoint. */
export function generateDocument(payload: GenerateDocumentRequest, profileId: string): Promise<DocumentOut> {
  return request("/documents/generate", {
    method: "POST",
    body: payload,
    params: { profile_id: profileId },
  });
}

export function getDocument(documentId: string): Promise<DocumentOut> {
  return request(`/documents/${documentId}`);
}

export function editDocument(documentId: string, payload: DocumentEditRequest): Promise<DocumentOut> {
  return request(`/documents/${documentId}`, { method: "PATCH", body: payload });
}

export function approveDocument(documentId: string): Promise<DocumentOut> {
  return request(`/documents/${documentId}/approve`, { method: "POST" });
}

/** Returns the rendered file; the backend rejects this unless status=approved. */
export function downloadDocument(documentId: string): Promise<{ blob: Blob; filename: string | null }> {
  return requestBlob(`/documents/${documentId}/download`);
}

// --- applications ---------------------------------------------------------

export function listApplications(): Promise<ApplicationOut[]> {
  return request("/applications");
}

export function createApplication(payload: ApplicationCreate): Promise<ApplicationOut> {
  return request("/applications", { method: "POST", body: payload });
}

export function updateApplicationStatus(
  applicationId: string,
  payload: ApplicationStatusUpdate,
): Promise<ApplicationOut> {
  return request(`/applications/${applicationId}`, { method: "PATCH", body: payload });
}

// --- browser file save ----------------------------------------------------

/** Object URL -> hidden `<a download>` -> click -> revoke. */
export function saveBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.style.display = "none";
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(url);
}
