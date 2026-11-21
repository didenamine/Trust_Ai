import { zodResolver } from '@hookform/resolvers/zod'
import { FormProvider, useForm } from 'react-hook-form'
import { profileFormSchema, type ProfileFormValues, type ProfileSource } from '../lib/profile'
import {
  CertificationsSection,
  EducationSection,
  ExperiencesSection,
  IdentitySection,
  LanguagesSection,
  ProjectsSection,
  SkillsSection,
} from './profile/sections'

type ProfileFormProps = {
  defaultValues: ProfileFormValues
  source?: ProfileSource | null
  updatedAt?: string | null
  isSaving: boolean
  serverError: string | null
  onSubmit: (values: ProfileFormValues) => void
  /** US07: leave edit mode without saving (only for an existing profile). */
  onCancel?: () => void
}

export default function ProfileForm({
  defaultValues,
  source,
  updatedAt,
  isSaving,
  serverError,
  onSubmit,
  onCancel,
}: ProfileFormProps) {
  const form = useForm<ProfileFormValues>({
    resolver: zodResolver(profileFormSchema),
    defaultValues,
    mode: 'onBlur',
  })

  return (
    <FormProvider {...form}>
      <form className="space-y-6" onSubmit={form.handleSubmit(onSubmit)} noValidate>
        {source === 'cv_analysis' && (
          <p className="rounded border border-blue-200 bg-blue-50 p-3 text-sm text-blue-800">
            Ce profil a été généré à partir de votre CV. Vos modifications sont enregistrées dans ce
            même profil.
          </p>
        )}
        {updatedAt && (
          <p className="text-sm text-slate-500">
            Dernière mise à jour le {new Date(updatedAt).toLocaleDateString('fr-FR')}
          </p>
        )}

        <IdentitySection />
        <SkillsSection />
        <ExperiencesSection />
        <EducationSection />
        <LanguagesSection />
        <CertificationsSection />
        <ProjectsSection />

        {serverError && (
          <p className="text-sm text-red-600" role="alert">
            {serverError}
          </p>
        )}

        <div className="flex gap-3">
          {onCancel && (
            <button
              type="button"
              onClick={onCancel}
              disabled={isSaving}
              className="rounded border border-slate-300 px-4 py-2 font-medium disabled:opacity-50"
            >
              Annuler
            </button>
          )}
          <button
            type="submit"
            disabled={isSaving}
            className="flex-1 rounded bg-slate-900 px-4 py-2 font-medium text-white disabled:opacity-50"
          >
            {isSaving ? 'Enregistrement…' : 'Enregistrer mon profil'}
          </button>
        </div>
      </form>
    </FormProvider>
  )
}
