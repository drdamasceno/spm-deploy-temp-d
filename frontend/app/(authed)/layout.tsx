import { Topbar } from "@/components/layout/topbar";
import { Nav } from "@/components/layout/nav";
import { FiltersProvider } from "@/lib/filters-context";

export default function AuthedLayout({ children }: { children: React.ReactNode }) {
  return (
    <FiltersProvider>
      <Topbar />
      <Nav />
      <main className="flex-1 overflow-auto bg-slate-50">{children}</main>
    </FiltersProvider>
  );
}
