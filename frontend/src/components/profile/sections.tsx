import type { ReactNode } from 'react'
import { useFieldArray, useFormContext, type FieldPath } from 'react-hook-form'
import {
  CONTENT_LANGUAGE_VALUES,
  EDUCATION_LEVEL_LABELS,
  EDUCATION_LEVEL_VALUES,
  EMPLOYMENT_TYPE_LABELS,
  EMPLOYMENT_TYPE_VALUES,
  LANGUAGE_LEVEL_LABELS,
  LANGUAGE_LEVEL_VALUES,
  SKILL_CATEGORY_LABELS,
  SKILL_CATEGORY_VALUES,
  SKILL_LEVEL_LABELS,
  SKILL_LEVEL_VALUES,
  emptyCertificationForm,
  emptyEducationForm,
  emptyExperienceForm,
  emptyLanguageForm,
  emptyProjectForm,
  emptySkillForm,
  type ProfileFormValues,
} from '../../lib/profile'
import {
  AddButton,
  CheckboxField,
  CommaListField,
  FormError,
  ItemActions,
  SelectField,
  TextAreaField,
  TextField,
} from './fields'

const NONE = { value: '', label: 'Non renseigné' }

const languageOptions = CONTENT_LANGUAGE_VALUES.map((value) => ({
  value,
  label: value === 'fr' ? 'Français' : 'English',
}))
const skillCategoryOptions = SKILL_CATEGORY_VALUES.map((value) => ({
  value,
  label: SKILL_CATEGORY_LABELS[value],
}))
const skillLevelOptions = [
  NONE,
  ...SKILL_LEVEL_VALUES.map((value) => ({ value, label: SKILL_LEVEL_LABELS[value] })),
]
const employmentTypeOptions = [
  NONE,
  ...EMPLOYMENT_TYPE_VALUES.map((value) => ({
    value,
    label: EMPLOYMENT_TYPE_LABELS[value],
  })),
]
const educationLevelOptions = [
  NONE,
  ...EDUCATION_LEVEL_VALUES.map((value) => ({ value, label: EDUCATION_LEVEL_LABELS[value] })),
]
const languageLevelOptions = [
  NONE,
  ...LANGUAGE_LEVEL_VALUES.map((value) => ({ value, label: LANGUAGE_LEVEL_LABELS[value] })),
]

function Section({
  title,
  description,
  name,
  children,
}: {
  title: string
  description?: string
  name: FieldPath<ProfileFormValues>
  children: ReactNode
}) {
  return (
    <fieldset className="space-y-4 rounded border border-slate-200 bg-white p-4">
      <legend className="px-1 text-lg font-semibold">{title}</legend>
      {description && <p className="text-sm text-slate-600">{description}</p>}
      <FormError name={name} />
      {children}
    </fieldset>
  )
}

type PeriodPath = `experiences.${number}` | `education.${number}` | `projects.${number}`

function PeriodFields({ path }: { path: PeriodPath }) {
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <TextField
        name={`${path}.start_date`}
        label="Début"
        placeholder="2021 ou 2021-03"
        hint="AAAA ou AAAA-MM"
      />
      <TextField
        name={`${path}.end_date`}
        label="Fin"
        placeholder="2023 ou 2023-06"
        hint="Laisser vide si l'activité est en cours"
      />
    </div>
  )
}

