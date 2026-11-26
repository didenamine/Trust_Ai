import {
  Controller,
  useFormContext,
  type FieldError,
  type FieldErrors,
  type FieldPath,
} from 'react-hook-form'
import type { ProfileFormValues } from '../../lib/profile'

const INPUT_CLASS =
  'mt-1 w-full rounded border border-slate-300 px-3 py-2 focus:border-brand-500 focus:outline-none'
const ERROR_CLASS = 'mt-1 text-sm text-red-600'

function inputId(name: string): string {
  return name.replace(/[^a-zA-Z0-9]/g, '-')
}

function getFieldError(
  errors: FieldErrors<ProfileFormValues>,
  name: string,
): FieldError | undefined {
  let current: unknown = errors
  for (const key of name.split('.')) {
    if (typeof current !== 'object' || current === null) return undefined
    current = (current as Record<string, unknown>)[key]
  }
  if (current && typeof current === 'object' && 'root' in current) {
    const root = (current as { root?: FieldError }).root
    if (root) return root
  }
  return current as FieldError | undefined
}

function FieldLabel({ name, label }: { name: string; label: string }) {
  return (
    <label htmlFor={inputId(name)} className="block text-sm font-medium">
      {label}
    </label>
  )
}

function FieldMessage({ name, hint }: { name: string; hint?: string }) {
  const { formState } = useFormContext<ProfileFormValues>()
  const error = getFieldError(formState.errors, name)
  return (
    <>
      {hint && !error && (
        <p id={`${inputId(name)}-hint`} className="mt-1 text-xs text-slate-500">
          {hint}
        </p>
      )}
      {error?.message && (
        <p id={`${inputId(name)}-error`} className={ERROR_CLASS} role="alert">
          {error.message}
        </p>
      )}
    </>
  )
}

export function FormError({ name }: { name: FieldPath<ProfileFormValues> }) {
  const { formState } = useFormContext<ProfileFormValues>()
  const error = getFieldError(formState.errors, name)
  return error?.message ? <p className={ERROR_CLASS}>{error.message}</p> : null
}

type TextFieldProps = {
  name: FieldPath<ProfileFormValues>
  label: string
  type?: 'text' | 'email' | 'tel' | 'url'
  placeholder?: string
  hint?: string
}

export function TextField({ name, label, type = 'text', placeholder, hint }: TextFieldProps) {
  const { register, formState } = useFormContext<ProfileFormValues>()
  const error = getFieldError(formState.errors, name)
  return (
    <div>
      <FieldLabel name={name} label={label} />
      <input
        id={inputId(name)}
        type={type}
        placeholder={placeholder}
        aria-invalid={Boolean(error)}
        aria-describedby={
          error ? `${inputId(name)}-error` : hint ? `${inputId(name)}-hint` : undefined
        }
        className={INPUT_CLASS}
        {...register(name)}
      />
      <FieldMessage name={name} hint={hint} />
    </div>
  )
}

export function TextAreaField({
  name,
  label,
  rows = 3,
  placeholder,
  hint,
}: {
  name: FieldPath<ProfileFormValues>
  label: string
  rows?: number
  placeholder?: string
  hint?: string
}) {
  const { register, formState } = useFormContext<ProfileFormValues>()
  const error = getFieldError(formState.errors, name)
  return (
    <div>
      <FieldLabel name={name} label={label} />
      <textarea
        id={inputId(name)}
        rows={rows}
        placeholder={placeholder}
        aria-invalid={Boolean(error)}
        aria-describedby={
          error ? `${inputId(name)}-error` : hint ? `${inputId(name)}-hint` : undefined
        }
        className={INPUT_CLASS}
        {...register(name)}
      />
      <FieldMessage name={name} hint={hint} />
    </div>
  )
}

export function SelectField({
  name,
  label,
  options,
}: {
  name: FieldPath<ProfileFormValues>
  label: string
  options: readonly { value: string; label: string }[]
}) {
  const { register, formState } = useFormContext<ProfileFormValues>()
  const error = getFieldError(formState.errors, name)
  return (
    <div>
      <FieldLabel name={name} label={label} />
      <select
        id={inputId(name)}
        aria-invalid={Boolean(error)}
        aria-describedby={error ? `${inputId(name)}-error` : undefined}
        className={INPUT_CLASS}
        {...register(name)}
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      <FieldMessage name={name} />
    </div>
  )
}

export function CheckboxField({
  name,
  label,
}: {
  name: FieldPath<ProfileFormValues>
  label: string
}) {
  const { register } = useFormContext<ProfileFormValues>()
  return (
    <label className="flex items-center gap-2 text-sm">
      <input type="checkbox" className="h-4 w-4" {...register(name)} />
      {label}
    </label>
  )
}

/** A string[] field edited as a comma-separated list (skills, achievements, links...). */
export function CommaListField({
  name,
  label,
  placeholder,
  hint,
}: {
  name: FieldPath<ProfileFormValues>
  label: string
  placeholder?: string
  hint?: string
}) {
  const { control, formState } = useFormContext<ProfileFormValues>()
  const error = getFieldError(formState.errors, name)
  return (
    <div>
      <FieldLabel name={name} label={label} />
      <Controller
        control={control}
        name={name}
        render={({ field }) => (
          <input
            id={inputId(name)}
            type="text"
            placeholder={placeholder}
            aria-invalid={Boolean(error)}
            aria-describedby={
              error ? `${inputId(name)}-error` : hint ? `${inputId(name)}-hint` : undefined
            }
            className={INPUT_CLASS}
            value={((field.value as string[] | undefined) ?? []).join(', ')}
            onChange={(event) =>
              field.onChange(
                event.target.value
                  .split(',')
                  .map((value) => value.trim())
                  .filter(Boolean),
              )
            }
            onBlur={field.onBlur}
            name={field.name}
            ref={field.ref}
          />
        )}
      />
      <FieldMessage name={name} hint={hint ?? 'Séparer les valeurs par une virgule.'} />
    </div>
  )
}

export function ItemActions({ onRemove, label }: { onRemove: () => void; label: string }) {
  return (
    <button
      type="button"
      onClick={onRemove}
      className="rounded border border-slate-300 px-3 py-1.5 text-sm font-medium text-red-700"
    >
      {label}
    </button>
  )
}

export function AddButton({ onClick, label }: { onClick: () => void; label: string }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="rounded border border-slate-300 px-3 py-1.5 text-sm font-medium"
    >
      {label}
    </button>
  )
}
