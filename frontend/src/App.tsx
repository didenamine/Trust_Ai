import { Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import AccountPage from './pages/AccountPage'
import ATSAnalysisPage from './pages/ATSAnalysisPage'
import CVUploadPage from './pages/CVUploadPage'
import DashboardPage from './pages/DashboardPage'
import ForgotPasswordPage from './pages/ForgotPasswordPage'
import HomePage from './pages/HomePage'
import LoginPage from './pages/LoginPage'
import ManualProfilePage from './pages/ManualProfilePage'
import NotFoundPage from './pages/NotFoundPage'
import RegisterPage from './pages/RegisterPage'
import ResetPasswordPage from './pages/ResetPasswordPage'
import RequireAuth from './components/RequireAuth'
import AddOfferPage from './pages/AddOfferPage'
import MyOffersPage from './pages/MyOffersPage'
import SkillGapsPage from './pages/SkillGapsPage'

// Routing is owned by Ikram (React Router). Add new pages here.
export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<HomePage />} />
        <Route path="inscription" element={<RegisterPage />} />
        <Route path="connexion" element={<LoginPage />} />
        <Route path="mot-de-passe-oublie" element={<ForgotPasswordPage />} />
        <Route path="reinitialiser-mot-de-passe" element={<ResetPasswordPage />} />
        <Route element={<RequireAuth />}>
          <Route path="tableau-de-bord" element={<DashboardPage />} />
          <Route path="analyse-ats" element={<ATSAnalysisPage />} />
          <Route path="offres" element={<MyOffersPage />} />
          <Route path="offres/nouvelle" element={<AddOfferPage />} />
          <Route path="competences-manquantes" element={<SkillGapsPage />} />
          <Route path="compte" element={<AccountPage />} />
        </Route>
        <Route path="mon-cv" element={<CVUploadPage />} />
        <Route path="mon-profil" element={<ManualProfilePage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  )
}