export function IdentitySection() {
  return (
    <Section
      title="Identité"
      description="La langue est obligatoire ; les autres champs sont optionnels."
      name="personal_info"
    >
      <div className="grid gap-3 sm:grid-cols-2">
        <SelectField name="language" label="Langue du profil" options={languageOptions} />
        <TextField name="personal_info.full_name" label="Nom complet" placeholder="Sarra Benali" />
        <TextField
          name="personal_info.headline"
          label="Titre professionnel"
          placeholder="Développeuse full-stack"
        />
        <TextField
          name="personal_info.email"
          label="E-mail"
          type="email"
          placeholder="sarra@exemple.fr"
        />
        <TextField
          name="personal_info.phone"
          label="Téléphone"
          type="tel"
          placeholder="+216 12 345 678"
        />
        <TextField
          name="personal_info.location"
          label="Localisation"
          placeholder="Tunis, Tunisie"
        />
      </div>
      <CommaListField
        name="personal_info.links"
        label="Liens (LinkedIn, GitHub, portfolio…)"
        placeholder="github.com/sarra, https://linkedin.com/in/sarra"
      />
      <TextAreaField
        name="summary"
        label="Résumé"
        placeholder="Quelques phrases sur votre parcours…"
      />
    </Section>
  )
}

export function SkillsSection() {
  const { control } = useFormContext<ProfileFormValues>()
  const { fields, append, remove } = useFieldArray({ control, name: 'skills' })

  return (
    <Section
      title="Compétences"
      description="Ajoutez vos compétences techniques et vos savoir-être."
      name="skills"
    >
      {fields.map((field, index) => (
        <div
          key={field.id}
          className="grid gap-3 rounded border border-slate-200 p-3 sm:grid-cols-3"
        >
          <TextField name={`skills.${index}.name`} label="Compétence" />
          <SelectField
            name={`skills.${index}.category`}
            label="Catégorie"
            options={skillCategoryOptions}
          />
          <SelectField name={`skills.${index}.level`} label="Niveau" options={skillLevelOptions} />
          <div className="sm:col-span-3">
            <ItemActions onRemove={() => remove(index)} label="Retirer cette compétence" />
          </div>
        </div>
      ))}
      <AddButton onClick={() => append(emptySkillForm())} label="Ajouter une compétence" />
    </Section>
  )
}

export function ExperiencesSection() {
  const { control } = useFormContext<ProfileFormValues>()
  const { fields, append, remove } = useFieldArray({ control, name: 'experiences' })

  return (
    <Section title="Expériences professionnelles" name="experiences">
      {fields.map((field, index) => (
        <div key={field.id} className="space-y-3 rounded border border-slate-200 p-3">
          <div className="grid gap-3 sm:grid-cols-2">
            <TextField name={`experiences.${index}.job_title`} label="Intitulé du poste" />
            <TextField name={`experiences.${index}.company`} label="Entreprise" />
            <TextField name={`experiences.${index}.location`} label="Lieu" />
            <SelectField
              name={`experiences.${index}.employment_type`}
              label="Type de contrat"
              options={employmentTypeOptions}
            />
          </div>
          <PeriodFields path={`experiences.${index}`} />
          <CheckboxField name={`experiences.${index}.is_current`} label="Poste actuel" />
          <TextAreaField name={`experiences.${index}.description`} label="Description" rows={2} />
          <CommaListField
            name={`experiences.${index}.achievements`}
            label="Réalisations"
            placeholder="A réduit les temps de réponse de 30 %, a encadré 3 personnes"
          />
          <CommaListField
            name={`experiences.${index}.skills`}
            label="Compétences utilisées"
            placeholder="Python, React, Scrum"
          />
          <ItemActions onRemove={() => remove(index)} label="Retirer cette expérience" />
        </div>
      ))}
      <AddButton onClick={() => append(emptyExperienceForm())} label="Ajouter une expérience" />
    </Section>
  )
}

