import { Routes, Route } from "react-router-dom";
import { Layout } from "@/components/Layout";
import LandingPage from "@/pages/LandingPage";
import CompaniesPage from "@/pages/CompaniesPage";
import CompanyProfilePage from "@/pages/CompanyProfilePage";
import FilingsPage from "@/pages/FilingsPage";
import FilingDetailPage from "@/pages/FilingDetailPage";
import MarketDataPage from "@/pages/MarketDataPage";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route element={<Layout />}>
        <Route path="/companies" element={<CompaniesPage />} />
        <Route path="/companies/:ticker" element={<CompanyProfilePage />} />
        <Route path="/filings" element={<FilingsPage />} />
        <Route path="/filings/:id" element={<FilingDetailPage />} />
        <Route path="/market" element={<MarketDataPage />} />
      </Route>
    </Routes>
  );
}
