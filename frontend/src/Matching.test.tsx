import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import MatchingExplanationPanel from './components/MatchingExplanationPanel'
import type { MatchingResult } from './lib/matching'

const sampleMatching: MatchingResult = {
  total_score: 84,
  band: 'excellent',
  dimension_scores: {
    skills: { weight: 50, points: 37.5, max_points: 50, ratio: 0.75 },
    experience: { weight: 30, points: 27, max_points: 30, ratio: 0.9 },
    education: { weight: 20, points: 20, max_points: 20, ratio: 1.0 },
  },
  details: {
    matched_skills: [
      { name: 'Python', category: 'hard', matched: true },
      { name: 'FastAPI', category: 'hard', matched: true },
      { name: 'React', category: 'hard', matched: true },
    ],
    missing_skills: [
      { name: 'AWS Cloud', category: 'hard', matched: false },
    ],
    experience: {
      candidate_years: 1.8,
      required_years: 2.0,
      meets_requirement: false,
    },
    education: {
      candidate_level: 'bachelor',
      required_level: 'bachelor',
      candidate_rank: 2,
      required_rank: 2,
      meets_requirement: true,
    },
  },
  strengths: [
    '3 compétence(s) requise(s) validée(s) : Python, FastAPI, React.',
    'Niveau d’études requis validé (bachelor).',
  ],
  improvements: [
    '1 compétence(s) demandée(s) manquante(s) : AWS Cloud.',
    'Expérience inférieure à l’exigence (1.8 an(s) vs 2.0 an(s) demandé(s)).',
  ],
}

describe('US13 - Explication du matching (MatchingExplanationPanel)', () => {
  it('renders global score, band, dimensions, strengths and missing skills', () => {
    render(<MatchingExplanationPanel matching={sampleMatching} />)

    // Score & Band
    expect(screen.getByText('84%')).toBeInTheDocument()
    expect(screen.getByText('Excellente compatibilité')).toBeInTheDocument()

    // Dimensions
    expect(screen.getByText('Compétences')).toBeInTheDocument()
    expect(screen.getByText('37.5 / 50 pts')).toBeInTheDocument()
    expect(screen.getByText('Expérience')).toBeInTheDocument()
    expect(screen.getByText('27 / 30 pts')).toBeInTheDocument()
    expect(screen.getByText('Formation')).toBeInTheDocument()
    expect(screen.getByText('20 / 20 pts')).toBeInTheDocument()

    // Strengths (US13)
    expect(screen.getByText('Points forts')).toBeInTheDocument()
    expect(
      screen.getByText(/3 compétence\(s\) requise\(s\) validée\(s\)/)
    ).toBeInTheDocument()
    expect(screen.getByText('✓ Python')).toBeInTheDocument()
    expect(screen.getByText('✓ FastAPI')).toBeInTheDocument()
    expect(screen.getByText('✓ React')).toBeInTheDocument()

    // Missing skills & improvements (US13)
    expect(
      screen.getByText('Compétences manquantes & axes d’amélioration')
    ).toBeInTheDocument()
    expect(
      screen.getByText(/1 compétence\(s\) demandée\(s\) manquante\(s\)/)
    ).toBeInTheDocument()
    expect(screen.getByText('✕ AWS Cloud')).toBeInTheDocument()
  })
})
