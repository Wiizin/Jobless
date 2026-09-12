"use client";

/**
 * TanStack Query bindings — one hook per api.ts function.
 *
 * Query-key convention: ["offers", params] / ["offer", id] / ["document", id]
 * / ["applications"] / ["profile", id] / ["search-profiles", id].
 *
 * Mutations invalidate every key whose *server* state they changed, which is
 * sometimes more than the obvious one: approving a document, for instance,
 * also renders a file and flips status, so the offers list is refetched too.
 */
import { useMemo } from "react";
import {
  useMutation,
  useQueries,
  useQuery,
  useQueryClient,
  type UseQueryResult,
} from "@tanstack/react-query";

import * as api from "./api";
import { rememberDocumentId, useKnownDocumentIds } from "./local-store";
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
  ProfileIn,
  ProfileOut,
  SearchProfileIn,
  SkillIn,
} from "./types";

export const queryKeys = {
  profile: (id: string) => ["profile", id] as const,
  searchProfiles: (id: string) => ["search-profiles", id] as const,
  offers: (params: ListOffersParams) => ["offers", params] as const,
  offer: (id: string) => ["offer", id] as const,
  document: (id: string) => ["document", id] as const,
  applications: () => ["applications"] as const,
};

// --- profile --------------------------------------------------------------

export function useProfile(profileId: string | null) {
  return useQuery({
    queryKey: queryKeys.profile(profileId ?? ""),
    queryFn: () => api.getProfile(profileId as string),
    enabled: Boolean(profileId),
  });
}

export function useCreateProfile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: ProfileIn) => api.createProfile(payload),
    onSuccess: (profile) => {
      qc.setQueryData(queryKeys.profile(profile.id), profile);
    },
  });
}

export function useUpdateProfile(profileId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: ProfileIn) => api.updateProfile(profileId as string, payload),
    onSuccess: (profile) => {
      qc.setQueryData(queryKeys.profile(profile.id), profile);
    },
  });
}

/**
 * The four "add a profile item" endpoints all return the whole refreshed
 * ProfileOut, so each writes straight into the profile cache.
 */
function useProfileItemMutation<TPayload>(
  profileId: string | null,
  mutationFn: (id: string, payload: TPayload) => Promise<ProfileOut>,
) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: TPayload) => mutationFn(profileId as string, payload),
    onSuccess: (profile) => {
      qc.setQueryData(queryKeys.profile(profile.id), profile);
    },
  });
}

export function useAddExperience(profileId: string | null) {
  return useProfileItemMutation<ExperienceIn>(profileId, api.addExperience);
}

export function useAddSkill(profileId: string | null) {
  return useProfileItemMutation<SkillIn>(profileId, api.addSkill);
}

export function useAddEducation(profileId: string | null) {
  return useProfileItemMutation<EducationIn>(profileId, api.addEducation);
}

export function useAddCertification(profileId: string | null) {
  return useProfileItemMutation<CertificationIn>(profileId, api.addCertification);
}

export function useSearchProfiles(profileId: string | null) {
  return useQuery({
    queryKey: queryKeys.searchProfiles(profileId ?? ""),
    queryFn: () => api.listSearchProfiles(profileId as string),
    enabled: Boolean(profileId),
  });
}

export function useCreateSearchProfile(profileId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: SearchProfileIn) => api.createSearchProfile(profileId as string, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.searchProfiles(profileId ?? "") });
    },
  });
}

export function useImportCv() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ file, profileId }: { file: File; profileId?: string }) => api.importCv(file, profileId),
    onSuccess: (profile) => {
      qc.setQueryData(queryKeys.profile(profile.id), profile);
    },
  });
}

// --- offers ---------------------------------------------------------------

export function useOffers(params: ListOffersParams = {}) {
  return useQuery({
    queryKey: queryKeys.offers(params),
    queryFn: () => api.listOffers(params),
  });
}

export function useOffer(offerId: string | null) {
  return useQuery({
    queryKey: queryKeys.offer(offerId ?? ""),
    queryFn: () => api.getOffer(offerId as string),
    enabled: Boolean(offerId),
  });
}