export function EducationSection() {
  const { control } = useFormContext<ProfileFormValues>()
  const { fields, append, remove } = useFieldArray({ control, name: 'education' })

  return (
    <Section title="Formations" name="education">
      {fields.map((field, index) => (
        <div key={field.id} className="space-y-3 rounded border border-slate-200 p-3">
          <div className="grid gap-3 sm:grid-cols-2">
            <TextField name={`education.${index}.degree`} label="Diplôme" />
            <SelectField
              name={`education.${index}.level`}
              label="Niveau"
              options={educationLevelOptions}
            />
            <TextField name={`education.${index}.field_of_study`} label="Domaine" />
            <TextField name={`education.${index}.institution`} label="Établissement" />
            <TextField name={`education.${index}.location`} label="Lieu" />
          </div>
          <PeriodFields path={`education.${index}`} />
          <CheckboxField name={`education.${index}.is_current`} label="Formation en cours" />
          <TextAreaField name={`education.${index}.description`} label="Description" rows={2} />
          <ItemActions onRemove={() => remove(index)} label="Retirer cette formation" />
        </div>
      ))}
      <AddButton onClick={() => append(emptyEducationForm())} label="Ajouter une formation" />
    </Section>
  )
}

export function LanguagesSection() {
  const { control } = useFormContext<ProfileFormValues>()
  const { fields, append, remove } = useFieldArray({ control, name: 'languages' })

  return (
    <Section title="Langues parlées" name="languages">
      {fields.map((field, index) => (
        <div
          key={field.id}
          className="grid gap-3 rounded border border-slate-200 p-3 sm:grid-cols-3"
        >
          <TextField name={`languages.${index}.name`} label="Langue" placeholder="Français" />
          <TextField
            name={`languages.${index}.code`}
            label="Code ISO"
            placeholder="fr"
            hint="Deux lettres"
          />
          <SelectField
            name={`languages.${index}.level`}
            label="Niveau"
            options={languageLevelOptions}
          />
          <div className="sm:col-span-3">
            <ItemActions onRemove={() => remove(index)} label="Retirer cette langue" />
          </div>
        </div>
      ))}
      <AddButton onClick={() => append(emptyLanguageForm())} label="Ajouter une langue" />
    </Section>
  )
}

export function CertificationsSection() {
  const { control } = useFormContext<ProfileFormValues>()
  const { fields, append, remove } = useFieldArray({ control, name: 'certifications' })

  return (
    <Section title="Certifications" name="certifications">
      {fields.map((field, index) => (
        <div
          key={field.id}
          className="grid gap-3 rounded border border-slate-200 p-3 sm:grid-cols-2"
        >
          <TextField name={`certifications.${index}.name`} label="Certification" />
          <TextField name={`certifications.${index}.issuer`} label="Organisme" />
          <TextField
            name={`certifications.${index}.issue_date`}
            label="Date d'obtention"
            placeholder="2022 ou 2022-05"
          />
          <TextField name={`certifications.${index}.url`} label="Lien" placeholder="https://…" />
          <div className="sm:col-span-2">
            <ItemActions onRemove={() => remove(index)} label="Retirer cette certification" />
          </div>
        </div>
      ))}
      <AddButton
        onClick={() => append(emptyCertificationForm())}
        label="Ajouter une certification"
      />
    </Section>
  )
}

export function ProjectsSection() {
  const { control } = useFormContext<ProfileFormValues>()
  const { fields, append, remove } = useFieldArray({ control, name: 'projects' })

  return (
    <Section title="Projets" name="projects">
      {fields.map((field, index) => (
        <div key={field.id} className="space-y-3 rounded border border-slate-200 p-3">
          <TextField name={`projects.${index}.name`} label="Nom du projet" />
          <TextAreaField name={`projects.${index}.description`} label="Description" rows={2} />
          <PeriodFields path={`projects.${index}`} />
          <CheckboxField name={`projects.${index}.is_current`} label="Projet en cours" />
          <CommaListField
            name={`projects.${index}.skills`}
            label="Compétences utilisées"
            placeholder="Python, TensorFlow"
          />
          <TextField
            name={`projects.${index}.url`}
            label="Lien"
            placeholder="github.com/moi/projet"
          />
          <ItemActions onRemove={() => remove(index)} label="Retirer ce projet" />
        </div>
      ))}
      <AddButton onClick={() => append(emptyProjectForm())} label="Ajouter un projet" />
    </Section>
  )
}
