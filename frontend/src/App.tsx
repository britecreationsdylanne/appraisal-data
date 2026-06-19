import { Navigate, Route, Routes } from "react-router-dom";
import Shell from "./components/Shell";
import Chat from "./pages/Chat";
import Trends from "./pages/Trends";
import Reports from "./pages/Reports";
import ExportStudio from "./pages/ExportStudio";
import FactFinder from "./pages/FactFinder";

export default function App() {
  return (
    <Shell>
      <Routes>
        <Route path="/" element={<Navigate to="/chat" replace />} />
        <Route path="/chat" element={<Chat />} />
        <Route path="/trends" element={<Trends />} />
        <Route path="/reports" element={<Reports />} />
        <Route path="/fact-finder" element={<FactFinder />} />
        <Route path="/export" element={<ExportStudio />} />
      </Routes>
    </Shell>
  );
}
