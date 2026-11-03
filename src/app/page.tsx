import { LanguageProvider } from "@/components/dashboard/lang";
import Dashboard from "@/components/dashboard/dashboard";

export default function Home() {
  return (
    <LanguageProvider>
      <Dashboard />
    </LanguageProvider>
  );
}
