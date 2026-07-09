import React from "react";
import { useSelector } from "react-redux";
import AssistantPanel from "./components/AssistantPanel.jsx";
import InteractionForm from "./components/InteractionForm.jsx";

export default function App() {
  const { draft } = useSelector((state) => state.crm);

  return (
    <main className="app-shell">
      <InteractionForm draft={draft} />
      <AssistantPanel />
    </main>
  );
}
