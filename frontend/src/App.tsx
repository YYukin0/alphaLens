import { Routes, Route } from "react-router-dom";
import { Layout } from "@/components/Layout";
import CompaniesPage from "@/pages/CompaniesPage";
import CompanyProfilePage from "@/pages/CompanyProfilePage";
import FilingsPage from "@/pages/FilingsPage";
import FilingDetailPage from "@/pages/FilingDetailPage";
import MarketDataPage from "@/pages/MarketDataPage";

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<CompaniesPage />} />
        <Route path="/companies/:ticker" element={<CompanyProfilePage />} />
        <Route path="/filings" element={<FilingsPage />} />
        <Route path="/filings/:id" element={<FilingDetailPage />} />
        <Route path="/market" element={<MarketDataPage />} />
      </Routes>
    </Layout>
  );
}