/** Fetch several offers at once — the applications table joins through these. */
export function useOffersByIds(offerIds: string[]): UseQueryResult<OfferDetail>[] {
  return useQueries({
    queries: offerIds.map((id) => ({
      queryKey: queryKeys.offer(id),
      queryFn: () => api.getOffer(id),
    })),
  });
}

export function useAddManualOffer(profileId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: ManualOfferIn) => api.addManualOffer(payload, profileId ?? undefined),
    onSuccess: (offer) => {
      qc.setQueryData(queryKeys.offer(offer.id), offer);
      qc.invalidateQueries({ queryKey: ["offers"] });
    },
  });
}

export function useDismissOffer() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (offerId: string) => api.dismissOffer(offerId),
    onSuccess: (offer) => {
      qc.setQueryData(queryKeys.offer(offer.id), offer);
      qc.invalidateQueries({ queryKey: ["offers"] });
    },
  });
}

// --- documents ------------------------------------------------------------

export function useDocument(documentId: string | null) {
  return useQuery({
    queryKey: queryKeys.document(documentId ?? ""),
    queryFn: () => api.getDocument(documentId as string),
    enabled: Boolean(documentId),
  });
}

/** Backfills the Documents page, which has no list endpoint to call. */
export function useDocumentsByIds(documentIds: string[]): UseQueryResult<DocumentOut>[] {
  return useQueries({
    queries: documentIds.map((id) => ({
      queryKey: queryKeys.document(id),
      queryFn: () => api.getDocument(id),
      // A document deleted server-side shouldn't hammer the API from a stale
      // local index; the page offers to drop it from the index instead.
      retry: false,
    })),
  });
}

export function useGenerateDocument(profileId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: GenerateDocumentRequest) => api.generateDocument(payload, profileId as string),
    onSuccess: (document) => {
      rememberDocumentId(document.id);
      qc.setQueryData(queryKeys.document(document.id), document);
    },
  });
}

export function useEditDocument(documentId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: DocumentEditRequest) => api.editDocument(documentId, payload),
    onSuccess: (document) => {
      qc.setQueryData(queryKeys.document(document.id), document);
    },
  });
}

export function useApproveDocument(documentId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.approveDocument(documentId),
    onSuccess: (document) => {
      qc.setQueryData(queryKeys.document(document.id), document);
      // Approval renders the file and flips status, which the offer detail
      // and the offers list both surface.
      qc.invalidateQueries({ queryKey: queryKeys.offer(document.offer_id) });
      qc.invalidateQueries({ queryKey: ["offers"] });
    },
  });
}

export function useDownloadDocument(documentId: string) {
  return useMutation({
    mutationFn: async () => {
      const { blob, filename } = await api.downloadDocument(documentId);
      api.saveBlob(blob, filename ?? `${documentId}.docx`);
    },
  });
}

// --- applications ---------------------------------------------------------

export function useApplications() {
  return useQuery({
    queryKey: queryKeys.applications(),
    queryFn: () => api.listApplications(),
  });
}

export function useCreateApplication() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: ApplicationCreate) => api.createApplication(payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.applications() });
    },
  });
}

export function useUpdateApplicationStatus() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: ApplicationStatusUpdate }) =>
      api.updateApplicationStatus(id, payload),
    onSuccess: (application: ApplicationOut) => {
      qc.setQueryData(queryKeys.applications(), (previous: ApplicationOut[] | undefined) =>
        previous?.map((row) => (row.id === application.id ? application : row)),
      );
      qc.invalidateQueries({ queryKey: queryKeys.applications() });
    },
  });
}

// --- documents index ------------------------------------------------------

/**
 * Every document id this browser can reach, newest-first.
 *
 * The backend exposes no document list, so this merges the local index of
 * documents generated here with any `document_id` attached to an application
 * (which recovers documents generated in another browser).
 */
export function useAllDocumentIds(): string[] {
  const localIds = useKnownDocumentIds();
  const { data: applications } = useApplications();

  return useMemo(() => {
    const merged = [...localIds];
    for (const application of applications ?? []) {
      if (application.document_id && !merged.includes(application.document_id)) {
        merged.push(application.document_id);
      }
    }
    return merged;
  }, [localIds, applications]);
}
